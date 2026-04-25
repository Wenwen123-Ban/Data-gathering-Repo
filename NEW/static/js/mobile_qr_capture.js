(() => {
  const token = document.body.dataset.token;

  async function boot() {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false });
    document.getElementById('video').srcObject = stream;
  }

  async function capture() {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    const image_data = canvas.toDataURL('image/jpeg', 0.85);
    const resp = await fetch(`/api/mobile/upload-proof/${token}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_data }),
    });
    const data = await resp.json();
    alert(data.success ? `Uploaded to server path: ${data.path}` : data.message);
  }

  document.getElementById('captureBtn').addEventListener('click', capture);
  boot();
})();
