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

/* 🔁 LOAD CHAT HISTORY AND AUTH STATUS ON PAGE LOAD */
window.addEventListener("load", () => {
  chatArea.innerHTML = "";

  fetch("/auth_status")
    .then(res => res.json())
    .then(data => {
      const actions = document.getElementById("headerActions");
      if (data.is_registered) {
        actions.innerHTML = `<span class="model">${data.username}</span><a href="/logout" class="logout-btn">Logout</a>`;
      } else {
        actions.innerHTML = `<span class="model">Guest</span><a href="/login" class="logout-btn">Sign In</a>`;
      }
    });

  fetch("/history")
    .then(res => res.json())
    .then(chats => {
      if (!Array.isArray(chats) || chats.length === 0) {
        addMessage("ai", "Hello 👋 I am NEHAL. How can I help you today?");
        return;
      }
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

function sendMessage() {
  const msg = input.value.trim();
  if (!msg) return;

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
        addMessage("ai", "I'd love to keep chatting! Please Login or Sign up to continue our conversation. 💖");
        const div = document.createElement("div");
        div.className = "message ai";
        div.innerHTML = `<a href="/signup" class="auth-btn" style="display:inline-block; margin-top:5px; text-decoration:none; padding:8px 16px; font-size:14px;">Sign Up Now</a>`;
        chatArea.appendChild(div);
        smoothScrollToBottom();
      } else {
        messageQueue.push({ sender: "ai", text: data.reply, mood: data.mood });
        processQueue();
      }
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
