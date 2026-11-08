const apiKeyEl = document.getElementById("apiKey");
const runBtn = document.getElementById("run");
const statusEl = document.getElementById("status");
const errorEl = document.getElementById("error");
const tiersList = document.getElementById("tiersList");
const tasksBox = document.getElementById("tasksBox");
const tasksList = document.getElementById("tasksList");
const summaryBox = document.getElementById("summaryBox");
const summaryBody = document.querySelector("#summaryTable tbody");
const pricingNote = document.getElementById("pricingNote");
const conclBox = document.getElementById("conclBox");
const conclusionsEl = document.getElementById("conclusions");
const detailsBox = document.getElementById("detailsBox");
const detailsEl = document.getElementById("details");

let meta = { tiers: [], tasks: [] };

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

function renderTiers(tiers) {
  tiersList.innerHTML = "";
  for (const t of tiers) {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${escapeHtml(t.title)}</strong> (` +
      `<code>${escapeHtml(t.tier)}</code>): ` +
      t.candidates.map((c) => `<code>${escapeHtml(c)}</code>`).join(" → ");
    tiersList.appendChild(li);
  }
}

function renderTasks(tasks) {
  tasksList.innerHTML = "";
  for (const t of tasks) {
    const li = document.createElement("li");
    li.innerHTML = `
      <strong>${escapeHtml(t.title)}</strong> <code>${escapeHtml(t.kind)}</code><br/>
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
      <td>${escapeHtml(row.tier_title || row.tier)}</td>
      <td><code>${escapeHtml(row.model_id || "—")}</code></td>
      <td>${scoreBadge(row.correct, row.total_tasks)}</td>
      <td>${escapeHtml(row.elapsed_sec)}</td>
      <td>${escapeHtml(row.total_tokens)}</td>
      <td>${escapeHtml(row.cost)}</td>
    `;
    summaryBody.appendChild(tr);
  }
  summaryBox.hidden = false;
}

function appendCell(cell) {
  detailsBox.hidden = false;
  let block = document.getElementById(`tier-${cell.tier}`);
  if (!block) {
    block = document.createElement("article");
    block.className = "cell-block";
    block.id = `tier-${cell.tier}`;
    block.innerHTML = `
      <h3>${escapeHtml(cell.tier_title)} · <code>${escapeHtml(cell.model_id || "—")}</code>
        <span class="live-score"></span></h3>
      <div class="runs"></div>
    `;
    detailsEl.appendChild(block);
  }
  const mark = cell.correct ? "ok" : "bad";
  const label = cell.correct ? "верно" : "неверно";
  const d = document.createElement("details");
  d.className = "run";
  d.open = true;
  d.innerHTML = `
    <summary>
      <span class="badge ${mark}">${label}</span>
      ${escapeHtml(cell.task_title)} —
      tokens=${cell.total_tokens}, cost=${escapeHtml(cell.cost ?? "—")},
      ${cell.elapsed_sec}s
    </summary>
    <p class="meta">
      got=<code>${escapeHtml(cell.check?.normalized ?? "—")}</code>,
      expected=<code>${escapeHtml(cell.check?.expected ?? cell.expected)}</code>,
      returned=<code>${escapeHtml(cell.model_returned || "—")}</code>
    </p>
    <pre>${escapeHtml(cell.content || cell.error || "")}</pre>
  `;
  block.querySelector(".runs").appendChild(d);
}

function renderFinal(data) {
  renderTasks(data.tasks);
  renderSummary(data.summary);
  pricingNote.textContent =
    "* " + (data.pricing_note || "стоимость в условных единицах каталога Wormsoft");

  conclusionsEl.innerHTML = "";
  for (const line of data.conclusions) {
    const li = document.createElement("li");
    li.textContent = line;
    conclusionsEl.appendChild(li);
  }
  conclBox.hidden = false;

  detailsEl.innerHTML = "";
  for (const m of data.models) {
    const cells = data.cells.filter((c) => c.tier === m.tier);
    const correct = cells.filter((c) => c.correct).length;
    const block = document.createElement("article");
    block.className = "cell-block";
    const notes = (m.fallback_notes || []).join(" · ") || "—";
    block.innerHTML = `
      <h3>${escapeHtml(m.title)} · <code>${escapeHtml(m.model_id || "—")}</code>
        ${scoreBadge(correct, cells.length)}</h3>
      <p class="meta">fallback: ${escapeHtml(notes)}</p>
    `;
    for (const c of cells) {
      const mark = c.correct ? "ok" : "bad";
      const label = c.correct ? "верно" : "неверно";
      const d = document.createElement("details");
      d.className = "run";
      d.innerHTML = `
        <summary>
          <span class="badge ${mark}">${label}</span>
          ${escapeHtml(c.task_title)} —
          tokens=${c.total_tokens}, cost=${escapeHtml(c.cost ?? "—")}, ${c.elapsed_sec}s
        </summary>
        <pre>${escapeHtml(c.content || c.error || "")}</pre>
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
    renderTiers(data.tiers || []);
    if (data.tasks) renderTasks(data.tasks);
    statusEl.hidden = false;
    statusEl.textContent =
      `Ожидается ~${data.calls_estimate || 18}+ запросов (probe + задачи). При 429 — пауза.`;
  } catch {
    /* ignore */
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
        if (ev.type === "progress" || ev.type === "rate_limit") {
          statusEl.textContent = ev.message || "";
        } else if (ev.type === "cell") {
          appendCell(ev.cell);
          if (ev.summary) renderSummary(ev.summary);
          statusEl.textContent = `[${ev.done}/${ev.total}] ${ev.cell.tier} × ${ev.cell.task_title}`;
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
