# Plan: Unified login + direct parent navigation — 2026-05-15

## Goal (Arabic)

توحيد تجربة الدخول لجميع الأدوار في صفحة `/login` واحدة، مع إزالة الصفحة الوسيطة التي تطلب الرقم الشخصي للطالب عند ضغط ولي الأمر المسجَّل على بطاقة "الغياب"، بحيث ينتقل مباشرة لصفحة الغياب الخاصة بطفله. التغيير في الـ flow والـ UI فقط، بدون أي تعديل على قاعدة البيانات.

## Surface goal vs underlying need

**Surface goal (ما طلبه المشغّل)**
- صفحة دخول واحدة لكل الأدوار (موظفون، أساتذة، أولياء أمور) — نظام يكتشف نوع المستخدم تلقائياً.
- إزالة الصفحة الوسيطة (~2 ثانية) التي تطلب `personal_id` عند ضغط الأهل على "الغياب".

**Underlying need (ما يقصده فعلياً — لازم تأكيد)**
- صفحة الدخول `/login` **موحَّدة فعلياً اليوم**: نفس الـ form لكل الأدوار، ويُرسَل username/password عبر `POST /login`، ثم `app.py:28384-28399` يحوّل المستخدم لـ landing page بناءً على `role` (`teacher`→`/teacher/hub`, `student`→`/portal/parent-hub`, `parent`→`/portal/parent`, `admin/reception`→`/dashboard`). فما الذي يراه المشغّل "غير موحَّد"؟ على الأرجح هو وجود `LOGIN_HTML` (للموظفين/الأساتذة/الطلاب) **بجانب** `/parent` (صفحة PID عامة بدون login لزائر يأتي من رابط واتساب، `app.py:28608-28615`).
- "الصفحة الوسيطة عند الغياب" هي تحديداً `/parent` (واجهة PID العامة، `PORTAL_PARENT_PID_HUB_HTML` في `app.py:11873`) و/أو `/parent/legacy?pid=…#section-attendance` (الـ flat-scroll القديم، `app.py:28618`). ولي الأمر المسجَّل بدور `role=student` (يستخدم الـ personal_id كـ username حسب التعليق في `app.py:28392-28396`) يجب أن يكون مساره الافتراضي `/portal/parent-hub/attendance` مباشرة — وهو مساره فعلاً حسب الكود الحالي (`app.py:78425-78433`)، فلا توجد صفحة وسيطة في هذا المسار. الصفحة الوسيطة تظهر فقط في `/parent` العامة.

**Two reasonable interpretations — operator must pick one (سؤال موجَّه للمشغّل)**

| Interpretation | الوصف | الأثر |
|---|---|---|
| **A — "نظِّف الازدواجية فقط"** | احذف/أعد توجيه `/parent` (PID العامة) لـ `/login`. ولي الأمر دائماً يدخل عبر `/login`. لا توجد PID prompt للمسجَّلين. | عودة بسيطة، تأثير على روابط الواتساب القديمة التي تشير لـ `/parent`. |
| **B — "اجعل بطاقات الـ hub القديم تروح للصفحات الجديدة"** | أبقِ `/parent` العامة لزائر بدون login، لكن تأكَّد أن أي ولي أمر مسجَّل لا يصل لها أبداً (redirect إذا `session["user"]` موجود) — وأعد توجيه روابط `/parent/legacy?pid=…#section-attendance` لـ `/portal/parent-hub/attendance` للمسجَّلين. | يبقي الـ legacy backwards-compat (لزائر `wa.me/…/parent?pid=`) ويزيل التأخير للمسجَّلين فقط. |

**التوصية المبدئية**: Interpretation B (أقل خطراً، يحافظ على روابط الواتساب القديمة)، لكن A أبسط معماريّاً. ينتظر قرار المشغّل قبل بدء Phase 2.

## Context

