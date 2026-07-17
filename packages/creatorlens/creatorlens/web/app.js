/* CreatorLens console — vanilla JS, no build step.
   Every rendered number traverses to its origin: score card -> evidence panel ->
   posts table; account row -> last sync run; audit event -> object + detail. */

"use strict";

const state = {
  meta: null,
  creators: [],
  targets: [],
  selectedCreatorId: null,
  selectedTargetId: 1,
  detail: null,
  posts: [],
  audience: null,
  timeline: [],
  openDimension: null,
  auditFilter: "",
};

const DIMS = [
  { key: "audience_scale", name: "Audience scale", code: "Scale",
    formula: "100 x (0.6 x logband(sum followers, 1e2..1e7) + 0.4 x logband(sum median reach, 1e2..1e6.5))" },
  { key: "engagement_quality", name: "Engagement quality", code: "Engagement",
    formula: "sum reach-weight x (0.7 x ER score + 0.3 x watch score) - ER benchmarks: ig 1.2% / tt 4.5% / yt 3.5% (benchmark = 50, 2x = 100)" },
  { key: "audience_fit", name: "Audience fit", code: "Fit",
    formula: "100 x (0.35 x age overlap + 0.30 x geo + 0.15 x gender + 0.20 x topic) vs sponsor target" },
  { key: "growth", name: "Growth", code: "Growth",
    formula: "monthly rate = 0.6 x g30 + 0.4 x (g90/3); -2%/mo = 0, +10%/mo = 100; follower-weighted" },
  { key: "consistency", name: "Consistency", code: "Consistency",
    formula: "0.5 x cadence vs norm (ig 3 / tt 4 / yt 1 per week) + 0.5 x reach stability (CV); reach-weighted" },
];

const NULL_REASONS = {
  no_target: "no sponsor target selected at computation",
  no_demographics: "no audience demographics available",
  no_posts: "no posts in the 90-day window",
  insufficient_snapshots: "not enough follower snapshots",
  no_followers_or_reach: "no follower or reach data",
};

const PLATFORM_SHORT = { instagram: "IG", youtube: "YT", tiktok: "TT" };

/* ---------- helpers ---------- */

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (_) { /* keep statusText */ }
    throw new Error(detail);
  }
  return res.json();
}

const post = (path, body) => api(path, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body || {}),
});

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function fmtNum(n) {
  if (n === null || n === undefined) return "—";
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (Math.abs(n) >= 1e4) return (n / 1e3).toFixed(0) + "k";
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1) + "k";
  return String(Math.round(n));
}
const fmtPct = (x, dp = 1) => x === null || x === undefined ? "—" : (100 * x).toFixed(dp) + "%";
const fmtDT = ts => ts ? ts.replace("T", " ").replace("Z", "") : "—";
const fmtDate = ts => ts ? ts.slice(0, 10) : "—";

function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

/* ---------- tooltip ---------- */

const tooltip = document.getElementById("tooltip");
function showTip(x, y, text) {
  tooltip.textContent = text;
  tooltip.style.left = x + "px";
  tooltip.style.top = y + "px";
  tooltip.hidden = false;
}
function hideTip() { tooltip.hidden = true; }

/* ---------- sparkline (single series, hover tooltip) ---------- */

function sparkline(snaps, width = 130, height = 28) {
  if (!snaps || snaps.length < 2) return el(`<span class="cell-sub">no snapshots</span>`);
  const values = snaps.map(s => s.followers);
  const min = Math.min(...values), max = Math.max(...values);
  const span = max - min || 1;
  const px = i => 1 + (i / (values.length - 1)) * (width - 2);
  const py = v => height - 3 - ((v - min) / span) * (height - 6);
  const pts = values.map((v, i) => `${px(i).toFixed(1)},${py(v).toFixed(1)}`).join(" ");
  const last = values.length - 1;
  const svg = el(
    `<svg class="spark" width="${width}" height="${height}" role="img" aria-label="follower trend">
       <polyline points="${pts}"></polyline>
       <circle cx="${px(last).toFixed(1)}" cy="${py(values[last]).toFixed(1)}" r="2.5"></circle>
     </svg>`);
  svg.addEventListener("mousemove", ev => {
    const rect = svg.getBoundingClientRect();
    const i = Math.max(0, Math.min(last, Math.round(((ev.clientX - rect.left) / rect.width) * last)));
    showTip(ev.clientX, ev.clientY - 6, `${snaps[i].snapshot_date}: ${fmtNum(values[i])} followers`);
  });
  svg.addEventListener("mouseleave", hideTip);
  return svg;
}

