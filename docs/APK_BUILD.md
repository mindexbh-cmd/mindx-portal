# Mindex Android APK — Build & Release Guide

This document walks through building a signed Android TWA APK for
Mindex via the `.github/workflows/build-apk.yml` GitHub Actions
workflow. The result is a sideloadable `.apk` file that parents
install once and get true heads-up notifications + a no-URL-bar
standalone window.

**One-time setup**: generate a keystore, encode it, add four
GitHub secrets. **Every build after that** is a one-click
"Run workflow" in the Actions tab.

---

## English Quickstart

### Step 1 — Generate the signing keystore (ONE TIME)

The keystore is a `.jks`/`.keystore` file that holds the private
key used to sign every APK. You only generate it once. If you
lose it, you can't ship updates — Android refuses to install an
APK signed by a different key over an existing one. **Back the
file up before deleting it from your machine.**

Open a terminal in any directory (`Documents`, etc.):

```
keytool -genkeypair \
  -keystore android.keystore \
  -alias android \
  -keyalg RSA \
  -keysize 2048 \
  -validity 36500 \
  -dname "CN=Mindex,O=Mindex,C=BH"
```

`keytool` ships with any JDK. If "command not found":
- Windows: install [Temurin JDK 17](https://adoptium.net/temurin/releases/?version=17), then re-open the terminal.
- macOS: `brew install temurin`.
- Linux: `sudo apt install openjdk-17-jdk-headless`.

The tool will prompt for two passwords:
- **Keystore password** — use a strong unique password. Save it.
- **Key password** — when asked "Same as keystore password?",
  press Enter to reuse. Save it.

You'll now have `android.keystore` in the current directory.

### Step 2 — Convert keystore to base64

GitHub secrets store text, not binary files. Base64-encode the
keystore so we can paste its contents into a secret.

**PowerShell (Windows):**
```
[Convert]::ToBase64String([IO.File]::ReadAllBytes("android.keystore")) | Set-Content android.keystore.b64
```

**macOS / Linux:**
```
base64 -i android.keystore > android.keystore.b64
```

Open `android.keystore.b64` in any text editor and copy the
ENTIRE contents (long single line — could be ~3 KB of base64).

### Step 3 — Add four GitHub secrets

GitHub → mindx-portal repository → **Settings → Secrets and
variables → Actions → New repository secret**. Add these four:

| Secret name | Value |
| --- | --- |
| `ANDROID_KEYSTORE_BASE64` | Paste the entire base64 string from step 2 |
| `ANDROID_KEYSTORE_PASSWORD` | The keystore password you set in step 1 |
| `ANDROID_KEY_ALIAS` | `android` (matches `-alias` in step 1) |
| `ANDROID_KEY_PASSWORD` | Same as keystore password (per step 1's prompt) |

### Step 4 — Trigger a build

GitHub → mindx-portal → **Actions** tab → "Build Mindex Android
APK" workflow on the left → **Run workflow → Run workflow**
(green button).

Build takes ~5–7 minutes. Most of it is Android SDK + Bubblewrap
install on the runner.

### Step 5 — Get the SHA-256 fingerprint

When the workflow finishes (green check), open the run. The
**Summary** view shows a `## Mindex APK build complete` section
with the SHA-256 fingerprint in a code block. Copy it — it looks
like `AB:CD:EF:01:23:...:99` (95 characters, 32 hex bytes
separated by colons).

### Step 6 — Add fingerprint to Render

Render dashboard → mindx-portal service → **Environment** →
Add Environment Variable:

| Key | Value |
| --- | --- |
| `TWA_SHA256_FINGERPRINT` | The fingerprint from step 5 |

Click **Save Changes**. Render auto-redeploys. Within ~3 min the
public `https://mindx-portal-1.onrender.com/.well-known/assetlinks.json`
will include the fingerprint. From then on, any TWA APK signed
with this keystore that opens `mindx-portal-1.onrender.com` runs
in true standalone mode (no URL bar, heads-up notifications).

### Step 7 — Download the APK

Same workflow run page → scroll to **Artifacts** at the bottom →
download `mindex-apk-<run-number>` (zip). Inside the zip:
`app-release-signed.apk`.

### Step 8 — Distribute to parents

The APK is a normal Android sideload file. Distribute via:
- **WhatsApp**: send the `.apk` directly to a parents group.
  They tap, get a one-time "install unknown apps from WhatsApp"
  toggle, then install.
- **Google Drive / Dropbox link**: same flow.
- **Direct download from Mindex**: optional future feature —
  we can add a `/download/mindex.apk` route that serves the
  latest artifact, but that requires a small Flask change.

When a parent installs, the app launches `mindx-portal-1.onrender.com`
in a no-chrome browser window. Web push notifications work the
same as they did in Chrome — but with native heads-up display
because the system trusts the verified asset link.

---

## النسخة العربية

### الخطوة 1 — إنشاء مفتاح التوقيع (مرة واحدة فقط)

من سطر الأوامر:

```
keytool -genkeypair -keystore android.keystore -alias android -keyalg RSA -keysize 2048 -validity 36500 -dname "CN=Mindex,O=Mindex,C=BH"
```

سيُطلب منك كلمتا مرور: **كلمة مرور المفتاح** و **كلمة مرور الإدخال**.
احفظهما — لا يمكن استعادتهما لاحقاً.

النتيجة: ملف `android.keystore` في المجلد الحالي.
**احتفظ بنسخة احتياطية منه**؛ فقدانه يعني عدم القدرة على إصدار
تحديثات للتطبيق.

### الخطوة 2 — تحويل الملف إلى Base64

**PowerShell (Windows):**
```
[Convert]::ToBase64String([IO.File]::ReadAllBytes("android.keystore")) | Set-Content android.keystore.b64
```

**Linux / macOS:**
```
base64 -i android.keystore > android.keystore.b64
```

### الخطوة 3 — إضافة 4 أسرار في GitHub

GitHub → مستودع mindx-portal → **Settings → Secrets and
variables → Actions → New repository secret**:

| اسم السر | القيمة |
| --- | --- |
| `ANDROID_KEYSTORE_BASE64` | محتوى ملف `android.keystore.b64` بالكامل |
| `ANDROID_KEYSTORE_PASSWORD` | كلمة مرور المفتاح من الخطوة 1 |
| `ANDROID_KEY_ALIAS` | `android` |
| `ANDROID_KEY_PASSWORD` | كلمة مرور الإدخال من الخطوة 1 |

### الخطوة 4 — تشغيل البناء

GitHub → Actions → "Build Mindex Android APK" → **Run workflow**.
يستغرق البناء 5-7 دقائق.

### الخطوة 5 — استخراج بصمة SHA-256

بعد انتهاء البناء (علامة خضراء) افتح صفحة التشغيل.
في قسم **Summary** ستجد البصمة بصيغة:

```
AB:CD:EF:01:23:...:99
```

(95 حرفاً، 32 بايت بصيغة Hex مفصولة بنقطتين رأسيتين).

### الخطوة 6 — إضافة البصمة إلى Render

لوحة Render → خدمة mindx-portal → **Environment** → إضافة:

| Key | Value |
| --- | --- |
| `TWA_SHA256_FINGERPRINT` | البصمة من الخطوة 5 |

احفظ — سيُعاد النشر تلقائياً.

### الخطوة 7 — تنزيل ملف APK

نفس صفحة التشغيل → **Artifacts** في الأسفل → نزّل
`mindex-apk-<رقم>`. داخل الملف المضغوط: `app-release-signed.apk`.

### الخطوة 8 — توزيع التطبيق على الأهالي

شارك الملف عبر:
- **واتساب**: أرسل ملف `.apk` مباشرة لمجموعة الأهالي.
- **Google Drive**: ارفع الملف وشارك رابطاً عاماً.
- يضغط الأهالي على الملف → تظهر رسالة "تثبيت تطبيق من مصدر
  غير معروف" → يقبلون → يُثبَّت التطبيق.

عند فتح التطبيق سيُحمَّل موقع `mindx-portal-1.onrender.com`
بدون شريط عنوان Chrome، مع إشعارات منبثقة (heads-up) كأي
تطبيق أصلي.

---

## Frequent questions

**Q. What if I lose the keystore?**
A. You cannot release updates for the existing APK. Android
verifies signing keys match between versions. Users would need
to uninstall the old APK first, then install a new one signed
by your new keystore. Avoid by storing the keystore + passwords
in a password manager.

**Q. Why pin a keystore, not let the workflow generate one?**
A. Auto-generation leaks the keystore through workflow logs
(however briefly), and rebuilds with different keystores break
upgrade installs. A single hand-managed keystore is the
standard Android signing model.

**Q. Can I rotate the keystore?**
A. Yes — generate a new one, swap the 4 GitHub secrets, build
a new APK, update `TWA_SHA256_FINGERPRINT` on Render
(comma-separate with the old fingerprint for a transition window
so existing installs still verify). Drop the old fingerprint
after every parent has installed the new APK.

**Q. The workflow failed at step 2 with "Missing required GitHub
Actions secrets"** — return to step 3 above, the secret names
must be EXACT (case-sensitive).

**Q. The build succeeded but the APK won't install on a parent's
phone** — Android refuses APKs signed by a different keystore
than the previous install. Have the parent uninstall any prior
Mindex APK first.

**Q. Can we also build for iOS?**
A. Not via this pipeline. iOS apps require Apple Developer
Program ($99/yr) + a Mac for signing. PWA + Add-to-Home-Screen
remains the path on iOS — the PWA shipped in v3.0 already
supports that.