**Memory files referenced**
- `docs/memory/HANDOFF_COMPACT.md` — حالة المشروع (502 routes, e2e 8/8 green, push subsystem live).
- `docs/memory/PROJECT_BIBLE.md` — قواعد inline-string templating + Arabic-entity rule.
- `docs/memory/DECISIONS_LOG.md` — ADR-007 (Expand-Migrate-Contract) لا ينطبق هنا (لا تغيير schema)، لكن أي تعديل على route routing يحتاج audit ux ومراجعة شاملة.
- `docs/memory/BUGS_LOG.md` — يجب التحقق من علاقة بـ bug سابق "bidi-mark CPR-lookup" (commit 2026-05-12) قبل تعديل أي PID-resolution path.

**Existing patterns to reuse**
- **Role-dispatch in `/login`** (`app.py:28335-28399`) — منطق `landing_page` per-user override + role default. سنبني عليه، لا نعيد كتابته.
- **`@login_required` + `session["user"]` guard** (`app.py:78403-78412`) — كل route من parent-hub يستخدمه. سنضيف نفس الـ guard لـ `/parent` (في Interpretation B).
- **`linked_parent_for` JSON array** على `users` (`app.py:775`, `app.py:6275`) — لـ `role=parent` (V1 portal، `app.py:79272-79361` يحلّ الأطفال عبر `/api/portal/parent/me`). لـ `role=student` (parent-with-child-PID-as-username)، فهو مرتبط مباشرة بـ `students` row عبر `linked_student_id`.
- **`_resolve_student_row_by_pid`** (`app.py:28641`) — bidi-tolerant PID lookup. يُستخدم في `/api/parent/lookup`. لو احتجناه في الـ redirect logic، يجب توجيه أي call عبره (لا regex مباشرة على personal_id).
- **`/api/parent/hub-stats`** (`app.py:28804`) — مدعِّم لبطاقات `PORTAL_PARENT_PID_HUB_HTML` الـ5. لو حذفنا الصفحة، نبقي الـ endpoint للتوافق العكسي.

**Routes that may be affected (لازم mapping كامل قبل التعديل)**
| Route | Handler line | Role required | الحالة |
|---|---|---|---|
| `/login` (GET/POST) | 28335 | none | ✅ unified already |
| `/` | (search) | none | يمسح session ويرسم login |
| `/parent` | 28608 | **none (public)** | الصفحة الوسيطة |
| `/parent/legacy` | 28618 | **none (public)** | flat-scroll legacy |
| `/portal/parent` | 79260 | parent | V1 portal |
| `/portal/parent-hub` | 78402 | student | V2 hub landing |
| `/portal/parent-hub/attendance` | 78425 | student | direct attendance ✅ |
| `/portal/parent-hub/payments` | 78414 | student | direct payments ✅ |
| `/portal/parent-hub/points` | 78436 | student | direct points ✅ |
| `/portal/parent-hub/messages` | 78710 | student | direct messages ✅ |
| `/portal/parent-hub/evaluations` | 79031 | student | direct evaluations ✅ |
| `/portal/parent-hub/curriculum` | (search) | student | direct curriculum ✅ |

## Phases

### Phase 1 — Discovery (read-only, before any code change)
- **Time**: 45–60 دقيقة
- **Risk**: NONE (read-only)
- **Agents to invoke**:
  ```
  Agent({subagent_type: "code-architect-agent",
         prompt: "Audit every callsite of /parent, /parent/legacy, /portal/parent, /portal/parent-hub, and /login in app.py. Produce a discovery doc at docs/migrations/unified-login-discovery.md listing: (a) the full route table with handler line numbers, (b) every internal href/redirect that points to /parent or /parent/legacy (including JS hrefs inside inline templates — these are the WhatsApp deep-links operator wants to preserve), (c) every external entry point (WhatsApp message templates, push-notification URLs in app.py:_push_*), (d) whether any role is explicitly designed to land on /parent (e.g. a parent-without-account flow). STOP for approval after the discovery doc is written. Do NOT propose changes yet."})
  ```
- **Steps**:
  1. Grep app.py for `'/parent'`, `"/parent"`, `/parent/legacy` (string literals).
  2. Grep WhatsApp + push templates for parent-page URLs (`portal_link = ...` at `app.py:76630`).
  3. Cross-check with `docs/memory/CODE_GENEALOGY.md` for the history of `PARENT_HTML` vs `PORTAL_PARENT_PID_HUB_HTML` (v2.8 redesign — `app.py:11866`).
  4. Confirm whether any external service (sideloaded TWA APK manifest, Render config) hard-codes a parent URL.
