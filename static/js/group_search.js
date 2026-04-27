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
    /* Card click → fetch + render detail view (step 5). */
    var cards = box.querySelectorAll('.grp-card');
    for (var j = 0; j < cards.length; j++) {
      cards[j].addEventListener('click', function () {
        var gid = parseInt(this.getAttribute('data-grp-id'), 10);
        pickGroup(gid);
      });
    }
  }

  /* ── Detail view (step 5) ────────────────────────────────────── */
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
    /* Bulk actions toolbar (step 6). */
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

    /* Roster table — clicking a row opens the existing student profile. */
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

    /* Hover styling for the roster (one-shot). */
    if (!document.getElementById('grp-roster-style')) {
      var st2 = document.createElement('style');
      st2.id = 'grp-roster-style';
      st2.textContent = '.grp-roster-row:hover{background:#faf7ff;}';
      document.head.appendChild(st2);
    }
    /* Roster row click → flip toggle to "طالب" mode and call the
       existing srPick(sid) so we reuse the existing student profile
       view 1:1. No re-implementation. */
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

    /* Bulk action wiring (step 6). */
    var btnPrint = box.querySelector('.grp-btn-print');
    if (btnPrint) {
      btnPrint.addEventListener('click', function () {
        printRoster(g.group_name || '', students);
      });
    }
    var btnWA = box.querySelector('.grp-btn-wa');
    if (btnWA) {
      btnWA.addEventListener('click', function () {
        bulkMessage(g.group_name || '', students);
      });
    }
  }

  /* ── Print roster (step 6) ───────────────────────────────────── */
  /* Note: this code lives in an EXTERNAL .js file, so any literal
     '</script>' substring inside JS strings here is NOT exposed to
     the parent page's HTML parser. We still split the closing tag
     defensively so a copy-paste into an inline context wouldn't
     re-introduce the bleed bug from before. */
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

  /* ── Bulk WhatsApp send (step 6) ─────────────────────────────── */
  /* Reuses the existing per-row WhatsApp pipeline pattern: open a
     wa.me link per parent in a small stagger so popup-blockers
     don't fight us. The user clicks "Send" inside WhatsApp manually
     for each — same flow as the existing .btn-wa buttons. */
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

  /* Expose for cross-script callers. */
  window.grpPickGroup = pickGroup;

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
