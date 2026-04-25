(() => {
  const STUDENT_ID = 'stu-001';

  function syncToast(message) {
    const id = `t-${Date.now()}`;
    const html = `<div id="${id}" class="toast align-items-center text-bg-primary border-0" role="alert"><div class="d-flex"><div class="toast-body">🔄 Sync: ${message}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div></div>`;
    document.getElementById('toastArea').insertAdjacentHTML('beforeend', html);
    new bootstrap.Toast(document.getElementById(id)).show();
  }

  async function loadReservations() {
    const txs = await fetch('/api/transactions').then((r) => r.json());
    const body = document.querySelector('#reservationTable tbody');
    body.innerHTML = '';

    txs
      .filter((t) => t.student_id === STUDENT_ID && ['reserved', 'approved'].includes((t.status || '').toLowerCase()))
      .forEach((t) => {
        body.insertAdjacentHTML(
          'beforeend',
          `<tr>
            <td>${t.transaction_id}</td>
            <td>${t.book_id}</td>
            <td>${t.reservation_date}</td>
            <td>${t.approval_admin_id || '-'}</td>
            <td>
              <button class="btn btn-sm btn-outline-danger" data-action="cancel" data-id="${t.transaction_id}">Cancel</button>
              <button class="btn btn-sm btn-outline-primary" data-action="extend" data-id="${t.transaction_id}">Extend</button>
            </td>
          </tr>`,
        );
      });
  }

  async function cancelReservation(id) {
    const resp = await fetch('/api/reservations/cancel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transaction_id: id }),
    });
    const data = await resp.json();
    if (data.success) {
      syncToast(data.sync_toast);
      loadReservations();
      loadNotifications();
    }
  }

  async function extendReservation(id) {
    const resp = await fetch('/api/reservations/extend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transaction_id: id }),
    });
    const data = await resp.json();
    if (resp.ok) {
      syncToast(data.sync_toast);
    } else {
      syncToast(`Extend blocked: ${data.message}`);
    }
    loadReservations();
    loadNotifications();
  }

  async function loadNotifications() {
    const notifs = await fetch(`/api/users/${STUDENT_ID}/notifications`).then((r) => r.json());
    const list = document.getElementById('notifList');
    list.innerHTML = '';
    notifs.forEach((n) =>
      list.insertAdjacentHTML('beforeend', `<li class="list-group-item">${n.message}<br><small>${n.timestamp}</small></li>`),
    );
  }

  document.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-action][data-id]');
    if (!button) return;
    const id = button.dataset.id;
    if (button.dataset.action === 'cancel') cancelReservation(id);
    if (button.dataset.action === 'extend') extendReservation(id);
  });

  setInterval(loadNotifications, 5000);
  Promise.all([loadReservations(), loadNotifications()]);
})();
