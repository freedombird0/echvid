# ─── STAGE 1: Build Frontend ─────────────────────────────────
FROM node:18-alpine AS frontend

WORKDIR /app/frontend

# انسخ ملفات الاعتمادات فقط ثم ثبّت
COPY frontend/package*.json ./
RUN npm ci

# انسخ باقي سورس الواجهة وشغّل البناء
COPY frontend/ ./
RUN npm run build


# ─── STAGE 2: Build Backend + Copy Frontend Static ──────────
FROM python:3.12-slim AS backend

WORKDIR /app

# ثبّت اعتمادات البايثون
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# انسخ كود الخلفية
COPY backend/ ./backend/

# جهّز static في الخلفية
RUN rm -rf backend/static && mkdir -p backend/static

# انسخ ملفات الواجهة الجاهزة من المرحلة الأولى
COPY --from=frontend /app/frontend/dist/ backend/static/

# شغّل التطبيق
WORKDIR /app/backend
CMD ["python", "app.py"]
