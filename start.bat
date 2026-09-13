@echo off
setlocal
cd /d "%~dp0"
title KopiTopsis

if not exist ".venv\Scripts\python.exe" (
    echo Aplikasi belum diinstal. Jalankan install.bat terlebih dahulu.
    pause
    exit /b 1
)
if not exist ".env" (
    echo Konfigurasi .env belum tersedia. Jalankan install.bat terlebih dahulu.
    pause
    exit /b 1
)

echo Menjalankan KopiTopsis di http://127.0.0.1:5000
echo Tekan Ctrl+C untuk menghentikan server.
".venv\Scripts\flask.exe" --app run.py run --debug --host 127.0.0.1 --port 5000

if errorlevel 1 (
    echo.
    echo Server berhenti karena kesalahan. Pastikan MySQL sedang aktif.
    pause
)
