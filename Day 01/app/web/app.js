const apiKeyEl = document.getElementById("apiKey");
const promptEl = document.getElementById("prompt");
const sendBtn = document.getElementById("send");
const outEl = document.getElementById("out");
const answerEl = document.getElementById("answer");
const errorEl = document.getElementById("error");

async function send() {
  const apiKey = apiKeyEl.value.trim();
  const prompt = promptEl.value.trim() || "Скажи привет в одном предложении.";

  errorEl.hidden = true;
  outEl.hidden = true;
  sendBtn.disabled = true;
  sendBtn.textContent = "Ждём ответ…";

  try {
    if (!apiKey) throw new Error("Введите API key.");

    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ apiKey, prompt }),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || `HTTP ${res.status}`);
    }

    answerEl.textContent = data.content;
    outEl.hidden = false;
  } catch (err) {
    errorEl.textContent = err.message || String(err);
    errorEl.hidden = false;
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = "Отправить";
  }
}

sendBtn.addEventListener("click", send);
promptEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) send();
});
