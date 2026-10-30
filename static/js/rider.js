const state = {
  online: false,
  job: null,
  mode: 'idle',
  pollTimer: null,
  countdownTimer: null,
  countdown: 30,
  paymentConfirmed: false,
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
  } catch (e) {
    showToast(e.message);
  }
}

function renderJob() {
  const idle = document.getElementById('idle-state');
  const offer = document.getElementById('offer-state');
  const active = document.getElementById('active-state');
  idle.classList.add('hidden');
  offer.classList.add('hidden');
  active.classList.add('hidden');

  if (state.mode === 'offer' && state.job) {
    offer.classList.remove('hidden');
    document.getElementById('offer-fee').textContent = state.job.fee_display;
    document.getElementById('offer-meta').textContent = `${state.job.distance_km} km · ~${state.job.eta_min} min`;
    document.getElementById('offer-pickup').textContent = state.job.pickup;
    document.getElementById('offer-drop').textContent = state.job.dropoff;
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
  const msg = idle.querySelector('div > div:nth-child(2)');
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
  { key: 'collected', label: 'Collected from vendor', hint: 'Upload pickup photo', photo: true },
  { key: 'seal_checked', label: 'Seal and weight checked', hint: 'Confirm factory seal' },
  { key: 'handover', label: 'Hand over the full cylinder and confirm the seal', hint: 'Customer confirms receipt' },
  { key: 'empty_collected', label: 'Collect the empty cylinder', hint: 'Take the empty back' },
  { key: 'payment', label: 'Payment', hint: 'Confirm MoMo / collect cash' },
];

function renderActive() {
  const job = state.job;
  document.getElementById('active-code').textContent = job.code;
  document.getElementById('active-step-label').textContent = `Step ${Math.min(job.current_step, 5)} of 5`;
  document.getElementById('active-drop').textContent = job.dropoff;
  document.getElementById('btn-navigate').href =
    `https://www.openstreetmap.org/directions?from=${job.vendor_lat}%2C${job.vendor_lng}&to=${job.lat}%2C${job.lng}`;
  if (job.customer_phone) {
    document.getElementById('btn-call-customer').href = `tel:${job.customer_phone}`;
  }

  const box = document.getElementById('checklist');
  box.innerHTML = '';
  let foundCurrent = false;
  STEP_DEFS.forEach((step) => {
    const done = !!job.steps_done[step.key] || (step.key === 'payment' && state.paymentConfirmed && job.payment_status === 'paid');
    // For payment prepaid: still need to tick
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

  const allDone = STEP_DEFS.every(s => {
    if (s.key === 'payment') return state.job.steps_done.payment || state.paymentConfirmed || state.job.payment_status === 'paid';
    return !!state.job.steps_done[s.key];
  });
  // payment step for momo: after ticking, steps_done.payment becomes true via session
  const ready = STEP_DEFS.slice(0, 4).every(s => !!state.job.steps_done[s.key]) &&
    (state.job.steps_done.payment || state.paymentConfirmed ||
      (['momo', 'airtel'].includes(state.job.payment_method) && state.job.payment_status === 'paid' && state.paymentConfirmed));

  const slider = document.getElementById('slide-deliver');
  const checklistComplete = STEP_DEFS.every((s, idx) => {
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
    // Ensure payment step recorded
    if (!state.job.steps_done.payment && !state.paymentConfirmed) {
      await api(`/api/rider/jobs/${state.job.id}/step`, { method: 'POST', body: { step: 'payment' } });
      state.paymentConfirmed = true;
    }
    const data = await api(`/api/rider/jobs/${state.job.id}/step`, {
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