/* ---------- roster ---------- */

function coverageChip(score) {
  if (!score) return `<span class="chip">no score</span>`;
  const p = score.coverage.platforms;
  const missing = p.missing.length ? ` — missing: ${p.missing.join(", ")}` : "";
  return `<span class="chip" title="connected: ${p.list.join(", ") || "none"}${missing}">${p.connected} of ${p.total} platforms</span>`;
}

function microStrip(score) {
  const bars = DIMS.map(d => {
    const v = score ? score[d.key] : null;
    if (v === null || v === undefined)
      return `<i class="null" style="height:100%" title="${d.name}: no data"></i>`;
    return `<i style="height:${Math.max(8, v)}%" title="${d.name}: ${v}"></i>`;
  }).join("");
  return `<span class="micro">${bars}</span>`;
}

function renderRoster() {
  const tbody = document.querySelector("#roster-table tbody");
  tbody.innerHTML = "";
  document.getElementById("roster-count").textContent = `${state.creators.length} creators`;
  for (const c of state.creators) {
    const platforms = c.accounts.map(a =>
      `<span class="status" title="${a.platform}: ${a.connection_status}">` +
      `<span class="dot ${a.connection_status}"></span>${PLATFORM_SHORT[a.platform]}</span>`
    ).join(" ") || `<span class="cell-sub">none</span>`;
    const tr = el(`<tr data-id="${c.id}" class="${c.id === state.selectedCreatorId ? "selected" : ""}">
      <td><div class="cell-main">${esc(c.display_name)}</div><div class="cell-sub">@${esc(c.handle)}</div></td>
      <td><span class="chip">${esc(c.primary_topic)}</span></td>
      <td>${platforms}</td>
      <td class="num">${fmtNum(c.total_followers)}</td>
      <td>${microStrip(c.latest_score)}</td>
      <td>${coverageChip(c.latest_score)}</td>
    </tr>`);
    tr.addEventListener("click", () => selectCreator(c.id));
    tbody.appendChild(tr);
  }
}

/* ---------- detail pane ---------- */

async function selectCreator(id) {
  state.selectedCreatorId = id;
  state.openDimension = null;
  renderRoster();
  const [detail, posts, audience, timeline] = await Promise.all([
    api(`/api/creators/${id}`),
    api(`/api/creators/${id}/posts`),
    api(`/api/creators/${id}/audience`),
    api(`/api/creators/${id}/timeline`),
  ]);
  state.detail = detail;
  state.posts = posts;
  state.audience = audience;
  state.timeline = timeline;
  if (detail.latest_score && detail.latest_score.sponsor_target_id)
    state.selectedTargetId = detail.latest_score.sponsor_target_id;
  renderDetail();
}

async function refreshAll() {
  state.creators = await api("/api/creators");
  renderRoster();
  if (state.selectedCreatorId) await selectCreator(state.selectedCreatorId);
}

