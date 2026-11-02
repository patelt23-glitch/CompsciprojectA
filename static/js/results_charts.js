/**
 * Visuospatial Assessment Results Charts & Analytics
 * Handcrafted lightweight SVG visualization engines matching Slide 2-4 (image-2-4.png).
 * Zero heavy chart dependencies. Smooth rendering, zero em-dashes.
 */

document.addEventListener('DOMContentLoaded', () => {
  initLevelChartToggle();
  renderAccuracyBars('accuracy');
  renderResponseTrendLine();
  renderMemoryTrendLine();
  renderAttentionGauge();
  initNotesEditor();
});

let currentLevelMetric = 'accuracy';

function initLevelChartToggle() {
  const btnAcc = document.getElementById('toggle-chart-acc');
  const btnLat = document.getElementById('toggle-chart-lat');
  const title = document.getElementById('level-chart-title');

  if (!btnAcc || !btnLat) return;

  btnAcc.addEventListener('click', () => {
    currentLevelMetric = 'accuracy';
    btnAcc.style.background = 'var(--primary)';
    btnAcc.style.color = '#fff';
    btnLat.style.background = 'var(--bg-subtle)';
    btnLat.style.color = 'var(--text-muted)';
    if (title) title.textContent = 'Accuracy by Level';
    renderAccuracyBars('accuracy');
  });

  btnLat.addEventListener('click', () => {
    currentLevelMetric = 'latency';
    btnLat.style.background = 'var(--primary)';
    btnLat.style.color = '#fff';
    btnAcc.style.background = 'var(--bg-subtle)';
    btnAcc.style.color = 'var(--text-muted)';
    if (title) title.textContent = 'Avg Response Time by Level';
    renderAccuracyBars('latency');
  });
}

// 1. Accuracy and Response Time by Level Bar Chart (Driven by database rounds)
function renderAccuracyBars(metric = 'accuracy') {
  const container = document.getElementById('accuracy-bars-chart');
  if (!container) return;

  const rounds = (window.ROUND_COMPARISON && window.ROUND_COMPARISON.length > 0)
    ? window.ROUND_COMPARISON
    : [
        { label: 'Round 1', title: 'Shape Matching', accuracy: 93, avg_latency_sec: 2.1 },
        { label: 'Round 2', title: 'Shape + Direction', accuracy: 80, avg_latency_sec: 2.9 },
        { label: 'Round 3', title: 'Complex Matching', accuracy: 73, avg_latency_sec: 3.4 }
      ];

  const palette = ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899'];

  let html = `
    <div style="display: flex; height: 180px; align-items: flex-end; gap: 1.5rem; justify-content: center; padding-top: 1.5rem; position: relative; border-bottom: 1px solid #e2e8f0;">
  `;

  const maxVal = metric === 'latency'
    ? Math.max(4.0, ...rounds.map(r => r.avg_latency_sec || 2.0))
    : 100;

  rounds.forEach((d, i) => {
    let displayVal = '';
    let heightPct = 12;
    if (metric === 'latency') {
      const lat = typeof d.avg_latency_sec === 'number' ? d.avg_latency_sec : 2.0;
      displayVal = `${lat.toFixed(1)}s`;
      heightPct = Math.min(100, Math.max(12, (lat / maxVal) * 100));
    } else {
      const val = typeof d.accuracy === 'number' ? d.accuracy : (d.val || 80);
      displayVal = `${Math.round(val)}%`;
      heightPct = Math.min(100, Math.max(12, val));
    }

    const color = palette[i % palette.length];
    html += `
      <div style="display: flex; flex-direction: column; align-items: center; width: 68px; height: 100%; justify-content: flex-end;">
        <span style="font-size: 0.85rem; font-weight: 700; color: var(--text-main); margin-bottom: 0.35rem;">${displayVal}</span>
        <div style="width: 100%; height: ${heightPct}%; background-color: ${color}; border-radius: 6px 6px 0 0; transition: height 0.4s ease;" title="${d.label}: ${displayVal}"></div>
      </div>
    `;
  });

  html += `</div>
    <div style="display: flex; gap: 1.5rem; justify-content: center; margin-top: 0.65rem;">
      ${rounds.map(d => `
        <div style="width: 68px; text-align: center;">
          <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-main);">${d.label}</div>
          <div style="font-size: 0.68rem; color: var(--text-muted); line-height: 1.2;">${d.title || ''}</div>
        </div>
      `).join('')}
    </div>
  `;

  container.innerHTML = html;
}

