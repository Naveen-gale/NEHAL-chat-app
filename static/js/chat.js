const chatArea = document.getElementById("chatArea");
const input = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");

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

window.copyText = function(btn) {
  const text = btn.previousElementSibling.textContent;
  navigator.clipboard.writeText(text).then(() => {
    const old = btn.textContent;
    btn.textContent = "✅ Copied";
    setTimeout(() => btn.textContent = old, 2000);
  });
}

function addMessage(sender, text, mood = "normal") {
  const div = document.createElement("div");
  div.className = `message ${sender} mood-${mood}`;
  if (sender === 'ai') {
    div.innerHTML = `<div class="msg-content"></div><button class="copy-btn" onclick="copyText(this)">📋 Copy</button>`;
    div.querySelector('.msg-content').textContent = text;
  } else {
    div.textContent = text;
  }
  chatArea.appendChild(div);
  smoothScrollToBottom();
  return div;
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
        addMessage(c.sender, c.text, c.mood || "normal");
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

async function sendMessage() {
  const msg = input.value.trim();
  if (!msg) return;

  // Hide welcome screen on first message
  const ws = document.getElementById('welcomeScreen');
  if (ws) ws.classList.add('hidden');

  addMessage("user", msg);
  input.value = "";

  showTypingIndicator();

  try {
    const response = await fetch("/chat_stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg })
    });
    
    removeTypingIndicator();
    
    if (!response.ok) throw new Error("Server error");
    
    // Create AI message bubble for streaming
    const aiDiv = document.createElement("div");
    aiDiv.className = `message ai`;
    aiDiv.innerHTML = `<div class="msg-content"></div><button class="copy-btn hidden" onclick="copyText(this)">📋 Copy</button>`;
    chatArea.appendChild(aiDiv);
    const contentDiv = aiDiv.querySelector('.msg-content');
    const copyBtn = aiDiv.querySelector('.copy-btn');
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let fullText = "";
    let buffer = "";
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        copyBtn.classList.remove("hidden");
        break;
      }
      
      buffer += decoder.decode(value, { stream: true });
      let boundary = buffer.indexOf("\n\n");
      
      while (boundary !== -1) {
        const line = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        boundary = buffer.indexOf("\n\n");
        
        if (line.startsWith("data: ")) {
          const dataStr = line.slice(6);
          if (dataStr === "[DONE]") {
            copyBtn.classList.remove("hidden");
            break;
          }
          try {
            const data = JSON.parse(dataStr);
            if (data.requires_login) {
               // Show auth prompt
               aiDiv.innerHTML = `
                  <p>I'd love to keep chatting! Please sign up or log in to continue our conversation. ♥</p>
                  <div class="auth-buttons">
                    <a href="/login" class="auth-btn login-btn">Log In</a>
                    <a href="/signup" class="auth-btn signup-btn">Sign Up</a>
                  </div>
                `;
               smoothScrollToBottom();
               return;
            } else if (data.chunk) {
               fullText += data.chunk;
               contentDiv.textContent = fullText;
               smoothScrollToBottom();
            } else if (data.error) {
               fullText += "\n" + data.error;
               contentDiv.textContent = fullText;
            }
          } catch(e) {}
        }
      }
    }
  } catch(e) {
    removeTypingIndicator();
    addMessage("ai", "⚠️ Server error");
  }
}

/* ⌨️ EVENT LISTENERS */
input.addEventListener("keydown", e => {
  if (e.key === "Enter") sendMessage();
});
if (sendBtn) {
  sendBtn.addEventListener("click", sendMessage);
}