function renderDetail() {
  const pane = document.getElementById("detail-pane");
  const d = state.detail;
  if (!d) { pane.innerHTML = `<div class="empty-note">Select a creator.</div>`; return; }
  pane.innerHTML = "";

  const score = d.latest_score;
  const connected = d.accounts.filter(a => a.connection_status === "connected");

  /* header */
  const header = el(`<div class="detail-header">
    <h2>${esc(d.display_name)}</h2>
    <span class="handle">@${esc(d.handle)}</span>
    <span class="chip">${esc(d.primary_topic)}</span>
    ${coverageChip(score)}
    <label class="filter-label" style="margin-left:auto">Sponsor target
      <select id="target-select">${state.targets.map(t =>
        `<option value="${t.id}" ${t.id === state.selectedTargetId ? "selected" : ""}>${esc(t.name)}</option>`).join("")}
      </select>
    </label>
  </div>`);
  header.querySelector("#target-select").addEventListener("change", ev => {
    state.selectedTargetId = Number(ev.target.value);
    renderDetail(); // re-highlight audience bars against the newly selected target
  });
  pane.appendChild(header);

  /* actions */
  const missing = (state.meta ? state.meta.platforms : []).filter(
    p => !d.accounts.some(a => a.platform === p && a.connection_status === "connected"));
  const actions = el(`<div class="actions-row">
    <select id="connect-platform" ${missing.length ? "" : "disabled"}>
      ${missing.map(p => `<option value="${p}">${p}</option>`).join("") || "<option>—</option>"}
    </select>
    <button class="btn" id="btn-connect" ${missing.length ? "" : `disabled title="all platforms connected"`}>Connect platform</button>
    <button class="btn" id="btn-sync-all" ${connected.length ? "" : `disabled title="precondition: at least one connected account"`}>Sync all accounts</button>
    <button class="btn primary" id="btn-recompute" ${connected.length ? "" : `disabled title="precondition: a connected account with a succeeded sync"`}>Recompute scores</button>
  </div>`);
  actions.querySelector("#btn-connect").addEventListener("click", async () => {
    const platform = actions.querySelector("#connect-platform").value;
    await runAction(() => post(`/api/creators/${d.id}/connect`, { platform }));
  });
  actions.querySelector("#btn-sync-all").addEventListener("click", () => runAction(async () => {
    for (const a of connected) await post(`/api/accounts/${a.id}/sync`);
  }));
  actions.querySelector("#btn-recompute").addEventListener("click", () => runAction(
    () => post(`/api/creators/${d.id}/recompute`, { target_id: state.selectedTargetId })));
  pane.appendChild(actions);

  if (!d.accounts.length) {
    pane.appendChild(el(`<div class="notice">No platforms connected — scores unavailable.
      Connect a platform above to start ingesting metrics.</div>`));
  }

  /* score dimensions */
  const scoreSection = el(`<div class="section"><h3>Marketability dimensions</h3></div>`);
  if (score) {
    const grid = el(`<div class="score-grid"></div>`);
    for (const dim of DIMS) {
      const v = score[dim.key];
      const cov = (score.coverage.dimensions || {})[dim.key] || {};
      const isNull = v === null || v === undefined;
      const card = el(`<button class="score-card ${state.openDimension === dim.key ? "open" : ""}" data-dim="${dim.key}">
        <div class="dim-name">${dim.name}</div>
        <div class="dim-value ${isNull ? "null" : ""}">${isNull ? "n/a" : v}</div>
        <div class="meter"><i style="width:${isNull ? 0 : v}%"></i></div>
        <div class="conf">${isNull
          ? esc(NULL_REASONS[cov.reason] || cov.reason || "no data")
          : `confidence: ${cov.confidence} (${cov.data_points} ${String(cov.unit || "").replaceAll("_", " ")})`}</div>
      </button>`);
      card.addEventListener("click", () => {
        state.openDimension = state.openDimension === dim.key ? null : dim.key;
        renderDetail();
      });
      grid.appendChild(card);
    }
    scoreSection.appendChild(grid);
    if (state.openDimension) scoreSection.appendChild(evidencePanel(score, state.openDimension));
    scoreSection.appendChild(el(`<div class="cell-sub" style="margin-top:6px">
      computed ${fmtDT(score.computed_at)} · formulas v${score.formula_version} · window ${state.meta.window_days}d
      ${score.sponsor_target_id ? " · fit vs " + esc((state.targets.find(t => t.id === score.sponsor_target_id) || {}).name || "target " + score.sponsor_target_id) : ""}</div>`));
  } else {
    scoreSection.appendChild(el(`<div class="empty-note">No score snapshot yet${connected.length ? " — recompute scores to create one." : "."}</div>`));
  }
  pane.appendChild(scoreSection);

  /* accounts */
  const accSection = el(`<div class="section"><h3>Platform accounts</h3></div>`);
  if (d.accounts.length) {
    const table = el(`<table class="table accounts-table"><thead><tr>
      <th>Platform</th><th>Status</th><th class="num">Followers</th>
      <th>Last sync</th><th>Followers, 90d</th><th></th></tr></thead><tbody></tbody></table>`);
    const tbody = table.querySelector("tbody");
    for (const a of d.accounts) {
      const run = a.last_sync_run;
      const runText = run
        ? `${run.status} · ${fmtDT(run.finished_at)}` +
          (run.error ? ` <span class="err-text">${esc(run.error)}</span>` : "")
        : "never";
      const tr = el(`<tr>
        <td><span class="chip">${a.platform}</span> <span class="cell-sub">@${esc(a.handle)}</span></td>
        <td><span class="status"><span class="dot ${a.connection_status}"></span>${a.connection_status}</span></td>
        <td class="num">${fmtNum(a.followers)}</td>
        <td><span class="cell-sub">${runText}</span></td>
        <td class="spark-cell"></td>
        <td class="actions-cell"></td>
      </tr>`);
      const actionsCell = tr.querySelector(".actions-cell");
      if (a.connection_status !== "disconnected") {
        const syncBtn = el(`<button class="btn" ${a.connection_status === "connected" ? "" : ""}>Sync</button>`);
        syncBtn.addEventListener("click", () => runAction(() => post(`/api/accounts/${a.id}/sync`)));
        const discBtn = el(`<button class="btn">Disconnect</button>`);
        discBtn.addEventListener("click", () => {
          if (confirm(`Disconnect ${a.platform}? Historical data is retained.`))
            runAction(() => post(`/api/accounts/${a.id}/disconnect`));
        });
        actionsCell.append(syncBtn, " ", discBtn);
      } else {
        const reBtn = el(`<button class="btn">Reconnect</button>`);
        reBtn.addEventListener("click", () =>
          runAction(() => post(`/api/creators/${d.id}/connect`, { platform: a.platform })));
        actionsCell.append(reBtn);
      }
      tbody.appendChild(tr);
      api(`/api/accounts/${a.id}/snapshots?days=90`)
        .then(snaps => tr.querySelector(".spark-cell").appendChild(sparkline(snaps)))
        .catch(() => {});
    }
    accSection.appendChild(table);
  } else {
    accSection.appendChild(el(`<div class="empty-note">No accounts.</div>`));
  }
  pane.appendChild(accSection);

  /* audience */
  pane.appendChild(audienceSection());

  /* posts */
  pane.appendChild(postsSection());

  /* timeline */
  const tl = el(`<div class="section"><h3>Timeline</h3></div>`);
  if (state.timeline.length) {
    const ul = el(`<ul class="timeline"></ul>`);
    for (const e of state.timeline.slice(0, 40)) {
      ul.appendChild(el(`<li><span class="ts">${fmtDT(e.ts)}</span>
        <span class="etype">${e.event_type}</span>
        <span>${esc(eventSummary(e))} <span class="cell-sub">(${e.actor})</span></span></li>`));
    }
    tl.appendChild(ul);
  } else {
    tl.appendChild(el(`<div class="empty-note">No events yet.</div>`));
  }
  pane.appendChild(tl);
}

