const state = {
  online: false,
  job: null,
  mode: 'idle',
  pollTimer: null,
  countdownTimer: null,
  countdown: 30,
  paymentConfirmed: false,
  map: null,
  markers: {},
  routeLine: null,
};

function showTab(name) {
  document.getElementById('view-jobs').classList.toggle('hidden', name !== 'jobs');
  document.getElementById('view-earnings').classList.toggle('hidden', name !== 'earnings');
  document.getElementById('view-profile').classList.toggle('hidden', name !== 'profile');
}

async function init() {
  try {
    const me = await api('/api/me');
    if (me.role !== 'rider') {
      window.location.href = me.role === 'vendor' ? '/vendor/' : '/app/';
      return;
    }
    await refreshSummary();
    const toggle = document.getElementById('online-toggle');
    state.online = !!(me.rider && me.rider.online);
    toggle.classList.toggle('on', state.online);
    startPolling();
  } catch (e) {
    if (e.status === 401) window.location.href = '/login/';
    else showToast(e.message);
  }
}

async function refreshSummary() {
  const s = await api('/api/rider/summary');
  document.getElementById('rider-hi').textContent = s.name.split(' ')[0];
  document.getElementById('sum-trips').textContent = s.trips_today;
  document.getElementById('sum-earn').textContent = s.earnings_today_display;
  document.getElementById('earn-big').textContent = s.earnings_today_display;
  document.getElementById('earn-trips').textContent = `${s.trips_today} trips`;
  document.getElementById('prof-name').textContent = s.name;
  document.getElementById('prof-phone').textContent = s.phone || '';
  document.getElementById('prof-meta').textContent = `★ ${s.rating} · ${s.trips_count} trips · ${s.vehicle_plate}`;
  state.online = s.online;
  document.getElementById('online-toggle').classList.toggle('on', state.online);
}

document.getElementById('online-toggle').onclick = async () => {
  state.online = !state.online;
  document.getElementById('online-toggle').classList.toggle('on', state.online);
  try {
    await api('/api/rider/online', { method: 'POST', body: { online: state.online } });
    pollJobs();
  } catch (error) {
    state.online = !state.online;
    document.getElementById('online-toggle').classList.toggle('on', state.online);
  }
};

// ---- Live GPS: share this phone's position while online or on a job ----
const gps = { watchId: null, lastSent: 0, warned: false };

function syncGps() {
  const wanted = state.online || state.mode === 'active';
  if (wanted && gps.watchId === null) startGps();
  if (!wanted && gps.watchId !== null) stopGps();
}

function startGps() {
  if (!('geolocation' in navigator)) {
    if (!gps.warned) { gps.warned = true; showToast('This device has no GPS. Customers will see an estimated position.'); }
    return;
  }
  gps.watchId = navigator.geolocation.watchPosition(
    (pos) => {
      const now = Date.now();
      if (now - gps.lastSent < 4000) return;
      gps.lastSent = now;
      api('/api/rider/location', {
        method: 'POST',
        body: { lat: pos.coords.latitude, lng: pos.coords.longitude },
      }).catch(() => {});
      setGpsBadge(true);
      if (state.map) upsertRiderMarker('me', pos.coords.latitude, pos.coords.longitude, 'You', '#15803D');
    },
    (err) => {
      setGpsBadge(false);
      if (!gps.warned) {
        gps.warned = true;
        showToast(err.code === 1
          ? 'Location is blocked. Allow location (HTTPS or localhost required) so customers can track you.'
          : 'Cannot get your GPS position yet.');
      }
    },
    { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 }
  );
}

function stopGps() {
  if (gps.watchId !== null) navigator.geolocation.clearWatch(gps.watchId);
  gps.watchId = null;
  setGpsBadge(false);
}

function setGpsBadge(on) {
  const el = document.getElementById('gps-badge');
  if (el) el.textContent = on ? '● GPS live' : '○ GPS off';
}

function startPolling() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  pollJobs();
  state.pollTimer = setInterval(pollJobs, 4000);
}

