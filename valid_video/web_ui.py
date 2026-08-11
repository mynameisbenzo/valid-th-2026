"""HTML for the browser-based upload/match console served at GET /.

Plain HTML/CSS/JS, no build step -- talks to the same POST /upload,
GET /match, GET /videos, DELETE /videos/{id} endpoints as curl would.
"""

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>valid-video console</title>
<style>
  :root {
    --bg: #12151a;
    --panel: #171b22;
    --border: #2a2f3a;
    --text: #e8e6df;
    --text-dim: #8b93a1;
    --accent: #4fd1c5;
    --accent-dim: #2d7d75;
    --other: #f2a541;
    --danger: #e56b6b;
    --mono: "JetBrains Mono", "SF Mono", Consolas, monospace;
    --sans: -apple-system, "Segoe UI", system-ui, sans-serif;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: var(--sans);
    min-height: 100vh;
  }
  header {
    padding: 2rem 1.5rem 1rem;
    max-width: 960px;
    margin: 0 auto;
  }
  header .eyebrow {
    font-family: var(--mono);
    color: var(--accent);
    font-size: 0.75rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
  }
  header h1 {
    margin: 0.4rem 0 0.2rem;
    font-size: 1.6rem;
    font-weight: 650;
  }
  header p { color: var(--text-dim); margin: 0; font-size: 0.9rem; }

  main { max-width: 960px; margin: 0 auto; padding: 0 1.5rem 3rem; }

  #dropzone {
    position: relative;
    margin-top: 1.5rem;
    padding: 3rem 1.5rem;
    border: 1px solid var(--border);
    border-radius: 6px;
    text-align: center;
    cursor: pointer;
    transition: border-color 0.15s ease, background 0.15s ease;
    background: var(--panel);
  }
  #dropzone::before, #dropzone::after,
  #dropzone .br-tl, #dropzone .br-tr, #dropzone .br-bl, #dropzone .br-br {
    content: "";
    position: absolute;
    width: 18px;
    height: 18px;
    border-color: var(--accent-dim);
    transition: border-color 0.15s ease;
  }
  #dropzone .br-tl { top: 8px; left: 8px; border-top: 2px solid; border-left: 2px solid; }
  #dropzone .br-tr { top: 8px; right: 8px; border-top: 2px solid; border-right: 2px solid; }
  #dropzone .br-bl { bottom: 8px; left: 8px; border-bottom: 2px solid; border-left: 2px solid; }
  #dropzone .br-br { bottom: 8px; right: 8px; border-bottom: 2px solid; border-right: 2px solid; }
  #dropzone.dragover { border-color: var(--accent); background: #182029; }
  #dropzone.dragover .br-tl, #dropzone.dragover .br-tr,
  #dropzone.dragover .br-bl, #dropzone.dragover .br-br { border-color: var(--accent); }
  #dropzone:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  #dropzone .dz-title { font-size: 1rem; margin-bottom: 0.35rem; }
  #dropzone .dz-sub { color: var(--text-dim); font-size: 0.82rem; font-family: var(--mono); }
  #fileInput { display: none; }

  #pending { margin-top: 1rem; }
  .pending-row {
    display: flex; justify-content: space-between; align-items: center;
    font-family: var(--mono); font-size: 0.82rem;
    padding: 0.5rem 0.7rem; border: 1px solid var(--border); border-radius: 4px;
    margin-bottom: 0.4rem; background: var(--panel);
  }
  .pending-row .muted { color: var(--text-dim); }

  button {
    font-family: var(--sans);
    font-size: 0.85rem;
    border-radius: 4px;
    border: 1px solid var(--border);
    background: var(--panel);
    color: var(--text);
    padding: 0.5rem 0.9rem;
    cursor: pointer;
    transition: border-color 0.15s ease, color 0.15s ease;
  }
  button:hover { border-color: var(--accent); color: var(--accent); }
  button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  button.primary { background: var(--accent); color: #0b1613; border-color: var(--accent); font-weight: 600; }
  button.primary:hover { background: #6fe0d5; color: #0b1613; }
  button.danger:hover { border-color: var(--danger); color: var(--danger); }
  button:disabled { opacity: 0.4; cursor: default; }
  button:disabled:hover { border-color: var(--border); color: var(--text); }

  #uploadBar { margin-top: 0.8rem; display: flex; gap: 0.6rem; align-items: center; }
  #status { font-family: var(--mono); font-size: 0.8rem; color: var(--text-dim); }

  section.bucket { margin-top: 2.2rem; }
  section.bucket h2 {
    font-family: var(--mono);
    font-size: 0.78rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-dim);
    display: flex; align-items: center; gap: 0.5rem;
    margin-bottom: 0.6rem;
  }
  section.bucket h2 .dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--accent); display: inline-block;
  }
  section.bucket[data-bucket="Other"] h2 .dot { background: var(--other); }

  .video-card {
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--panel);
    padding: 0.75rem 0.9rem;
    margin-bottom: 0.5rem;
  }
  .video-card .row1 { display: flex; justify-content: space-between; gap: 1rem; align-items: baseline; }
  .video-card .fname {
    font-size: 0.88rem; overflow: hidden; text-overflow: ellipsis;
    white-space: nowrap; max-width: 480px;
  }
  .video-card .dims { font-family: var(--mono); font-size: 0.78rem; color: var(--text-dim); white-space: nowrap; }
  .video-card .row2 { display: flex; gap: 0.5rem; margin-top: 0.6rem; }
  .video-card .row2 button { font-size: 0.78rem; padding: 0.35rem 0.65rem; }

  .matches { margin-top: 0.6rem; padding-top: 0.6rem; border-top: 1px dashed var(--border); }
  .match-row { display: flex; justify-content: space-between; align-items: center; font-size: 0.82rem; padding: 0.25rem 0; }
  .match-row .fname { max-width: 420px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .confidence-bar {
    width: 90px; height: 6px; border-radius: 3px; background: var(--border); overflow: hidden; margin-left: 0.6rem;
  }
  .confidence-bar > div { height: 100%; background: var(--accent); }
  .confidence-val { font-family: var(--mono); font-size: 0.76rem; color: var(--text-dim); width: 38px; text-align: right; }
  .no-matches { color: var(--text-dim); font-size: 0.8rem; font-style: italic; }

  #empty-state {
    margin-top: 2rem; padding: 2rem; text-align: center;
    color: var(--text-dim); font-size: 0.88rem; font-family: var(--mono);
    border: 1px dashed var(--border); border-radius: 6px;
  }

  @media (prefers-reduced-motion: reduce) {
    * { transition: none !important; }
  }
