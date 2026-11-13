(() => {
  const roles = ['customer', 'rider', 'vendor'];
  const loginForm = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');
  const loginError = document.getElementById('login-error');
  const registerError = document.getElementById('register-error');
  const registerSupport = document.getElementById('register-support');
  let selectedRole = localStorage.getItem('quickrefill-role') || 'customer';
  const urlParams = new URLSearchParams(window.location.search);
  let selectedMode = urlParams.get('mode') === 'register' ? 'register' : 'login';
  if (selectedMode === 'register') selectedRole = 'customer';

  if (!roles.includes(selectedRole)) selectedRole = 'customer';

  const eyeIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>';
  const eyeOffIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17.9 17.9A10.9 10.9 0 0 1 12 19C5.5 19 2 12 2 12a18 18 0 0 1 5.1-5.9M9.9 5.1A10 10 0 0 1 12 5c6.5 0 10 7 10 7a18 18 0 0 1-2.2 3.2M1 1l22 22"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/></svg>';

  document.querySelectorAll('.password-toggle').forEach(button => {
    const input = button.previousElementSibling;
    button.innerHTML = eyeIcon;
    button.addEventListener('click', () => {
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      button.innerHTML = show ? eyeOffIcon : eyeIcon;
      button.setAttribute('aria-pressed', String(show));
      button.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
      input.focus();
    });
  });

  const updateForm = () => {
    const canRegister = selectedRole === 'customer';
    loginForm.classList.toggle('hidden', selectedMode !== 'login');
    registerForm.classList.toggle('hidden', selectedMode !== 'register' || !canRegister);
    registerSupport.classList.toggle('hidden', selectedMode !== 'register' || canRegister);
    document.querySelectorAll('[data-mode]').forEach(button => {
      const active = button.dataset.mode === selectedMode;
      button.classList.toggle('active', active);
      button.setAttribute('aria-selected', String(active));
    });
    loginError.textContent = '';
    registerError.textContent = '';
  };

  document.querySelectorAll('[data-role]').forEach(button => {
    button.addEventListener('click', () => {
      selectedRole = button.dataset.role;
      localStorage.setItem('quickrefill-role', selectedRole);
      document.querySelectorAll('[data-role]').forEach(roleButton => {
        const active = roleButton.dataset.role === selectedRole;
        roleButton.classList.toggle('active', active);
        roleButton.setAttribute('aria-pressed', String(active));
      });
      updateForm();
    });
  });
  document.querySelectorAll('[data-mode]').forEach(button => {
    button.addEventListener('click', () => {
      selectedMode = button.dataset.mode;
      updateForm();
    });
  });

  loginForm.addEventListener('submit', async event => {
    event.preventDefault();
    loginError.textContent = '';
    const submit = loginForm.querySelector('[type="submit"]');
    submit.disabled = true;
    try {
      const result = await api('/api/auth/login', {
        method: 'POST',
        body: {
          email: document.getElementById('login-email').value.trim(),
          password: document.getElementById('login-password').value,
          role: selectedRole,
        },
      });
      window.location.assign(result.redirect);
    } catch (error) {
      loginError.textContent = error.message;
    } finally {
      submit.disabled = false;
    }
  });

  registerForm.addEventListener('submit', async event => {
    event.preventDefault();
    registerError.textContent = '';
    if (selectedRole !== 'customer') {
      registerSupport.classList.remove('hidden');
      return;
    }
    const submit = registerForm.querySelector('[type="submit"]');
    submit.disabled = true;
    try {
      const phoneEl = document.getElementById('register-phone');
      const result = await api('/api/auth/register', {
        method: 'POST',
        body: {
          first_name: document.getElementById('register-first-name').value.trim(),
          last_name: document.getElementById('register-last-name').value.trim(),
          phone: phoneEl ? phoneEl.value.trim() : '',
          email: document.getElementById('register-email').value.trim(),
          password: document.getElementById('register-password').value,
          password_confirm: document.getElementById('register-password-confirm').value,
        },
      });
      window.location.assign(result.redirect);
    } catch (error) {
      registerError.textContent = error.message;
    } finally {
      submit.disabled = false;
    }
  });

  document.querySelectorAll('[data-role]').forEach(button => {
    const active = button.dataset.role === selectedRole;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
  updateForm();
})();
