/* group_search.js — search-mode toggle + group search.
 *
 * External by design: the previous attempt put inline JS into
 * HOME_HTML and a literal `</body>` substring inside a JS string
 * literal collided with the mx-helpers.js auto-injector, prematurely
 * closing the surrounding <script> block. External JS is loaded by
 * the browser as its own resource — the auto-injector cannot reach
 * inside it.
 *
 * UI: chip-style filters (each chip is a button that toggles a
 * dropdown panel of checkboxes). Live-search on any change.
 */
(function () {
  'use strict';

  /* ── Filter state lives in plain JS (no hidden form fields needed
        because we only fire fetch() requests, not form submissions). */
  var STATE = {
    days:     [],
    times:    [],
    names:    [],
    levels:   [],
    teachers: []
  };
  /* Map our internal STATE keys to the query-param names the
     /api/groups/search endpoint expects. */
  var QS_KEY = {
    days:     'days',
    times:    'times',
    names:    'group_names',
    levels:   'levels',
    teachers: 'teachers'
  };
  /* Cached facet options per filter — populated on first reveal. */
  var OPTIONS = {
    days:     [],
    times:    [],
    names:    [],
    levels:   [],
    teachers: []
  };
  var FACETS_LOADED  = false;
  var SEARCH_DEBOUNCE = null;
  var CSS_INJECTED   = false;
  var OPEN_FILTER    = null;  /* which filter panel is currently open */

  /* ── HTML escaping ───────────────────────────────────────────── */
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* ── CSS injection (one-shot) ────────────────────────────────── */
  function injectCSS() {
    if (CSS_INJECTED || document.getElementById('grp-search-style')) return;
    var st = document.createElement('style');
    st.id = 'grp-search-style';
    st.textContent = [
      /* Chip button (the always-visible filter trigger). */
      '.grp-chip{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1.5px solid #c4a8e8;color:#4a148c;padding:7px 14px;border-radius:999px;font-weight:800;font-family:inherit;font-size:13px;cursor:pointer;line-height:1;transition:background .12s,box-shadow .12s,border-color .12s;}',
      '.grp-chip:hover{background:#faf7ff;border-color:#6B3FA0;}',
      '.grp-chip.active{background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;border-color:transparent;box-shadow:0 3px 10px rgba(107,63,160,.30);}',
      '.grp-chip-count{display:none;background:rgba(255,255,255,.25);color:inherit;border-radius:999px;padding:1px 8px;font-size:11px;font-weight:900;}',
      '.grp-chip.active .grp-chip-count{display:inline-block;}',
      '.grp-chip-clear{display:none;cursor:pointer;font-size:14px;line-height:1;padding:0 4px;border-radius:50%;}',
      '.grp-chip-clear:hover{background:rgba(255,255,255,.25);}',
      '.grp-chip.active .grp-chip-clear{display:inline-block;}',
      '.grp-chip-caret{font-size:10px;opacity:.7;}',
      /* Dropdown panel (anchored under the chip). */
      '.grp-chip-panel{position:absolute;top:calc(100% + 6px);right:0;min-width:200px;max-width:280px;max-height:260px;overflow:auto;background:#fff;border:1.5px solid #c4a8e8;border-radius:12px;box-shadow:0 8px 24px rgba(76,29,149,.18);z-index:10001;padding:6px;display:none;}',
      '.grp-chip-panel.show{display:block;}',
      '.grp-chip-opt{display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:8px;cursor:pointer;font-size:13px;color:#212121;font-family:inherit;}',
      '.grp-chip-opt:hover{background:#faf7ff;}',
      '.grp-chip-opt input[type=checkbox]{accent-color:#6B3FA0;width:14px;height:14px;flex-shrink:0;cursor:pointer;}',
      '.grp-chip-opt span{flex:1;line-height:1.3;}',
      '.grp-chip-empty{padding:14px;text-align:center;color:#888;font-size:12px;}',
      /* Result cards hover. */
      '.grp-card:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(107,63,160,.18);border-color:#6B3FA0;}',
      '.grp-roster-row:hover{background:#faf7ff;}',
      /* Mobile: chips wrap and stretch full width. */
      '@media (max-width:560px){',
      '  .grp-chip-row{gap:6px;}',
      '  .grp-chip-wrap{flex:1 1 100%;}',
      '  .grp-chip{width:100%;justify-content:space-between;}',
      '  .grp-chip-panel{left:0;right:0;max-width:none;}',
      '}'
    ].join('\n');
    document.head.appendChild(st);
    CSS_INJECTED = true;
  }

  /* ── Toggle handler (search mode) ────────────────────────────── */
  function applyMode(mode) {
    var modal = document.getElementById('sr-modal');
    if (!modal) return;
    var paneStudent = modal.querySelector('.search-mode-student');
    var paneGroup   = modal.querySelector('.search-mode-group');
    if (mode === 'group') {
      if (paneStudent) paneStudent.style.display = 'none';
      if (paneGroup)   paneGroup.style.display   = '';
      injectCSS();
      if (!FACETS_LOADED) loadFacets();
    } else {
      closeOpenPanel();
      if (paneGroup)   paneGroup.style.display   = 'none';
      if (paneStudent) paneStudent.style.display = '';
    }
  }

  function bindToggle() {
    var radios = document.querySelectorAll('input[name="search-mode"]');
    if (!radios.length) return;
    for (var i = 0; i < radios.length; i++) {
      radios[i].addEventListener('change', function () {
        if (this.checked) applyMode(this.value);
      });
    }
    var checked = document.querySelector('input[name="search-mode"]:checked');
    if (checked) applyMode(checked.value);
  }

  /* ── Facet loading ───────────────────────────────────────────── */
  function loadFacets() {
    fetch('/api/groups/filters', { credentials: 'include' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d || !d.ok) return;
        OPTIONS.days     = d.days        || [];
        OPTIONS.times    = d.times       || [];
        OPTIONS.names    = d.group_names || [];
        OPTIONS.levels   = d.levels      || [];
        OPTIONS.teachers = d.teachers    || [];
        FACETS_LOADED = true;
        /* Pre-render all five chip panels so opening them is instant. */
        renderAllPanels();
        runSearch();
      })
      .catch(function () { /* error states surface in runSearch. */ });
  }

  /* ── Chip + panel rendering ──────────────────────────────────── */
  function renderAllPanels() {
    var wraps = document.querySelectorAll('.grp-chip-wrap');
    for (var i = 0; i < wraps.length; i++) {
      var key = wraps[i].getAttribute('data-filter');
      ensurePanel(wraps[i], key);
      updateChip(wraps[i], key);
    }
  }

  function ensurePanel(wrap, key) {
    var existing = wrap.querySelector('.grp-chip-panel');
    if (existing) existing.parentNode.removeChild(existing);
    var panel = document.createElement('div');
    panel.className = 'grp-chip-panel';
    var opts = OPTIONS[key] || [];
    if (!opts.length) {
      panel.innerHTML = '<div class="grp-chip-empty">لا توجد خيارات</div>';
    } else {
      var html = '';
      for (var i = 0; i < opts.length; i++) {
        var v = opts[i];
        var checked = STATE[key].indexOf(v) >= 0 ? ' checked' : '';
        html += '<label class="grp-chip-opt"><input type="checkbox" data-val="' + esc(v) + '"' + checked + '><span>' + esc(v) + '</span></label>';
      }
      panel.innerHTML = html;
    }
    wrap.appendChild(panel);
    /* Wire each checkbox to update STATE + chip + run search. */
    var boxes = panel.querySelectorAll('input[type=checkbox]');
    for (var j = 0; j < boxes.length; j++) {
      boxes[j].addEventListener('change', function (ev) {
        var val = this.getAttribute('data-val');
        var arr = STATE[key];
        var idx = arr.indexOf(val);
        if (this.checked) {
          if (idx < 0) arr.push(val);
        } else {
          if (idx >= 0) arr.splice(idx, 1);
        }
        updateChip(wrap, key);
        runSearch();
      });
    }
  }

  function updateChip(wrap, key) {
    var chip = wrap.querySelector('.grp-chip');
    var count = chip.querySelector('.grp-chip-count');
    var n = STATE[key].length;
    if (n > 0) {
      chip.classList.add('active');
      if (count) count.textContent = n;
    } else {
      chip.classList.remove('active');
      if (count) count.textContent = '';
    }
  }

  function closeOpenPanel() {
    if (!OPEN_FILTER) return;
    var wrap = document.querySelector('.grp-chip-wrap[data-filter="' + OPEN_FILTER + '"]');
    if (wrap) {
      var p = wrap.querySelector('.grp-chip-panel');
      if (p) p.classList.remove('show');
    }
    OPEN_FILTER = null;
  }

  function togglePanel(key) {
    var wrap = document.querySelector('.grp-chip-wrap[data-filter="' + key + '"]');
    if (!wrap) return;
    var panel = wrap.querySelector('.grp-chip-panel');
    if (!panel) return;
    if (OPEN_FILTER === key) {
      panel.classList.remove('show');
      OPEN_FILTER = null;
    } else {
      closeOpenPanel();
      panel.classList.add('show');
      OPEN_FILTER = key;
    }
  }

  function bindChips() {
    var wraps = document.querySelectorAll('.grp-chip-wrap');
    for (var i = 0; i < wraps.length; i++) {
      var wrap = wraps[i];
      var key  = wrap.getAttribute('data-filter');
      var chip = wrap.querySelector('.grp-chip');
      if (!chip) continue;
      /* Bind the chip click. The clear-X swallows its own click so
         it doesn't also toggle the panel. */
      chip.addEventListener('click', (function (k) {
        return function (ev) {
          if (ev.target && ev.target.classList && ev.target.classList.contains('grp-chip-clear')) {
            ev.stopPropagation();
            ev.preventDefault();
            STATE[k] = [];
            updateChip(wrap, k);
            ensurePanel(wrap, k);   /* re-render to uncheck visible boxes */
            runSearch();
            return;
          }
          togglePanel(k);
        };
      })(key));
    }
    /* Click outside any chip-wrap → close. */
    document.addEventListener('click', function (ev) {
      if (!OPEN_FILTER) return;
      var wrap = document.querySelector('.grp-chip-wrap[data-filter="' + OPEN_FILTER + '"]');
      if (!wrap) return;
      if (!wrap.contains(ev.target)) closeOpenPanel();
    });
    /* ESC → close. */
    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape') closeOpenPanel();
    });
  }

  /* ── Search execution + results ──────────────────────────────── */
  function runSearch() {
    var qs = new URLSearchParams();
    var keys = ['days','times','names','levels','teachers'];
    for (var i = 0; i < keys.length; i++) {
      var k = keys[i];
      if (STATE[k].length) qs.set(QS_KEY[k], STATE[k].join(','));
    }
    var qInput = document.getElementById('grp-flt-q');
    var q = qInput ? (qInput.value || '').trim() : '';
    if (q) qs.set('q', q);

    var box = document.getElementById('grp-results');
    if (!box) return;
    box.innerHTML = '<div style="padding:14px;color:#888;text-align:center;">جاري التحميل...</div>';
    fetch('/api/groups/search?' + qs.toString(), { credentials: 'include' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d || !d.ok) {
          box.innerHTML = '<div style="padding:14px;color:#c00;text-align:center;">' + esc((d && d.error) || 'خطأ') + '</div>';
          return;
        }
        renderResults(d.groups || []);
      })
      .catch(function () {
        box.innerHTML = '<div style="padding:14px;color:#c00;text-align:center;">خطأ في الاتصال</div>';
      });
  }

  function scheduleSearch() {
    if (SEARCH_DEBOUNCE) clearTimeout(SEARCH_DEBOUNCE);
    SEARCH_DEBOUNCE = setTimeout(runSearch, 300);
  }

  function renderResults(groups) {
    var box = document.getElementById('grp-results');
    if (!box) return;
    if (!groups.length) {
      box.innerHTML = '<div style="padding:18px;color:#888;text-align:center;font-weight:700;">لا توجد مجموعات مطابقة. جرّبي تعديل الفلاتر.</div>';
      return;
    }
    var html = '<div style="font-size:12.5px;color:#666;margin-bottom:8px;">عدد النتائج: <b>' + groups.length + '</b></div>';
    html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;">';
    for (var i = 0; i < groups.length; i++) {
      var g = groups[i];
      var time = g.study_time || g.online_time || g.ramadan_time || '—';
      var days = (g.study_days || []).join('، ') || '—';
      html += '<div data-grp-id="' + (g.id|0) + '" class="grp-card" style="background:#fff;border:1.6px solid #e0d0f8;border-radius:12px;padding:12px;cursor:pointer;transition:transform .15s, box-shadow .15s, border-color .15s;">'
        + '<div style="font-weight:900;color:#4a148c;font-size:15px;margin-bottom:4px;">' + esc(g.group_name) + '</div>'
        + '<div style="font-size:12px;color:#5d4037;line-height:1.65;">'
        +   '👩‍🏫 <b>' + esc(g.teacher_name || '—') + '</b><br>'
        +   '🎓 ' + esc(g.level || '—') + '<br>'
        +   '📅 ' + esc(days) + ' &middot; ⏰ ' + esc(time) + '<br>'
        +   '👥 عدد الطلاب: <b>' + (g.student_count|0) + '</b>'
        + '</div>'
        + '</div>';
    }
    html += '</div>';
    box.innerHTML = html;
    var cards = box.querySelectorAll('.grp-card');
    for (var j = 0; j < cards.length; j++) {
      cards[j].addEventListener('click', function () {
        var gid = parseInt(this.getAttribute('data-grp-id'), 10);
        pickGroup(gid);
      });
    }
  }

  function clearAllFilters() {
    STATE.days     = [];
    STATE.times    = [];
    STATE.names    = [];
    STATE.levels   = [];
    STATE.teachers = [];
    var q = document.getElementById('grp-flt-q'); if (q) q.value = '';
    var det = document.getElementById('grp-details'); if (det) det.innerHTML = '';
    /* Re-render all panels (uncheck) and update chip badges. */
    var wraps = document.querySelectorAll('.grp-chip-wrap');
    for (var i = 0; i < wraps.length; i++) {
      var key = wraps[i].getAttribute('data-filter');
      ensurePanel(wraps[i], key);
      updateChip(wraps[i], key);
    }
    runSearch();
  }

  function bindOuterControls() {
    var btnSearch = document.getElementById('grp-btn-search');
    if (btnSearch) btnSearch.addEventListener('click', runSearch);
    var btnClear  = document.getElementById('grp-btn-clear');
    if (btnClear)  btnClear.addEventListener('click', clearAllFilters);
    var qInput    = document.getElementById('grp-flt-q');
    if (qInput)    qInput.addEventListener('input', scheduleSearch);
  }

  /* ── Detail view ─────────────────────────────────────────────── */
  function fmtMoney(n) {
    var v = Number(n || 0);
    return v.toLocaleString('ar-EG', { maximumFractionDigits: 3 }) + ' د.ب';
  }
  function attBadge(p) {
    if (p == null) return '<span style="color:#999;">—</span>';
    var col = (p>=75)?'#1B5E20':((p>=50)?'#e65100':'#c62828');
    var bg  = (p>=75)?'#e8f5e9':((p>=50)?'#fff3e0':'#ffebee');
    return '<span style="background:'+bg+';color:'+col+';padding:2px 8px;border-radius:8px;font-weight:800;font-size:12px;">' + p + '%</span>';
  }
  function payBadge(s) {
    if (!s) return '<span style="color:#999;">—</span>';
    if (s === 'مدفوع بالكامل') return '<span style="background:#e8f5e9;color:#1B5E20;padding:2px 8px;border-radius:8px;font-weight:800;font-size:12px;">' + s + '</span>';
    if (s === 'لم يدفع')        return '<span style="background:#ffebee;color:#c62828;padding:2px 8px;border-radius:8px;font-weight:800;font-size:12px;">' + s + '</span>';
    if (s === 'متبقي')          return '<span style="background:#fff3e0;color:#e65100;padding:2px 8px;border-radius:8px;font-weight:800;font-size:12px;">' + s + '</span>';
    return esc(s);
  }

  function pickGroup(gid) {
    var box = document.getElementById('grp-details');
    if (!box) return;
    box.innerHTML = '<div style="padding:14px;color:#888;text-align:center;">جاري التحميل...</div>';
    setTimeout(function () { try { box.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (e) {} }, 50);
    fetch('/api/groups/' + gid + '/detail', { credentials: 'include' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d || !d.ok) {
          box.innerHTML = '<div style="padding:14px;color:#c00;text-align:center;">' + esc((d && d.error) || 'خطأ') + '</div>';
          return;
        }
        renderDetail(d);
      })
      .catch(function () {
        box.innerHTML = '<div style="padding:14px;color:#c00;text-align:center;">خطأ في الاتصال</div>';
      });
  }

  function renderDetail(d) {
    var g = d.group || {};
    var st = d.stats || {};
    var students = d.students || [];
    var box = document.getElementById('grp-details');
    if (!box) return;
    var parts = [];
    parts.push('<div style="background:#faf7ff;border:1.5px solid #c4a8e8;border-radius:14px;padding:14px;">');
    parts.push(  '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;margin-bottom:10px;">');
    parts.push(    '<div>');
    parts.push(      '<div style="font-weight:900;color:#4a148c;font-size:18px;margin-bottom:4px;">' + esc(g.group_name) + '</div>');
    parts.push(      '<div style="font-size:13px;color:#5d4037;line-height:1.7;">');
    parts.push(        '👩‍🏫 <b>' + esc(g.teacher_name || '—') + '</b> &middot; 🎓 ' + esc(g.level || '—') + '<br>');
    parts.push(        '📅 ' + esc(g.study_days || '—') + ' &middot; ⏰ ' + esc(g.study_time || '—'));
    if (g.session_duration) parts.push(' &middot; ⏱ ' + esc(g.session_duration));
    parts.push(      '</div>');
    parts.push(    '</div>');
    parts.push(    '<div class="grp-actions" style="display:flex;gap:8px;flex-wrap:wrap;">');
    parts.push(      '<button type="button" class="grp-btn-print" style="background:#fff;color:#4a148c;border:1.5px solid #c4a8e8;padding:7px 14px;border-radius:9px;font-weight:700;cursor:pointer;font-family:inherit;font-size:13px;">📋 طباعة قائمة الطلاب</button>');
    parts.push(      '<button type="button" class="grp-btn-wa" data-grp-id="' + (g.id|0) + '" style="background:#25D366;color:#fff;border:none;padding:7px 14px;border-radius:9px;font-weight:700;cursor:pointer;font-family:inherit;font-size:13px;">📨 إرسال رسالة لكل أولياء الأمور</button>');
    parts.push(    '</div>');
    parts.push(  '</div>');
    parts.push(  '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-top:8px;">');
    parts.push(    '<div style="background:#fff;border-radius:10px;padding:10px;text-align:center;border:1px solid #eee;"><div style="color:#666;font-size:11px;">عدد الطلاب</div><div style="font-weight:900;color:#4a148c;font-size:20px;">' + (st.student_count|0) + '</div></div>');
    parts.push(    '<div style="background:#fff;border-radius:10px;padding:10px;text-align:center;border:1px solid #eee;"><div style="color:#666;font-size:11px;">متوسط نسبة الحضور</div><div style="font-weight:900;color:#4a148c;font-size:20px;">' + (st.avg_attendance_pct == null ? '—' : (st.avg_attendance_pct + '%')) + '</div></div>');
    parts.push(    '<div style="background:#fff;border-radius:10px;padding:10px;text-align:center;border:1px solid #eee;"><div style="color:#666;font-size:11px;">عليهم متبقي</div><div style="font-weight:900;color:#c62828;font-size:20px;">' + (st.students_with_remaining|0) + '</div></div>');
    parts.push(    '<div style="background:#fff;border-radius:10px;padding:10px;text-align:center;border:1px solid #eee;"><div style="color:#666;font-size:11px;">إجمالي المتبقي</div><div style="font-weight:900;color:#e65100;font-size:18px;">' + fmtMoney(st.total_remaining || 0) + '</div></div>');
    parts.push(  '</div>');
    parts.push('</div>');

    parts.push('<div style="margin-top:12px;">');
    if (!students.length) {
      parts.push('<div style="padding:14px;color:#888;text-align:center;">لا يوجد طلاب في هذه المجموعة</div>');
    } else {
      parts.push('<table id="grp-roster" style="width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.06);">');
      parts.push('<thead><tr style="background:#f8f3ff;color:#4a148c;font-size:13px;">');
      parts.push('<th style="padding:9px 10px;text-align:right;font-weight:800;">#</th>');
      parts.push('<th style="padding:9px 10px;text-align:right;font-weight:800;">اسم الطالب</th>');
      parts.push('<th style="padding:9px 10px;text-align:right;font-weight:800;">الرقم الشخصي</th>');
      parts.push('<th style="padding:9px 10px;text-align:right;font-weight:800;">رقم ولي الأمر</th>');
      parts.push('<th style="padding:9px 10px;text-align:right;font-weight:800;">حالة الدفع</th>');
      parts.push('<th style="padding:9px 10px;text-align:center;font-weight:800;">نسبة الحضور</th>');
      parts.push('</tr></thead><tbody>');
      for (var i = 0; i < students.length; i++) {
        var s = students[i];
        parts.push('<tr class="grp-roster-row" data-sid="' + (s.id|0) + '" style="cursor:pointer;border-bottom:1px solid #f0e7f8;font-size:13px;">');
        parts.push('<td style="padding:8px 10px;color:#999;">' + (i+1) + '</td>');
        parts.push('<td style="padding:8px 10px;font-weight:800;color:#212121;">' + esc(s.student_name) + '</td>');
        parts.push('<td style="padding:8px 10px;direction:ltr;color:#555;">' + esc(s.personal_id || '—') + '</td>');
        parts.push('<td style="padding:8px 10px;direction:ltr;color:#555;">' + esc(s.parent_phone || '—') + '</td>');
        parts.push('<td style="padding:8px 10px;">' + payBadge(s.pay_status) + '</td>');
        parts.push('<td style="padding:8px 10px;text-align:center;">' + attBadge(s.att_percent) + '</td>');
        parts.push('</tr>');
      }
      parts.push('</tbody></table>');
    }
    parts.push('</div>');
    box.innerHTML = parts.join('');

    var rows = box.querySelectorAll('.grp-roster-row');
    for (var k = 0; k < rows.length; k++) {
      rows[k].addEventListener('click', function () {
        var sid = parseInt(this.getAttribute('data-sid'), 10);
        if (!sid) return;
        var radio = document.querySelector('input[name="search-mode"][value="student"]');
        if (radio) { radio.checked = true; applyMode('student'); }
        if (typeof window.srPick === 'function') window.srPick(sid);
      });
    }
    var btnPrint = box.querySelector('.grp-btn-print');
    if (btnPrint) btnPrint.addEventListener('click', function () { printRoster(g.group_name || '', students); });
    var btnWA = box.querySelector('.grp-btn-wa');
    if (btnWA) btnWA.addEventListener('click', function () { bulkMessage(g.group_name || '', students); });
  }

  /* ── Print roster ────────────────────────────────────────────── */
  function printRoster(groupName, students) {
    var w = window.open('', '_blank');
    if (!w) { alert('فشل فتح نافذة الطباعة. تحقق من إعدادات المتصفح.'); return; }
    var head = '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
      + '<title>قائمة الطلاب — ' + esc(groupName || '') + '</title>'
      + '<style>'
      +   'body{font-family:Tahoma,Arial,sans-serif;padding:20px;direction:rtl;}'
      +   'h1{font-size:18px;color:#4a148c;margin:0 0 12px;}'
      +   '.meta{color:#666;font-size:13px;margin-bottom:14px;}'
      +   'table{width:100%;border-collapse:collapse;}'
      +   'th,td{border:1px solid #ccc;padding:6px 10px;text-align:right;font-size:13px;}'
      +   'th{background:#f0f0f0;}'
      + '</style></head><body>';
    var body = '<h1>قائمة الطلاب: ' + esc(groupName || '') + '</h1>'
      + '<div class="meta">عدد الطلاب: ' + (students || []).length + '</div>'
      + '<table><thead><tr>'
      +   '<th>#</th><th>اسم الطالب</th><th>الرقم الشخصي</th><th>رقم ولي الأمر</th>'
      +   '<th>حالة الدفع</th><th>نسبة الحضور</th>'
      + '</tr></thead><tbody>';
    for (var i = 0; i < (students || []).length; i++) {
      var s = students[i];
      body += '<tr>'
        + '<td>' + (i+1) + '</td>'
        + '<td>' + esc(s.student_name || '') + '</td>'
        + '<td style="direction:ltr;">' + esc(s.personal_id || '—') + '</td>'
        + '<td style="direction:ltr;">' + esc(s.parent_phone || '—') + '</td>'
        + '<td>' + esc(s.pay_status || '—') + '</td>'
        + '<td>' + (s.att_percent == null ? '—' : (s.att_percent + '%')) + '</td>'
        + '</tr>';
    }
    body += '</tbody></table>';
    /* Split closing tags so even a copy-paste into inline scope can't
       collide with an outer <script>. */
    var foot = '<scr' + 'ipt>window.onload=function(){window.print();};<' + '/scr' + 'ipt></body></html>';
    w.document.write(head + body + foot);
    w.document.close();
  }

  /* ── Bulk WhatsApp send ──────────────────────────────────────── */
  function bulkMessage(groupName, students) {
    var withPhone = (students || []).filter(function (s) { return s.parent_phone; });
    if (!withPhone.length) {
      alert('لا يوجد أرقام أولياء أمور لهذه المجموعة');
      return;
    }
    if (!confirm('سيتم فتح ' + withPhone.length + ' محادثة واتساب. متابعة؟')) return;
    for (var i = 0; i < withPhone.length; i++) {
      (function (s, idx) {
        setTimeout(function () {
          var phone = (s.parent_phone || '').replace(/[^0-9]/g, '');
          if (phone.charAt(0) === '0') phone = '973' + phone.slice(1);
          var msg = 'السلام عليكم، بخصوص ابنتكم/ابنكم ' + s.student_name + ' في مجموعة ' + groupName + ' — ';
          var url = 'https://wa.me/' + phone + '?text=' + encodeURIComponent(msg);
          window.open(url, '_blank');
        }, idx * 350);
      })(withPhone[i], i);
    }
  }

  /* Boot */
  function boot() {
    bindToggle();
    bindChips();
    bindOuterControls();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  /* Expose for cross-script callers (testing / debugging). */
  window.grpPickGroup = pickGroup;
})();