- **Output**: `docs/migrations/unified-login-discovery.md` — route inventory + callsite map + operator-decision table for Interpretation A vs B.

### Phase 2 — Design (pick interpretation, propose redirect rules)
- **Time**: 30 دقيقة
- **Risk**: NONE (documentation only)
- **Agents to invoke**:
  ```
  Agent({subagent_type: "data-protector-agent",
         prompt: "No DB writes are proposed in this plan but login/session is sensitive. Audit the proposed redirect logic for: (a) any session-tampering risk if a logged-in parent visits /parent (Interpretation B redirect must check session['user'] BEFORE rendering PID prompt), (b) any rate-limit bypass risk (the /parent PID lookup is rate-limited per IP at app.py:28631 — does redirecting authenticated parents reduce or bypass that?), (c) what happens to anonymous visitors arriving via WhatsApp deep-link if /parent is removed (Interpretation A). Return GO/NO-GO with conditions."})
  ```
  ```
  Agent({subagent_type: "ux-employee-agent",
         prompt: "Compare two flows for a logged-in parent clicking the الغياب card: (1) current — passes through /parent/legacy?pid=...#section-attendance with a PID prompt if session lookup fails, (2) proposed — direct to /portal/parent-hub/attendance. Verify the proposed flow handles edge cases: parent with TWO children (does the destination page have a child-switcher?), parent whose session is stale (redirect to /login, not /parent), parent on iOS Safari with a back-button click after viewing attendance (must land on hub, not on /parent). Return verdict."})
  ```
- **Steps**:
  1. Operator picks Interpretation A or B (gate before Phase 3).
  2. Document the chosen redirect rules table in `docs/migrations/unified-login-design.md` — exact conditions, exact destinations, exact error fallbacks.
  3. Document the rollback rule (single-commit revert + safety tag name).
- **Output**: `docs/migrations/unified-login-design.md` with operator sign-off line at the bottom.

### Phase 3 — Implementation (atomic commits, one concern each)
- **Time**: 2–3 ساعات
- **Risk**: MEDIUM (login/session boundary; affects every parent on every visit)
- **Commits planned** (Interpretation B — adjust if operator picks A):
  1. **`refactor(parent-routes): guard /parent and /parent/legacy from authenticated parents`** — in `app.py:28608` and `app.py:28618`, add a check: if `session.get("user")` and that user's `role` is `student` (parent-with-child-PID), `redirect("/portal/parent-hub")`. If `role` is `parent` (V1), `redirect("/portal/parent")`. Anonymous visitors keep the existing public PID flow untouched.
  2. **`feat(login): clarify /login is the single entry point`** — in `LOGIN_HTML` (`app.py:9680`), add a small RTL hint under the form: "أولياء الأمور: استخدم الرقم الشخصي للطالب كاسم مستخدم" (Arabic-entity encoded). Single string change. No layout shift.
  3. **`feat(parent-hub): replace /parent/legacy?pid=…#section-X anchors with direct sub-page links`** — in `PORTAL_PARENT_PID_HUB_HTML` (`app.py:12106`), branch the `href` computation: if the request is from a logged-in `role=student` user, point each of the 5 cards at `/portal/parent-hub/{payments,attendance,points,evaluations,curriculum}` directly. Anonymous visitors (no session) keep the legacy `?pid=` hash route. (Server-side: pass an `IS_LOGGED_IN` flag into the template via `.replace("__IS_LOGGED_IN__", ...)` per the existing inline-template pattern.)
  4. **`docs(memory): log unified-login decision`** — append to `docs/memory/DECISIONS_LOG.md` with the chosen interpretation + rationale + commits.
- **Agents to run after each commit**:
  - After commit 1: `code-architect-agent` (verify guard placement and that no test path is broken).
  - After commit 2: `arabic-quality-agent` + `ui-designer-agent` (verify the new login hint Arabic + visual rhythm).
  - After commit 3: `mobile-first-agent` (verify card tap-target + viewport on 360px).
- **Syntax check after every commit**:
  ```
  python -c "import ast; ast.parse(open('app.py', encoding='utf-8').read())"
  ```

