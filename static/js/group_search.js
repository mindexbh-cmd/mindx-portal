/* group_search.js — search-mode toggle (طالب / مجموعة).
 *
 * Step 3 of the safe re-implementation. This file contains ONLY the
 * toggle handler at this stage. Mode 2 dropdowns + fuzzy search +
 * results + detail view + bulk actions ship in later atomic commits.
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

  function applyMode(mode) {
    var modal = document.getElementById('sr-modal');
    if (!modal) return;
    var paneStudent = modal.querySelector('.search-mode-student');
    var paneGroup   = modal.querySelector('.search-mode-group');
    if (mode === 'group') {
      if (paneStudent) paneStudent.style.display = 'none';
      if (paneGroup)   paneGroup.style.display   = '';
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
    /* Apply default state from whichever radio is currently checked. */
    var checked = document.querySelector('input[name="search-mode"]:checked');
    if (checked) applyMode(checked.value);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindToggle);
  } else {
    bindToggle();
  }
})();
