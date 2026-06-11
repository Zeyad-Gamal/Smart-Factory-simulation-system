/* ═══════════════════════════════════════════════════════════════
   SOC — AI Agent Bridge  |  app.js
   ═══════════════════════════════════════════════════════════════ */
(function () {
    'use strict';

    // ── State ────────────────────────────────────────────────────
    let socket          = null;
    let ingestLogs      = [];        // all received logs (newest first)
    let pendingMap      = {};        // decision_id → decision
    let historyList     = [];        // resolved decisions
    let decisionQueue   = [];        // decisions waiting for modal
    let currentDecision = null;      // currently shown in modal
    let sevCounts       = { critical:0, high:0, medium:0, low:0, info:0 };
    let statsApproved   = 0;
    let statsRejected   = 0;
    let historyFilter   = 'all';

    // ── Helpers ───────────────────────────────────────────────────
    const $  = id => document.getElementById(id);
    const $$ = s  => document.querySelectorAll(s);

    function esc(str) {
        if (typeof str !== 'string') str = String(str || '');
        return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }
    function fmtTime(iso) {
        if (!iso) return '—';
        try { return new Date(iso).toLocaleTimeString('en-GB', { hour12: false }); }
        catch { return iso.slice(11, 19) || '—'; }
    }
    function fmtDateTime(iso) {
        if (!iso) return '—';
        try { return new Date(iso).toLocaleString('en-GB', { hour12: false }); }
        catch { return iso; }
    }
    function shortId(id) { return (id || '').slice(0, 8).toUpperCase(); }

    const SEV_COLOR = {
        critical: '#ff2d55', high: '#ff6b35',
        medium: '#f59e0b',   low: '#00ff88', info: '#00d4ff'
    };
    function sevColor(sev) { return SEV_COLOR[(sev||'info').toLowerCase()] || SEV_COLOR.info; }

    // ── Boot sequence ─────────────────────────────────────────────
    function boot() {
        const fill = $('bootFill');
        const pre  = $('preloader');
        if (!pre) return done();
        let pct = 0;
        const iv = setInterval(() => {
            pct += Math.random() * 22 + 6;
            if (fill) fill.style.width = Math.min(pct, 98) + '%';
            if (pct >= 100) {
                clearInterval(iv);
                if (fill) fill.style.width = '100%';
                setTimeout(() => {
                    pre.classList.add('hidden');
                    setTimeout(() => { pre.style.display = 'none'; done(); }, 600);
                }, 300);
            }
        }, 200);
    }
    function done() {
        const app = $('app');
        if (app) app.style.display = 'flex';
        startClock();
        bindNav();
        bindModal();
        bindFilters();
        connectSocket();
        loadInitialData();
    }

    // ── Clock ─────────────────────────────────────────────────────
    function startClock() {
        const update = () => {
            const el = $('clock');
            if (el) el.textContent = new Date().toISOString().slice(11, 19);
        };
        update();
        setInterval(update, 1000);
    }

    // ── Navigation ────────────────────────────────────────────────
    const PAGE_NAMES = {
        dashboard: 'overview',
        logs:      'ingest-logs',
        decisions: 'ai-decisions',
        history:   'decision-history',
    };

    function bindNav() {
        $$('.nav-item').forEach(a => {
            a.addEventListener('click', e => {
                e.preventDefault();
                const p = a.getAttribute('data-page');
                if (p) navigateTo(p);
                const sb = $('sidebar');
                if (sb) sb.classList.remove('mobile-open');
            });
        });
        $('sidebarToggle')?.addEventListener('click', () => {
            $('sidebar')?.classList.toggle('collapsed');
        });
        $('mobileToggle')?.addEventListener('click', () => {
            $('sidebar')?.classList.toggle('mobile-open');
        });
    }

    function navigateTo(page) {
        $$('.page').forEach(p => p.classList.remove('active'));
        $$('.nav-item').forEach(a => a.classList.remove('active'));
        const pg = $(`page-${page}`);
        if (pg) pg.classList.add('active');
        const na = document.querySelector(`.nav-item[data-page="${page}"]`);
        if (na) na.classList.add('active');
        const cp = $('currentPage');
        if (cp) cp.textContent = PAGE_NAMES[page] || page;

        // Render page-specific content
        if (page === 'logs')      renderLogsPage();
        if (page === 'decisions') renderDecisionsPage();
        if (page === 'history')   renderHistoryPage();
    }

    // ── Socket.IO ─────────────────────────────────────────────────
    function connectSocket() {
        socket = io();

        socket.on('connect', () => {
            setConnStatus(true);
            setAlert('Connected to SOC backend — monitoring active', 'success');
        });
        socket.on('disconnect', () => {
            setConnStatus(false);
            setAlert('Connection lost — attempting to reconnect...', 'warning');
        });
        socket.on('ingest_log', log => {
            ingestLogs.unshift(log);
            sevCounts[(log.severity||'info').toLowerCase()] = (sevCounts[(log.severity||'info').toLowerCase()]||0) + 1;
            updateKPIs();
            updateSevBars();
            renderDashLogFeed();
            updateNavCount('navCountLogs', ingestLogs.length);
            // Update logs page if open
            if ($('page-logs')?.classList.contains('active')) renderLogsPage();
        });
        socket.on('ai_decision', decision => {
            pendingMap[decision.decision_id] = decision;
            updateKPIs();
            updateNavBadgeDecisions();
            renderDashDecisionFeed();
            if ($('page-decisions')?.classList.contains('active')) renderDecisionsPage();
            // Show modal
            if (!currentDecision) showModal(decision);
            else {
                decisionQueue.push(decision);
                updateQueueBar();
            }
            toast(`🤖 AI: ${decision.threat_type} — ${(decision.severity||'').toUpperCase()}`, 'critical');
        });
        socket.on('decision_resolved', decision => {
            delete pendingMap[decision.decision_id];
            historyList.unshift(decision);
            if (decision.status === 'approved') statsApproved++;
            else statsRejected++;
            updateKPIs();
            updateNavBadgeDecisions();
            renderDashDecisionFeed();
            if ($('page-decisions')?.classList.contains('active')) renderDecisionsPage();
            if ($('page-history')?.classList.contains('active')) renderHistoryPage();
        });
    }

    function setConnStatus(online) {
        const dot   = $('connDot');
        const label = $('connLabel');
        if (dot)   { dot.className = 'live-dot ' + (online ? 'online' : 'offline'); }
        if (label) { label.textContent = online ? 'LIVE' : 'OFFLINE'; }
    }

    function setAlert(msg, type = 'info') {
        const strip = $('alertStrip');
        const msgEl = $('alertMsg');
        if (!strip || !msgEl) return;
        strip.style.display = 'flex';
        strip.className = `alert-strip ${type}`;
        msgEl.textContent = msg;
        const icons = { info:'fa-circle-info', success:'fa-circle-check', warning:'fa-triangle-exclamation', critical:'fa-skull' };
        const i = strip.querySelector('i');
        if (i) i.className = `fas ${icons[type]||icons.info}`;
    }

    // ── Initial data load ─────────────────────────────────────────
    async function loadInitialData() {
        try {
            const [logsRes, pendRes, histRes] = await Promise.all([
                fetch('/api/ingest/logs?limit=100'),
                fetch('/api/decisions/pending'),
                fetch('/api/decisions/history?limit=50'),
            ]);
            const logsData = await logsRes.json();
            const pendData = await pendRes.json();
            const histData = await histRes.json();

            ingestLogs = logsData.logs || [];
            ingestLogs.forEach(l => {
                const s = (l.severity||'info').toLowerCase();
                sevCounts[s] = (sevCounts[s]||0) + 1;
            });

            (pendData.decisions || []).forEach(d => { pendingMap[d.decision_id] = d; });

            historyList = histData.decisions || [];
            statsApproved = historyList.filter(d => d.status === 'approved').length;
            statsRejected = historyList.filter(d => d.status === 'rejected').length;

            updateKPIs();
            updateSevBars();
            renderDashLogFeed();
            renderDashDecisionFeed();
            updateNavCount('navCountLogs', ingestLogs.length);
            updateNavBadgeDecisions();

            // Show first pending decision if any
            const pending = Object.values(pendingMap);
            if (pending.length > 0) {
                const [first, ...rest] = pending;
                decisionQueue = rest;
                showModal(first);
            }
        } catch (e) {
            console.error('Initial load error:', e);
        }
    }

    // ── KPIs ──────────────────────────────────────────────────────
    function updateKPIs() {
        setText('kpiLogsTotal',        ingestLogs.length);
        setText('kpiDecisionsPending', Object.keys(pendingMap).length);
        setText('kpiApproved',         statsApproved);
        setText('kpiRejected',         statsRejected);

        // THREATCON
        const pending = Object.values(pendingMap);
        const hasCrit = pending.some(d => d.severity === 'critical') ||
                        ingestLogs.slice(0,20).some(l => l.severity === 'critical');
        const hasHigh = pending.some(d => d.severity === 'high') ||
                        ingestLogs.slice(0,20).some(l => l.severity === 'high');
        let tc = 5, status = 'NORMAL', color = '#00ff88';
        if (hasCrit)               { tc = 1; status = 'MAXIMUM';  color = '#ff2d55'; }
        else if (hasHigh)          { tc = 2; status = 'ELEVATED'; color = '#ff6b35'; }
        else if (pending.length>0) { tc = 3; status = 'GUARDED';  color = '#f59e0b'; }
        setText('tcLevel', tc);
        setText('tcStatus', status);
        const lvl = $('tcLevel');
        const sta = $('tcStatus');
        if (lvl) lvl.style.color = color;
        if (sta) sta.style.color = color;
    }

    function setText(id, val) {
        const el = $(id);
        if (el) el.textContent = val ?? '--';
    }

    // ── Severity bars ─────────────────────────────────────────────
    function updateSevBars() {
        const total = Math.max(1, Object.values(sevCounts).reduce((a,b)=>a+b,0));
        ['critical','high','medium','low','info'].forEach(s => {
            const bar = $(`sevBar${s.charAt(0).toUpperCase()+s.slice(1)}`);
            const cnt = $(`sevCount${s.charAt(0).toUpperCase()+s.slice(1)}`);
            const pct = Math.round(((sevCounts[s]||0)/total)*100);
            if (bar) bar.style.width = pct + '%';
            if (cnt) cnt.textContent = sevCounts[s]||0;
        });
    }

    // ── Nav badges ────────────────────────────────────────────────
    function updateNavBadgeDecisions() {
        const badge = $('navCountDecisions');
        if (!badge) return;
        const count = Object.keys(pendingMap).length;
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline-flex' : 'none';
    }

    function updateNavCount(id, count) {
        const el = $(id);
        if (el) el.textContent = count;
    }

    // ── Dashboard feeds ───────────────────────────────────────────
    function renderDashLogFeed() {
        const container = $('dashLogFeed');
        if (!container) return;
        const recent = ingestLogs.slice(0, 20);
        if (!recent.length) {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-inbox"></i> No logs received yet</div>';
            return;
        }
        container.innerHTML = recent.map(l => `
            <div class="feed-row">
                <span class="feed-sev ${(l.severity||'info').toLowerCase()}">${(l.severity||'INFO').toUpperCase()}</span>
                <div class="feed-main">
                    <div class="feed-msg">${esc(l.message||'—')}</div>
                    <div class="feed-meta">${esc(l.source||'—')}</div>
                </div>
                <span class="feed-time">${fmtTime(l.received)}</span>
            </div>
        `).join('');
    }

    function renderDashDecisionFeed() {
        const container = $('dashDecisionFeed');
        const badge     = $('dashPendingBadge');
        const decisions = Object.values(pendingMap);
        if (badge) badge.textContent = decisions.length;
        if (!container) return;
        if (!decisions.length) {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-check-circle"></i> No pending decisions</div>';
            return;
        }
        container.innerHTML = decisions.map(d => {
            const col = sevColor(d.severity);
            const conf = Math.min(100, Number(d.confidence)||0);
            return `
            <div class="dash-dec-card" onclick="App.openDecision('${d.decision_id}')">
                <div class="dash-dec-sev" style="background:${col};"></div>
                <div class="dash-dec-info">
                    <div class="dash-dec-type">${esc(d.threat_type||'—')}</div>
                    <div class="dash-dec-action">${esc(d.decision||'—')}</div>
                </div>
                <div class="dash-dec-conf">${conf}%</div>
            </div>`;
        }).join('');
    }

    // ── Logs page ─────────────────────────────────────────────────
    function renderLogsPage() {
        const tbody  = $('logTableBody');
        if (!tbody) return;
        const search = ($('logSearch')?.value || '').toLowerCase();
        const sevF   = $('logSevFilter')?.value || 'all';
        let logs = [...ingestLogs];
        if (sevF !== 'all') logs = logs.filter(l => (l.severity||'info').toLowerCase() === sevF);
        if (search)         logs = logs.filter(l =>
            (l.message||'').toLowerCase().includes(search) ||
            (l.source||'').toLowerCase().includes(search) ||
            (l.severity||'').toLowerCase().includes(search)
        );
        if (!logs.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-cell">No logs match the current filter</td></tr>';
            return;
        }
        tbody.innerHTML = logs.slice(0, 200).map(l => {
            const sev = (l.severity||'info').toLowerCase();
            const col = sevColor(sev);
            return `<tr>
                <td class="mono">${fmtDateTime(l.received)}</td>
                <td><span style="font-family:var(--mono);font-size:10px;font-weight:700;color:${col};">${sev.toUpperCase()}</span></td>
                <td>${esc(l.source||'—')}</td>
                <td>${esc(l.message||'—')}</td>
                <td class="log-id-cell">${(l.log_id||'').slice(0,8)}</td>
            </tr>`;
        }).join('');
    }

    // ── Decisions page ────────────────────────────────────────────
    function renderDecisionsPage() {
        const container = $('decisionsPageList');
        if (!container) return;
        const decisions = Object.values(pendingMap);
        if (!decisions.length) {
            container.innerHTML = '<div class="empty-state large"><i class="fas fa-check-circle"></i> No pending decisions</div>';
            return;
        }
        container.innerHTML = decisions.map(d => buildDecCard(d, true)).join('');
    }

    // ── History page ──────────────────────────────────────────────
    function renderHistoryPage() {
        const container = $('historyList');
        if (!container) return;
        let items = [...historyList];
        if (historyFilter !== 'all') items = items.filter(d => d.status === historyFilter);
        if (!items.length) {
            container.innerHTML = '<div class="empty-state large"><i class="fas fa-clock-rotate-left"></i> No history yet</div>';
            return;
        }
        container.innerHTML = items.map(d => buildDecCard(d, false)).join('');
    }

    function buildDecCard(d, isPending) {
        const sev  = (d.severity||'high').toLowerCase();
        const col  = sevColor(sev);
        const conf = Math.min(100, Number(d.confidence)||0);
        const confColor = conf >= 80 ? '#00ff88' : conf >= 50 ? '#f59e0b' : '#ff6b35';

        let footerHtml = '';
        if (isPending) {
            footerHtml = `
            <div class="dec-actions">
                <button class="dec-reject-btn" onclick="App.quickReject('${d.decision_id}')">
                    <i class="fas fa-ban"></i> Reject
                </button>
                <button class="dec-review-btn" onclick="App.openDecision('${d.decision_id}')">
                    <i class="fas fa-eye"></i> Review &amp; Decide
                </button>
            </div>`;
        } else {
            const statusColor = d.status === 'approved' ? '#00ff88' : 'rgba(255,255,255,.3)';
            const statusLabel = d.status === 'approved' ? 'APPROVED' : 'REJECTED';
            footerHtml = `
            ${d.operator_note ? `<div class="dec-note"><i class="fas fa-note-sticky"></i> ${esc(d.operator_note)}</div>` : ''}
            <div class="dec-times">
                <span>Created: ${fmtDateTime(d.created)}</span>
                <span>Resolved: ${fmtDateTime(d.resolved)}</span>
            </div>`;
        }

        const statusChip = !isPending
            ? `<span class="dec-status-chip ${d.status}">${d.status === 'approved' ? 'APPROVED' : 'REJECTED'}</span>`
            : '';

        return `
        <div class="dec-card ${isPending ? sev : d.status}">
            <div class="dec-card-header">
                <span class="dec-sev-badge" style="background:${col};">${sev.toUpperCase()}</span>
                <span class="dec-type">${esc(d.threat_type||'—')}</span>
                ${statusChip}
                <span class="dec-time">${fmtTime(d.created)}</span>
            </div>
            <div class="dec-decision">${esc(d.decision||'—')}</div>
            <div class="dec-conf-row">
                <span class="dec-conf-label">AI Confidence</span>
                <div class="dec-conf-track"><div class="dec-conf-fill" style="width:${conf}%;background:${confColor};"></div></div>
                <span class="dec-conf-pct">${conf}%</span>
            </div>
            ${footerHtml}
        </div>`;
    }

    // ── Decision Modal ────────────────────────────────────────────
    function bindModal() {
        $('dmApproveBtn')?.addEventListener('click', () => resolveDecision('approved'));
        $('dmRejectBtn')?.addEventListener('click',  () => resolveDecision('rejected'));
    }

    function showModal(decision) {
        currentDecision = decision;
        const sev  = (decision.severity||'high').toLowerCase();
        const col  = sevColor(sev);
        const conf = Math.min(100, Number(decision.confidence)||0);
        const confColor = conf >= 80 ? '#00ff88' : conf >= 50 ? '#f59e0b' : '#ff6b35';

        setText('dmId', 'DEC-' + shortId(decision.decision_id));
        const badge = $('dmSevBadge');
        if (badge) { badge.textContent = sev.toUpperCase(); badge.style.background = col; }

        setText('dmThreatType', decision.threat_type || '—');
        setText('dmLogId', decision.log_id || '—');
        setText('dmDecision', decision.decision || '—');
        setText('dmReasoning', decision.reasoning || '—');

        const fill = $('dmConfFill');
        const pct  = $('dmConfPct');
        if (fill) { fill.style.width = conf + '%'; fill.style.background = confColor; }
        if (pct)  { pct.textContent = conf + '%'; pct.style.color = confColor; }

        const extra = decision.extra;
        const hasExtra = extra && Object.keys(extra).length > 0;
        $('dmExtraLabel').style.display = hasExtra ? '' : 'none';
        $('dmExtra').style.display = hasExtra ? '' : 'none';
        if (hasExtra) $('dmExtra').textContent = JSON.stringify(extra, null, 2);

        const note = $('dmNote');
        if (note) note.value = '';

        updateQueueBar();

        // alert sound
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const g   = ctx.createGain();
            osc.connect(g); g.connect(ctx.destination);
            osc.frequency.value = 880;
            g.gain.setValueAtTime(0.12, ctx.currentTime);
            g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
            osc.start(); osc.stop(ctx.currentTime + 0.4);
        } catch(_) {}

        $('decisionOverlay').style.display = 'flex';
    }

    function hideModal() {
        $('decisionOverlay').style.display = 'none';
        currentDecision = null;
        if (decisionQueue.length > 0) {
            const next = decisionQueue.shift();
            setTimeout(() => showModal(next), 300);
        }
    }

    function updateQueueBar() {
        const bar = $('dmQueueBar');
        const cnt = $('dmQueueCount');
        if (!bar) return;
        if (decisionQueue.length > 0) {
            bar.style.display = 'flex';
            if (cnt) cnt.textContent = decisionQueue.length;
        } else {
            bar.style.display = 'none';
        }
    }

    async function resolveDecision(action) {
        if (!currentDecision) return;
        const note     = $('dmNote')?.value.trim() || '';
        const decId    = currentDecision.decision_id;
        const approveBtn = $('dmApproveBtn');
        const rejectBtn  = $('dmRejectBtn');
        if (approveBtn) approveBtn.disabled = true;
        if (rejectBtn)  rejectBtn.disabled  = true;
        try {
            const res  = await fetch(`/api/decision/${decId}/resolve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action, operator_note: note }),
            });
            const data = await res.json();
            if (data.status === 'ok') {
                const label = action === 'approved' ? 'APPROVED' : 'REJECTED';
                const type  = action === 'approved' ? 'success' : 'warning';
                toast(`Decision ${label}: ${data.decision.threat_type}`, type);
                hideModal();
            } else {
                toast('Failed to resolve decision', 'critical');
            }
        } catch (e) {
            toast('Network error resolving decision', 'critical');
        } finally {
            if (approveBtn) approveBtn.disabled = false;
            if (rejectBtn)  rejectBtn.disabled  = false;
        }
    }

    // ── Quick reject from list ────────────────────────────────────
    async function quickReject(decisionId) {
        try {
            const res  = await fetch(`/api/decision/${decisionId}/resolve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'rejected', operator_note: 'Quick reject' }),
            });
            const data = await res.json();
            if (data.status === 'ok') {
                decisionQueue = decisionQueue.filter(x => x.decision_id !== decisionId);
                if (currentDecision?.decision_id === decisionId) hideModal();
                toast(`Decision REJECTED: ${data.decision.threat_type}`, 'warning');
            }
        } catch (e) {}
    }

    // ── Open specific decision in modal ───────────────────────────
    function openDecision(decisionId) {
        const d = pendingMap[decisionId];
        if (!d) return;
        decisionQueue = decisionQueue.filter(x => x.decision_id !== decisionId);
        if (currentDecision) decisionQueue.unshift(currentDecision);
        showModal(d);
    }

    // ── Filters ───────────────────────────────────────────────────
    function bindFilters() {
        // Log search / filter
        $('logSearch')?.addEventListener('input', () => {
            if ($('page-logs')?.classList.contains('active')) renderLogsPage();
        });
        $('logSevFilter')?.addEventListener('change', () => {
            if ($('page-logs')?.classList.contains('active')) renderLogsPage();
        });
        // History filter buttons
        $$('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                $$('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                historyFilter = btn.getAttribute('data-filter') || 'all';
                renderHistoryPage();
            });
        });
    }

    // ── Refresh helpers ───────────────────────────────────────────
    async function refreshLogs() {
        try {
            const res  = await fetch('/api/ingest/logs?limit=200');
            const data = await res.json();
            ingestLogs = data.logs || [];
            sevCounts = { critical:0, high:0, medium:0, low:0, info:0 };
            ingestLogs.forEach(l => { const s=(l.severity||'info').toLowerCase(); sevCounts[s]=(sevCounts[s]||0)+1; });
            updateKPIs(); updateSevBars(); renderDashLogFeed(); renderLogsPage();
        } catch (e) {}
    }

    // ── Toast ─────────────────────────────────────────────────────
    function toast(msg, type = 'info') {
        const container = $('toastContainer');
        if (!container) return;
        const t = document.createElement('div');
        t.className = `toast ${type}`;
        const icons = { critical:'fa-skull', warning:'fa-triangle-exclamation', success:'fa-check-circle', info:'fa-circle-info' };
        t.innerHTML = `
            <i class="fas ${icons[type]||icons.info}"></i>
            <span>${esc(msg)}</span>
            <button class="toast-close" onclick="this.parentElement.remove()"><i class="fas fa-xmark"></i></button>`;
        container.appendChild(t);
        setTimeout(() => { if (t.parentNode) t.remove(); }, 5000);
    }

    // ── Public API ────────────────────────────────────────────────
    window.App = { openDecision, quickReject, refreshLogs };

    // ── Init ──────────────────────────────────────────────────────
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
