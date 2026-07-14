
async function fetchJSON(url, opts) {
  const res = await fetch(url, opts || {});
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || `Request failed: ${res.status}`);
  }
  return res.json();
}

function badgeFor(verdict) {
  if (verdict === 'NEW') return 'pill-good';
  if (verdict === 'UPDATE') return 'pill-warn';
  if (verdict === 'DUPLICATE') return 'pill-bad';
  return '';
}

function readBadge(i) {
  const r = i.impact?.should_you_read?.recommendation || 'Watch';
  if (r === 'Read Now') return 'pill-good';
  if (r === 'Evaluate' || r === 'Compare Against Current Approach' || r === 'Watch') return 'pill-warn';
  if (r === 'Skim' || r === 'File Away') return 'pill-warn';
  return 'pill-bad'; // Ignore
}

async function loadLatest() {
  const data = await fetchJSON('/api/latest');
  const items = data.items || [];
  const stats = document.getElementById('stats');
  const itemsEl = document.getElementById('items');
  const repairsEl = document.getElementById('repairs');

  const counts = {
    total: items.length,
    new: items.filter(i => i.novelty_verdict === 'NEW').length,
    update: items.filter(i => i.novelty_verdict === 'UPDATE').length,
    dup: items.filter(i => i.novelty_verdict === 'DUPLICATE').length,
    avgSignal: items.length ? Math.round(items.reduce((s, i) => s + (i.impact?.signal_score || 0), 0) / items.length) : 0,
  };

  stats.innerHTML = `
    <div class="stat"><div class="muted small">Latest items</div><div class="n">${counts.total}</div></div>
    <div class="stat"><div class="muted small">New</div><div class="n">${counts.new}</div></div>
    <div class="stat"><div class="muted small">Updates</div><div class="n">${counts.update}</div></div>
    <div class="stat"><div class="muted small">Avg signal</div><div class="n">${counts.avgSignal}</div></div>
  `;

  itemsEl.innerHTML = items.map(i => `
    <div class="item">
      <div class="flex" style="align-items:center; justify-content:space-between;">
        <div>
          <span class="badge ${badgeFor(i.novelty_verdict)}">${i.novelty_verdict || 'UNKNOWN'}</span>
          <span class="badge">${i.source_category}</span>
          ${i.impact?.should_you_read?.recommendation ? `<span class="badge ${readBadge(i)}">${i.impact.should_you_read.recommendation}</span>` : ''}
        </div>
        <div class="muted small">${i.source_name}</div>
      </div>
      <h3 style="margin:10px 0 8px;">${i.title}</h3>
      ${i.impact ? `
        <p><strong>${i.impact.headline}</strong></p>
        <p class="muted">${i.impact.executive_summary || ''}</p>
        <div class="flex" style="margin: 10px 0;">
          <span class="badge">Signal ${i.impact.signal_score || 0}/100</span>
          <span class="badge">${i.impact.signal_type || 'general'}</span>
        </div>
        <ul>
          ${(i.impact.what_changed || []).slice(0,4).map(b => `<li>${b}</li>`).join('')}
        </ul>
        <p class="muted"><strong>Action:</strong> ${i.impact.recommended_action || ''}</p>
        <p class="muted">${i.impact.why_it_matters?.product || ''}</p>
      ` : `<p class="muted">No impact analysis stored yet.</p>`}
      <p class="small"><a href="${i.url}" target="_blank">Open source</a></p>
      <p class="small muted">Confidence: ${((i.novelty_confidence || 0) * 100).toFixed(0)}%</p>
    </div>
  `).join('');

  const repairs = await fetchJSON('/api/repairs');
  repairsEl.innerHTML = (repairs.items || []).map(r => `
    <div class="repair">
      <div class="badge">${r.status}</div>
      <h3>${r.title}</h3>
      <pre>${r.proposal_text}</pre>
    </div>
  `).join('') || '<p class="muted">No repair proposals.</p>';
}

async function runDigest() {
  await fetchJSON('/api/daily-digest');
  await loadLatest();
}

loadLatest().catch(err => {
  console.error(err);
  document.getElementById('items').innerHTML = `<p class="muted">Failed to load dashboard.</p>`;
});