### Phase 4 — Verification (full persona walkthrough — MANDATORY)
- **Time**: 60–90 دقيقة
- **Risk**: NONE (read-only e2e)
- **Local e2e**:
  ```
  python app.py                        # one terminal
  python scripts/run_e2e.py            # other terminal
  ```
  All 8 e2e tests must stay green; the suite includes login + the four critical pages.
- **Persona walkthrough — MANDATORY before deploy**:
  ```
  Agent({subagent_type: "real-user-tester-agent",
         prompt: "Walk through the unified-login + direct-parent-nav change for ALL five personas. For each, document: (1) entry point (URL or click path), (2) credentials used, (3) expected landing page after /login submit, (4) parent-flow specific — click الغياب from hub, measure time-to-attendance-data, confirm no PID prompt appears. Personas: (a) admin_test/TestAdmin2026!, (b) teacher_test/TestTeacher2026!, (c) parent_test/TestParent2026! — V1 parent role landing on /portal/parent, (d) student_test/TestStudent2026! — student-role parent landing on /portal/parent-hub, (e) reception (seeded by init_db, login reception/rec123). Also test the public /parent flow ANONYMOUSLY (logout first, visit /parent) — verify the PID prompt still works for WhatsApp-link visitors. Report PASS/FAIL per persona with screenshots."})
  ```
- **Performance check**:
  ```
  Agent({subagent_type: "performance-watchdog",
         prompt: "Measure the click-to-attendance-data latency for a logged-in parent: BEFORE = /portal/parent-hub → click الغياب → previous flow (if any intermediate) → attendance data visible. AFTER = same click → /portal/parent-hub/attendance → data visible. Verify the ~2s the operator reported is real (capture network trace) and confirm the new flow is sub-1s. Use admin_test session for harness only — measure as student_test."})
  ```
- **Approval gate**: green from all five personas + sub-1s click-to-data measurement.

### Phase 5 — Deployment
- **Time**: 5 دقيقة (safe_deploy auto-rollback safety net)
- **Risk**: LOW (additive guards; rollback is single-tag revert)
- **CLI**:
  ```
  python scripts/safe_deploy.py --feature unified-login-parent-direct-nav
  ```
- **Safety tag** (auto-created by safe_deploy): `safety/pre-unified-login-parent-direct-nav-<timestamp>`.
- **Rollback** (if `/api/health` red or smoke e2e fails):
  ```
  git reset --hard safety/pre-unified-login-parent-direct-nav-<timestamp>
  git push --force-with-lease origin main
  ```
  (safe_deploy does this automatically.)
- **Post-deploy verification against prod**:
  ```
  python scripts/run_e2e.py --base https://mindx-portal-1.onrender.com
  ```

### Phase 6 — Documentation
- **Time**: 20 دقيقة
- **Risk**: NONE
- **Agents to invoke**:
  ```
  Agent({subagent_type: "documentation-keeper",
         prompt: "Update CLAUDE.md 'Seeded credentials' section to mention that /parent (public) and /portal/parent-* (logged-in) are intentionally separate surfaces. Update the AUTH/route table if one exists. Add a short ARCHITECTURE.md note under 'Auth boundaries' explaining the role→landing-page dispatch logic at app.py:28384-28399."})
  ```
  ```
  Agent({subagent_type: "memory-keeper-agent",
         prompt: "Passive-tracking mode. The unified-login-parent-direct-nav change has shipped (commits <list>). Append entries to docs/memory/CHANGE_LOG.md, DECISIONS_LOG.md (Interpretation A vs B decision), and DESIGN_LOG.md (login-hint string + card-href branching). No new BUGS_LOG entry expected."})
  ```

## Approval gates

1. **After Phase 1 (Discovery)** — operator reviews `docs/migrations/unified-login-discovery.md` and picks Interpretation A or B. STOP here until decision.
2. **After Phase 2 (Design)** — operator approves the redirect rules table in `docs/migrations/unified-login-design.md` before any code change.
3. **Before Phase 5 (Deploy)** — full persona walkthrough PASS + performance verdict + e2e green confirmed by coordinator.
4. **Post-deploy** — confirm prod e2e green within 10 minutes of deploy; otherwise auto-rollback fires.

