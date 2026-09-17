document.querySelectorAll('[data-password-toggle]').forEach(button => {
  const input = document.getElementById(button.dataset.passwordToggle);
  if (!input || input.type !== 'password') return;

  const setVisible = visible => {
    input.type = visible ? 'text' : 'password';
    button.setAttribute('aria-pressed', String(visible));
    button.setAttribute('aria-label', `${button.dataset.fieldLabel}を${visible ? '非表示' : '表示'}`);
    button.textContent = visible ? '非表示' : '表示';
  };
  button.hidden = false;
  button.addEventListener('click', () => setVisible(input.type === 'password'));
  // Hide passwords again when returning through the browser's page cache.
  window.addEventListener('pageshow', () => setVisible(false));
});
