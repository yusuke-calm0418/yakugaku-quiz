const answerForm = document.getElementById('quiz-answer-form');
if (answerForm) {
  const inputs = [...answerForm.querySelectorAll('input[name="choice"]')];
  const error = document.getElementById('choice-error');
  inputs.forEach(input => input.addEventListener('change', () => {
    if (inputs.filter(item => item.checked).length > 2) {
      input.checked = false;
      error.textContent = '選択できるのは2つまでです。';
    } else {
      error.textContent = '';
    }
  }));
  answerForm.addEventListener('submit', event => {
    if (!inputs.some(input => input.checked)) {
      event.preventDefault();
      error.textContent = '選択肢を選んでから回答してください。';
      inputs[0]?.focus();
    }
  });
}
const bookmarkForm = document.getElementById('quiz-bookmark-form');
if (bookmarkForm) {
  bookmarkForm.addEventListener('submit', async event => {
    event.preventDefault();
    const button = bookmarkForm.querySelector('button');
    const status = document.getElementById('bookmark-status');
    button.disabled = true;
    try {
      const response = await fetch(location.href, {method: 'POST', body: new FormData(bookmarkForm), credentials: 'same-origin'});
      if (!response.ok) throw new Error('Bookmark failed');
      const data = await response.json();
      button.setAttribute('aria-pressed', String(data.bookmarked));
      button.textContent = data.bookmarked ? '★ ブックマーク済み' : '☆ ブックマーク';
      status.textContent = data.bookmarked ? '保存しました。' : '解除しました。';
    } catch {
      status.textContent = '保存できませんでした。もう一度お試しください。';
    } finally {
      button.disabled = false;
    }
  });
}

// Bring the grading result into view after the answer page has loaded.
const resultTitle = document.getElementById('result-title');
if (resultTitle) {
  window.addEventListener('pageshow', () => {
    resultTitle.focus({preventScroll: true});
    resultTitle.scrollIntoView({block: 'start', behavior: 'instant'});
  });
}
