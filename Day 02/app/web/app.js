const apiKeyEl = document.getElementById("apiKey");
const promptEl = document.getElementById("prompt");
const runsEl = document.getElementById("runs");
const runBtn = document.getElementById("run");
const statusEl = document.getElementById("status");
const errorEl = document.getElementById("error");
const modelLabel = document.getElementById("modelLabel");
const usedPromptBox = document.getElementById("usedPromptBox");
const usedPromptEl = document.getElementById("usedPrompt");
const compareBox = document.getElementById("compareBox");
const compareBody = document.querySelector("#compareTable tbody");
const detailsBox = document.getElementById("detailsBox");
const detailsEl = document.getElementById("details");
const conclBox = document.getElementById("conclBox");
const conclusionsEl = document.getElementById("conclusions");

let metaLoaded = false;

function score(n, total) {
  const ok = n === total && total > 0;
  return `<span class="badge ${ok ? "ok" : "bad"}">${n}/${total}</span>`;
}

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function stripMd(s) {
  return String(s ?? "").replaceAll("**", "");
}

function render(data) {
  const runs = data.runs;

  usedPromptEl.textContent = data.base_prompt || "";
  usedPromptBox.hidden = false;

  compareBody.innerHTML = "";
  for (const row of data.comparison) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(row.title)}</td>
      <td>${score(row.api_ok, runs)}</td>
      <td>${escapeHtml(row.avg_chars)}</td>
      <td>${score(row.json_parse, runs)}</td>
      <td>${score(row.schema_ok, runs)}</td>
      <td>${escapeHtml(row.breaks)}</td>
    `;
    compareBody.appendChild(tr);
  }
  compareBox.hidden = false;

  detailsEl.innerHTML = "";
  for (const row of data.comparison) {
    const block = document.createElement("article");
    block.className = "variant";
    const extras = row.extra && Object.keys(row.extra).length
      ? `<pre>${escapeHtml(JSON.stringify(row.extra, null, 2))}</pre>`
      : `<p class="meta">Без доп. параметров API</p>`;

    const runsHtml = row.runs
      .map((r, i) => {
        if (!r.ok) {
          return `<details class="run"><summary>Прогон ${i + 1}: ошибка</summary>
            <pre>${escapeHtml(r.error)}</pre></details>`;
        }
        return `<details class="run">
          <summary>
            Прогон ${i + 1}: ${r.chars} симв., finish=${escapeHtml(r.finish_reason)},
            JSON ${r.json_parse_ok ? "да" : "нет"},
            схема ${r.schema_ok ? "да" : "нет"}
          </summary>
          <p class="meta">
            model=${escapeHtml(r.model)}; ${r.elapsed_sec}s;
            ${escapeHtml(r.json_parse_note)}; ${escapeHtml(r.schema_note)}
          </p>
          <pre>${escapeHtml(r.content)}</pre>
        </details>`;
      })
      .join("");

    block.innerHTML = `
      <h3>${escapeHtml(row.title)} <code>${escapeHtml(row.id)}</code></h3>
      ${extras}
      ${runsHtml}
    `;
    detailsEl.appendChild(block);
  }
  detailsBox.hidden = false;

  conclusionsEl.innerHTML = "";
  for (const line of data.conclusions) {
    const li = document.createElement("li");
    li.textContent = stripMd(line);
    conclusionsEl.appendChild(li);
  }
  conclBox.hidden = false;
}

async function loadMeta() {
  try {
    const res = await fetch("/api/meta", { cache: "no-store" });
    const data = await res.json();
    modelLabel.textContent = data.model || "wormsoft/agent/low";
    if (data.default_runs) runsEl.value = String(data.default_runs);
    // Не затираем текст, который пользователь уже успел ввести.
    if (data.base_prompt && !promptEl.dataset.touched) {
      promptEl.value = data.base_prompt;
    }
  } catch {
    modelLabel.textContent = "wormsoft/agent/low";
  } finally {
    metaLoaded = true;
  }
}

promptEl.addEventListener("input", () => {
  promptEl.dataset.touched = "1";
});

async function runExperiment() {
  errorEl.hidden = true;
  statusEl.hidden = false;
  statusEl.textContent =
    "Идёт прогон… это может занять пару минут (несколько запросов к API).";
  runBtn.disabled = true;

  usedPromptBox.hidden = true;
  compareBox.hidden = true;
  detailsBox.hidden = true;
  conclBox.hidden = true;

  try {
    const apiKey = apiKeyEl.value.trim();
    if (!apiKey) throw new Error("Введите API key.");
    const prompt = promptEl.value.trim();
    if (!prompt) throw new Error("Введите текст запроса.");
    const runs = Number(runsEl.value) || 3;

    const body = { apiKey, prompt, runs };
    console.log("Sending experiment payload:", { runs, prompt });

    const res = await fetch("/api/experiment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);

    if (data.base_prompt && data.base_prompt.trim() !== prompt) {
      console.warn("Server used different prompt:", data.base_prompt);
    }

    render(data);
    statusEl.textContent = `Готово: ${data.comparison.length} вариантов × ${data.runs} прогон(ов). Отчёт сохранён в experiment_control_report.md`;
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
