(() => {
  const mode = document.body.dataset.mode;

  const form = document.getElementById("form");
  const userInput = document.getElementById("username");
  const passInput = document.getElementById("password");
  const statusEl = document.getElementById("status");

  let startTime = null;
  let events = [];
  let pressed = new Set();

  function isTracked(e) {
    return e.key.length === 1 || e.key === "Backspace" || e.key === "Shift";
  }

  function resetAttempt() {
    startTime = null;
    events = [];
    pressed = new Set();
  }

  function setStatus(text, kind) {
    statusEl.textContent = text;
    statusEl.className = "status" + (kind ? " " + kind : "");
  }

  passInput.addEventListener("keydown", (e) => {
    if (e.repeat) return;
    if (e.ctrlKey || e.altKey || e.metaKey) return;
    if (!isTracked(e)) return;

    if (startTime === null) startTime = performance.now();
    pressed.add(e.code);
    events.push({ key: e.key, code: e.code, type: "down", t: performance.now() - startTime });
  });

  passInput.addEventListener("keyup", (e) => {
    if (startTime === null || !pressed.has(e.code)) return;
    pressed.delete(e.code);
    events.push({ key: e.key, code: e.code, type: "up", t: performance.now() - startTime });
  });

  passInput.addEventListener("input", () => {
    if (passInput.value === "") {
      resetAttempt();
      setStatus("", "");
    }
  });

  ["paste", "drop", "cut", "copy", "contextmenu"].forEach((name) => {
    passInput.addEventListener(name, (e) => {
      e.preventDefault();
      if (name === "paste" || name === "drop") {
        setStatus("Вставка заборонена: набери пароль вручну.", "error");
      }
    });
  });

  function showResult(data) {
    const box = document.getElementById("result");
    const title = document.getElementById("result-title");
    const reason = document.getElementById("result-reason");
    const score = document.getElementById("result-score");

    box.hidden = false;
    box.className = "result " + (data.access ? "ok" : "bad");
    title.textContent = data.access ? "Доступ дозволено" : "Доступ відхилено";
    reason.textContent = data.reason;

    if (data.distance !== undefined) {
      score.textContent = "Відстань до твого профілю: " + data.distance +
        " (поріг: " + data.threshold + "). Менше за поріг означає «свій».";
    } else {
      score.textContent = "";
    }
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (events.length === 0) {
      setStatus("Набери пароль з клавіатури.", "error");
      return;
    }
    if (pressed.size > 0) {
      setStatus("Відпусти всі клавіші та спробуй ще раз.", "error");
      return;
    }

    const url = mode === "register" ? "/api/register" : "/api/login";
    const payload = {
      username: userInput.value.trim(),
      password: passInput.value,
      events: events,
    };

    setStatus("Перевірка…", "");

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (mode === "register") {
        if (data.ok) {
          document.getElementById("count").textContent = data.count;
          if (data.ready) {
            setStatus("Готово! Профіль створено. Тепер можна увійти.", "ok");
            userInput.value = "";
          } else {
            setStatus("Спробу збережено. Ще треба: " + (data.needed - data.count), "ok");
          }
        } else {
          setStatus(data.error || "Помилка", "error");
        }
      } else {
        if (data.ok) {
          setStatus("", "");
          showResult(data);
        } else {
          setStatus(data.error || "Помилка", "error");
        }
      }
    } catch (err) {
      setStatus("Помилка з'єднання із сервером.", "error");
    }

    passInput.value = "";
    resetAttempt();
    passInput.focus();
  });
})();
