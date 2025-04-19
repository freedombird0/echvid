@echo off
echo 🚀 Starting Echvid Build & Server...

:: الانتقال إلى frontend
cd frontend

:: بناء المشروع
echo 🛠️ Running npm run build...
call npm run build

:: التحقق من نجاح البناء
if not exist dist (
  echo ❌ Build failed: dist folder not found!
  pause
  exit
)

:: تنظيف static في backend
echo 🧹 Cleaning backend/static...
cd ..
rmdir /S /Q backend\static
mkdir backend\static

:: نسخ ملفات dist إلى static
echo 📦 Copying frontend build to backend/static...
xcopy /E /I /Y frontend\dist\* backend\static\

:: تشغيل الخادم Flask
echo 🚀 Starting Flask backend...
cd backend
start cmd /k python app.py

echo ✅ Done. Flask server is running.
pause
