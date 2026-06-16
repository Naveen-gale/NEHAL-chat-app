const chatArea = document.getElementById("chatArea");
const input = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");

let isTyping = false;
let messageQueue = [];
let typingIndicator = null;

function smoothScrollToBottom() {
  chatArea.scrollTo({
    top: chatArea.scrollHeight,
    behavior: 'smooth'
  });
}

function showTypingIndicator() {
  if (typingIndicator) return;
  typingIndicator = document.createElement("div");
  typingIndicator.className = "message ai typing";
  typingIndicator.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  chatArea.appendChild(typingIndicator);
  smoothScrollToBottom();
}

function removeTypingIndicator() {
  if (typingIndicator) {
    typingIndicator.remove();
    typingIndicator = null;
  }
}

function processQueue() {
  if (isTyping || messageQueue.length === 0) return;
  const curr = messageQueue.shift();

  isTyping = true;
  showTypingIndicator();

  // Simulated human typing time based on message length (min 1.0s, max 3.5s)
  const typingDuration = Math.min(3500, Math.max(1000, curr.text.length * 20));

  setTimeout(() => {
    removeTypingIndicator();
    addMessage(curr.sender, curr.text, curr.mood);
    isTyping = false;
    processQueue();
  }, typingDuration);
}

function addMessage(sender, text, mood = "normal") {
  const div = document.createElement("div");
  div.className = `message ${sender} mood-${mood}`;
  div.textContent = text;
  chatArea.appendChild(div);
  smoothScrollToBottom();
}

/* 🔁 LOAD CHAT HISTORY ON PAGE LOAD */
window.addEventListener("load", () => {
  chatArea.innerHTML = "";
  updateAuthUI();

  fetch("/history")
    .then(res => res.json())
    .then(chats => {
      if (!Array.isArray(chats) || chats.length === 0) {
        return; // Welcome screen is shown by default in HTML
      }
      // Hide welcome screen since there is chat history
      const ws = document.getElementById('welcomeScreen');
      if (ws) ws.classList.add('hidden');
      chats.forEach(c => {
        const div = document.createElement("div");
        div.className = `message ${c.sender}`;
        div.textContent = c.text;
        chatArea.appendChild(div);
      });
      // Scroll bottom after load
      chatArea.scrollTop = chatArea.scrollHeight;
    })
    .catch(err => {
      console.error("History load error:", err);
      addMessage("ai", "⚠️ Unable to load chat history");
    });
});

function updateAuthUI() {
  fetch("/auth_status")
    .then(res => res.json())
    .then(data => {
      const headerActions = document.getElementById("headerActions");
      const userBadge = document.getElementById("userBadge");
      if (!headerActions) return;

      if (data.is_registered) {
        // Logged in
        if (userBadge) {
          userBadge.textContent = `${data.username}`;
          userBadge.className = "model logged-in-badge";
          userBadge.style.color = "#ec4899"; // pink color
          userBadge.style.borderColor = "rgba(236, 72, 153, 0.3)";
        }
        // Update welcome screen name
        const welcomeName = document.getElementById('welcomeName');
        if (welcomeName) welcomeName.textContent = data.username;
        // Check if logout button already exists
        if (!document.getElementById("logoutBtn")) {
          const logoutBtn = document.createElement("a");
          logoutBtn.id = "logoutBtn";
          logoutBtn.href = "/logout";
          logoutBtn.className = "logout-btn";
          logoutBtn.textContent = "Logout";
          headerActions.appendChild(logoutBtn);
        }
      } else {
        // Guest mode
        if (userBadge) {
          userBadge.textContent = "Guest";
          userBadge.className = "model";
          userBadge.style.color = "";
          userBadge.style.borderColor = "";
        }
        // Remove logout button if it exists
        const logoutBtn = document.getElementById("logoutBtn");
        if (logoutBtn) logoutBtn.remove();
      }
    })
    .catch(err => console.error("Error fetching auth status:", err));
}

function sendMessage() {
  const msg = input.value.trim();
  if (!msg) return;

  // Hide welcome screen on first message
  const ws = document.getElementById('welcomeScreen');
  if (ws) ws.classList.add('hidden');

  addMessage("user", msg);
  input.value = "";

  // Show typing indicator immediately while waiting for server response
  showTypingIndicator();

  fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: msg })
  })
    .then(res => res.json())
    .then(data => {
      // Remove placeholder loading indicator
      removeTypingIndicator();
      if (data.requires_login) {
        // Show auth prompt
        const div = document.createElement("div");
        div.className = "message system-auth-prompt";
        div.innerHTML = `
          <p>I'd love to keep chatting! Please sign up or log in to continue our conversation. ♥</p>
          <div class="auth-buttons">
            <a href="/login" class="auth-btn login-btn">Log In</a>
            <a href="/signup" class="auth-btn signup-btn">Sign Up</a>
          </div>
        `;
        chatArea.appendChild(div);
        smoothScrollToBottom();
        return;
      }
      messageQueue.push({ sender: "ai", text: data.reply, mood: data.mood });
      processQueue();
    })
    .catch(() => {
      removeTypingIndicator();
      addMessage("ai", "⚠️ Server error");
    });
}

/* ⌨️ EVENT LISTENERS */
input.addEventListener("keydown", e => {
  if (e.key === "Enter") sendMessage();
});
if (sendBtn) {
  sendBtn.addEventListener("click", sendMessage);
}



let aichat = 0;