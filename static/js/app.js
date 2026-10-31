/* =====================================================
   Smart Healthcare PM — Frontend JS
   ===================================================== */

// ── Toast ──────────────────────────────────────────────
function toast(msg, type='ok') {
  const c = document.getElementById('toast-container');
  if (!c) return;
  const t = document.createElement('div');
  t.className = `toast toast-${type}`;
  const icon = type==='ok'?'✓':type==='err'?'✕':'ℹ';
  t.innerHTML = `<span>${icon}</span><span>${msg}</span>`;
  c.appendChild(t);
  setTimeout(()=>{ t.style.transition='opacity .4s'; t.style.opacity='0'; setTimeout(()=>t.remove(),400); }, 3500);
}

// ── Drawer ─────────────────────────────────────────────
function openDrawer(id) {
  const ov = document.getElementById(id);
  if (ov) { ov.classList.add('open'); document.body.style.overflow='hidden'; }
}
function closeDrawer(id) {
  const ov = document.getElementById(id);
  if (ov) { ov.classList.remove('open'); document.body.style.overflow=''; }
}
// close on overlay click
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('drawer-overlay')) {
    e.target.classList.remove('open');
    document.body.style.overflow='';
  }
});
// Escape key closes drawer
document.addEventListener('keydown', function(e) {
  if (e.key==='Escape') {
    document.querySelectorAll('.drawer-overlay.open').forEach(el=>{
      el.classList.remove('open'); document.body.style.overflow='';
    });
  }
});

// ── AJAX form submit ────────────────────────────────────
function submitForm(formId, drawerId, successCb) {
  const form = document.getElementById(formId);
  if (!form) return;
  // clear old errors
  form.querySelectorAll('.ferr').forEach(el=>el.remove());
  const data = new FormData(form);
  fetch(form.action, { method:'POST', body:data })
    .then(r=>r.json().then(j=>({ok:r.ok, data:j})))
    .then(({ok, data})=>{
      if (!ok || data.errors) {
        const errs = data.errors || ['An error occurred.'];
        // show first error as toast
        toast(errs[0], 'err');
        // also show inline if possible
        const firstField = form.querySelector('input,select,textarea');
        if (firstField) {
          const div = document.createElement('div');
          div.className='ferr';
          div.style.color='var(--danger)';div.style.fontSize='12px';div.style.marginTop='6px';
          div.textContent = errs.join(' | ');
          firstField.parentNode.appendChild(div);
        }
        return;
      }
      toast(data.msg || 'Saved.', 'ok');
      if (drawerId) closeDrawer(drawerId);
      if (successCb) successCb(data);
      else setTimeout(()=>window.location.reload(), 600);
    })
    .catch(()=>toast('Network error.', 'err'));
}

// ── Status date propagation ─────────────────────────────
document.addEventListener('change', function(e) {
  if (e.target.id === 'sd-picker') {
    const url = new URL(window.location);
    url.searchParams.set('sd', e.target.value);
    window.location = url.toString();
  }
});

// ── Accordion ──────────────────────────────────────────
document.addEventListener('click', function(e) {
  const h = e.target.closest('.accordion-header');
  if (!h) return;
  const body = h.nextElementSibling;
  if (!body) return;
  const isOpen = body.style.display !== 'none';
  body.style.display = isOpen ? 'none' : 'block';
  const arr = h.querySelector('.acc-arrow');
  if (arr) arr.textContent = isOpen ? '▶' : '▼';
});

// ── WBS collapse ───────────────────────────────────────
document.addEventListener('click', function(e) {
  const n = e.target.closest('.wbs-del-node');
  if (!n) return;
  const container = n.closest('.wbs-level1');
  if (!container) return;
  const children = container.querySelector('.wbs-level2-group');
  if (!children) return;
  children.style.display = children.style.display==='none' ? '' : 'none';
});

