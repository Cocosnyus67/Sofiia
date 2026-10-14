(() => {
  const phrase = document.currentScript.dataset.phrase;

  const userIdInput = document.getElementById("user-id");
  const typeField = document.getElementById("type-field");
  const submitBtn = document.getElementById("submit-btn");
  const statusEl = document.getElementById("status");
  const counterEl = document.getElementById("attempt-count");

  const isTracked = (e) =>
    e.key.length === 1 || e.key === "Backspace" || e.key === "Shift";

  let attemptCount = 0;
  let startTime = null;
  let events = [];
  let pressed = new Set();
  let backspaceCount = 0;
  let errorCount = 0;
  let lastGoodPrefixLen = 0;

  function genId() {
    return Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
  }

  let sessionId;
  try {
    sessionId = sessionStorage.getItem("session_id");
    if (!sessionId) {
      sessionId = genId();
      sessionStorage.setItem("session_id", sessionId);
    }
  } catch (_) {
    sessionId = genId();
  }

  function resetAttemptState() {
    startTime = null;
    events = [];
    pressed = new Set();
    backspaceCount = 0;
    errorCount = 0;
    lastGoodPrefixLen = 0;
  }

  function setStatus(text, kind) {
    statusEl.textContent = text;
    statusEl.className = "status" + (kind ? " " + kind : "");
  }

  const isCombo = (e) => e.ctrlKey || e.altKey || e.metaKey;

  typeField.addEventListener("keydown", (e) => {
    if (e.repeat || isCombo(e) || !isTracked(e)) return;   // автоповтор ігноруємо

    if (startTime === null) startTime = performance.now();
    const t = performance.now() - startTime;

    if (e.key === "Backspace") backspaceCount += 1;

    pressed.add(e.code);
    events.push({ key: e.key, code: e.code, type: "down", t });
  });

  typeField.addEventListener("keyup", (e) => {
    if (startTime === null || !pressed.has(e.code)) return;
    pressed.delete(e.code);

    const t = performance.now() - startTime;
    events.push({ key: e.key, code: e.code, type: "up", t });
  });

  ["paste", "drop", "cut", "copy", "contextmenu"].forEach((name) =>
    typeField.addEventListener(name, (e) => {
      e.preventDefault();
      if (name === "paste" || name === "drop") {
        setStatus("Вставка заборонена: набери фразу вручну.", "error");
      }
    })
  );

  typeField.addEventListener("input", () => {
    const value = typeField.value;

    if (value === "") {
      resetAttemptState();
      submitBtn.disabled = true;
      setStatus("", "");
      return;
    }

    let goodPrefixLen = 0;
    while (
      goodPrefixLen < value.length &&
      goodPrefixLen < phrase.length &&
      value[goodPrefixLen] === phrase[goodPrefixLen]
    ) {
      goodPrefixLen += 1;
    }
    if (goodPrefixLen < lastGoodPrefixLen) errorCount += 1;
    lastGoodPrefixLen = goodPrefixLen;

    submitBtn.disabled = value !== phrase;
    setStatus(value === phrase ? "Фразу набрано правильно, можна зберегти." : "", "");
  });

  submitBtn.addEventListener("click", async () => {
    const userId = userIdInput.value.trim();
    if (!/^[A-Za-z0-9_-]{1,32}$/.test(userId)) {
      setStatus("Ідентифікатор: лише латиниця, цифри, _ або - (наприклад u01).", "error");
      userIdInput.focus();
      return;
    }
    if (events.length === 0) {
      setStatus("Немає зафіксованих подій набору.", "error");
      return;
    }
    if (pressed.size > 0) {
      setStatus("Відпусти всі клавіші та натисни ще раз.", "error");
      return;
    }

    const payload = {
      user_id: userId,
      session_id: sessionId,
      attempt_id: genId(),
      user_agent: navigator.userAgent,
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

      let data = null;
      try {
        data = await res.json();
      } catch (_) {}

      if (res.ok && data && data.ok) {
        attemptCount += 1;
        counterEl.textContent = String(attemptCount);
        setStatus("Спробу збережено (" + data.saved_events + " подій).", "ok");
      } else {
        setStatus("Помилка: " + ((data && data.error) || "сервер повернув " + res.status), "error");
      }
    } catch (err) {
      setStatus("Помилка з'єднання із сервером.", "error");
    }

    typeField.value = "";
    resetAttemptState();
    typeField.focus();
  });
})();