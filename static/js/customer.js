const state = {
  user: null,
  orderType: 'refill',
  size: 6,
  brands: [],
  selected: null,
  order: null,
  trackTimer: null,
  map: null,
  markers: {},
  routeLine: null,
  riderStars: 5,
  vendorStars: 5,
  tags: [],
  customCoords: null,
};

function showView(name) {
  const current = state.currentView;
  const isBack = (name === 'home' && ['checkout', 'rate'].includes(current))
    || (name === 'orders' && current === 'track');
  document.querySelectorAll('#app > section').forEach(s => s.classList.add('hidden'));
  const el = document.getElementById('view-' + name);
  if (el) {
    el.classList.toggle('screen-back', isBack);
    el.classList.remove('hidden');
  }
  state.currentView = name;
}

function renderStars(containerId, key) {
  const el = document.getElementById(containerId);
  el.innerHTML = '';
  for (let i = 1; i <= 5; i++) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = '★';
    b.className = i <= state[key] ? 'on' : '';
    b.onclick = () => { state[key] = i; renderStars(containerId, key); };
    el.appendChild(b);
  }
}

async function init() {
  try {
    state.user = await api('/api/me');
    if (state.user.role !== 'customer') {
      window.location.href = state.user.role === 'rider' ? '/rider/' : '/vendor/';
      return;
    }
    document.getElementById('greet-title').textContent = `Welcome back, ${state.user.first_name}.`;
    document.getElementById('account-name').textContent = state.user.first_name + (state.user.last_name ? ' ' + state.user.last_name : '');
    document.getElementById('account-phone').textContent = state.user.phone || '';
    showView('home');
    await loadBrands();
  } catch (e) {
    if (e.status === 401) window.location.assign('/login/');
    else showToast(e.message);
  }
}

document.querySelectorAll('.segmented button').forEach(btn => {
  btn.onclick = () => {
    document.querySelectorAll('.segmented button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.orderType = btn.dataset.type;
    state.selected = null;
    loadBrands();
  };
});

document.querySelectorAll('.size-card').forEach(card => {
  card.onclick = () => {
    document.querySelectorAll('.size-card').forEach(c => c.classList.remove('active'));
    card.classList.add('active');
    state.size = Number(card.dataset.size);
    state.selected = null;
    loadBrands();
  };
});

async function loadBrands() {
  const list = document.getElementById('brand-list');
  list.innerHTML = '<div class="loading-state"><span class="spinner"></span>Loading options…</div>';
  try {
    state.brands = await api(`/api/stock?size=${state.size}&type=${state.orderType}`);
  } catch (error) {
    list.innerHTML = '<p class="muted">We could not load available brands. Please try again.</p>';
    updateContinue();
    return;
  }
  list.innerHTML = '';
  if (!state.brands.length) {
    list.innerHTML = '<p class="muted">No brands for this size right now.</p>';
    updateContinue();
    return;
  }
  const brandColors = {
    Stabex: '#1E3A8A',
    Oryx: '#B91C1C',
    Total: '#EA580C',
    Shell: '#D97706',
    Hashi: '#15803D',
  };
  state.brands.forEach(item => {
    const row = document.createElement('div');
    row.className = 'brand-item' + (item.clickable ? '' : ' disabled');
    if (state.selected && state.selected.id === item.id) row.classList.add('selected');
    const availClass = item.availability === 'out_of_stock' ? 'badge-grey'
      : item.availability === 'low' ? 'badge-amber' : 'badge-green';
    const badgeColor = brandColors[item.brand] || '#0B1730';
    row.innerHTML = `
      <div style="display:flex;align-items:center;gap:12px;">
        <div style="width:42px;height:42px;border-radius:11px;background:${badgeColor};color:#fff;display:grid;place-items:center;font-weight:800;font-size:13px;flex-shrink:0;">
          ${item.size_kg}kg
        </div>
        <div>
          <div style="font-weight:800;font-size:15px;">${item.brand} <span class="muted" style="font-weight:500;font-size:12px;">· ${item.vendor_name || 'Verified vendor'}</span></div>
          <div class="${availClass}" style="margin-top:2px;">${item.availability_label}</div>
        </div>
      </div>
      <div style="font-weight:800;font-size:15px;">${item.price_display}</div>
    `;
    if (item.clickable) {
      row.onclick = () => {
        state.selected = item;
        loadBrands();
      };
    }
    list.appendChild(row);
  });
  updateContinue();
}

function updateContinue() {
  const btn = document.getElementById('btn-continue');
  if (!state.selected) {
    btn.disabled = true;
    btn.textContent = 'Continue';
    return;
  }
  btn.disabled = false;
  btn.textContent = `Continue ${state.selected.continue_total_display}`;
}

document.getElementById('btn-continue').onclick = () => {
  if (!state.selected) return;
  document.getElementById('co-item').textContent = `${state.selected.brand} ${state.selected.size_kg} kg`;
  document.getElementById('co-type').textContent = state.orderType === 'refill' ? 'Cylinder refill' : 'Brand exchange';
  const homeAddr = document.getElementById('address-select').value.trim();
  const coAddrInput = document.getElementById('co-address');
  if (homeAddr && !coAddrInput.value.trim()) {
    coAddrInput.value = homeAddr;
  } else if (homeAddr) {
    coAddrInput.value = homeAddr;
  }
  document.getElementById('co-gas').textContent = state.selected.price_display;
  document.getElementById('co-total').textContent = state.selected.continue_total_display;
  showView('checkout');
};

document.getElementById('co-address').addEventListener('input', (e) => {
  document.getElementById('address-select').value = e.target.value;
  state.customCoords = null;
  document.getElementById('gps-status').textContent = 'Coordinates optional — rider uses your place & landmark';
});

document.getElementById('btn-use-gps').onclick = () => {
  const statusEl = document.getElementById('gps-status');
  if (!navigator.geolocation) {
    statusEl.textContent = 'GPS not supported on this browser — place name will be used.';
    return;
  }
  statusEl.textContent = 'Detecting your current location…';
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      state.customCoords = {
        lat: pos.coords.latitude,
        lng: pos.coords.longitude,
      };
      statusEl.textContent = '✓ Current GPS location attached';
      try {
        const res = await fetch(
          `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${state.customCoords.lat}&lon=${state.customCoords.lng}`
        );
        if (res.ok) {
          const data = await res.json();
          if (data && data.display_name) {
            const shortName = data.display_name.split(',').slice(0, 3).join(',').trim();
            document.getElementById('co-address').value = shortName;
            document.getElementById('address-select').value = shortName;
          }
        }
      } catch (_) {
        // Ignore reverse geocode failure; place name + GPS coords still work
      }
    },
    () => {
      statusEl.textContent = 'Could not read GPS — your typed place & landmark will be used.';
    },
    { enableHighAccuracy: true, timeout: 8000 }
  );
};