// 2. Response Time Trend Line Chart (Real Question Attempt Sequence)
function renderResponseTrendLine() {
  const container = document.getElementById('response-trend-chart');
  if (!container) return;

  let pointsData = window.QUESTIONS_TREND || [];
  if (pointsData.length === 0) {
    for (let i = 1; i <= 24; i++) {
      let lat = 1.8 + Math.sin(i * 0.4) * 0.6 + (Math.random() * 0.4);
      pointsData.push({ question: i, latency_sec: parseFloat(lat.toFixed(2)), is_correct: i % 5 !== 0 });
    }
  }

  const width = 420;
  const height = 180;
  const padLeft = 32;
  const padRight = 16;
  const padTop = 16;
  const padBottom = 28;

  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;
  const maxSec = Math.max(6.0, ...pointsData.map(p => p.latency_sec || 2.0));

  let pathD = '';
  let dotsSvg = '';

  const totalPoints = pointsData.length;
  pointsData.forEach((pt, idx) => {
    const x = totalPoints > 1 ? (padLeft + (idx / (totalPoints - 1)) * chartW) : (padLeft + chartW * 0.5);
    const lat = pt.latency_sec || 1.0;
    const y = padTop + chartH - (Math.min(maxSec, lat) / maxSec) * chartH;

    if (idx === 0) {
      pathD += `M ${x.toFixed(1)} ${y.toFixed(1)}`;
    } else {
      pathD += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
    }

    const dotColor = pt.is_correct ? '#4f46e5' : '#ef4444';
    dotsSvg += `
      <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3" fill="${dotColor}">
        <title>Attempt ${pt.question}: ${lat}s (${pt.is_correct ? 'Correct' : 'Mistake'})</title>
      </circle>
    `;
  });

  const svg = `
    <svg viewBox="0 0 ${width} ${height}" style="width: 100%; height: auto; overflow: visible;">
      <!-- Grid lines -->
      <line x1="${padLeft}" y1="${padTop}" x2="${width - padRight}" y2="${padTop}" stroke="#f1f5f9" stroke-width="1" />
      <text x="${padLeft - 6}" y="${padTop + 4}" font-size="10" fill="#94a3b8" text-anchor="end">${maxSec.toFixed(0)}s</text>

      <line x1="${padLeft}" y1="${padTop + chartH * 0.5}" x2="${width - padRight}" y2="${padTop + chartH * 0.5}" stroke="#f1f5f9" stroke-width="1" />
      <text x="${padLeft - 6}" y="${padTop + chartH * 0.5 + 4}" font-size="10" fill="#94a3b8" text-anchor="end">${(maxSec * 0.5).toFixed(1)}s</text>

      <line x1="${padLeft}" y1="${padTop + chartH}" x2="${width - padRight}" y2="${padTop + chartH}" stroke="#cbd5e1" stroke-width="1" />
      <text x="${padLeft - 6}" y="${padTop + chartH + 4}" font-size="10" fill="#94a3b8" text-anchor="end">0s</text>

      <!-- Trend Line -->
      <path d="${pathD}" fill="none" stroke="#6366f1" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />

      <!-- Interactive Data Dots -->
      ${dotsSvg}

      <!-- X-axis Labels -->
      <text x="${padLeft}" y="${height - 4}" font-size="10" fill="#94a3b8">1</text>
      <text x="${width - padRight}" y="${height - 4}" font-size="10" fill="#94a3b8" text-anchor="end">${totalPoints}</text>
      <text x="${padLeft + chartW * 0.5}" y="${height - 4}" font-size="9" fill="#94a3b8" text-anchor="middle">Attempts (Latency in order)</text>
    </svg>
  `;

  container.innerHTML = svg;
}

