const apiKeyEl = document.getElementById("apiKey");
const modelEl = document.getElementById("model");
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

let meta = { tasks: [], temperatures: [0, 0.7, 1.2], runs: 5 };

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function scoreBadge(correct, total) {
  if (correct == null) return "—";
  const ok = correct === total && total > 0;
  return `<span class="badge ${ok ? "ok" : "bad"}">${correct}/${total}</span>`;
}

function renderTasks(tasks) {
  tasksList.innerHTML = "";
  for (const t of tasks) {
    const li = document.createElement("li");
    const ans =
      t.answer != null
        ? `<div class="meta">Эталон: <code>${escapeHtml(t.answer)}</code></div>`
        : `<div class="meta">Эталона нет — оцениваем разнообразие и формат списка</div>`;
    li.innerHTML = `
      <strong><span class="kind">${escapeHtml(t.kind)}</span> — ${escapeHtml(t.title)}</strong>
      ${escapeHtml(t.prompt)}
      ${ans}
    `;
    tasksList.appendChild(li);
  }
  tasksBox.hidden = false;
}

function renderSummary(summary) {
  summaryBody.innerHTML = "";
  for (const row of summary) {
    const tr = document.createElement("tr");
    const jac =
      row.avg_pairwise_jaccard == null ? "—" : row.avg_pairwise_jaccard;
    tr.innerHTML = `
      <td>${escapeHtml(row.task_title)}</td>
      <td><code>${escapeHtml(row.temperature)}</code></td>
      <td>${scoreBadge(row.correct, row.runs)}</td>
      <td>${escapeHtml(row.format_broken)}/${escapeHtml(row.runs)}</td>
      <td>${escapeHtml(row.unique_count)}/${escapeHtml(row.runs)}</td>
      <td>${escapeHtml(jac)}</td>
      <td>${escapeHtml(row.total_tokens)}</td>
      <td>${escapeHtml(row.elapsed_sec)}</td>
    `;
    summaryBody.appendChild(tr);
  }
  summaryBox.hidden = false;
}

function blockId(taskId, temp) {
  return `block-${taskId}-${String(temp).replace(".", "_")}`;
}

function ensureScaffold() {
  if (detailsEl.dataset.ready) return;
  detailsEl.innerHTML = "";
  for (const temp of meta.temperatures) {
    for (const t of meta.tasks) {
      const block = document.createElement("article");
      block.className = "cell-block";
      block.id = blockId(t.id, temp);
      block.innerHTML = `
        <h3>${escapeHtml(t.title)} × <code>temp=${escapeHtml(temp)}</code>
          <span class="live-score"></span></h3>
        <div class="runs"></div>
      `;
      detailsEl.appendChild(block);
    }
  }
  detailsEl.dataset.ready = "1";
  detailsBox.hidden = false;
}

function appendCell(cell) {
  ensureScaffold();
  const block = document.getElementById(blockId(cell.task_id, cell.temperature));
  if (!block) return;
  const mark =
    cell.task_kind === "exact"
      ? cell.correct
        ? "ok"
        : "bad"
      : cell.format_ok
        ? "ok"
        : "bad";
  const label =
    cell.task_kind === "exact"
      ? cell.correct
        ? "верно"
        : "неверно"
      : cell.format_ok
        ? "формат ок"
        : "формат↓";

  const details = document.createElement("details");
  details.className = "run";
  details.open = true;
  const body =
    cell.content ||
    cell.empty_note ||
    cell.error ||
    (cell.reasoning
      ? `[reasoning only]\n${cell.reasoning}`
      : "(пустой ответ)");
  details.innerHTML = `
    <summary>
      <span class="badge ${mark}">${label}</span>
      run ${escapeHtml(cell.run)} —
      model=${escapeHtml(cell.model || "—")},
      finish=${escapeHtml(cell.finish_reason || "—")},
      tokens=${cell.total_tokens}, ${cell.elapsed_sec}s
    </summary>
    <pre>${escapeHtml(body)}</pre>
  `;
  block.querySelector(".runs").appendChild(details);
}

