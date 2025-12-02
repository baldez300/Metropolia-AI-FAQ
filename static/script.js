// script.js — Handles UI interactions, validation and backend calls

// Configuration: character limits
const TEXT_MAX = 5000;   // max chars for lecture text
const QUESTION_MAX = 300; // max chars for question
const TEXT_MIN = 20;     // minimum useful lecture text
const QUESTION_MIN = 3;  // minimum question length
const HISTORY_MAX = 10;  // max stored history items

// DOM elements
const askBtn = document.getElementById("askBtn");
const textInput = document.getElementById("text");
const questionInput = document.getElementById("question");
const resultContainer = document.getElementById("resultContainer");
const loading = document.getElementById("loading");
const errorBox = document.getElementById("error");
const result = document.getElementById("result");
const textHelp = document.getElementById("textHelp");
const questionHelp = document.getElementById("questionHelp");
const historyList = document.getElementById("historyList");
const clearHistoryBtn = document.getElementById("clearHistoryBtn");

// Initialize maxlength attributes (in case HTML doesn't include them)
if (!textInput.getAttribute('maxlength')) textInput.setAttribute('maxlength', TEXT_MAX);
if (!questionInput.getAttribute('maxlength')) questionInput.setAttribute('maxlength', QUESTION_MAX);

// Helper: update submit button state based on simple validation
function updateButtonState() {
  const t = textInput.value.trim();
  const q = questionInput.value.trim();
  const enabled = t.length >= TEXT_MIN && q.length >= QUESTION_MIN;
  askBtn.disabled = !enabled;
  askBtn.setAttribute('aria-disabled', (!enabled).toString());
}

// Helper: show a field-level message (info or error)
function showFieldMessage(el, message, isError = false) {
  // If the target element is missing (defensive), silently skip to avoid
  // uncaught exceptions when the DOM changes during development.
  if (!el) return;
  el.textContent = message || '';
  el.classList.toggle('error', isError);
}

// Live validation handlers
textInput.addEventListener('input', () => {
  const len = textInput.value.length;
  if (len === 0) showFieldMessage(textHelp, 'Paste lecture text here (max ' + TEXT_MAX + ' chars).');
  else if (len < TEXT_MIN) showFieldMessage(textHelp, `Text too short (${len}/${TEXT_MIN}); add more detail.`);
  else showFieldMessage(textHelp, `${len} / ${TEXT_MAX} characters`);
  updateButtonState();
});

questionInput.addEventListener('input', () => {
  const len = questionInput.value.length;
  if (len === 0) showFieldMessage(questionHelp, 'Enter a focused question (max ' + QUESTION_MAX + ' chars).');
  else if (len < QUESTION_MIN) showFieldMessage(questionHelp, `Question too short (${len}/${QUESTION_MIN}).`);
  else showFieldMessage(questionHelp, `${len} / ${QUESTION_MAX} characters`);
  updateButtonState();
});

// Initial messages
showFieldMessage(textHelp, 'Paste lecture text here (max ' + TEXT_MAX + ' chars).');
showFieldMessage(questionHelp, 'Enter a focused question (max ' + QUESTION_MAX + ' chars).');
updateButtonState();

// Submit handler
askBtn.addEventListener('click', async () => {
  // clear previous UI state
  errorBox.classList.remove('show');
  errorBox.textContent = '';
  result.textContent = '';

  const text = textInput.value.trim();
  const question = questionInput.value.trim();

  // final client-side validation (prevents accidental submissions)
  let hasError = false;
  if (!text) { showFieldMessage(textHelp, 'Please provide lecture text.', true); hasError = true; }
  if (!question) { showFieldMessage(questionHelp, 'Please enter a question.', true); hasError = true; }
  if (text.length < TEXT_MIN) { showFieldMessage(textHelp, `Lecture text is too short (min ${TEXT_MIN} chars).`, true); hasError = true; }
  if (question.length < QUESTION_MIN) { showFieldMessage(questionHelp, `Question is too short (min ${QUESTION_MIN} chars).`, true); hasError = true; }
  if (hasError) { updateButtonState(); return; }

  // show loading
  askBtn.disabled = true;
  loading.classList.add('show');
  resultContainer.classList.add('show');

  try {
    const res = await fetch('/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, question })
    });

    const data = await res.json();
    loading.classList.remove('show');

    if (res.ok && data.answer) {
      // success
      result.textContent = data.answer;
      // add successful query to history
      addToHistory(text, question);
    } else {
      // server-side validation or other error
      const msg = data.error || 'An unexpected error occurred. Please try again.';
      errorBox.textContent = '❌ ' + msg;
      errorBox.classList.add('show');

      // attempt to show field-level hints if possible
      const lower = msg.toLowerCase();
      if (lower.includes('lecture') || lower.includes('text')) {
        showFieldMessage(textHelp, msg, true);
      } else if (lower.includes('question')) {
        showFieldMessage(questionHelp, msg, true);
      }
    }
  } catch (err) {
    loading.classList.remove('show');
    errorBox.textContent = '❌ Network error. Please check your connection and try again.';
    errorBox.classList.add('show');
    console.error(err);
  } finally {
    askBtn.disabled = false;
    updateButtonState();
  }
});

// Allow Ctrl+Enter to submit from a textarea to avoid capturing plain Enter
[questionInput, textInput].forEach(el => {
  el.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      askBtn.click();
    }
  });
});

// Also allow Enter to submit when focus is on the question field and it's a single-line intent (for convenience)
questionInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    askBtn.click();
  }
});

// Accessibility: ensure button state reflects validity on startup
updateButtonState();

// ============ HISTORY MANAGEMENT ============

// Load and render history from localStorage on page load
function loadHistory() {
  const stored = localStorage.getItem('faqHistory');
  return stored ? JSON.parse(stored) : [];
}

function saveHistory(items) {
  localStorage.setItem('faqHistory', JSON.stringify(items.slice(0, HISTORY_MAX)));
}

function renderHistory() {
  const items = loadHistory();
  historyList.innerHTML = '';
  if (items.length === 0) {
    historyList.innerHTML = '<p class="history-empty">No recent questions yet.</p>';
    return;
  }
  items.forEach((item, idx) => {
    const el = document.createElement('div');
    el.className = 'history-item';
    el.innerHTML = `<strong>${item.question.substring(0, 50)}${item.question.length > 50 ? '...' : ''}</strong><br><small>${new Date(item.timestamp).toLocaleString()}</small>`;
    el.style.cursor = 'pointer';
    el.addEventListener('click', () => {
      textInput.value = item.text;
      questionInput.value = item.question;
      updateButtonState();
      textInput.scrollIntoView({ behavior: 'smooth' });
    });
    historyList.appendChild(el);
  });
}

function addToHistory(text, question) {
  const items = loadHistory();
  items.unshift({ text, question, timestamp: new Date().toISOString() });
  saveHistory(items);
  renderHistory();
}

clearHistoryBtn.addEventListener('click', () => {
  if (confirm('Clear all recent Lecture text & Question(s)?')) {
    localStorage.removeItem('faqHistory');
    renderHistory();
  }
});

// Render history on startup
renderHistory();