async function pollJobs() {
  try {
    const data = await api('/api/rider/jobs/available');
    state.mode = data.mode;
    state.job = data.job;
    renderJob();
    syncGps();
  } catch (e) {
    showToast(e.message);
  }
}

function renderJob() {
  const topHeader = document.getElementById('rider-top-header');
  const idle = document.getElementById('idle-state');
  const offer = document.getElementById('offer-state');
  const active = document.getElementById('active-state');
  idle.classList.add('hidden');
  offer.classList.add('hidden');
  active.classList.add('hidden');

  const isActiveDelivery = state.mode === 'active' && !!state.job;
  if (topHeader) {
    topHeader.classList.toggle('hidden', isActiveDelivery);
  }

  if (state.mode === 'offer' && state.job) {
    offer.classList.remove('hidden');
    document.getElementById('offer-fee').textContent = state.job.fee_display;
    document.getElementById('offer-meta').textContent = `${state.job.distance_km} km · ~${state.job.eta_min} min`;
    document.getElementById('offer-pickup').textContent = state.job.pickup;
    document.getElementById('offer-drop').textContent = state.job.dropoff;
    document.getElementById('offer-note').textContent = state.job.address_note
      ? `Landmark / note: ${state.job.address_note}`
      : '';
    document.getElementById('offer-cyl').textContent = state.job.cylinder;
    document.getElementById('offer-pay').textContent = state.job.payment_label;
    startCountdown();
    return;
  }
  stopCountdown();

  if (state.mode === 'active' && state.job) {
    active.classList.remove('hidden');
    renderActive();
    return;
  }

  idle.classList.remove('hidden');
  if (state.mode === 'offline') {
    idle.querySelector('p').textContent = 'You are offline. Toggle online to get jobs.';
  } else {
    idle.querySelector('p').textContent = 'Turn online to receive new deliveries.';
  }
}

function startCountdown() {
  if (state.countdownTimer) return;
  state.countdown = 30;
  document.getElementById('countdown').textContent = state.countdown;
  state.countdownTimer = setInterval(() => {
    state.countdown -= 1;
    document.getElementById('countdown').textContent = Math.max(0, state.countdown);
    if (state.countdown <= 0) stopCountdown();
  }, 1000);
}

function stopCountdown() {
  if (state.countdownTimer) {
    clearInterval(state.countdownTimer);
    state.countdownTimer = null;
  }
}

document.getElementById('btn-accept').onclick = async () => {
  if (!state.job) return;
  try {
    const data = await api(`/api/rider/jobs/${state.job.id}/accept`, { method: 'POST', body: {} });
    state.mode = data.mode;
    state.job = data.job;
    renderJob();
  } catch (error) { showToast(error.message); }
};

document.getElementById('btn-decline').onclick = async () => {
  if (!state.job) return;
  try {
    await api(`/api/rider/jobs/${state.job.id}/decline`, { method: 'POST', body: {} });
    state.job = null;
    state.mode = 'idle';
    renderJob();
  } catch (error) { showToast(error.message); }
};

const STEP_DEFS = [
  { key: 'collected', label: 'Collected from vendor', hint: 'Confirm cylinder pickup at vendor', photo: true },
  { key: 'seal_checked', label: 'Seal and weight checked', hint: 'Confirm factory seal before heading to customer' },
  { key: 'handover', label: 'Hand over the full cylinder and confirm the seal', hint: 'Customer confirms receipt at drop-off' },
  { key: 'empty_collected', label: 'Collect the empty cylinder', hint: 'Take the empty back' },
  { key: 'payment', label: 'Payment', hint: 'Confirm MoMo / collect cash' },
];

