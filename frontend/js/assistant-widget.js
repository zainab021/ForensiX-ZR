(function () {
  const API_BASE = window.FORENSIX_API_BASE || "http://127.0.0.1:8000";

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = (s === null || s === undefined) ? '' : String(s);
    return d.innerHTML;
  }

  // Only show the assistant once a citizen is logged in
  if (!localStorage.getItem('token')) return;

  const toggle = document.createElement('button');
  toggle.className = 'ai-widget-toggle';
  toggle.innerHTML = '<i class="fa-solid fa-comment-dots"></i>';
  toggle.setAttribute('aria-label', 'Open assistant');

  const HISTORY_KEY = 'ai_chat_history';
  const DEFAULT_GREETING = "Hi! I can help with reporting a concern, tracking report status, emergency SOS, evidence uploads, and account questions. How can I help?";

  function loadHistory() {
    try {
      return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
    } catch (e) {
      return [];
    }
  }

  function saveHistory(history) {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  }

  let history = loadHistory();
  if (history.length === 0) {
    history.push({ text: DEFAULT_GREETING, sender: 'bot' });
    saveHistory(history);
  }

  const panel = document.createElement('div');
  panel.className = 'ai-widget-panel ai-widget-hidden';
  panel.innerHTML = `
    <div class="ai-widget-header">
      <span><i class="fa-solid fa-robot"></i> ForensiX Assistant</span>
      <button type="button" aria-label="Close assistant">&times;</button>
    </div>
    <div class="ai-widget-messages" id="aiWidgetMessages"></div>
    <div class="ai-widget-input-row">
      <input type="text" id="aiWidgetInput" placeholder="Type your question..." />
      <button type="button" id="aiWidgetSend"><i class="fa-solid fa-paper-plane"></i></button>
    </div>
  `;

  document.body.appendChild(toggle);
  document.body.appendChild(panel);

  const messagesEl = panel.querySelector('#aiWidgetMessages');
  const inputEl = panel.querySelector('#aiWidgetInput');
  const sendBtn = panel.querySelector('#aiWidgetSend');
  const closeBtn = panel.querySelector('.ai-widget-header button');

  function renderMessage(text, sender) {
    const msg = document.createElement('div');
    msg.className = 'ai-widget-msg ' + sender;
    msg.innerHTML = esc(text);
    messagesEl.appendChild(msg);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function addMessage(text, sender) {
    renderMessage(text, sender);
    history.push({ text, sender });
    saveHistory(history);
  }

  history.forEach(m => renderMessage(m.text, m.sender));

  async function sendMessage() {
    const text = inputEl.value.trim();
    if (!text) return;
    addMessage(text, 'user');
    inputEl.value = '';

    try {
      const response = await fetch(API_BASE + '/api/ai/assistant', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + localStorage.getItem('token')
        },
        body: JSON.stringify({ message: text })
      });
      const data = await response.json();
      addMessage(response.ok ? data.reply : "Sorry, I couldn't process that right now.", 'bot');
    } catch (err) {
      addMessage("Connection error. Is the backend running?", 'bot');
    }
  }

  toggle.addEventListener('click', () => {
    panel.classList.toggle('ai-widget-hidden');
    if (!panel.classList.contains('ai-widget-hidden')) inputEl.focus();
  });

  closeBtn.addEventListener('click', () => panel.classList.add('ai-widget-hidden'));

  sendBtn.addEventListener('click', sendMessage);
  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendMessage();
  });
})();