</style>
</head>
<body>

<header>
  <div class="eyebrow">valid-video</div>
  <h1>Aspect ratio &amp; creative-match console</h1>
  <p>Drop MP4s below. Each gets bucketed by real aspect ratio and checked for visual matches against everything else you've uploaded this session.</p>
</header>

<main>
  <div id="dropzone" tabindex="0" role="button" aria-label="Upload videos">
    <span class="br-tl"></span><span class="br-tr"></span><span class="br-bl"></span><span class="br-br"></span>
    <div class="dz-title">Drag &amp; drop video files here, or click to browse</div>
    <div class="dz-sub">.mp4 &middot; multiple files supported</div>
    <input type="file" id="fileInput" accept="video/mp4" multiple>
  </div>

  <div id="pending"></div>

  <div id="uploadBar" style="display:none;">
    <button class="primary" id="uploadBtn">Upload</button>
    <button id="clearBtn">Clear</button>
    <span id="status"></span>
  </div>

  <div id="results"></div>
  <div id="empty-state">No videos uploaded yet this session.</div>
</main>

<script>
const BUCKET_ORDER = ["9:16", "1:1", "4:5", "16:9", "Other"];
let pendingFiles = [];
let uploadedVideos = [];

const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const pendingEl = document.getElementById('pending');
const uploadBar = document.getElementById('uploadBar');
const uploadBtn = document.getElementById('uploadBtn');
const clearBtn = document.getElementById('clearBtn');
const statusEl = document.getElementById('status');
const resultsEl = document.getElementById('results');
const emptyState = document.getElementById('empty-state');

dropzone.addEventListener('click', () => fileInput.click());
dropzone.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput.click(); }
});
dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
dropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropzone.classList.remove('dragover');
  addFiles(e.dataTransfer.files);
});
fileInput.addEventListener('change', () => addFiles(fileInput.files));

function addFiles(fileList) {
  for (const f of fileList) pendingFiles.push(f);
  renderPending();
}

