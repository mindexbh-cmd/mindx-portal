# قالب التصميم المرجعي — Mindex

> هذا المرجع يوحّد قرارات الـ visual design عبر صفحات بوابة ولي الأمر في
> `mindex-portal`. التطبيق التقني يحدث **داخل Python string constants
> في `app.py`** — لا `templates/` ولا `static/css/` منفصلة في هذا المشروع.
> الـ skill المعتمدة `mindex-design` هي المصدر الفني الموثوق لتفاصيل
> CSS؛ هذا الملف هو الـ summary القصير الذي يلخّص النية التصميمية.

## الهوية البصرية

### اللون الأساسي
- `#6b2c91` — البنفسجي الأساسي (هوية مايندكس، لا يُستبدل)
- `#8B6BA8` — البنفسجي الفاتح (لـ hover / states)
- `#F8F6FB` — خلفية ناعمة جداً
- `#F3EFFA` — purple-100 (للـ chips / tags)

### الخلفيات والنصوص
- `#FFFFFF` / `#FAFAF7` — خلفية الصفحة
- `#1A1A1A` — نص أساسي
- `#6B6B6B` — نص ثانوي
- `#EBE3F0` — حدود ناعمة

### لكنة دافئة
- `#D4A574` — للـ accent الذهبي (المالية / أرقام مميزة)
- `#F5EFE6` — خلفية دافئة للـ KPI cards

### ألوان الحالة (للـ dashboard / breakdown bar)
- `#2D7D5A` — نجاح / حضور (متناسق مع `mindex-green`)
- `#D4A574` — تحذير / تأخير
- `#B84545` — خطر / غياب
- `#5B7C99` — معلومة محايدة

> ملاحظة: الـ skill `mindex-design` تذكر 7 ألوان (primary/green/gold/blue/pink/coral/system)
> للأقسام الإدارية. صفحة ولي الأمر تستخدم فقط الأربعة أعلاه + البنفسجي
> الأساسي. لا نُغرق الصفحة بألوان متعددة.

## التايبوغرافي

- **عربي:** نظام `font-family` الحالي مع `'Segoe UI', Tahoma, Arial, sans-serif`
  يعمل بشكل ممتاز للعربية على أنظمة المستخدم. لا تتدخّل في `font-family`
  إلا إذا أضفنا CDN جديد بإذن صريح.
- **إنجليزي/أرقام:** نفس الـ stack
- **هرمية الأحجام:**
  - عناوين رئيسية (Hero): `clamp(1.5rem, 4vw, 2rem)` — وزن 800
  - أرقام إحصائية (KPI numbers): `clamp(1.8rem, 5vw, 2.5rem)` — وزن 900، الرقم هو البطل البصري
  - عناوين أقسام: `1.05rem` — وزن 900
  - نصوص أساسية: `0.92rem` — وزن 600-700
  - labels / hints: `0.78rem` — وزن 700
- **line-height:** 1.6 للعربي، 1.5 للإنجليزي
- **letter-spacing:** خفيف على العناوين الكبيرة فقط (`-0.01em`)

## الاتجاه والـ RTL

- `dir="rtl"` على `<html>` (موجود أصلاً)
- استخدم `margin-inline-start` / `margin-inline-end` عوضاً عن
  `margin-left` / `margin-right` حيث أمكن
- الأرقام بالعربية الشرقية حسب المُتعارف عليه — التواريخ بصيغة
  `DD/MM/YYYY (يوم الأسبوع)` (موجود في `_fmtAbsenceDate`)

## الجمهور والانطباع

- **الجمهور:** أولياء أمور بحرينيون/خليجيون، 28-50 سنة
- **المرجع الذهني:** لوحة تحكم مؤسسة تعليمية رصينة — لا «تطبيق مرح».
  تخيّل: «هذه ابنتي، أرى حضورها، الساعات المتبقية، الدفعات — معلومة بمعلومة، بسرعة».
- **السياق:** 70%+ من الزيارات من الجوال. الـ above-the-fold على 375px
  يجب أن يحوي: اسم الطالب + ملخص الحضور (بطاقة الساعات).
- **تجنّب:** المظهر الكرتوني، gradient بنفسجي→أبيض القياسي، بطاقات
  متطابقة مزدحمة، إيقونات emoji كثيرة في خط واحد، gauge charts ملونة.

## ضد المتوسط (Anti-slop)

| تجنّب | استخدم |
|---|---|
| تدرّج «بنفسجي إلى أبيض» على كل بطاقة | تدرّج واحد محسوب في الـ Hero فقط، وخلفيات بيضاء/شبه-بيضاء للباقي |
| 4-5 بطاقات KPI ملونة بألوان مختلفة | تايبوغرافي معمارية: الرقم هو البطل، الـ label خافت |
| `box-shadow: 0 6px 24px` على كل عنصر | ظلال خفيفة `0 1px 2px rgba(0,0,0,.04)` فقط للبطاقات الرئيسية |
| emojis متناثرة في كل label | emoji واحد لكل قسم رئيسي (📅 ⏱ 💳)، لا أكثر |
| `border-radius: 24px` كبير وكرتوني | `14px` للبطاقات الكبيرة، `10px` للداخلية، `8px` للأزرار |
| `font-weight: 600` للعناوين | وزن **800-900** للأرقام، **700** للعناوين، **500-600** للنصوص |

## القيود التقنية (حاسمة)

1. **لا `templates/` directory.** التعديل داخل `PORTAL_PARENT_PID_HUB_HTML` في `app.py:12726`.
2. **لا `static/css/`.** الـ CSS داخل `<style>` block في نفس الـ string constant.
3. **لا libraries جديدة.** ممنوع إضافة Tabler/FontAwesome/Google Fonts بدون موافقة صريحة.
4. **JS handlers محمية:** `phShowAbsenceModal`, `phHideAbsenceModal`, `_g9RenderBreakdown`, `phLookup`, `phResetLookup`, `phRenderHub` — لا تُعدّل سلوكها، فقط تنسيقها البصري.
5. **API bindings محمية:** `_PH.absence_dates`, `_PH.attendance_breakdown`, `_PH.stats`, `_PH.student`, `_PH.pid` — لا نُعيد تسميتها.
6. **العناصر بـ ID محمية وظيفياً:** `hours-taken-head`, `hours-required`, `hours-taken`, `hours-contract`, `hours-remaining`, `hours-overrun-banner`, `hours-fill`, `hours-summary`, `g5-absence-modal`, `g5-absence-body`, `g5-absence-title`, `action-tabs`, `hub-content`, `lookup-card`.
   - يجوز تغيير ألوانها، أبعادها، حدودها، الـ font.
   - **ممنوع** حذفها أو تغيير معرّفها (`id="..."`).
7. **viewport targets:** 375px (أولوية) / 768px / 1280px. الموبايل-أولاً.
