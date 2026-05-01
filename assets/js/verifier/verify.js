let activeMethod = 'qr';
let cameraStream = null;
let scanLoop     = null;
let sigFile      = null;
let ocrFile      = null;
let wmFile       = null;

function selectMethod(method) {
  activeMethod = method;
  stopCamera();
  document.querySelectorAll('.method-card').forEach(c => c.classList.remove('active'));
  document.querySelectorAll('.verify-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('m-' + method).classList.add('active');
  document.getElementById('panel-' + method).classList.add('active');
  document.getElementById('result-area').innerHTML = '';
}

async function startCamera() {
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    const video  = document.getElementById('camera-feed');
    video.srcObject = cameraStream;
    document.getElementById('start-cam-btn').style.display = 'none';
    document.getElementById('stop-cam-btn').style.display  = 'inline-block';
    scanLoop = requestAnimationFrame(scanFrame);
  } catch (e) {
    showResult('unverifiable', 'Camera access denied. Please upload a QR image instead.');
  }
}

function stopCamera() {
  if (cameraStream) { cameraStream.getTracks().forEach(t => t.stop()); cameraStream = null; }
  if (scanLoop)     { cancelAnimationFrame(scanLoop); scanLoop = null; }
  document.getElementById('start-cam-btn').style.display = 'inline-block';
  document.getElementById('stop-cam-btn').style.display  = 'none';
}

function scanFrame() {
  const video  = document.getElementById('camera-feed');
  const canvas = document.getElementById('qr-canvas');
  if (!video.videoWidth) { scanLoop = requestAnimationFrame(scanFrame); return; }
  canvas.width  = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx  = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0);
  const img  = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const code = jsQR(img.data, img.width, img.height);
  if (code) {
    stopCamera();
    sendVerifyQR(code.data);
  } else {
    scanLoop = requestAnimationFrame(scanFrame);
  }
}

function verifyQRFromFile(input) {
  const file   = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    const img  = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width  = img.width;
      canvas.height = img.height;
      const ctx  = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0);
      const data = ctx.getImageData(0, 0, img.width, img.height);
      const code = jsQR(data.data, data.width, data.height);
      if (code) sendVerifyQR(code.data);
      else showResult('unverifiable', 'No QR code detected in this image. Please try a clearer photo.');
    };
    img.src = e.target.result;
  };
  reader.readAsDataURL(file);
}

async function sendVerifyQR(qrData) {
  showVerifying();
  try {
    const res  = await fetch(`${API.VERIFICATION}/verify/qr/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ qr_data: qrData }),
    });
    handleVerifyResponse(await res.json(), res.ok);
  } catch (e) { showResult('unverifiable', 'Connection error. Please try again.'); }
}

async function verifyBySerial() {
  const serial = document.getElementById('serial-input').value.trim();
  if (!serial) { showResult('error', 'Please enter a serial number.'); return; }
  setLoading('serial-btn', true, 'Verifying...');
  try {
    const res  = await fetch(`${API.VERIFICATION}/verify/serial/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ serial_number: serial }),
    });
    handleVerifyResponse(await res.json(), res.ok);
  } catch (e) { showResult('unverifiable', 'Connection error.'); }
  finally { setLoading('serial-btn', false, 'Verify'); }
}

function verifySignature(input) {
  sigFile = input.files[0];
  if (sigFile) {
    document.getElementById('sig-filename').textContent = '📎 ' + sigFile.name;
    document.getElementById('sig-btn').style.display = 'inline-block';
  }
}

async function submitSignatureVerify() {
  if (!sigFile) return;
  setLoading('sig-btn', true, 'Verifying...');
  const fd = new FormData();
  fd.append('file', sigFile);
  try {
    const res  = await fetch(`${API.VERIFICATION}/verify/signature/`, { method: 'POST', body: fd });
    handleVerifyResponse(await res.json(), res.ok);
  } catch (e) { showResult('unverifiable', 'Connection error.'); }
  finally { setLoading('sig-btn', false, 'Verify signature'); }
}

function showOCRPreview(input) {
  ocrFile = input.files[0];
  if (ocrFile) {
    const reader = new FileReader();
    reader.onload = e => {
      document.getElementById('ocr-preview').src          = e.target.result;
      document.getElementById('ocr-preview').style.display = 'block';
      document.getElementById('ocr-btn').style.display    = 'inline-block';
    };
    reader.readAsDataURL(ocrFile);
  }
}

async function submitOCRVerify() {
  if (!ocrFile) return;
  setLoading('ocr-btn', true, 'Scanning...');
  const fd = new FormData();
  fd.append('image', ocrFile);
  try {
    const res  = await fetch(`${API.VERIFICATION}/verify/ocr/`, { method: 'POST', body: fd });
    handleVerifyResponse(await res.json(), res.ok);
  } catch (e) { showResult('unverifiable', 'Connection error.'); }
  finally { setLoading('ocr-btn', false, 'Scan & verify'); }
}

