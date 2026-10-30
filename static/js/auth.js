(() => {
  const roles = ['customer', 'rider', 'vendor'];
  const loginForm = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');
  const loginError = document.getElementById('login-error');
  const registerError = document.getElementById('register-error');
  const registerSupport = document.getElementById('register-support');
  let selectedRole = localStorage.getItem('quickrefill-role') || 'customer';
  let selectedMode = 'login';

  if (!roles.includes(selectedRole)) selectedRole = 'customer';

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
      const result = await api('/api/auth/register', {
        method: 'POST',
        body: {
          first_name: document.getElementById('register-first-name').value.trim(),
          last_name: document.getElementById('register-last-name').value.trim(),
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
