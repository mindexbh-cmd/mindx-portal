/* ==========================================================================
   Mindex Sidebar — Phase 2
   ==========================================================================
   Self-mounting RTL sidebar for admin / staff pages. Loaded by the
   auto-injector in app.py only on admin-class HTML constants; it
   double-checks the URL on the client side anyway so a page that
   shouldn't have it can never get it (defense in depth).

   Behaviour:
     • Renders a fixed 260px right-anchored sidebar on >=1025px.
     • Renders a hamburger trigger at the top-right on <=1024px and
       slides the sidebar in on tap.
     • Reads `location.pathname` to mark the matching nav item
       `.active` (uses startsWith for /points and /admin route
       prefixes so /admin/lessons activates the right item).
     • Includes a backdrop on mobile that closes the drawer on tap.
     • Closes on Escape.

   The sidebar is purely navigational: every link points to an
   already-existing route. No new routes, no role logic on the
   client (server still 403s). RBAC-driven hiding can be layered on
   later if needed.
   ========================================================================== */
(function(){
  'use strict';

  // Skip non-admin URLs. The auto-injector also restricts which page
  // constants get the script, but checking here means a copy-paste
  // mistake or future page rename can't accidentally show the
  // sidebar to teachers / parents / login.
  var path = (location.pathname || '/').toLowerCase();
  var ADMIN_PREFIXES = [
    '/dashboard', '/database', '/attendance', '/groups', '/settings',
    '/admin/', '/points/manage', '/points/bulk-adjust'
  ];
  var isAdmin = ADMIN_PREFIXES.some(function(p){ return path === p || path.indexOf(p) === 0; });
  if (!isAdmin) return;

  // Idempotency — if this script ever loads twice, second run is a no-op.
  if (document.getElementById('mx-sidebar')) return;

  // ---- Nav definition. Every href targets a route confirmed to
  // exist in the codebase (verified server-side before commit). ----
  var NAV = [
    {
      label: 'رئيسية',
      icon:  '⚑', // flag-like glyph; emoji-free for max compatibility
      items: [
        { href: '/dashboard',                  label: 'لوحة التحكم',              icon: '⌂' },
        { href: '/admin/teacher-deliveries',   label: 'متابعة تسليمات المعلمين',  icon: '≡' }
      ]
    },
    {
      label: 'الأكاديمي',
      icon:  '⚘',
      items: [
        { href: '/database',                   label: 'قاعدة بيانات الطلاب',     icon: '☰' },
        { href: '/groups',                     label: 'المجموعات',                icon: '☸' },
        { href: '/attendance',                 label: 'تسجيل الغياب',             icon: '✓' },
        { href: '/admin/lessons',              label: 'متابعة التقدم في الدروس',  icon: '✎' },
        { href: '/admin/evaluations',          label: 'التقييم الشهري',           icon: '★' },
        { href: '/admin/parent-messages',      label: 'رسائل المعلمة',            icon: '✉' }
      ]
    },
    {
      label: 'المالية',
      icon:  '¤',
      items: [
        { href: '/admin/receipts',             label: 'إيصالات أولياء الأمور',    icon: '✐' }
      ]
    },
    {
      label: 'العمليات',
      icon:  '⚙',
      items: [
        { href: '/points/manage',              label: 'إدارة نظام النقاط',        icon: '☆' },
        { href: '/points/board',               label: 'لوحة الصف',                icon: '⦿' }
      ]
    },
    {
      label: 'الإعدادات',
      icon:  '⚙',
      items: [
        { href: '/settings',                   label: 'الإعدادات',                icon: '⚙' },
        { href: '/admin/permissions',          label: 'إدارة الصلاحيات',          icon: '⚿' },
        { href: '/admin/table-audit',          label: 'تدقيق الجداول',            icon: '⛬' },
        { href: '/admin/backups',              label: 'النسخ الاحتياطية',         icon: '⚙' },
        { href: '/admin/docs',                 label: 'التوثيق',                  icon: '☕' }
      ]
    }
  ];

  // ---- Helpers ----
  function el(tag, props, children){
    var n = document.createElement(tag);
    if (props){
      Object.keys(props).forEach(function(k){
        if (k === 'class') n.className = props[k];
        else if (k === 'text') n.textContent = props[k];
        else if (k === 'html') n.innerHTML = props[k];
        else if (k === 'on') {
          Object.keys(props.on).forEach(function(ev){ n.addEventListener(ev, props.on[ev]); });
        } else n.setAttribute(k, props[k]);
      });
    }
    (children || []).forEach(function(c){ if (c) n.appendChild(c); });
    return n;
  }

  // Active-state matcher: match the nav item whose href is the
  // longest prefix of the current path (so /admin/lessons activates
  // the lessons item even if /admin/ is also a registered prefix
  // somewhere).
  function isActive(href){
    if (href === '/') return path === '/' || path === '';
    if (path === href) return true;
    if (path.indexOf(href + '/') === 0) return true;
    return false;
  }

  // ---- Markup builder ----
  function render(){
    // Trigger button (mobile-only; CSS hides on desktop).
    var trigger = el('button', {
      'class': 'mx-sidebar-trigger',
      'type': 'button',
      'aria-label': 'فتح القائمة',
      'aria-controls': 'mx-sidebar',
      'on': { click: openDrawer }
    });
    trigger.innerHTML = '☰'; // ☰ horizontal bars

    // Backdrop (mobile-only).
    var backdrop = el('div', {
      'class': 'mx-sidebar-backdrop',
      'id': 'mx-sidebar-backdrop',
      'on': { click: closeDrawer }
    });

    // Sidebar container.
    var aside = el('aside', {
      'class': 'mx-sidebar',
      'id': 'mx-sidebar',
      'role': 'navigation',
      'aria-label': 'القائمة الجانبية'
    });

    // Header.
    var head = el('div', { 'class': 'mx-sidebar-head' });
    head.appendChild(el('h2', { 'class': 'mx-sidebar-title', 'text': 'مايندكس' }));
    var closeBtn = el('button', {
      'class': 'mx-sidebar-close',
      'type': 'button',
      'aria-label': 'إغلاق القائمة',
      'on': { click: closeDrawer }
    });
    closeBtn.innerHTML = '✕'; // ✕
    head.appendChild(closeBtn);

    // Body.
    var nav = el('nav', { 'class': 'mx-sidebar-nav' });
    NAV.forEach(function(group){
      var wrap = el('div', { 'class': 'mx-sidebar-group' });
      var lbl = el('div', { 'class': 'mx-sidebar-group-label' });
      lbl.appendChild(el('span', { 'class': 'mx-sidebar-group-icon', 'html': group.icon }));
      lbl.appendChild(el('span', { 'text': group.label }));
      wrap.appendChild(lbl);
      group.items.forEach(function(item){
        var a = el('a', {
          'class': 'mx-sidebar-item' + (isActive(item.href) ? ' active' : ''),
          'href': item.href
        });
        a.appendChild(el('span', { 'class': 'mx-sidebar-item-icon', 'html': item.icon }));
        a.appendChild(el('span', { 'class': 'mx-sidebar-item-text', 'text': item.label }));
        wrap.appendChild(a);
      });
      nav.appendChild(wrap);
    });

    // Footer (logout).
    var foot = el('div', { 'class': 'mx-sidebar-foot' });
    foot.appendChild(el('span', { 'text': 'مايندكس MIS' }));
    foot.appendChild(el('a', { 'href': '/logout', 'text': 'تسجيل الخروج' }));

    aside.appendChild(head);
    aside.appendChild(nav);
    aside.appendChild(foot);

    document.body.appendChild(trigger);
    document.body.appendChild(backdrop);
    document.body.appendChild(aside);
    document.body.classList.add('mx-sidebar-mounted');
  }

  // ---- Open / close drawer (mobile) ----
  function openDrawer(){
    var s = document.getElementById('mx-sidebar');
    var b = document.getElementById('mx-sidebar-backdrop');
    if (s) s.classList.add('open');
    if (b) b.classList.add('open');
  }
  function closeDrawer(){
    var s = document.getElementById('mx-sidebar');
    var b = document.getElementById('mx-sidebar-backdrop');
    if (s) s.classList.remove('open');
    if (b) b.classList.remove('open');
  }
  window.mxSidebarOpen  = openDrawer;
  window.mxSidebarClose = closeDrawer;

  // Close on Escape.
  document.addEventListener('keydown', function(ev){
    if (ev.key === 'Escape') closeDrawer();
  });

  // ---- Mount as soon as the DOM is parseable ----
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', render);
  } else {
    render();
  }
})();
