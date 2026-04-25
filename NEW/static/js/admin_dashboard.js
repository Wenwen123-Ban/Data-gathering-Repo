(() => {
  function syncToast(message) {
    const id = `t-${Date.now()}`;
    const area = document.getElementById('toastArea');
    area.insertAdjacentHTML(
      'beforeend',
      `<div id="${id}" class="toast text-bg-success"><div class="toast-body">🔄 Sync: ${message}</div></div>`,
    );
    new bootstrap.Toast(document.getElementById(id)).show();
  }

  async function loadRequests() {
    const rows = await fetch('/api/registration_requests').then((r) => r.json());
    const body = document.querySelector('#rrTable tbody');
    body.innerHTML = '';

    rows.forEach((r) =>
      body.insertAdjacentHTML(
        'beforeend',
        `<tr>
          <td>${r.request_id}</td>
          <td>${r.name}</td>
          <td>${r.school_level}/${r.year}/${r.course}</td>
          <td>${r.contact}</td>
          <td>${r.status}</td>
          <td>${
            r.status === 'pending'
              ? `<button class='btn btn-sm btn-primary' data-action='approve-request' data-id='${r.request_id}'>Approve</button>`
              : ''
          }</td>
        </tr>`,
      ),
    );
  }

  async function approveRequest(id) {
    const resp = await fetch(`/api/admin/registration_requests/${id}/approve`, { method: 'POST' });
    const data = await resp.json();
    if (data.success) {
      syncToast('Registration approved');
      loadRequests();
    }
  }

  async function loadLiveLog() {
    const rows = await fetch('/api/admin/live_log').then((r) => r.json());
    const body = document.querySelector('#logTable tbody');
    body.innerHTML = '';

    rows.forEach((r) =>
      body.insertAdjacentHTML(
        'beforeend',
        `<tr>
          <td>${r.transaction_id}</td>
          <td>${r.student_id}</td>
          <td>${r.book_id}</td>
          <td>${r.status}</td>
          <td>${r.approval_admin_id || '-'}</td>
          <td>${r.proof_image_path ? `<a href='${r.proof_image_path}' target='_blank'>Open proof</a>` : '-'}</td>
          <td><button class='btn btn-sm btn-outline-primary' data-action='approve-borrow' data-id='${r.transaction_id}'>Approve + QR</button></td>
        </tr>`,
      ),
    );
  }

  async function approveBorrow(tx) {
    const resp = await fetch('/api/admin/borrow/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transaction_id: tx, admin_id: 'admin-001' }),
    });
    const data = await resp.json();
    if (data.success) {
      syncToast(data.sync_toast);
      alert(`Temporary Link (use on mobile within ${data.expires_in_minutes} minutes): ${location.origin}${data.temporary_link}`);
      loadLiveLog();
    }
  }

  document.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-action][data-id]');
    if (!button) return;
    const id = button.dataset.id;
    if (button.dataset.action === 'approve-request') approveRequest(id);
    if (button.dataset.action === 'approve-borrow') approveBorrow(id);
  });

  Promise.all([loadRequests(), loadLiveLog()]);
  setInterval(loadLiveLog, 5000);
})();
