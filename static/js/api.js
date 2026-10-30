function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

function showToast(message) {
  let toast = document.getElementById('app-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'app-toast';
    toast.className = 'app-toast';
    toast.setAttribute('role', 'status');
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add('visible');
  clearTimeout(showToast.timeout);
  showToast.timeout = setTimeout(() => toast.classList.remove('visible'), 3500);
}

async function api(path, options = {}) {
  const opts = {
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken') || '',
      ...(options.headers || {}),
    },
    ...options,
  };
  if (opts.body && typeof opts.body !== 'string') {
    opts.body = JSON.stringify(opts.body);
  }
  const res = await fetch(path, opts);
  let data = null;
  const text = await res.text();
  try { data = text ? JSON.parse(text) : null; } catch { data = { detail: text }; }
  if (!res.ok) {
    const err = new Error((data && data.detail) || 'Request failed');
    err.status = res.status;
    err.data = data;
    if (!path.startsWith('/api/auth/')) showToast(err.message);
    throw err;
  }
  return data;
}

function formatUGX(n) {
  return 'UGX ' + Number(n).toLocaleString('en-UG');
}

function initials(name) {
  if (!name) return '?';
  return name.split(/\s+/).map(p => p[0]).slice(0, 2).join('').toUpperCase();
}

function flameLogoSVG() {
  return `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 2c1.5 3 1 5.5-.5 7.2 2.2-.3 4.5-2 5.5-4.7 3 3.2 3.8 7.2 1.7 10.2C16.8 17.8 14.5 19 12 19s-4.8-1.2-6.7-4.3C3.2 11.7 4 7.7 7 4.5c.2 2.2 1.8 4.2 3.5 4.8C9.2 6.8 10 3.8 12 2z" fill="white"/>
  </svg>`;
}
