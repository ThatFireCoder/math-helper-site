const calcForm = document.querySelector('#calc-form');
const calcResult = document.querySelector('#calc-result');
const askForm = document.querySelector('#ask-form');
const askResult = document.querySelector('#ask-result');

async function postJson(path, data) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `Request failed (${response.status}).`);
  return payload;
}

function showMessage(element, message, isError = false) {
  element.hidden = false;
  element.classList.toggle('error', isError);
  element.textContent = message;
}

calcForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = calcForm.querySelector('button');
  button.disabled = true;
  showMessage(calcResult, 'Working…');
  try {
    const data = await postJson('/api/calculate', { expression: document.querySelector('#expression').value });
    showMessage(calcResult, `Answer: ${data.result}`);
  } catch (error) {
    showMessage(calcResult, error.message, true);
  } finally {
    button.disabled = false;
  }
});

askForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = askForm.querySelector('button');
  button.disabled = true;
  showMessage(askResult, 'Thinking through it…');
  try {
    const data = await postJson('/api/ask', { question: document.querySelector('#question').value });
    // textContent prevents model output from being interpreted as HTML.
    showMessage(askResult, data.answer);
  } catch (error) {
    showMessage(askResult, error.message, true);
  } finally {
    button.disabled = false;
  }
});