function renderFinal(data) {
  meta.tasks = data.tasks;
  meta.temperatures = data.temperatures;
  renderTasks(data.tasks);
  renderSummary(data.summary);

  conclusionsEl.innerHTML = "";
  for (const line of data.conclusions) {
    const li = document.createElement("li");
    li.textContent = line;
    conclusionsEl.appendChild(li);
  }
  conclBox.hidden = false;

  detailsEl.innerHTML = "";
  detailsEl.dataset.ready = "";
  for (const row of data.summary) {
    const cells = data.cells.filter(
      (c) => c.task_id === row.task_id && c.temperature === row.temperature
    );
    const block = document.createElement("article");
    block.className = "cell-block";
    const score =
      row.task_kind === "exact"
        ? scoreBadge(row.correct, row.runs)
        : `<span class="badge ${row.format_broken ? "bad" : "ok"}">uniq ${row.unique_count}/${row.runs}</span>`;
    block.innerHTML = `
      <h3>${escapeHtml(row.task_title)} × <code>temp=${escapeHtml(row.temperature)}</code>
        ${score}</h3>
      <p class="meta">
        format_broken=${row.format_broken}/${row.runs};
        identical=${row.all_identical ? "yes" : "no"};
        jaccard=${row.avg_pairwise_jaccard ?? "—"}
      </p>
    `;
    for (const c of cells) {
      const mark =
        c.task_kind === "exact"
          ? c.correct
            ? "ok"
            : "bad"
          : c.format_ok
            ? "ok"
            : "bad";
      const label =
        c.task_kind === "exact"
          ? c.correct
            ? "верно"
            : "неверно"
          : c.format_ok
            ? "формат ок"
            : "формат↓";
      const body =
        c.content ||
        c.empty_note ||
        c.error ||
        (c.reasoning ? `[reasoning only]\n${c.reasoning}` : "(пустой ответ)");
      const d = document.createElement("details");
      d.className = "run";
      d.innerHTML = `
        <summary>
          <span class="badge ${mark}">${label}</span>
          run ${escapeHtml(c.run)} —
          model=${escapeHtml(c.model || "—")},
          finish=${escapeHtml(c.finish_reason || "—")},
          <code>${escapeHtml(String(c.signature || "").slice(0, 60))}</code>
        </summary>
        <pre>${escapeHtml(body)}</pre>
      `;
      block.appendChild(d);
    }
    detailsEl.appendChild(block);
  }
  detailsBox.hidden = false;
}

async function loadMeta() {
  try {
    const res = await fetch("/api/meta", { cache: "no-store" });
    const data = await res.json();
    meta = data;
    modelLabel.textContent = data.model || "google/gemma4:31b";
    modelEl.innerHTML = "";
    const choices = data.model_choices || [
      { id: data.model || "google/gemma4:31b", label: data.model || "google/gemma4:31b" },
    ];
    for (const m of choices) {
      const opt = document.createElement("option");
      opt.value = m.id;
      opt.textContent = m.label || m.id;
      if (m.id === data.model) opt.selected = true;
      modelEl.appendChild(opt);
    }
    if (data.tasks) renderTasks(data.tasks);
    statusEl.hidden = false;
    statusEl.textContent = `Ожидается ${data.calls_estimate || 30} запросов. При 429 — автопауза.`;
  } catch {
    modelLabel.textContent = "google/gemma4:31b";
  }
}

async function runExperiment() {
  errorEl.hidden = true;
  statusEl.hidden = false;
  statusEl.textContent = "Старт…";
  runBtn.disabled = true;
  summaryBox.hidden = true;
  conclBox.hidden = true;
  detailsBox.hidden = true;
  detailsEl.innerHTML = "";
  detailsEl.dataset.ready = "";

  try {
    const apiKey = apiKeyEl.value.trim();
    if (!apiKey) throw new Error("Введите API key.");
    const model = modelEl.value.trim();

    const res = await fetch("/api/experiment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      body: JSON.stringify({ apiKey, model }),
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
          statusEl.textContent = ev.message || "";
        } else if (ev.type === "rate_limit" || ev.type === "retry_empty") {
          statusEl.textContent = ev.message || `Ждём ${ev.wait_sec || ""}…`;
        } else if (ev.type === "cell") {
          appendCell(ev.cell);
          if (ev.summary) renderSummary(ev.summary);
          statusEl.textContent = ev.message || `[${ev.done}/${ev.total}] готово`;
        } else if (ev.type === "done") {
          renderFinal(ev.result);
          statusEl.textContent =
            "Готово. Отчёт: experiment_report.md / experiment_raw.json";
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
