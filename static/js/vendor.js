let refreshTimer = null;

function showPanel(name) {
  document.querySelectorAll('[id^="panel-"]').forEach(p => p.classList.add('hidden'));
  document.getElementById('panel-' + name).classList.remove('hidden');
  document.querySelectorAll('.nav-item').forEach(b => {
    b.classList.toggle('active', b.dataset.panel === name);
  });
}

async function init() {
  try {
    const me = await api('/api/me');
    if (me.role !== 'vendor') {
      window.location.href = me.role === 'rider' ? '/rider/' : '/app/';
      return;
    }
    document.getElementById('vendor-name').textContent = (me.vendor && me.vendor.name) || 'QuickRefill Vendor';
    document.getElementById('vendor-greet').textContent = `Good day, ${me.first_name}`;
    if (me.vendor) {
      document.getElementById('settings-name').textContent = me.vendor.name;
      document.getElementById('settings-loc').textContent = me.vendor.location;
      document.getElementById('accepting-toggle').classList.toggle('on', me.vendor.accepting_orders);
      document.getElementById('verified-badge').classList.toggle('hidden', !me.vendor.verified);
    }
    await refreshAll();
    refreshTimer = setInterval(refreshOrdersAndStats, 5000);
  } catch (e) {
    if (e.status === 401) window.location.href = '/login/';
    else showToast(e.message);
  }
}

async function refreshAll() {
  await Promise.all([refreshOrdersAndStats(), loadStock(), loadSettlements(), loadRatings()]);
}

async function refreshOrdersAndStats() {
  const [stats, orders] = await Promise.all([
    api('/api/vendor/stats'),
    api('/api/vendor/orders'),
  ]);
  document.getElementById('stat-today').textContent = stats.orders_today;
  document.getElementById('stat-waiting').textContent = stats.waiting;
  document.getElementById('stat-out').textContent = stats.out_for_delivery;
  document.getElementById('stat-rating').textContent = stats.rating;
  document.getElementById('accepting-toggle').classList.toggle('on', stats.accepting_orders);

  const body = document.getElementById('orders-body');
  body.innerHTML = '';
  orders.forEach(o => {
    const tr = document.createElement('tr');
    const pay = o.payment_method === 'momo' ? 'MoMo'
      : o.payment_method === 'airtel' ? 'Airtel'
      : 'Cash';
    const payStatus = o.payment_status === 'paid' ? ' paid' : '';
    tr.innerHTML = `
      <td><strong>${o.code}</strong></td>
      <td>${o.delivery_address}<div class="muted" style="font-size:12px;">${o.address_note || ''}</div></td>
      <td>${o.item_label || ''}</td>
      <td>${o.order_type}</td>
      <td>${pay}${payStatus}</td>
      <td><span class="status-pill ${o.status}">${o.status_label}</span></td>
      <td style="white-space:nowrap;"></td>
    `;
    const actions = tr.lastElementChild;
    if (o.status === 'new') {
      const rej = document.createElement('button');
      rej.className = 'btn btn-danger';
      rej.style.cssText = 'width:auto;padding:8px 12px;margin-right:6px;';
      rej.textContent = 'Reject';
      rej.onclick = async () => {
        try {
          await api(`/api/vendor/orders/${o.id}/reject`, { method: 'POST', body: {} });
          refreshOrdersAndStats();
        } catch (error) { showToast(error.message); }
      };
      const acc = document.createElement('button');
      acc.className = 'btn btn-primary';
      acc.style.cssText = 'width:auto;padding:8px 12px;';
      acc.textContent = 'Accept';
      acc.onclick = async () => {
        try {
          await api(`/api/vendor/orders/${o.id}/accept`, { method: 'POST', body: {} });
          refreshOrdersAndStats();
          loadStock();
        } catch (e) {
          showToast(e.message);
        }
      };
      actions.appendChild(rej);
      actions.appendChild(acc);
    }
    body.appendChild(tr);
  });
}

async function loadStock() {
  const items = await api('/api/vendor/stock');
  const body = document.getElementById('stock-body');
  body.innerHTML = '';
  items.forEach(item => {
    const tr = document.createElement('tr');
    let statusPill = '<span class="status-pill delivered">In stock</span>';
    if (item.quantity <= 0) {
      statusPill = '<span class="status-pill rejected">Out of stock</span>';
    } else if (item.is_low) {
      statusPill = `<span class="status-pill new">Low (${item.quantity} left)</span>`;
    }
    tr.innerHTML = `
      <td><strong>${item.brand}</strong></td>
      <td>${item.size_kg} kg</td>
      <td>${item.price_display}</td>
      <td>${item.price_exchange_display || formatUGX(item.price_exchange)}</td>
      <td>${statusPill}</td>
      <td>
        <div class="stock-stepper">
          <button data-delta="-1">−</button>
          <strong>${item.quantity}</strong>
          <button data-delta="1">+</button>
        </div>
      </td>
    `;
    tr.querySelectorAll('button').forEach(btn => {
      btn.onclick = async () => {
        const next = Math.max(0, item.quantity + Number(btn.dataset.delta));
        await api('/api/vendor/stock', {
          method: 'PATCH',
          body: { id: item.id, quantity: next },
        });
        loadStock();
      };
    });
    body.appendChild(tr);
  });
}

async function loadSettlements() {
  const rows = await api('/api/vendor/settlement');
  const body = document.getElementById('settlements-body');
  body.innerHTML = '';
  if (rows.length) {
    const s = rows[0];
    document.getElementById('set-sales').textContent = s.gas_sales_display;
    document.getElementById('set-comm').textContent = s.commission_amount_display;
    document.getElementById('set-payout').textContent = s.payout_display;
  }
  rows.forEach(s => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${s.week_start}</td>
      <td>${s.gas_sales_display}</td>
      <td>${s.commission_percent}% (${s.commission_amount_display})</td>
      <td><strong>${s.payout_display}</strong></td>
    `;
    body.appendChild(tr);
  });
}

async function loadRatings() {
  const rows = await api('/api/vendor/ratings');
  const body = document.getElementById('ratings-body');
  body.innerHTML = '';
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="5" class="muted">No ratings yet.</td></tr>';
    return;
  }
  rows.forEach(r => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${r.order_code}</td>
      <td>${r.vendor_stars}</td>
      <td>${r.rider_stars}</td>
      <td>${(r.tags || []).join(', ')}</td>
      <td>${r.comment || ''}</td>
    `;
    body.appendChild(tr);
  });
}

document.getElementById('accepting-toggle').onclick = async () => {
  const el = document.getElementById('accepting-toggle');
  const next = !el.classList.contains('on');
  el.classList.toggle('on', next);
  try {
    await api('/api/vendor/accepting', {
      method: 'PATCH',
      body: { accepting_orders: next },
    });
  } catch (error) {
    el.classList.toggle('on', !next);
    showToast(error.message);
  }
};

document.querySelectorAll('.nav-item').forEach(btn => {
  btn.onclick = () => {
    showPanel(btn.dataset.panel);
    document.querySelector('.vendor-sidebar').classList.remove('mobile-open');
    document.getElementById('vendor-menu-toggle').setAttribute('aria-expanded', 'false');
  };
});

document.getElementById('vendor-menu-toggle').onclick = event => {
  const sidebar = document.querySelector('.vendor-sidebar');
  const isOpen = sidebar.classList.toggle('mobile-open');
  event.currentTarget.setAttribute('aria-expanded', String(isOpen));
};

document.getElementById('link-settlement').onclick = (e) => {
  e.preventDefault();
  showPanel('settlements');
};

init();
