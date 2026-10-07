(() => {
  const phrase = document.currentScript.dataset.phrase;

  const userIdInput = document.getElementById("user-id");
  const typeField = document.getElementById("type-field");
  const submitBtn = document.getElementById("submit-btn");
  const statusEl = document.getElementById("status");
  const counterEl = document.getElementById("attempt-count");

  let attemptCount = 0;
  let startTime = null;     // performance.now() у момент першого keydown спроби
  let events = [];          // [{key, type, t}]
  let backspaceCount = 0;
  let errorCount = 0;
  let lastGoodPrefixLen = 0; // для підрахунку "помилок" — відхилень від очікуваного префікса

  function genId() {
    return Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
  }

  function resetAttemptState() {
    startTime = null;
    events = [];
    backspaceCount = 0;
    errorCount = 0;
    lastGoodPrefixLen = 0;
  }

  function setStatus(text, kind) {
    statusEl.textContent = text;
    statusEl.className = "status" + (kind ? " " + kind : "");
  }

  typeField.addEventListener("keydown", (e) => {
    if (startTime === null) {
      startTime = performance.now();
    }
    const t = performance.now() - startTime;

    if (e.key === "Backspace") {
      backspaceCount += 1;
    }

    // Записуємо лише друковані символи та backspace, ігноруємо Shift/Tab тощо,
    // щоб не забруднювати дані службовими клавішами.
    if (e.key.length === 1 || e.key === "Backspace") {
      events.push({ key: e.key, type: "down", t });
    }
  });

  typeField.addEventListener("keyup", (e) => {
    if (startTime === null) return;
    const t = performance.now() - startTime;
    if (e.key.length === 1 || e.key === "Backspace") {
      events.push({ key: e.key, type: "up", t });
    }
  });

  typeField.addEventListener("input", () => {
    const value = typeField.value;

    // Підрахунок "помилок": скільки разів довжина коректного префікса
    // (порівняно з еталонною фразою) зменшувалася або переставала зростати монотонно.
    let goodPrefixLen = 0;
    while (goodPrefixLen < value.length && goodPrefixLen < phrase.length &&
           value[goodPrefixLen] === phrase[goodPrefixLen]) {
      goodPrefixLen += 1;
    }
    if (goodPrefixLen < lastGoodPrefixLen) {
      errorCount += 1;
    }
    lastGoodPrefixLen = goodPrefixLen;

    submitBtn.disabled = value !== phrase;
    setStatus(value === phrase ? "Фразу набрано правильно, можна зберегти." : "", "");
  });

  submitBtn.addEventListener("click", async () => {
    const userId = userIdInput.value.trim();
    if (!userId) {
      setStatus("Вкажіть ідентифікатор учасника.", "error");
      userIdInput.focus();
      return;
    }
    if (events.length === 0) {
      setStatus("Немає зафіксованих подій набору.", "error");
      return;
    }

    const payload = {
      user_id: userId,
      attempt_id: genId(),
      backspace_count: backspaceCount,
      error_count: errorCount,
      events,
    };

    submitBtn.disabled = true;
    setStatus("Збереження…", "");

    try {
      const res = await fetch("/collect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (data.ok) {
        attemptCount += 1;
        counterEl.textContent = String(attemptCount);
        setStatus("Спробу збережено (" + data.saved_events + " подій).", "ok");
      } else {
        setStatus("Помилка: " + (data.error || "невідома"), "error");
      }
    } catch (err) {
      setStatus("Помилка з'єднання із сервером.", "error");
    }

    typeField.value = "";
    resetAttemptState();
    typeField.focus();
  });
})();