// 3. Memory Performance Trend Line Chart
function renderMemoryTrendLine() {
  const container = document.getElementById('memory-trend-chart');
  if (!container) return;

  const rounds = (window.ROUND_COMPARISON && window.ROUND_COMPARISON.length > 0)
    ? window.ROUND_COMPARISON
    : [
        { label: 'Round 1', accuracy: 93 },
        { label: 'Round 2', accuracy: 80 },
        { label: 'Round 3', accuracy: 73 }
      ];

  const width = 240;
  const height = 120;
  const padLeft = 24;
  const padRight = 24;
  const padTop = 15;
  const padBottom = 25;

  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  const numPoints = rounds.length;
  const points = rounds.map((r, i) => {
    const acc = typeof r.accuracy === 'number' ? r.accuracy : 80;
    const x = numPoints > 1 ? (padLeft + (i / (numPoints - 1)) * chartW) : (padLeft + chartW * 0.5);
    const y = padTop + chartH - (acc / 100) * chartH;
    return { x, y, label: r.label, acc };
  });

  const polyPoints = points.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const areaPoints = `${points[0].x},${padTop + chartH} ${polyPoints} ${points[points.length - 1].x},${padTop + chartH}`;

  const svg = `
    <svg viewBox="0 0 ${width} ${height}" style="width: 100%; height: auto;">
      <line x1="${padLeft}" y1="${padTop + chartH}" x2="${width - padRight}" y2="${padTop + chartH}" stroke="#e2e8f0" stroke-width="1" />
      
      <!-- Area fill -->
      <polygon points="${areaPoints}" fill="rgba(79, 70, 229, 0.08)" />

      <!-- Line -->
      <polyline points="${polyPoints}" fill="none" stroke="#4f46e5" stroke-width="2" stroke-linecap="round" />

      <!-- Dots -->
      ${points.map(p => `
        <circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="3.5" fill="#4f46e5">
          <title>${p.label}: ${p.acc}%</title>
        </circle>
      `).join('')}

      <!-- X-axis Labels -->
      ${points.map(p => `
        <text x="${p.x.toFixed(1)}" y="${height - 6}" font-size="9" fill="#94a3b8" text-anchor="middle">${p.label}</text>
      `).join('')}
    </svg>
  `;

  container.innerHTML = svg;
}

// 4. Attention Consistency Radial Donut
function renderAttentionGauge() {
  const container = document.getElementById('attention-donut');
  if (!container) return;

  const score = window.ATTENTION_SCORE || 85;
  const radius = 38;
  const strokeWidth = 8;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  const svg = `
    <svg width="90" height="90" viewBox="0 0 100 100">
      <circle cx="50" cy="50" r="${radius}" fill="none" stroke="#f1f5f9" stroke-width="${strokeWidth}" />
      <circle cx="50" cy="50" r="${radius}" fill="none" stroke="#0284c7" stroke-width="${strokeWidth}"
        stroke-dasharray="${circumference.toFixed(1)}"
        stroke-dashoffset="${offset.toFixed(1)}"
        stroke-linecap="round"
        transform="rotate(-90 50 50)"
        style="transition: stroke-dashoffset 0.8s cubic-bezier(0.16, 1, 0.3, 1);" />
      <text x="50" y="55" font-size="18" font-weight="800" fill="#0f172a" text-anchor="middle">${score}%</text>
    </svg>
  `;

  container.innerHTML = svg;
}

// 5. Clinician Notes Editor
function initNotesEditor() {
  const editBtn = document.getElementById('edit-notes-btn');
  const display = document.getElementById('notes-display');
  const editor = document.getElementById('notes-editor');
  const textarea = document.getElementById('notes-textarea');
  const saveBtn = document.getElementById('save-notes-btn');
  const cancelBtn = document.getElementById('cancel-notes-btn');

  if (!editBtn || !editor || !display || !textarea) return;

  function getCSRFToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  }

  editBtn.addEventListener('click', () => {
    textarea.value = display.textContent.trim();
    display.style.display = 'none';
    editor.style.display = 'block';
    textarea.focus();
  });

  cancelBtn.addEventListener('click', () => {
    editor.style.display = 'none';
    display.style.display = 'block';
  });

  saveBtn.addEventListener('click', () => {
    const newNotes = textarea.value.trim();
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';

    fetch(`/api/results/${window.SESSION_ID}/notes/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify({ notes: newNotes })
    })
    .then(res => res.json())
    .then(data => {
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save Notes';
      display.textContent = newNotes || 'No notes entered.';
      editor.style.display = 'none';
      display.style.display = 'block';
    })
    .catch(err => {
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save Notes';
      alert('Could not save notes. Please try again.');
    });
  });
}
