/* ── State ── */
let activeMethod   = 'qr';
let cameraStream   = null;
let scanLoop       = null;
let sigFile        = null;
let ocrFile        = null;
let wmFile         = null;
let selectedItem   = null;
let allItems       = [];
let displayedItems = [];

/* ── Step 1: Item list ── */

function loadItems() {
  allItems = [
    /* ── Certificates ── */
    { id: 1, name: 'Bachelor of Science in Computer Engineering', category: 'Certificate', issuer_name: 'ICT University Cameroon',    created_at: '2026-03-15T10:00:00Z' },
    { id: 2, name: 'Master of Business Administration (MBA)',      category: 'Certificate', issuer_name: 'University of Yaoundé I',    created_at: '2026-02-20T09:30:00Z' },
    { id: 3, name: 'Doctor of Medicine (MD)',                      category: 'Certificate', issuer_name: 'Faculty of Medicine UBUEA',  created_at: '2026-01-10T08:00:00Z' },
    { id: 4, name: 'BACC Série C — 2026',                         category: 'Certificate', issuer_name: 'Office du Bac Cameroun',     created_at: '2026-04-05T08:00:00Z' },
    /* ── Pharmaceuticals ── */
    { id: 5, name: 'Amoxicillin 500mg — Batch #AMX-2026-004',     category: 'Drug',        issuer_name: 'PharmaLink Cameroon',        created_at: '2026-04-01T11:00:00Z' },
    { id: 6, name: 'Artemether-Lumefantrine 80/480mg — B#AL-089', category: 'Drug',        issuer_name: 'MedSupply Africa Ltd',       created_at: '2026-03-28T14:00:00Z' },
    { id: 7, name: 'Paracétamol 1000mg — Batch #PCM-2026-017',    category: 'Drug',        issuer_name: 'LABOREX Cameroun',           created_at: '2026-03-10T09:00:00Z' },
    { id: 8, name: 'Quinine 300mg — Batch #QNN-2026-003',         category: 'Drug',        issuer_name: 'CENAME',                     created_at: '2026-02-18T10:30:00Z' },
    /* ── Currency ── */
    { id: 9,  name: '500 FCFA Banknote — Series 2023-B',          category: 'Banknote',    issuer_name: 'BEAC — Banque Centrale',     created_at: '2023-06-01T00:00:00Z' },
    { id: 10, name: '1000 FCFA Banknote — Series 2024-A',         category: 'Banknote',    issuer_name: 'BEAC — Banque Centrale',     created_at: '2024-01-15T00:00:00Z' },
    { id: 11, name: '5000 FCFA Banknote — Series 2024-C',         category: 'Banknote',    issuer_name: 'BEAC — Banque Centrale',     created_at: '2024-06-01T00:00:00Z' },
    { id: 12, name: '10000 FCFA Banknote — Series 2025-A',        category: 'Banknote',    issuer_name: 'BEAC — Banque Centrale',     created_at: '2025-01-01T00:00:00Z' },
    /* ── Official Documents ── */
    { id: 13, name: 'National Identity Card — CNI 2025',           category: 'Document',    issuer_name: 'DGSN — Délégation Générale',  created_at: '2025-03-01T08:00:00Z' },
    { id: 14, name: 'Cameroonian Passport — Type P',               category: 'Document',    issuer_name: 'DGSN — Délégation Générale',  created_at: '2025-06-15T09:00:00Z' },
    { id: 15, name: 'Birth Certificate — Acte de Naissance',       category: 'Document',    issuer_name: 'État Civil — Mairie Yaoundé', created_at: '2026-01-20T08:30:00Z' },
    { id: 16, name: 'Business Registration — Registre du Commerce', category: 'Document',   issuer_name: 'CFCE Cameroun',               created_at: '2026-02-10T10:00:00Z' },
  ];
  document.getElementById('items-loading').style.display = 'none';
  renderItems(allItems);
}

function filterItems(query) {
  const q        = query.toLowerCase().trim();
  const filtered = q
    ? allItems.filter(item =>
        (item.name         || '').toLowerCase().includes(q) ||
        (item.category     || '').toLowerCase().includes(q) ||
        (item.issuer_name  || '').toLowerCase().includes(q)
      )
    : allItems;
  renderItems(filtered);
}

function renderItems(items) {
  displayedItems = items;
  const grid  = document.getElementById('items-grid');
  const empty = document.getElementById('items-empty');

  if (!items.length) {
    grid.innerHTML = '';
    empty.style.display = 'block';
    return;
  }

  empty.style.display = 'none';
  grid.innerHTML = items.map((item, i) => `
    <div class="item-card" onclick="selectItem(${i})">
      <span class="q-badge q-badge-active">${item.category || 'Item'}</span>
      <div class="item-card-name">${item.name}</div>
      <div class="item-card-issuer">${item.issuer_name || item.institution_name || '—'}</div>
      <div class="item-card-date">${formatDate(item.created_at)}</div>
      <div class="item-card-action">Verify this item →</div>
    </div>
  `).join('');
}

function selectItem(idx) {
  const item = displayedItems[idx];
  if (!item) return;
  selectedItem = item;

  document.getElementById('step-items').style.display  = 'none';
  document.getElementById('step-verify').style.display = 'block';

  document.getElementById('selected-name').textContent = item.name;
  document.getElementById('selected-meta').textContent =
    [item.category, item.issuer_name ? 'by ' + item.issuer_name : ''].filter(Boolean).join(' · ');

  document.getElementById('result-area').innerHTML = '';
  selectMethod('qr');
}