function showWMPreview(input) {
  wmFile = input.files[0];
  if (wmFile) {
    const reader = new FileReader();
    reader.onload = e => {
      document.getElementById('wm-preview').src          = e.target.result;
      document.getElementById('wm-preview').style.display = 'block';
      document.getElementById('wm-btn').style.display    = 'inline-block';
    };
    reader.readAsDataURL(wmFile);
  }
}

async function submitWatermarkVerify() {
  if (!wmFile) return;
  setLoading('wm-btn', true, 'Detecting...');
  const fd = new FormData();
  fd.append('image', wmFile);
  try {
    const res  = await fetch(`${API.VERIFICATION}/verify/watermark/`, { method: 'POST', body: fd });
    handleVerifyResponse(await res.json(), res.ok);
  } catch (e) { showResult('unverifiable', 'Connection error.'); }
  finally { setLoading('wm-btn', false, 'Detect & verify'); }
}

function handleVerifyResponse(data, ok) {
  if (!ok) { showResult('unverifiable', data.detail || 'Verification failed.'); return; }
  const status = data.status?.toUpperCase();
  if (status === 'AUTHENTIC') showResultAuthentic(data);
  else if (status === 'NOT_AUTHENTIC') showResult('not-authentic', data.message || 'No matching record found.');
  else showResult('unverifiable', data.message || 'Could not verify this item.');
}

function showVerifying() {
  document.getElementById('result-area').innerHTML = `
    <div class="q-card verifying-card">
      <div class="q-spinner verifying-spinner"></div>
      <div class="verifying-text">Querying blockchain...</div>
    </div>`;
  document.getElementById('result-area').scrollIntoView({ behavior: 'smooth' });
}

function showResultAuthentic(data) {
  document.getElementById('result-area').innerHTML = `
    <div class="q-result-authentic">
      <div class="result-header">
        <div class="result-icon result-icon--authentic">✓</div>
        <div>
          <div class="q-result-title">AUTHENTIC</div>
          <div class="result-verified-label">Verified on blockchain</div>
        </div>
      </div>
      <div class="result-details">
        ${data.item_name   ? `<div class="result-detail"><div class="result-detail-label">ITEM</div><div class="result-detail-value">${data.item_name}</div></div>` : ''}
        ${data.category    ? `<div class="result-detail"><div class="result-detail-label">CATEGORY</div><div class="result-detail-value">${data.category}</div></div>` : ''}
        ${data.issuer_name ? `<div class="result-detail"><div class="result-detail-label">ISSUED BY</div><div class="result-detail-value">${data.issuer_name}</div></div>` : ''}
        ${data.issued_date ? `<div class="result-detail"><div class="result-detail-label">ISSUE DATE</div><div class="result-detail-value">${formatDate(data.issued_date)}</div></div>` : ''}
      </div>
      ${data.blockchain_hash ? `
        <div class="result-blockchain">
          <div class="result-blockchain-label">BLOCKCHAIN RECORD</div>
          <div class="q-hash">${data.blockchain_hash}</div>
        </div>` : ''}
      <div class="result-actions">
        <span class="q-blockchain-badge">⛓ On-chain verified</span>
        <button onclick="reportItem('${data.item_id}')" class="btn-report">Report as suspicious</button>
      </div>
    </div>`;
  document.getElementById('result-area').scrollIntoView({ behavior: 'smooth' });
}

function showResult(type, message) {
  const config = {
    'not-authentic': { cls: 'q-result-not-authentic', iconCls: 'result-icon--not-authentic', icon: '✗', title: 'NOT AUTHENTIC' },
    'unverifiable':  { cls: 'q-result-unverifiable',  iconCls: 'result-icon--unverifiable',  icon: '?', title: 'UNVERIFIABLE'  },
    'error':         { cls: 'q-result-unverifiable',  iconCls: 'result-icon--unverifiable',  icon: '!', title: 'Error'         },
  };
  const c = config[type] || config['unverifiable'];
  document.getElementById('result-area').innerHTML = `
    <div class="${c.cls}">
      <div class="result-header">
        <div class="result-icon ${c.iconCls}">${c.icon}</div>
        <div>
          <div class="q-result-title">${c.title}</div>
          <div class="result-message">${message}</div>
        </div>
      </div>
    </div>`;
  document.getElementById('result-area').scrollIntoView({ behavior: 'smooth' });
}

async function reportItem(itemId) {
  if (!confirm('Report this item as suspicious?')) return;
  await fetch(`${API.VERIFICATION}/report/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ item_id: itemId }),
  });
  showToast('Report submitted. Thank you.');
}