async function geocodePlaceName(place, landmark) {
  if (state.customCoords) return state.customCoords;
  const query = `${place} ${landmark || ''} Kampala Uganda`.trim();
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=ug&q=${encodeURIComponent(query)}`
    );
    if (res.ok) {
      const results = await res.json();
      if (Array.isArray(results) && results.length > 0) {
        return {
          lat: parseFloat(results[0].lat),
          lng: parseFloat(results[0].lon),
        };
      }
    }
  } catch (_) {
    // Fallback to backend Kampala place dictionary
  }
  return null;
}

document.getElementById('btn-checkout-back').onclick = () => showView('home');
document.getElementById('btn-edit-item').onclick = () => showView('home');

document.getElementById('btn-place-order').onclick = async () => {
  const deliveryAddress = (
    document.getElementById('co-address').value.trim() ||
    document.getElementById('address-select').value.trim()
  );
  if (!deliveryAddress) {
    showToast('Please enter the name of your place or area.');
    document.getElementById('co-address').focus();
    return;
  }
  const addressNote = document.getElementById('co-note').value.trim();
  const pay = document.querySelector('input[name="pay"]:checked').value;
  const when = document.querySelector('input[name="when"]:checked').value;
  const markPaid = pay === 'momo' || pay === 'airtel';

  if (markPaid) {
    document.getElementById('momo-overlay').classList.remove('hidden');
    await new Promise(r => setTimeout(r, 3000));
    document.getElementById('momo-overlay').classList.add('hidden');
  }

  const coords = await geocodePlaceName(deliveryAddress, addressNote);
  const payload = {
    stock_item_id: state.selected.id,
    order_type: state.orderType,
    delivery_address: deliveryAddress,
    address_note: addressNote,
    schedule: when,
    payment_method: pay,
    mark_paid: markPaid,
  };
  if (coords && !Number.isNaN(coords.lat) && !Number.isNaN(coords.lng)) {
    payload.lat = coords.lat;
    payload.lng = coords.lng;
  }

  try {
    const order = await api('/api/orders', {
      method: 'POST',
      body: payload,
    });
    state.order = order;
    startTracking(order.id);
  } catch (e) {
    showToast(e.message);
  }
};

function setProgress(step) {
  document.querySelectorAll('.progress-steps .step').forEach(el => {
    const n = Number(el.dataset.step);
    el.classList.remove('active', 'done');
    if (n < step) el.classList.add('done');
    if (n === step) el.classList.add('active');
    if (step >= 4 && n === 4) el.classList.add('done');
  });
}

function ensureMap() {
  if (state.map) {
    setTimeout(() => state.map.invalidateSize(), 100);
    return;
  }
  state.map = L.map('map', { zoomControl: true }).setView([0.332, 32.563], 14);
  L.tileLayer('/api/tiles/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(state.map);
}

function upsertMarker(key, lat, lng, label, color) {
  const icon = L.divIcon({
    className: '',
    html: `<div style="background:${color};color:#fff;padding:4px 8px;border-radius:10px;font-size:11px;font-weight:800;box-shadow:0 2px 8px rgba(0,0,0,.25);white-space:nowrap;">${label}</div>`,
    iconSize: [70, 24],
    iconAnchor: [35, 12],
  });
  if (state.markers[key]) {
    state.markers[key].setLatLng([lat, lng]);
  } else {
    state.markers[key] = L.marker([lat, lng], { icon }).addTo(state.map);
  }
}

async function pollTrack(orderId) {
  const t = await api(`/api/orders/${orderId}/track`);
  ensureMap();
  upsertMarker('vendor', t.vendor_lat, t.vendor_lng, 'Vendor', '#0B1730');
  upsertMarker('you', t.customer_lat, t.customer_lng, 'You', '#C2410C');
  if (t.rider_lat != null && t.rider_lng != null) {
    upsertMarker('rider', t.rider_lat, t.rider_lng, 'Rider', '#15803D');
  } else if (state.markers.rider) {
    state.map.removeLayer(state.markers.rider);
    delete state.markers.rider;
  }

  if (state.routeLine) state.map.removeLayer(state.routeLine);
  const points = (t.rider_lat != null && t.rider_lng != null)
    ? [[t.vendor_lat, t.vendor_lng], [t.rider_lat, t.rider_lng], [t.customer_lat, t.customer_lng]]
    : [[t.vendor_lat, t.vendor_lng], [t.customer_lat, t.customer_lng]];
  state.routeLine = L.polyline(
    points,
    { color: '#C2410C', weight: 4, opacity: 0.85 }
  ).addTo(state.map);
  state.map.fitBounds(state.routeLine.getBounds(), { padding: [35, 35], maxZoom: 16 });

  const etaEl = document.getElementById('track-eta');
  if (t.status === 'delivered') {
    etaEl.textContent = 'Delivered';
  } else {
    etaEl.textContent = `Arriving in about ${t.eta_minutes} min`;
  }
  document.getElementById('track-meta').textContent = `${t.code} · ${t.item_label}`;
  document.getElementById('track-vendor').textContent =
    `${t.vendor_name}${t.vendor_location ? ' · ' + t.vendor_location : ''}`;
  document.getElementById('track-dropoff').textContent = t.delivery_address || '—';
  document.getElementById('track-landmark').textContent = t.address_note
    ? `Landmark / note: ${t.address_note}`
    : '';
  setProgress(t.progress_step || 1);

  state.riderPhone = t.rider_phone || '+256700000002';
  state.helpPhone = t.help_phone || '0784113900';

  if (t.rider_name) {
    document.getElementById('rider-name').textContent = t.rider_name;
    document.getElementById('rider-avatar').textContent = initials(t.rider_name);
    document.getElementById('rider-meta').textContent =
      `★ ${t.rider_rating} · ${t.rider_trips} trips · ${t.rider_plate}`;
  } else {
    document.getElementById('rider-name').textContent = 'Assigning rider…';
    document.getElementById('rider-avatar').textContent = 'QR';
    document.getElementById('rider-meta').textContent = 'Waiting for vendor confirmation';
  }

  const payLabel = t.payment_method === 'cash'
    ? '✓ Pay cash on delivery'
    : t.payment_method === 'airtel'
      ? '✓ Paid with Airtel Money'
      : '✓ Paid with MoMo';
  document.getElementById('trust-pay').textContent = payLabel;

  if (t.status === 'delivered') {
    clearInterval(state.trackTimer);
    state.trackTimer = null;
    setTimeout(() => openRate(t), 800);
  }
}

function startTracking(orderId) {
  showView('track');
  ensureMap();
  if (state.trackTimer) clearInterval(state.trackTimer);
  pollTrack(orderId);
  state.trackTimer = setInterval(() => pollTrack(orderId), 4000);
}

function openRate(t) {
  const created = t.created_at ? new Date(t.created_at) : null;
  const delivered = t.delivered_at ? new Date(t.delivered_at) : new Date();
  let duration = '';
  if (created) {
    const mins = Math.max(1, Math.round((delivered - created) / 60000));
    duration = ` · ${mins} min`;
  }
  document.getElementById('rate-meta').textContent =
    `${t.item_label}${duration}`;
  state.riderStars = 5;
  state.vendorStars = 5;
  state.tags = [];
  document.querySelectorAll('#tag-chips .chip').forEach(c => c.classList.remove('selected'));
  renderStars('rider-stars', 'riderStars');
  renderStars('vendor-stars', 'vendorStars');
  showView('rate');
}

document.querySelectorAll('#tag-chips .chip').forEach(chip => {
  chip.onclick = () => {
    chip.classList.toggle('selected');
    state.tags = [...document.querySelectorAll('#tag-chips .chip.selected')].map(c => c.dataset.tag);
  };
});

document.getElementById('btn-submit-rating').onclick = async () => {
  try {
    await api(`/api/orders/${state.order.id}/rate`, {
      method: 'POST',
      body: {
        rider_stars: state.riderStars,
        vendor_stars: state.vendorStars,
        tags: state.tags,
        comment: document.getElementById('rate-comment').value,
      },
    });
    showToast('Thanks for your feedback!');
    showView('home');
    state.selected = null;
    loadBrands();
  } catch (e) {
    showToast(e.message);
  }
};

document.getElementById('btn-skip-rating').onclick = () => {
  showView('home');
  state.selected = null;
  loadBrands();
};

document.getElementById('btn-share').onclick = async () => {
  const shareData = {
    title: 'QuickRefill',
    text: 'Get cooking gas delivered fast with QuickRefill!',
    url: window.location.origin + '/',
  };
  try {
    if (navigator.share) await navigator.share(shareData);
    else {
      await navigator.clipboard.writeText(shareData.url);
      showToast('Link copied!');
    }
  } catch (_) {
    try {
      await navigator.clipboard.writeText(shareData.url);
      showToast('Link copied!');
    } catch {
      showToast('Unable to share the link from this device.');
    }
  }
};

document.getElementById('rider-call').onclick = () => {
  const riderPhone = state.riderPhone || '+256700000002';
  showPhonePopup(
    'To call the rider, copy and paste their number into the phone app and call him/her.',
    riderPhone
  );
};

document.getElementById('btn-get-help').onclick = () => {
  showPhonePopup('For help call 0784113900', '0784113900');
};

document.getElementById('btn-order-details').onclick = () => {
  if (!state.order) return;
  showOrderDetailsModal(state.order);
};

document.querySelectorAll('[data-nav]').forEach(btn => {
  btn.addEventListener('click', async () => {
    const nav = btn.dataset.nav;
    if (nav === 'home') showView('home');
    if (nav === 'orders') {
      showView('orders');
      await loadOrders();
    }
    if (nav === 'account') showView('account');
  });

  document.getElementById('btn-track-back').onclick = () => {
    if (state.trackTimer) clearInterval(state.trackTimer);
    state.trackTimer = null;
    showView('orders');
    loadOrders();
  };
});

async function loadOrders() {
  const list = document.getElementById('orders-list');
  list.innerHTML = '<p class="muted">Loading…</p>';
  try {
    const orders = await api('/api/orders');
    list.innerHTML = '';
    if (!orders.length) {
      list.innerHTML = '<p class="muted">No orders yet.</p>';
      return;
    }
    orders.forEach(o => {
      const card = document.createElement('div');
      card.className = 'card';
      card.style.marginBottom = '10px';
      card.style.cursor = 'pointer';
      card.innerHTML = `
        <div style="display:flex;justify-content:space-between;">
          <strong>${o.code}</strong>
          <span class="status-pill ${o.status}">${o.status_label}</span>
        </div>
        <div class="muted" style="margin-top:6px;">${o.item_label}</div>
        <div class="muted" style="font-size:12px;margin-top:2px;">${o.delivery_address}${o.address_note ? ' · ' + o.address_note : ''}</div>
        <div style="font-weight:700;margin-top:6px;">${o.total_display}</div>
      `;
      card.onclick = () => {
        state.order = o;
        if (o.status === 'delivered') {
          openRate({
            item_label: o.item_label,
            created_at: o.created_at,
            delivered_at: o.delivered_at,
          });
        } else if (!['rejected', 'cancelled'].includes(o.status)) {
          startTracking(o.id);
        }
      };
      list.appendChild(card);
    });
  } catch (e) {
    list.innerHTML = `<p class="muted">${e.message}</p>`;
  }
}

init();
