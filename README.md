# SH Agency — Backend Setup Guide 🚀

## ما اللي اتعمل؟

- **FastAPI** باك اند بـ Python
- **SQLite** داتابيز (محفوظة في `/tmp`)
- **Contact Form** بيرسل الرسائل ويحفظها
- **إيميل تلقائي** عبر Resend
- **Admin Panel** (admin.html) للتحكم في الرسائل والبورتفوليو
- **Portfolio API** لعرض المشاريع ديناميكياً

---

## خطوات الرفع على Vercel

### 1. انشئ GitHub Repo
```bash
cd sh-agency-backend
git init
git add .
git commit -m "initial commit"
# ارفعه على GitHub
```

### 2. ادخل على vercel.com
- New Project → Import من GitHub
- Framework: **Other**
- Root Directory: `.`
- اضغط Deploy

### 3. ضيف Environment Variables في Vercel
اروح Settings → Environment Variables وضيف:

| Key | Value |
|-----|-------|
| `ADMIN_USER` | اسم المستخدم بتاعك |
| `ADMIN_PASS` | باسورد قوي |
| `RESEND_API_KEY` | من resend.com (مجاني) |
| `NOTIFY_EMAIL` | إيميلك اللي هيستقبل الإشعارات |

### 4. بعد الرفع — عدّل الـ URL في الملفات

**في `index.html`** (الموقع الأصلي):
```javascript
const BACKEND = 'https://YOUR-PROJECT.vercel.app';
// غيّرها لـ URL الفعلي مثلاً:
const BACKEND = 'https://sh-agency-api.vercel.app';
```

**في `admin.html`**:
```javascript
const API = localStorage.getItem('sh_api_url') || 'http://localhost:8000';
// أو افتح اللوحة بـ:
// https://yourdomain.com/admin.html?api=https://sh-agency-api.vercel.app
```

---

## إزاي تفتح لوحة التحكم

افتح `admin.html` في البراوزر وسجّل دخول بـ:
- Username: اللي حطيته في `ADMIN_USER`
- Password: اللي حطيته في `ADMIN_PASS`

---

## إعداد Resend (الإيميل)

1. اروح resend.com وعمل حساب مجاني
2. اضغط API Keys → Create API Key
3. حط الـ key في Vercel كـ `RESEND_API_KEY`
4. حط إيميلك في `NOTIFY_EMAIL`

---

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/contact` | استقبال رسالة جديدة |
| GET | `/api/portfolio` | جلب المشاريع |
| GET | `/api/admin/messages` | كل الرسائل (admin) |
| PATCH | `/api/admin/messages/{id}/read` | تحديد كمقروءة |
| DELETE | `/api/admin/messages/{id}` | حذف رسالة |
| GET | `/api/admin/portfolio` | إدارة البورتفوليو |
| POST | `/api/admin/portfolio` | إضافة مشروع |
| PUT | `/api/admin/portfolio/{id}` | تعديل مشروع |
| DELETE | `/api/admin/portfolio/{id}` | حذف مشروع |
| GET | `/api/admin/stats` | إحصائيات |
| GET | `/api/health` | فحص الحالة |

---

## ملاحظات مهمة

> ⚠️ Vercel بيستخدم `/tmp` للـ SQLite — الداتا بتتمسح كل فترة.
> لو عايز داتا ثابتة: استخدم **Supabase** (مجاني) أو **PlanetScale**.
> ممكن أساعدك تعمل ده لو احتجت.
