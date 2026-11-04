const apiKeyEl = document.getElementById("apiKey");
const runBtn = document.getElementById("run");
const statusEl = document.getElementById("status");
const errorEl = document.getElementById("error");
const modelLabel = document.getElementById("modelLabel");
const tasksBox = document.getElementById("tasksBox");
const tasksList = document.getElementById("tasksList");
const summaryBox = document.getElementById("summaryBox");
const summaryBody = document.querySelector("#summaryTable tbody");
const conclBox = document.getElementById("conclBox");
const conclusionsEl = document.getElementById("conclusions");
const detailsBox = document.getElementById("detailsBox");
const detailsEl = document.getElementById("details");

let meta = { strategies: [], reasoning_modes: [], tasks: [] };
let liveCells = [];

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function scoreBadge(correct, total) {
  const ok = correct === total && total > 0;
  return `<span class="badge ${ok ? "ok" : "bad"}">${correct}/${total}</span>`;
}

function renderTasks(tasks) {
  tasksList.innerHTML = "";
  for (const t of tasks) {
    const li = document.createElement("li");
    li.innerHTML = `
      <strong><span class="kind">${escapeHtml(t.kind)}</span> — ${escapeHtml(t.title)}</strong>
      ${escapeHtml(t.prompt)}
      <div class="meta">Эталон: <code>${escapeHtml(t.answer)}</code></div>
    `;
    tasksList.appendChild(li);
  }
  tasksBox.hidden = false;
}

