(() => {
    const toggle = document.querySelector('[data-password-toggle]');
    if (toggle) {
        const password = document.getElementById(toggle.getAttribute('aria-controls'));
        if (password) {
            toggle.hidden = false;
            password.parentElement.classList.add('has-toggle');
            toggle.addEventListener('click', () => {
                const show = password.type === 'password';
                password.type = show ? 'text' : 'password';
                toggle.setAttribute('aria-pressed', String(show));
                toggle.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
                toggle.querySelector('i').className = `bi ${show ? 'bi-eye-slash' : 'bi-eye'}`;
                toggle.querySelector('span').textContent = show ? 'Hide' : 'Show';
            });
        }
    }
    const error = document.getElementById('signin-error');
    if (error) error.focus();
    else document.querySelector('.signin-form [aria-invalid="true"]')?.focus();
})();