// ── Gantt render ───────────────────────────────────────
function renderGantt(ganttData, milestones, statusDate, deadline, containerId) {
  const container = document.getElementById(containerId || 'gantt-container');
  if (!container || !ganttData || !ganttData.length) {
    if (container) container.innerHTML = '<div class="empty-state"><div class="es-icon">📅</div><p>No activities to display.</p></div>';
    return;
  }
  // find date range
  const allDates = [];
  ganttData.forEach(a => {
    if (a.planned_start) allDates.push(new Date(a.planned_start));
    if (a.planned_end) allDates.push(new Date(a.planned_end));
    if (a.ee) allDates.push(new Date(a.ee));
  });
  milestones.forEach(m => { if (m.due_date) allDates.push(new Date(m.due_date)); });
  if (deadline) allDates.push(new Date(deadline));
  if (!allDates.length) return;

  const minD = new Date(Math.min(...allDates.map(d=>d.getTime())));
  const maxD = new Date(Math.max(...allDates.map(d=>d.getTime())));
  minD.setDate(minD.getDate()-3); maxD.setDate(maxD.getDate()+7);
  const totalMs = maxD - minD;

  function pct(dateStr) {
    if (!dateStr) return 0;
    const d = new Date(dateStr);
    return Math.max(0, Math.min(100, ((d - minD) / totalMs) * 100));
  }
  function width(startStr, endStr) {
    if (!startStr || !endStr) return 0;
    const s = new Date(startStr), e = new Date(endStr);
    return Math.max(0.4, ((e - s) / totalMs) * 100);
  }

  // build month labels
  const months = [];
  let cur = new Date(minD.getFullYear(), minD.getMonth(), 1);
  while (cur <= maxD) {
    months.push({ label: cur.toLocaleString('default',{month:'short',year:'2-digit'}), pct: pct(cur.toISOString().split('T')[0]) });
    cur = new Date(cur.getFullYear(), cur.getMonth()+1, 1);
  }

  const todayPct = pct(statusDate);
  const dlPct = deadline ? pct(deadline) : null;

  let html = `<div class="gantt-container">`;
  // header
  html += `<div class="gantt-header"><div class="gantt-name-col">Activity</div><div class="gantt-timeline-header" style="position:relative">`;
  months.forEach(m => {
    html += `<span style="position:absolute;left:${m.pct}%;font-size:10px;color:var(--ink3);border-left:1px solid var(--border2);padding-left:3px;top:6px;white-space:nowrap">${m.label}</span>`;
  });
  html += `</div></div>`;

  // rows
  ganttData.forEach((a, idx) => {
    const nameStyle = a.delayed ? 'color:var(--danger);font-weight:700' : '';
    let barClass = 'gantt-bar-ok';
    if (a.delayed) barClass = 'gantt-bar-delayed';
    else if (a.pct >= 100) barClass = 'gantt-bar-done';

    const ps = pct(a.planned_start), pw = width(a.planned_start, a.planned_end);
    const es = pct(a.es || a.planned_start), ew = width(a.es || a.planned_start, a.ee || a.planned_end);

    html += `<div class="gantt-row" id="grow-${a.id}" data-id="${a.id}">`;
    html += `<div class="gantt-act-name" title="${a.name}" style="${nameStyle}">${a.name}${a.delayed?' ⚠':''}</div>`;
    html += `<div class="gantt-bar-area">`;
    // today line
    html += `<div class="gantt-today" style="left:${todayPct}%" title="Status date: ${statusDate}"></div>`;
    // deadline line
    if (dlPct !== null) html += `<div class="gantt-deadline" style="left:${dlPct}%" title="Deadline: ${deadline}"></div>`;
    // planned bar (grey, behind)
    html += `<div class="gantt-bar gantt-bar-planned" style="left:${ps}%;width:${pw}%;opacity:.45" title="Planned: ${a.planned_start} → ${a.planned_end}"></div>`;
    // actual/projected bar
    html += `<div class="gantt-bar ${barClass}" style="left:${es}%;width:${ew}%" title="${a.name}: ${a.pct}% complete">`;
    html += `<div class="gantt-progress" style="width:${a.pct}%"></div>`;
    html += `<span class="gantt-bar-label">${a.pct}%</span>`;
    html += `</div>`;
    html += `</div></div>`;
  });

  // milestones
  milestones.forEach(m => {
    const mp = pct(m.due_date);
    const cls = m.status==='Completed'?'gantt-bar-done':(m.status==='Delayed'?'gantt-bar-delayed':'');
    html += `<div class="gantt-row">`;
    html += `<div class="gantt-act-name" style="font-style:italic;color:var(--ink3)" title="${m.name}">⬦ ${m.name}</div>`;
    html += `<div class="gantt-bar-area">`;
    html += `<div class="gantt-today" style="left:${todayPct}%"></div>`;
    if (dlPct !== null) html += `<div class="gantt-deadline" style="left:${dlPct}%"></div>`;
    html += `<div class="gantt-milestone ${cls}" style="left:${mp}%" title="${m.name}: ${m.due_date}"></div>`;
    html += `<span style="position:absolute;left:calc(${mp}% + 14px);top:5px;font-size:10px;color:var(--ink3);white-space:nowrap">${m.name.substring(0,14)}</span>`;
    html += `</div></div>`;
  });

  html += `<div class="gantt-legend">
    <div class="gantt-leg-item"><div class="gantt-leg-box" style="background:#B0C4DE"></div>Planned</div>
    <div class="gantt-leg-item"><div class="gantt-leg-box" style="background:var(--primary)"></div>In Progress</div>
    <div class="gantt-leg-item"><div class="gantt-leg-box" style="background:var(--danger)"></div>Delayed</div>
    <div class="gantt-leg-item"><div class="gantt-leg-box" style="background:var(--success)"></div>Complete</div>
    <div class="gantt-leg-item"><div class="gantt-leg-box" style="background:var(--warning);transform:rotate(45deg);border-radius:0"></div>Milestone</div>
    <div class="gantt-leg-item"><div style="width:12px;height:12px;border-left:2px solid var(--danger)"></div>Status date</div>
    <div class="gantt-leg-item"><div style="width:12px;height:12px;border-left:2px dashed var(--ink)"></div>Deadline</div>
  </div>`;
  html += `</div>`;
  container.innerHTML = html;

  // highlight delayed deps on click
  container.addEventListener('click', function(e) {
    const row = e.target.closest('.gantt-row[data-id]');
    if (!row) return;
    const aid = parseInt(row.dataset.id);
    const act = ganttData.find(a=>a.id===aid);
    if (!act || !act.delayed) return;
    // highlight via delayedAffected global
    if (window._delayedAffected && window._delayedAffected[aid]) {
      window._delayedAffected[aid].forEach(sid => {
        const sr = document.getElementById('grow-'+sid);
        if (sr) { sr.style.background='#FFF9C4'; setTimeout(()=>sr.style.background='',2000); }
      });
    }
  });
}

