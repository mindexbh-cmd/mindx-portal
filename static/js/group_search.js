/* group_search.js — search-mode toggle + group search (steps 3+4).
 *
 * External by design: the previous attempt put inline JS into
 * HOME_HTML and a literal `</body>` substring inside a JS string
 * literal collided with the mx-helpers.js auto-injector, prematurely
 * closing the surrounding <script> block. External JS is loaded by
 * the browser as its own resource — the auto-injector cannot reach
 * inside it.
 */
(function () {
  'use strict';

  var FACETS_LOADED = false;
  var SEARCH_DEBOUNCE = null;

  /* ── HTML escaping (avoid raw user/group text being interpreted) ── */
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* ── Toggle handler (step 3) ─────────────────────────────────── */
  function applyMode(mode) {
    var modal = document.getElementById('sr-modal');
    if (!modal) return;
    var paneStudent = modal.querySelector('.search-mode-student');
    var paneGroup   = modal.querySelector('.search-mode-group');
    if (mode === 'group') {
      if (paneStudent) paneStudent.style.display = 'none';
      if (paneGroup)   paneGroup.style.display   = '';
      if (!FACETS_LOADED) loadFacets();
    } else {
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

  /* ── Facet loading (step 4) ──────────────────────────────────── */
  function fillSelect(id, values) {
    var sel = document.getElementById(id);
    if (!sel) return;
    sel.innerHTML = '';
    for (var i = 0; i < values.length; i++) {
      var v = values[i];
      var o = document.createElement('option');
      o.value = v;
      o.textContent = v;
      sel.appendChild(o);
    }
  }

  function loadFacets() {
    fetch('/api/groups/filters', { credentials: 'include' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d || !d.ok) return;
        fillSelect('grp-flt-days',     d.days        || []);
        fillSelect('grp-flt-times',    d.times       || []);
        fillSelect('grp-flt-names',    d.group_names || []);
        fillSelect('grp-flt-levels',   d.levels      || []);
        fillSelect('grp-flt-teachers', d.teachers    || []);
        FACETS_LOADED = true;
        runSearch();
      })
      .catch(function () { /* network errors handled in runSearch */ });
  }

  /* ── Search execution (step 4) ───────────────────────────────── */
  function selectedValues(id) {
    var sel = document.getElementById(id);
    if (!sel) return [];
    var out = [];
    for (var i = 0; i < sel.options.length; i++) {
      if (sel.options[i].selected) out.push(sel.options[i].value);
    }
    return out;
  }

  function runSearch() {
    var qs = new URLSearchParams();
    var pairs = [
      ['days',     'grp-flt-days'],
      ['times',    'grp-flt-times'],
      ['group_names', 'grp-flt-names'],
      ['levels',   'grp-flt-levels'],
      ['teachers', 'grp-flt-teachers']
    ];
    for (var i = 0; i < pairs.length; i++) {
      var arr = selectedValues(pairs[i][1]);
      if (arr.length) qs.set(pairs[i][0], arr.join(','));
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
    SEARCH_DEBOUNCE = setTimeout(runSearch, 220);
  }

  /* ── Result cards (step 4) ───────────────────────────────────── */
  function renderResults(groups) {
    var box = document.getElementById('grp-results');
    if (!box) return;
    if (!groups.length) {
      box.innerHTML = '<div style="padding:14px;color:#888;text-align:center;">لا توجد مجموعات مطابقة</div>';
      return;
    }
    var html = '<div style="font-size:12.5px;color:#666;margin-bottom:8px;">عدد النتائج: <b>' + groups.length + '</b></div>';
    html += '<div class="grp-cards" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;">';
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
    /* Hover effect via JS-injected stylesheet (one-shot) */
    if (!document.getElementById('grp-card-style')) {
      var st = document.createElement('style');
      st.id = 'grp-card-style';
      st.textContent = '.grp-card:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(107,63,160,.18);border-color:#6B3FA0;}';
      document.head.appendChild(st);
    }
    /* Card click handler — detail view ships in step 5; for now log. */
    var cards = box.querySelectorAll('.grp-card');
    for (var j = 0; j < cards.length; j++) {
      cards[j].addEventListener('click', function () {
        var gid = parseInt(this.getAttribute('data-grp-id'), 10);
        if (typeof window.grpPickGroup === 'function') {
          window.grpPickGroup(gid);
        }
      });
    }
  }

  function clearFilters() {
    var ids = ['grp-flt-days','grp-flt-times','grp-flt-names','grp-flt-levels','grp-flt-teachers'];
    for (var i = 0; i < ids.length; i++) {
      var sel = document.getElementById(ids[i]);
      if (!sel) continue;
      for (var j = 0; j < sel.options.length; j++) sel.options[j].selected = false;
    }
    var q = document.getElementById('grp-flt-q'); if (q) q.value = '';
    var det = document.getElementById('grp-details'); if (det) det.innerHTML = '';
    runSearch();
  }

  function bindGroupSearch() {
    var btnSearch = document.getElementById('grp-btn-search');
    if (btnSearch) btnSearch.addEventListener('click', runSearch);
    var btnClear  = document.getElementById('grp-btn-clear');
    if (btnClear)  btnClear.addEventListener('click', clearFilters);
    var qInput    = document.getElementById('grp-flt-q');
    if (qInput)    qInput.addEventListener('input', scheduleSearch);
    var selIds = ['grp-flt-days','grp-flt-times','grp-flt-names','grp-flt-levels','grp-flt-teachers'];
    for (var i = 0; i < selIds.length; i++) {
      var sel = document.getElementById(selIds[i]);
      if (sel) sel.addEventListener('change', runSearch);
    }
  }

  /* Boot */
  function boot() {
    bindToggle();
    bindGroupSearch();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