## Risk assessment

- **Overall**: MEDIUM
- **Worst case** (Arabic): تكسُّر مسار الدخول لجميع أولياء الأمور بسبب redirect خاطئ، فيظهر لهم 500 أو حلقة redirect لانهائية. الـ mitigation: `safe_deploy.py` يطلق smoke e2e فور النشر وإذا فشل يرجع تلقائياً للـ safety tag السابق.
- **Most likely real risk**: انكسار روابط واتساب القديمة بصيغة `…/parent/legacy?pid=…#section-attendance` لو اخترنا Interpretation A — لذا التوصية بـ B.
- **Rollback**: tag واحد + `safe_deploy --rollback` — وقت الاسترجاع < 60 ثانية.

## Time estimate

- **Total**: 5–8 ساعات (نطاق صادق، يعتمد على اختيار المشغّل بين A و B)
- **Breakdown**:
  - Phase 1 Discovery: 45–60 دقيقة
  - Phase 2 Design + approval: 30 دقيقة + وقت قرار المشغّل
  - Phase 3 Implementation (3 commits + tests after each): 2–3 ساعات
  - Phase 4 Verification (5 personas + perf): 60–90 دقيقة
  - Phase 5 Deployment: 5–10 دقيقة
  - Phase 6 Documentation: 20 دقيقة

## Success criteria

- [ ] `/login` يقبل كل من admin_test / teacher_test / parent_test / student_test / reception ويوجِّه كل واحد للوحة الصحيحة (لا regression على المنطق الحالي).
- [ ] ولي أمر مسجَّل بدور `role=student` يضغط بطاقة الغياب → يصل لـ `/portal/parent-hub/attendance` خلال < 1 ثانية بدون أي PID prompt.
- [ ] ولي أمر مسجَّل بدور `role=parent` (V1) يضغط `/parent` أو `/parent/legacy` مباشرة → يُعاد توجيهه فوراً لـ `/portal/parent` بدون عرض PID prompt.
- [ ] زائر مجهول (logout) يفتح `/parent` من رابط واتساب قديم → ما زال يرى PID prompt ويعمل بشكل صحيح (لا backwards-compat breakage).
- [ ] e2e suite 8/8 خضراء locally و prod.
- [ ] لا تعديل على schema — `git diff` على ملفات migration فارغ.
- [ ] `docs/memory/CHANGE_LOG.md` يحوي entry جديد، و `DECISIONS_LOG.md` يحوي ADR للاختيار بين A و B.

## Notes on environment + constraints

- **Budget**: Render Starter 512 MB — التغيير لا يضيف أي memory pressure (HTML guards فقط).
- **No DB writes**: `data-protector-agent` تشغيلها preventive فقط؛ لا توقُّع لـ GO conditions تتطلب backup.
- **Arabic encoding**: أي string Arabic جديدة (مثل hint سطر الدخول) يجب كتابتها كـ HTML numeric entities داخل `LOGIN_HTML` ولا تُكتب raw Arabic داخل `app.py` (CLAUDE.md rule).
- **Inline templating**: لو احتجنا تمرير `IS_LOGGED_IN` flag للـ template، نستخدم نفس نمط `.replace("__PH_CSS__", _PORTAL_HUB_SHARED_CSS)` الحالي — لا Jinja.

## Open questions for operator (must answer before Phase 2)

1. **Interpretation A أم B؟** A = احذف `/parent` العامة كلياً (أبسط، يكسر روابط واتساب القديمة). B = أبقها لزائر مجهول فقط، redirect للمسجَّلين (أكثر أماناً، أكثر كوداً). توصيتي: **B**.
2. هل توجد روابط واتساب نشطة حالياً بصيغة `…/parent?pid=…` أو `…/parent/legacy?pid=…`؟ لو نعم — Interpretation B إلزامية.
3. هل تريد إبقاء `/portal/parent` (V1) أم دمجه مع `/portal/parent-hub` (V2)؟ خارج نطاق هذه الخطة، لكن أُذكِّر بالسؤال لأن وجود portal-ين لـ "parent" يضاعف تعقيد التوجيه.
