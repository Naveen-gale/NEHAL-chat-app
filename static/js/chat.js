const chatArea = document.getElementById("chatArea");
const input = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");

let isTyping = false;
let messageQueue = [];

function smoothScrollToBottom() {
  chatArea.scrollTo({
    top: chatArea.scrollHeight,
    behavior: 'smooth'
  });
}

function processQueue() {
  if (isTyping || messageQueue.length === 0) return;
  const curr = messageQueue.shift();
  typeMessage(curr.sender, curr.text, curr.mood);
}

function addMessage(sender, text) {
  const div = document.createElement("div");
  div.className = `message ${sender}`;
  div.textContent = text;
  chatArea.appendChild(div);
  smoothScrollToBottom();
}

/* 🔁 LOAD CHAT HISTORY ON PAGE LOAD */
window.addEventListener("load", () => {
  chatArea.innerHTML = "";

  fetch("/history")
    .then(res => res.json())
    .then(chats => {
      if (!Array.isArray(chats) || chats.length === 0) {
        addMessage("ai", "Hello 👋 I am NEHAL AI. How can I help you today?");
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
  // Optional loading indicator could go here

  fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: msg })
  })
    .then(res => res.json())
    .then(data => {
      messageQueue.push({ sender: "ai", text: data.reply, mood: data.mood });
      processQueue();
    })
    .catch(() => {
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

function typeMessage(sender, text, mood = "normal") {
  isTyping = true;
  const div = document.createElement("div");
  div.className = `message ${sender} mood-${mood}`;
  chatArea.appendChild(div);

  // Very fast typing speed to feel snappy
  const speed = 10; 
  let i = 0;
  
  // Use textContent for better performance instead of innerText
  const interval = setInterval(() => {
    div.textContent += text[i];
    i++;
    
    // Snapping scroll to bottom immediately during typing
    chatArea.scrollTop = chatArea.scrollHeight;

    if (i >= text.length) {
      clearInterval(interval);
      isTyping = false;
      processQueue();
    }
  }, speed);
}