function renderPending() {
  pendingEl.innerHTML = '';
  pendingFiles.forEach((f, i) => {
    const row = document.createElement('div');
    row.className = 'pending-row';
    row.innerHTML = `<span>${f.name}</span><span class="muted">${(f.size/1024/1024).toFixed(1)} MB</span>`;
    pendingEl.appendChild(row);
  });
  uploadBar.style.display = pendingFiles.length ? 'flex' : 'none';
}

clearBtn.addEventListener('click', () => {
  pendingFiles = [];
  fileInput.value = '';
  renderPending();
});

uploadBtn.addEventListener('click', async () => {
  if (!pendingFiles.length) return;
  uploadBtn.disabled = true;
  statusEl.textContent = `Uploading ${pendingFiles.length} file(s)...`;

  const formData = new FormData();
  pendingFiles.forEach(f => formData.append('files', f));

  try {
    const resp = await fetch('/upload', { method: 'POST', body: formData });
    if (!resp.ok) throw new Error(`Upload failed (${resp.status})`);
    const newVideos = await resp.json();
    uploadedVideos = uploadedVideos.concat(newVideos);
    pendingFiles = [];
    fileInput.value = '';
    renderPending();
    statusEl.textContent = `Uploaded ${newVideos.length} file(s).`;
    renderResults();
  } catch (err) {
    statusEl.textContent = err.message;
  } finally {
    uploadBtn.disabled = false;
  }
});

function renderResults() {
  resultsEl.innerHTML = '';
  emptyState.style.display = uploadedVideos.length ? 'none' : 'block';

  const byBucket = {};
  for (const v of uploadedVideos) {
    (byBucket[v.ratio_bucket] = byBucket[v.ratio_bucket] || []).push(v);
  }

  for (const bucket of BUCKET_ORDER) {
    const videos = byBucket[bucket];
    if (!videos || !videos.length) continue;

    const section = document.createElement('section');
    section.className = 'bucket';
    section.dataset.bucket = bucket;
    section.innerHTML = `<h2><span class="dot"></span>${bucket} &middot; ${videos.length}</h2>`;

    for (const v of videos) {
      section.appendChild(renderVideoCard(v));
    }
    resultsEl.appendChild(section);
  }
}

function renderVideoCard(v) {
  const card = document.createElement('div');
  card.className = 'video-card';
  card.innerHTML = `
    <div class="row1">
      <span class="fname" title="${v.filename}">${v.filename}</span>
      <span class="dims">${v.width}&times;${v.height} &middot; ${v.aspect_ratio}</span>
    </div>
    <div class="row2">
      <button class="matches-btn">Find matches</button>
      <button class="danger delete-btn">Delete</button>
    </div>
    <div class="matches" style="display:none;"></div>
  `;

  const matchesBtn = card.querySelector('.matches-btn');
  const matchesDiv = card.querySelector('.matches');
  matchesBtn.addEventListener('click', async () => {
    if (matchesDiv.style.display === 'block') { matchesDiv.style.display = 'none'; return; }
    matchesBtn.disabled = true;
    try {
      const resp = await fetch(`/match?video_id=${encodeURIComponent(v.video_id)}`);
      const matches = await resp.json();
      matchesDiv.innerHTML = matches.length
        ? matches.map(m => `
            <div class="match-row">
              <span class="fname" title="${m.filename}">${m.filename}</span>
              <span style="display:flex; align-items:center;">
                <div class="confidence-bar"><div style="width:${m.confidence*100}%"></div></div>
                <span class="confidence-val">${m.confidence.toFixed(2)}</span>
              </span>
            </div>`).join('')
        : '<div class="no-matches">No cross-bucket matches found.</div>';
      matchesDiv.style.display = 'block';
    } catch (err) {
      matchesDiv.innerHTML = `<div class="no-matches">${err.message}</div>`;
      matchesDiv.style.display = 'block';
    } finally {
      matchesBtn.disabled = false;
    }
  });

  card.querySelector('.delete-btn').addEventListener('click', async () => {
    await fetch(`/videos/${encodeURIComponent(v.video_id)}`, { method: 'DELETE' });
    uploadedVideos = uploadedVideos.filter(x => x.video_id !== v.video_id);
    renderResults();
  });

  return card;
}

// Load any videos already uploaded this server session (e.g. after a page refresh).
(async () => {
  try {
    const resp = await fetch('/videos');
    uploadedVideos = await resp.json();
    renderResults();
  } catch (e) { /* server not reachable yet, ignore */ }
})();
</script>
</body>
</html>
"""