function renderSummary(summary) {
  summaryBody.innerHTML = "";
  for (const row of summary) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(row.strategy_title)}</td>
      <td><code>${escapeHtml(row.reasoning)}</code></td>
      <td>${scoreBadge(row.correct, row.total_tasks)}</td>
      <td>${escapeHtml(row.total_tokens)}</td>
      <td>${escapeHtml(row.elapsed_sec)}</td>
    `;
    summaryBody.appendChild(tr);
  }
  summaryBox.hidden = false;
}

function cellHtml(c) {
  const mark = c.correct ? "ok" : "bad";
  const label = c.correct ? "верно" : "неверно";
  return `<details class="run" open>
    <summary>
      <span class="badge ${mark}">${label}</span>
      ${escapeHtml(c.task_title)} —
      got=<code>${escapeHtml(c.check?.normalized ?? "—")}</code>,
      expected=<code>${escapeHtml(c.check?.expected ?? c.expected)}</code>,
      tokens=${c.total_tokens}, ${c.elapsed_sec}s
    </summary>
    <p class="meta">
      ${escapeHtml(c.strategy)} × ${escapeHtml(c.reasoning)};
      model=${escapeHtml(c.model || "—")};
      reasoning_field=${c.has_reasoning ? "yes" : "no"};
      extracted=${escapeHtml(c.check?.extracted ?? "—")}
    </p>
    <pre>${escapeHtml(c.content || c.error || "")}</pre>
  </details>`;
}

function ensureDetailsScaffold() {
  if (!detailsEl.dataset.ready) {
    detailsEl.innerHTML = "";
    for (const s of meta.strategies) {
      for (const r of meta.reasoning_modes) {
        const block = document.createElement("article");
        block.className = "cell-block";
        block.id = `block-${s.id}-${r.id}`;
        block.innerHTML = `
          <h3>${escapeHtml(s.title)} × <code>${escapeHtml(r.id)}</code>
            <span class="live-score"></span></h3>
          <p class="meta">${escapeHtml(r.title)}</p>
          <div class="runs"></div>
        `;
        detailsEl.appendChild(block);
      }
    }
    detailsEl.dataset.ready = "1";
  }
  detailsBox.hidden = false;
}

function appendLiveCell(cell) {
  ensureDetailsScaffold();
  const block = document.getElementById(`block-${cell.strategy}-${cell.reasoning}`);
  if (!block) return;
  const runs = block.querySelector(".runs");
  const wrap = document.createElement("div");
  wrap.innerHTML = cellHtml(cell);
  runs.appendChild(wrap.firstElementChild);

  const group = liveCells.filter(
    (c) => c.strategy === cell.strategy && c.reasoning === cell.reasoning
  );
  const correct = group.filter((c) => c.correct).length;
  block.querySelector(".live-score").innerHTML = scoreBadge(correct, group.length);
}

function renderFinal(data) {
  renderTasks(data.tasks);
  renderSummary(data.summary);

  conclusionsEl.innerHTML = "";
  for (const line of data.conclusions) {
    const li = document.createElement("li");
    li.textContent = line;
    conclusionsEl.appendChild(li);
  }
  conclBox.hidden = false;

  // финальная перерисовка деталей (без open у всех)
  detailsEl.innerHTML = "";
  detailsEl.dataset.ready = "";
  for (const s of data.strategies) {
    for (const r of data.reasoning_modes) {
      const cells = data.cells.filter(
        (c) => c.strategy === s.id && c.reasoning === r.id
      );
      const block = document.createElement("article");
      block.className = "cell-block";
      const correct = cells.filter((c) => c.correct).length;
      block.innerHTML = `
        <h3>${escapeHtml(s.title)} × <code>${escapeHtml(r.id)}</code>
          ${scoreBadge(correct, cells.length)}</h3>
        <p class="meta">${escapeHtml(r.title)}</p>
        ${cells
          .map((c) => cellHtml(c).replace(' open>', ">"))
          .join("")}
      `;
      detailsEl.appendChild(block);
    }
  }
  detailsBox.hidden = false;
}

async function loadMeta() {
  try {
    const res = await fetch("/api/meta", { cache: "no-store" });
    const data = await res.json();
    meta = data;
    modelLabel.textContent = data.model || "wormsoft/agent/low";
    if (data.tasks) renderTasks(data.tasks);
    if (data.calls_estimate) {
      statusEl.hidden = false;
      statusEl.textContent =
        `Ожидается около ${data.calls_estimate} запросов к API. При 429 будет пауза автоматически.`;
    }
  } catch {
    modelLabel.textContent = "wormsoft/agent/low";
  }
}

async function runExperiment() {
  errorEl.hidden = true;
  statusEl.hidden = false;
  statusEl.textContent = "Старт прогона…";
  runBtn.disabled = true;
  summaryBox.hidden = true;
  conclBox.hidden = true;
  detailsBox.hidden = true;
  detailsEl.innerHTML = "";
  detailsEl.dataset.ready = "";
  liveCells = [];

  try {
    const apiKey = apiKeyEl.value.trim();
    if (!apiKey) throw new Error("Введите API key.");

    const res = await fetch("/api/experiment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      body: JSON.stringify({ apiKey }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || `HTTP ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.trim()) continue;
        let ev;
        try {
          ev = JSON.parse(line);
        } catch {
          continue;
        }

        if (ev.type === "progress") {
          statusEl.textContent = ev.message || `[${ev.done}/${ev.total}] …`;
        } else if (ev.type === "rate_limit") {
          statusEl.textContent = ev.message || `Rate limit: ждём ${ev.wait_sec} с…`;
        } else if (ev.type === "cell") {
          liveCells.push(ev.cell);
          appendLiveCell(ev.cell);
          if (ev.summary) renderSummary(ev.summary);
          const mark = ev.cell.correct ? "✓" : "✗";
          statusEl.textContent =
            `[${ev.done}/${ev.total}] ${mark} ${ev.cell.task_title} ` +
            `(${ev.cell.strategy} × ${ev.cell.reasoning})`;
        } else if (ev.type === "done") {
          renderFinal(ev.result);
          statusEl.textContent =
            "Готово. Отчёт сохранён в experiment_report.md / experiment_raw.json";
        } else if (ev.type === "error") {
          throw new Error(ev.error || "Ошибка эксперимента");
        }
      }
    }
  } catch (err) {
    errorEl.textContent = err.message || String(err);
    errorEl.hidden = false;
    statusEl.hidden = true;
  } finally {
    runBtn.disabled = false;
  }
}

runBtn.addEventListener("click", runExperiment);
loadMeta();