/* evidence panel: the inputs behind one dimension */
function evidencePanel(score, dimKey) {
  const dim = DIMS.find(x => x.key === dimKey);
  const inter = (score.inputs.intermediate || {})[dimKey];
  const cov = (score.coverage.dimensions || {})[dimKey] || {};
  const panel = el(`<div class="evidence">
    <h4>${dim.name} — evidence</h4>
    <div class="formula">${esc(dim.formula)}</div>
  </div>`);

  if (!inter) {
    panel.appendChild(el(`<div class="basis">${esc(NULL_REASONS[cov.reason] || cov.reason || "no inputs recorded")}</div>`));
    return panel;
  }

  const isPlatformKeyed = Object.values(inter).every(v => typeof v === "object" && v !== null);
  if (isPlatformKeyed && !("total_followers" in inter)) {
    const platforms = Object.keys(inter);
    const cols = Object.keys(inter[platforms[0]]);
    const table = el(`<table class="table"><thead><tr><th>Platform</th>${
      cols.map(c => `<th class="num">${c.replaceAll("_", " ")}</th>`).join("")}</tr></thead><tbody></tbody></table>`);
    for (const p of platforms) {
      table.querySelector("tbody").appendChild(el(`<tr><td>${p}</td>${
        cols.map(c => `<td class="num">${inter[p][c] === null ? "—" : inter[p][c]}</td>`).join("")}</tr>`));
    }
    panel.appendChild(table);
  } else {
    const table = el(`<table class="table"><tbody>${Object.entries(inter).map(([k, v]) =>
      `<tr><td>${k.replaceAll("_", " ")}</td><td class="num">${typeof v === "number" ? (v >= 1000 ? fmtNum(v) : v) : esc(v)}</td></tr>`).join("")}</tbody></table>`);
    panel.appendChild(table);
  }

  const kpis = score.inputs.platform_kpis || {};
  const basisBits = Object.entries(kpis).map(([p, k]) =>
    `${PLATFORM_SHORT[p]}: ${k.posts_in_window} posts, ${k.snapshot_days} snapshot days`);
  panel.appendChild(el(`<div class="basis">Basis — ${basisBits.join(" · ")}.
    Confidence ${cov.confidence || "n/a"}. Contributing posts are listed in the Posts section below.</div>`));
  return panel;
}

