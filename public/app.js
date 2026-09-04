(function () {
  const messagesEl = document.getElementById("messages");
  const userEl = document.getElementById("user");
  const inputEl = document.getElementById("input");
  const sendBtn = document.getElementById("send");
  const resetBtn = document.getElementById("reset");
  const form = document.getElementById("composer");
  const starterPrompts = document.querySelectorAll("[data-prompt]");

  function uuid() {
    if (crypto.randomUUID) return crypto.randomUUID();
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  let sessionId = localStorage.getItem("fa_session_id");
  if (!sessionId) {
    sessionId = uuid();
    localStorage.setItem("fa_session_id", sessionId);
  }

  userEl.value = localStorage.getItem("fa_user") || "";
  userEl.addEventListener("change", () => {
    localStorage.setItem("fa_user", userEl.value.trim());
  });

  function addMessage(role, text) {
    const el = document.createElement("div");
    el.className = "msg " + role;
    el.textContent = text;
    messagesEl.appendChild(el);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return el;
  }

  function setBusy(busy) {
    inputEl.disabled = busy;
    sendBtn.disabled = busy;
  }

  async function sendMessage(message) {
    const user = (userEl.value || "").trim() || "guest";
    localStorage.setItem("fa_user", user);

    addMessage("user", message);
    const pending = addMessage("assistant pending", "…thinking");
    setBusy(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, user, message }),
      });
      const data = await response.json();

      pending.remove();
      if (data.error) {
        addMessage("error", data.error);
      } else {
        addMessage("assistant", data.reply || "(no reply)");
      }
    } catch (error) {
      pending.remove();
      addMessage("error", "Request failed: " + error.message);
    } finally {
      setBusy(false);
      inputEl.focus();
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const message = inputEl.value.trim();
    if (!message) return;
    inputEl.value = "";
    sendMessage(message);
  });

  resetBtn.addEventListener("click", async () => {
    await fetch("/api/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    messagesEl.innerHTML = "";
    addMessage("assistant", "Conversation reset. What would you like to work on?");
  });

  starterPrompts.forEach((promptButton) => {
    promptButton.addEventListener("click", () => {
      inputEl.value = promptButton.dataset.prompt;
      form.requestSubmit();
    });
  });

  addMessage("assistant", "Hi! Tell me your goals, and I'll build workouts grounded in real exercise data.");
})();