function goBack() {
  selectedItem = null;
  stopCamera();
  document.getElementById('step-verify').style.display = 'none';
  document.getElementById('step-items').style.display  = 'block';
  document.getElementById('result-area').innerHTML     = '';
}

/* ── Step 2: Method switcher ── */

function selectMethod(method) {
  activeMethod = method;
  stopCamera();
  document.querySelectorAll('.method-card').forEach(c => c.classList.remove('active'));
  document.querySelectorAll('.verify-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('m-'     + method).classList.add('active');
  document.getElementById('panel-' + method).classList.add('active');
  document.getElementById('result-area').innerHTML = '';
}

/* ── QR camera ── */

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
  const startBtn = document.getElementById('start-cam-btn');
  const stopBtn  = document.getElementById('stop-cam-btn');
  if (startBtn) startBtn.style.display = 'inline-block';
  if (stopBtn)  stopBtn.style.display  = 'none';
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
  if (code) { stopCamera(); sendVerifyQR(code.data); }
  else { scanLoop = requestAnimationFrame(scanFrame); }
}

function verifyQRFromFile(input) {
  const file = input.files[0];
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
    const res = await fetch(`${API.VERIFICATION}/verify/qr/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ qr_data: qrData, item_id: selectedItem?.id }),
    });
    handleVerifyResponse(await res.json(), res.ok);
  } catch (e) { showResult('unverifiable', 'Connection error. Please try again.'); }
}

/* ── Serial number ── */

async function verifyBySerial() {
  const serial = document.getElementById('serial-input').value.trim();
  if (!serial) { showResult('error', 'Please enter a serial number.'); return; }
  setLoading('serial-btn', true, 'Verifying...');
  try {
    const res = await fetch(`${API.VERIFICATION}/verify/serial/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ serial_number: serial, item_id: selectedItem?.id }),
    });
    handleVerifyResponse(await res.json(), res.ok);
  } catch (e) { showResult('unverifiable', 'Connection error.'); }
  finally { setLoading('serial-btn', false, 'Verify'); }
}

/* ── Signature ── */

function verifySignature(input) {
  sigFile = input.files[0];
  if (sigFile) {
    document.getElementById('sig-filename').textContent = '📎 ' + sigFile.name;
    document.getElementById('sig-btn').style.display   = 'inline-block';
  }
}

async function submitSignatureVerify() {
  if (!sigFile) return;
  setLoading('sig-btn', true, 'Verifying...');
  const fd = new FormData();
  fd.append('file', sigFile);
  if (selectedItem?.id) fd.append('item_id', selectedItem.id);
  try {
    const res = await fetch(`${API.VERIFICATION}/verify/signature/`, { method: 'POST', body: fd });
    handleVerifyResponse(await res.json(), res.ok);
  } catch (e) { showResult('unverifiable', 'Connection error.'); }
  finally { setLoading('sig-btn', false, 'Verify signature'); }
}

/* ── OCR ── */

function showOCRPreview(input) {
  ocrFile = input.files[0];
  if (ocrFile) {
    const reader = new FileReader();
    reader.onload = e => {
      document.getElementById('ocr-preview').src           = e.target.result;
      document.getElementById('ocr-preview').style.display = 'block';
      document.getElementById('ocr-btn').style.display     = 'inline-block';
    };
    reader.readAsDataURL(ocrFile);
  }
}

async function submitOCRVerify() {
  if (!ocrFile) return;
  setLoading('ocr-btn', true, 'Scanning...');
  const fd = new FormData();
  fd.append('image', ocrFile);
  if (selectedItem?.id) fd.append('item_id', selectedItem.id);
  try {
    const res = await fetch(`${API.VERIFICATION}/verify/ocr/`, { method: 'POST', body: fd });
    handleVerifyResponse(await res.json(), res.ok);
  } catch (e) { showResult('unverifiable', 'Connection error.'); }
  finally { setLoading('ocr-btn', false, 'Scan & verify'); }
}

/* ── Watermark ── */

function showWMPreview(input) {
  wmFile = input.files[0];
  if (wmFile) {
    const reader = new FileReader();
    reader.onload = e => {
      document.getElementById('wm-preview').src           = e.target.result;
      document.getElementById('wm-preview').style.display = 'block';
      document.getElementById('wm-btn').style.display     = 'inline-block';
    };
    reader.readAsDataURL(wmFile);
  }
}

async function submitWatermarkVerify() {
  if (!wmFile) return;
  setLoading('wm-btn', true, 'Detecting...');
  const fd = new FormData();
  fd.append('image', wmFile);
  if (selectedItem?.id) fd.append('item_id', selectedItem.id);
  try {
    const res = await fetch(`${API.VERIFICATION}/verify/watermark/`, { method: 'POST', body: fd });
    handleVerifyResponse(await res.json(), res.ok);
  } catch (e) { showResult('unverifiable', 'Connection error.'); }
  finally { setLoading('wm-btn', false, 'Detect & verify'); }
}

/* ── Result rendering ── */

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

/* ── Boot ── */
loadItems();