function audienceSection() {
  const section = el(`<div class="section"><h3>Audience vs sponsor target</h3></div>`);
  const a = state.audience;
  const target = state.targets.find(t => t.id === state.selectedTargetId);
  if (!a || !a.dimensions || !Object.keys(a.dimensions).length) {
    section.appendChild(el(`<div class="empty-note">No demographics available (Audience fit stays n/a — by design, not zero).</div>`));
    return section;
  }
  const inTarget = {
    age: new Set(target ? target.age_buckets : []),
    gender: new Set(target ? target.genders : []),
    country: new Set(target ? target.countries : []),
  };
  const grid = el(`<div class="audience-grid"></div>`);
  for (const dimName of ["age", "gender", "country"]) {
    const buckets = a.dimensions[dimName];
    if (!buckets) continue;
    const col = el(`<div><h4 style="font-size:12px;color:var(--muted);margin-bottom:6px">${dimName}</h4></div>`);
    const maxShare = Math.max(...Object.values(buckets), 0.01);
    for (const [bucket, share] of Object.entries(buckets)) {
      const hit = inTarget[dimName].has(bucket) || (dimName === "gender" && target && !target.genders.length);
      col.appendChild(el(`<div class="bar-row">
        <span class="label">${esc(bucket)}</span>
        <span class="bar-track"><span class="bar-fill ${hit ? "hit" : ""}" style="width:${(100 * share / maxShare).toFixed(1)}%"></span></span>
        <span class="val">${fmtPct(share)}</span>
      </div>`));
    }
    grid.appendChild(col);
  }
  section.appendChild(grid);
  section.appendChild(el(`<div class="legend">
    <span><span class="swatch" style="background:var(--series)"></span>in selected target</span>
    <span><span class="swatch" style="background:var(--baseline)"></span>outside target</span>
    <span>weighted by followers across ${a.platforms_with_demos} platform(s)</span>
  </div>`));
  return section;
}

function postsSection() {
  const section = el(`<div class="section"><h3>Posts (evidence layer, last 90 days)</h3></div>`);
  if (!state.posts.length) {
    section.appendChild(el(`<div class="empty-note">No posts ingested yet — connect a platform and sync.</div>`));
    return section;
  }
  const shown = state.posts.slice(0, 30);
  const table = el(`<table class="table posts-table"><thead><tr>
    <th>Published</th><th>Platform</th><th>Type</th><th>Title</th>
    <th class="num">Reach</th><th class="num">Impressions</th><th class="num">ER</th>
  </tr></thead><tbody></tbody></table>`);
  for (const p of shown) {
    table.querySelector("tbody").appendChild(el(`<tr>
      <td>${fmtDate(p.published_at)}</td>
      <td><span class="chip">${PLATFORM_SHORT[p.platform]}</span></td>
      <td>${p.content_type}</td>
      <td class="title-cell" title="${esc(p.title)}">${esc(p.title)}</td>
      <td class="num">${fmtNum(p.reach)}</td>
      <td class="num">${fmtNum(p.impressions)}</td>
      <td class="num">${fmtPct(p.engagement_rate, 2)}</td>
    </tr>`));
  }
  section.appendChild(table);
  section.appendChild(el(`<div class="cell-sub" style="margin-top:6px">showing ${shown.length} of ${state.posts.length} posts in window · metrics are each post's latest capture (older captures retained as lineage)</div>`));
  return section;
}

