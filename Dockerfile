# syntax=docker/dockerfile:1.4

# ---- STAGE 1: Build Frontend ----
    FROM node:18-alpine AS frontend
    WORKDIR /app/frontend
    
    # استثمار cache لمجلدات npm لكي لا يُعاد تحميل الحزم في كل بناء
    COPY frontend/package*.json ./
    RUN --mount=type=cache,target=/root/.npm \
        --mount=type=cache,target=/root/.cache/npm \
        npm ci
    
    # انسخ الشفرة وشغّل البنية
    COPY frontend/ ./
    RUN npm run build   # يخرج إلى /app/static
    
    # ---- STAGE 2: Build Backend + Copy Frontend Static ----
    FROM python:3.12-slim AS backend
    WORKDIR /app
    
    # استخدم cache لـ apt ولـ pip
    RUN --mount=type=cache,target=/var/cache/apt \
        --mount=type=cache,target=/var/lib/apt/lists \
        apt-get update \
     && apt-get install -y imagemagick \
     && rm -rf /var/lib/apt/lists/*
    
    # علّم MoviePy على مسار binary الصحيح
    ENV IMAGEMAGICK_BINARY=/usr/bin/convert
    
    # انسخ وثبّت متطلبات بايثون مع cache لـ pip
    COPY requirements.txt ./
    RUN --mount=type=cache,target=/root/.cache/pip \
        pip install --no-cache-dir -r requirements.txt
    
    # انسخ كود الـ backend
    COPY backend/ ./backend/
    
    # حضّر مجلّد static
    RUN rm -rf backend/static \
     && mkdir -p backend/static
    
    # انسخ الأصول المبنية من الواجهة
    COPY --from=frontend /app/static/ backend/static/
    
    # انتقل إلى مجلّد backend وشغّل التطبيق
    WORKDIR /app/backend
    CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
    