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

function showPhonePopup(message, phoneNumber) {
  let modal = document.getElementById('qr-phone-popup');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'qr-phone-popup';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(11,23,48,0.65);display:flex;align-items:center;justify-content:center;z-index:9999;padding:20px;';
    modal.innerHTML = `
      <div style="background:#fff;color:#0B1730;border-radius:18px;max-width:360px;width:100%;padding:24px 20px;box-shadow:0 20px 40px rgba(0,0,0,0.3);text-align:center;">
        <div style="width:48px;height:48px;border-radius:12px;background:#FFF7ED;color:#C2410C;display:grid;place-items:center;margin:0 auto 12px;">
          <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.12.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.58 2.81.7A2 2 0 0 1 22 16.92z"/>
          </svg>
        </div>
        <p id="qr-popup-msg" style="margin:0 0 14px;font-size:15px;font-weight:600;line-height:1.45;color:#1E293B;"></p>
        <div id="qr-popup-phone-wrap" style="background:#F8FAFC;border:1px solid #CBD5E1;border-radius:12px;padding:12px;margin-bottom:16px;font-size:20px;font-weight:800;letter-spacing:0.03em;color:#0B1730;user-select:all;"></div>
        <div style="display:flex;gap:10px;">
          <button type="button" id="qr-popup-copy" class="btn btn-navy" style="flex:1;padding:11px;">Copy number</button>
          <button type="button" id="qr-popup-close" class="btn btn-primary" style="flex:1;padding:11px;">Close</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.style.display = 'none';
    });
    modal.querySelector('#qr-popup-close').onclick = () => {
      modal.style.display = 'none';
    };
  }
  const msgEl = modal.querySelector('#qr-popup-msg');
  const phoneWrap = modal.querySelector('#qr-popup-phone-wrap');
  const copyBtn = modal.querySelector('#qr-popup-copy');

  msgEl.textContent = message;
  if (phoneNumber) {
    phoneWrap.style.display = 'block';
    phoneWrap.textContent = phoneNumber;
    copyBtn.style.display = 'block';
    copyBtn.onclick = async () => {
      try {
        await navigator.clipboard.writeText(phoneNumber);
        showToast('Phone number copied!');
      } catch (_) {
        showToast(phoneNumber);
      }
    };
  } else {
    phoneWrap.style.display = 'none';
    copyBtn.style.display = 'none';
  }
  modal.style.display = 'flex';
}

function showOrderDetailsModal(order) {
  let modal = document.getElementById('qr-order-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'qr-order-modal';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(11,23,48,0.65);display:flex;align-items:center;justify-content:center;z-index:9999;padding:20px;';
    modal.innerHTML = `
      <div style="background:#fff;color:#0B1730;border-radius:18px;max-width:380px;width:100%;padding:22px 20px;box-shadow:0 20px 40px rgba(0,0,0,0.3);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
          <h3 style="margin:0;font-size:18px;font-weight:800;">Order summary</h3>
          <span id="qr-od-status" class="status-pill"></span>
        </div>
        <div style="border-top:1px solid #E2E8F0;border-bottom:1px solid #E2E8F0;padding:12px 0;margin-bottom:16px;font-size:14px;display:grid;gap:8px;">
          <div style="display:flex;justify-content:space-between;"><span class="muted">Order code</span><strong id="qr-od-code"></strong></div>
          <div style="display:flex;justify-content:space-between;"><span class="muted">Cylinder</span><strong id="qr-od-item"></strong></div>
          <div style="display:flex;justify-content:space-between;gap:12px;"><span class="muted">Delivery place</span><strong id="qr-od-address" style="text-align:right;"></strong></div>
          <div id="qr-od-note-row" style="display:flex;justify-content:space-between;gap:12px;"><span class="muted">Landmark / note</span><span id="qr-od-note" style="text-align:right;font-weight:600;"></span></div>
          <div style="display:flex;justify-content:space-between;"><span class="muted">Total</span><strong id="qr-od-total" style="color:#C2410C;font-size:16px;"></strong></div>
        </div>
        <button type="button" id="qr-od-close" class="btn btn-primary" style="width:100%;padding:12px;">Done</button>
      </div>
    `;
    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.style.display = 'none';
    });
    modal.querySelector('#qr-od-close').onclick = () => {
      modal.style.display = 'none';
    };
  }
  const statusEl = modal.querySelector('#qr-od-status');
  statusEl.textContent = order.status_label || order.status || 'Active';
  statusEl.className = 'status-pill ' + (order.status || '');
  modal.querySelector('#qr-od-code').textContent = order.code || '—';
  modal.querySelector('#qr-od-item').textContent = order.item_label || '—';
  modal.querySelector('#qr-od-address').textContent = order.delivery_address || '—';
  const noteRow = modal.querySelector('#qr-od-note-row');
  if (order.address_note) {
    noteRow.style.display = 'flex';
    modal.querySelector('#qr-od-note').textContent = order.address_note;
  } else {
    noteRow.style.display = 'none';
  }
  modal.querySelector('#qr-od-total').textContent = order.total_display || '—';
  modal.style.display = 'flex';
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