function eventSummary(e) {
  const d = e.detail || {};
  switch (e.event_type) {
    case "creator.created": return `creator @${d.handle} created`;
    case "account.connected": return `${d.platform} connected (@${d.handle})${d.reconnect ? " — reconnect" : ""}`;
    case "account.disconnected": return `${d.platform} disconnected — data retained`;
    case "sync.started": return `sync started — ${d.platform || ""} (${d.trigger})`;
    case "sync.finished": return `sync ${d.status}: ${d.posts_fetched} posts, ${d.metrics_written} metric captures, ${d.snapshots_written} snapshots${d.error ? " — " + d.error : ""}`;
    case "sync.failed": return `sync failed — ${d.error || d.reason || ""}`;
    case "scores.computed": {
      const dims = d.dimensions || {};
      const bits = DIMS.filter(x => dims[x.key] !== null && dims[x.key] !== undefined)
        .map(x => `${x.code} ${dims[x.key]}`);
      return `scores v${d.formula_version} — ${bits.join(", ") || "no dimensions"} (${(d.coverage || {}).connected ?? "?"}/3 platforms)`;
    }
    case "target.created": return `sponsor target "${d.name}" created`;
    default: return JSON.stringify(d);
  }
}

/* ---------- actions ---------- */

async function runAction(fn) {
  try {
    await fn();
  } catch (err) {
    alert("Action rejected: " + err.message);
  }
  await refreshAll();
}

/* ---------- audit view ---------- */

async function loadAudit() {
  const params = state.auditFilter ? `?event_type=${encodeURIComponent(state.auditFilter)}` : "";
  const events = await api(`/api/events${params}`);
  const tbody = document.querySelector("#audit-table tbody");
  tbody.innerHTML = "";
  document.getElementById("audit-count").textContent = `${events.length} events (latest first)`;
  for (const e of events) {
    tbody.appendChild(el(`<tr>
      <td class="ts" style="font-variant-numeric:tabular-nums">${fmtDT(e.ts)}</td>
      <td>${e.actor}</td>
      <td><span class="etype">${e.event_type}</span></td>
      <td class="cell-sub">${e.object_type ? `${e.object_type} #${e.object_id}` : "—"}</td>
      <td>${esc(eventSummary(e))}</td>
    </tr>`));
  }
  const filter = document.getElementById("audit-filter");
  if (filter.options.length <= 1) {
    const types = ["creator.created", "account.connected", "account.disconnected",
      "sync.started", "sync.finished", "sync.failed", "scores.computed", "target.created"];
    for (const t of types) filter.appendChild(el(`<option value="${t}">${t}</option>`));
  }
}

/* ---------- view switching & boot ---------- */

document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t === tab));
    const view = tab.dataset.view;
    document.getElementById("view-roster").hidden = view !== "roster";
    document.getElementById("view-audit").hidden = view !== "audit";
    if (view === "audit") loadAudit();
  });
});
document.getElementById("audit-filter").addEventListener("change", ev => {
  state.auditFilter = ev.target.value;
  loadAudit();
});

(async function boot() {
  const [meta, targets, creators] = await Promise.all([
    api("/api/meta"), api("/api/targets"), api("/api/creators"),
  ]);
  state.meta = meta;
  state.targets = targets;
  state.creators = creators;
  if (targets.length) state.selectedTargetId = targets[0].id;
  document.getElementById("meta-line").textContent =
    `formulas v${meta.formula_version} · window ${meta.window_days}d · ${meta.counts.post_metrics} metric captures · ${meta.counts.events} events`;
  renderRoster();
  if (creators.length) selectCreator(creators[0].id);
})();
