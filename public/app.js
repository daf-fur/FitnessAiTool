(function () {
  const messagesEl = document.getElementById("messages");
  const userEl = document.getElementById("user");
  const inputEl = document.getElementById("input");
  const sendBtn = document.getElementById("send");
  const resetBtn = document.getElementById("reset");
  const statusEl = document.getElementById("connection-status");
  const form = document.getElementById("composer");
  const starterPrompts = document.querySelectorAll("[data-prompt]");
  let scrollFrame = null;

  function setStatus(label) {
    statusEl.innerHTML = '<i class="signal-dot" aria-hidden="true"></i> ' + label;
  }

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

    if (scrollFrame === null) {
      scrollFrame = requestAnimationFrame(() => {
        messagesEl.scrollTop = messagesEl.scrollHeight;
        scrollFrame = null;
      });
    }

    return el;
  }

  function setBusy(busy) {
    inputEl.disabled = busy;
    sendBtn.disabled = busy;
    sendBtn.setAttribute("aria-busy", busy ? "true" : "false");
  }

  async function sendMessage(message) {
    const user = (userEl.value || "").trim() || "guest";
    localStorage.setItem("fa_user", user);

    addMessage("user", message);

    const pending = addMessage("assistant pending", "Thinking…");
    const thinkingMessages = ["Checking the exercise library…", "Shaping your session…", "Finding the best next step…"];
    let index = 0;
    const timer = window.setInterval(() => {
      index = (index + 1) % thinkingMessages.length;
      pending.textContent = thinkingMessages[index];
    }, 1200);

    setBusy(true);
    setStatus("Working");

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, user, message })
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);

      window.clearInterval(timer);
      pending.remove();

      if (data.error) {
        addMessage("error", data.error);
        setStatus("Error");
      } else {
        addMessage("assistant", data.reply || "(no reply)");
        setStatus("Ready");
      }
    } catch (error) {
      window.clearInterval(timer);
      pending.remove();
      addMessage("error", "Request failed: " + error.message);
      setStatus("Error");
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
    resetBtn.disabled = true;
    setStatus("Resetting");

    try {
      const response = await fetch("/api/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId })
      });

      if (!response.ok) throw new Error(`Reset failed (${response.status})`);

      messagesEl.replaceChildren();
      addMessage("assistant", "Conversation reset. What would you like to work on?");
      setStatus("Ready");
    } catch (error) {
      addMessage("error", "Could not reset the conversation: " + error.message);
      setStatus("Error");
    } finally {
      resetBtn.disabled = false;
    }
  });

  starterPrompts.forEach((promptButton) => {
    promptButton.addEventListener("click", () => {
      inputEl.value = promptButton.dataset.prompt;
      form.requestSubmit();
    });
  });

  setStatus("Ready");
  addMessage("assistant", "Hi! I can help plan a session, suggest alternatives, or review your recent training.");
})();