// ── Semicircle gauge ───────────────────────────────────
function drawGauge(canvasId, value, label) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  const cx = W/2, cy = H*0.78, r = H*0.65;
  // background arc
  ctx.clearRect(0,0,W,H);
  ctx.beginPath();
  ctx.arc(cx,cy,r,Math.PI,2*Math.PI);
  ctx.lineWidth=14; ctx.strokeStyle='#E2E8F0'; ctx.stroke();
  // value arc
  let color = value===null?'#CBD5E0':(value>=1.0?'#2F9E6E':(value>=0.9?'#F2A541':'#D64545'));
  const frac = value===null?0:Math.min(Math.max(value,0)/1.5,1);
  ctx.beginPath();
  ctx.arc(cx,cy,r,Math.PI,Math.PI+frac*Math.PI);
  ctx.lineWidth=14; ctx.strokeStyle=color; ctx.stroke();
  // value text
  ctx.fillStyle=color;
  ctx.font=`bold 18px 'Plus Jakarta Sans',sans-serif`;
  ctx.textAlign='center';
  ctx.fillText(value===null?'N/A':value.toFixed(3),cx,cy+4);
  ctx.fillStyle='#718096'; ctx.font=`600 11px 'IBM Plex Sans',sans-serif`;
  ctx.fillText(label,cx,cy+20);
}

// ── S-curve chart ──────────────────────────────────────
function renderScurve(canvasId, data) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !data || !data.length) return;
  if (window._scurveChart) window._scurveChart.destroy();
  window._scurveChart = new Chart(canvas, {
    type:'line',
    data:{
      labels: data.map(d=>d.month),
      datasets:[
        {label:'PV',data:data.map(d=>d.pv),borderColor:'#B0C4DE',backgroundColor:'rgba(176,196,222,.15)',tension:.3,fill:true,pointRadius:3},
        {label:'EV',data:data.map(d=>d.ev),borderColor:'#2F9E6E',backgroundColor:'rgba(47,158,110,.1)',tension:.3,fill:true,pointRadius:3},
        {label:'AC',data:data.map(d=>d.ac),borderColor:'#F2A541',backgroundColor:'rgba(242,165,65,.1)',tension:.3,fill:false,pointRadius:3},
      ]
    },
    options:{
      responsive:true, maintainAspectRatio:false,
      plugins:{legend:{position:'top',labels:{font:{family:'IBM Plex Sans'},boxWidth:12}}},
      scales:{
        y:{ticks:{callback:v=>'PKR '+(v/1000).toFixed(0)+'K',font:{family:'IBM Plex Sans',size:11}},grid:{color:'#E8EDF2'}},
        x:{ticks:{font:{family:'IBM Plex Sans',size:11}},grid:{display:false}}
      }
    }
  });
}