function ensureRiderMap() {
  const container = document.getElementById('rider-map');
  if (!container) return;
  if (state.map) {
    setTimeout(() => state.map.invalidateSize(), 100);
    return;
  }
  state.map = L.map('rider-map', { zoomControl: true }).setView([0.332, 32.563], 14);
  L.tileLayer('/api/tiles/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(state.map);
}

function upsertRiderMarker(key, lat, lng, label, color) {
  const icon = L.divIcon({
    className: '',
    html: `<div style="background:${color};color:#fff;padding:4px 8px;border-radius:10px;font-size:11px;font-weight:800;box-shadow:0 2px 8px rgba(0,0,0,.25);white-space:nowrap;">${label}</div>`,
    iconSize: [85, 24],
    iconAnchor: [42, 12],
  });
  if (state.markers[key]) {
    state.markers[key].setLatLng([lat, lng]);
  } else {
    state.markers[key] = L.marker([lat, lng], { icon }).addTo(state.map);
  }
}

function updateRiderMap(job, isPickupStage) {
  ensureRiderMap();
  if (!state.map) return;
  upsertRiderMarker('vendor', job.vendor_lat, job.vendor_lng, '1. Vendor Pickup', '#0B1730');
  upsertRiderMarker('customer', job.lat, job.lng, '2. Customer Drop-off', '#C2410C');

  if (state.routeLine) state.map.removeLayer(state.routeLine);
  state.routeLine = L.polyline(
    [[job.vendor_lat, job.vendor_lng], [job.lat, job.lng]],
    { color: isPickupStage ? '#0B1730' : '#C2410C', weight: 4, opacity: 0.85 }
  ).addTo(state.map);
  state.map.fitBounds(state.routeLine.getBounds(), { padding: [25, 25], maxZoom: 15 });
}

function renderActive() {
  const job = state.job;
  const isPickupStage = !job.steps_done.collected;

  document.getElementById('active-code').textContent = `${job.code} · ${job.cylinder}`;
  document.getElementById('active-step-label').textContent = `Step ${Math.min(job.current_step, 5)} of 5`;

  const stageBadge = document.getElementById('active-stage-badge');
  const primaryStop = document.getElementById('active-drop');
  const landmarkEl = document.getElementById('active-landmark');
  const secondaryStop = document.getElementById('active-secondary-stop');
  const navBtn = document.getElementById('btn-navigate');

  if (isPickupStage) {
    stageBadge.textContent = 'STAGE 1 OF 2 · GO TO VENDOR FOR PICKUP';
    primaryStop.textContent = job.pickup;
    landmarkEl.textContent = `Pick up: ${job.cylinder} (${job.order_type})`;
    secondaryStop.textContent = `Next (Customer drop-off): ${job.dropoff}${job.address_note ? ' — ' + job.address_note : ''}`;
    navBtn.textContent = 'Navigate to Vendor';
    const fromLat = job.rider_lat || (job.vendor_lat + 0.004);
    const fromLng = job.rider_lng || (job.vendor_lng - 0.004);
    navBtn.href =
      `https://www.openstreetmap.org/directions?from=${fromLat}%2C${fromLng}&to=${job.vendor_lat}%2C${job.vendor_lng}`;
  } else {
    stageBadge.textContent = 'STAGE 2 OF 2 · DELIVER TO CUSTOMER';
    primaryStop.textContent = job.dropoff;
    landmarkEl.textContent = job.address_note
      ? `Landmark / Note: ${job.address_note}`
      : 'No extra landmark note provided';
    secondaryStop.textContent = `Picked up from: ${job.pickup}`;
    navBtn.textContent = 'Navigate to Customer';
    navBtn.href =
      `https://www.openstreetmap.org/directions?from=${job.vendor_lat}%2C${job.vendor_lng}&to=${job.lat}%2C${job.lng}`;
  }

  document.getElementById('btn-call-customer').onclick = () => {
    const custPhone = job.customer_phone;
    if (!custPhone) {
      showToast('This customer has no phone number on file.');
      return;
    }
    showPhonePopup(
      'To call the customer, copy and paste their number into the phone app and call him/her.',
      custPhone
    );
  };
  const helpBtn = document.getElementById('btn-rider-help');
  if (helpBtn) {
    helpBtn.onclick = () => {
      showPhonePopup('For help call 0784113900', '0784113900');
    };
  }

  updateRiderMap(job, isPickupStage);

  const box = document.getElementById('checklist');
  box.innerHTML = '';
  let foundCurrent = false;
  STEP_DEFS.forEach((step) => {
    const isDone = step.key === 'payment'
      ? !!job.steps_done.payment || state.paymentConfirmed
      : !!job.steps_done[step.key];

    let isCurrent = false;
    if (!isDone && !foundCurrent) {
      isCurrent = true;
      foundCurrent = true;
    }

    const row = document.createElement('div');
    row.className = 'checklist-item' + (isDone ? ' done' : '') + (isCurrent ? ' current' : '');
    row.innerHTML = `
      <input type="checkbox" ${isDone ? 'checked disabled' : ''} ${!isCurrent && !isDone ? 'disabled' : ''} />
      <div style="flex:1;">
        <div style="font-weight:700;">${step.label}</div>
        <div class="muted" style="font-size:12px;">${step.hint}</div>
        ${step.photo && isCurrent ? '<input type="file" accept="image/*" style="margin-top:8px;font-size:12px;" />' : ''}
      </div>
    `;
    const cb = row.querySelector('input[type="checkbox"]');
    if (isCurrent) {
      cb.onchange = async () => {
        if (!cb.checked) return;
        try {
          const data = await api(`/api/rider/jobs/${job.id}/step`, {
            method: 'POST',
            body: { step: step.key },
          });
          if (step.key === 'payment') state.paymentConfirmed = true;
          state.job = data.job;
          renderActive();
        } catch (e) {
          cb.checked = false;
          showToast(e.message);
        }
      };
    }
    box.appendChild(row);
  });

  const slider = document.getElementById('slide-deliver');
  const checklistComplete = STEP_DEFS.every((s) => {
    if (s.key === 'payment') return state.paymentConfirmed || state.job.steps_done.payment;
    return !!state.job.steps_done[s.key];
  });
  slider.classList.toggle('disabled', !checklistComplete);
  slider.classList.toggle('ready', checklistComplete);
}

function setupSlider() {
  const slider = document.getElementById('slide-deliver');
  const knob = slider.querySelector('.knob');
  let dragging = false;
  let startX = 0;
  let startLeft = 0;

  const onDown = (e) => {
    if (slider.classList.contains('disabled')) return;
    dragging = true;
    startX = (e.touches ? e.touches[0].clientX : e.clientX);
    startLeft = knob.offsetLeft;
    e.preventDefault();
  };
  const onMove = (e) => {
    if (!dragging) return;
    const x = (e.touches ? e.touches[0].clientX : e.clientX);
    const max = slider.clientWidth - knob.clientWidth - 8;
    let left = Math.max(4, Math.min(max, startLeft + (x - startX)));
    knob.style.left = left + 'px';
    if (left >= max - 2) {
      dragging = false;
      completeDelivery();
    }
  };
  const onUp = () => {
    if (!dragging) return;
    dragging = false;
    knob.style.left = '4px';
  };

  knob.addEventListener('mousedown', onDown);
  knob.addEventListener('touchstart', onDown, { passive: false });
  window.addEventListener('mousemove', onMove);
  window.addEventListener('touchmove', onMove, { passive: false });
  window.addEventListener('mouseup', onUp);
  window.addEventListener('touchend', onUp);
}

async function completeDelivery() {
  if (!state.job) return;
  try {
    if (!state.job.steps_done.payment && !state.paymentConfirmed) {
      await api(`/api/rider/jobs/${state.job.id}/step`, { method: 'POST', body: { step: 'payment' } });
      state.paymentConfirmed = true;
    }
    await api(`/api/rider/jobs/${state.job.id}/step`, {
      method: 'POST',
      body: { step: 'delivered' },
    });
    showToast('Delivery complete!');
    state.job = null;
    state.mode = 'idle';
    state.paymentConfirmed = false;
    await refreshSummary();
    renderJob();
  } catch (e) {
    showToast(e.message);
    const knob = document.querySelector('#slide-deliver .knob');
    if (knob) knob.style.left = '4px';
  }
}

document.querySelectorAll('[data-tab]').forEach(btn => {
  btn.addEventListener('click', () => showTab(btn.dataset.tab));
});

setupSlider();
init();
