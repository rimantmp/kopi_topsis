@echo off
setlocal
cd /d "%~dp0"

title Instalasi KopiTopsis
echo ============================================================
echo  INSTALASI KOPITOPSIS - FLASK DAN MYSQL
echo ============================================================
echo.

set "PYTHON_PATH_FILE=%TEMP%\kopitopsis_python_%RANDOM%.txt"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ensure_python.ps1" -OutputFile "%PYTHON_PATH_FILE%" -MinimumMajor 3 -MinimumMinor 12
if errorlevel 1 (
    echo [GAGAL] Python yang kompatibel tidak dapat disiapkan.
    if exist "%PYTHON_PATH_FILE%" del /q "%PYTHON_PATH_FILE%"
    pause
    exit /b 1
)
set /p "PYTHON_EXE="<"%PYTHON_PATH_FILE%"
del /q "%PYTHON_PATH_FILE%"
if not defined PYTHON_EXE goto :failed

echo [OK] Python kompatibel: %PYTHON_EXE%

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info.major == 3 and sys.version_info.minor >= 12 else 1)"
    if errorlevel 1 (
        echo [INFO] Virtual environment lama menggunakan Python yang tidak kompatibel.
        echo [INFO] Membuat ulang .venv dengan Python yang sesuai ...
        rmdir /s /q ".venv"
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/7] Membuat virtual environment .venv ...
    "%PYTHON_EXE%" -m venv .venv
    if errorlevel 1 goto :failed
) else (
    echo [1/7] Virtual environment sudah tersedia.
)

echo [2/7] Memperbarui pip ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed

echo [3/7] Menginstal dependency ...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo [4/7] Memeriksa client MySQL atau MariaDB ...
where mysql >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%M in ('where mysql') do if not defined MYSQL_CLIENT set "MYSQL_CLIENT=%%M"
)
if not defined MYSQL_CLIENT if exist "C:\laragon\bin\mysql" (
    for /f "delims=" %%M in ('where /r "C:\laragon\bin\mysql" mysql.exe 2^>nul') do if not defined MYSQL_CLIENT set "MYSQL_CLIENT=%%M"
)
if not defined MYSQL_CLIENT if exist "C:\laragon\bin\mariadb" (
    for /f "delims=" %%M in ('where /r "C:\laragon\bin\mariadb" mysql.exe 2^>nul') do if not defined MYSQL_CLIENT set "MYSQL_CLIENT=%%M"
)
if defined MYSQL_CLIENT (
    echo [OK] Client ditemukan: %MYSQL_CLIENT%
) else (
    echo [PERINGATAN] mysql.exe tidak ditemukan pada PATH atau Laragon.
    echo Installer tetap akan mengecek server melalui driver PyMySQL.
)

echo.
set "INSTALL_DB_HOST=127.0.0.1"
set "INSTALL_DB_PORT=3306"
set "INSTALL_DB_USER=root"
set "INSTALL_DB_NAME=db_kopi_topsis"
set /p "INPUT=Host MySQL [127.0.0.1]: "
if defined INPUT set "INSTALL_DB_HOST=%INPUT%"
set "INPUT="
set /p "INPUT=Port MySQL [3306]: "
if defined INPUT set "INSTALL_DB_PORT=%INPUT%"
set "INPUT="
set /p "INPUT=Username MySQL [root]: "
if defined INPUT set "INSTALL_DB_USER=%INPUT%"
set "INPUT="
set /p "INSTALL_DB_PASSWORD=Password MySQL [kosong jika tidak ada]: "
set /p "INPUT=Nama database [db_kopi_topsis]: "
if defined INPUT set "INSTALL_DB_NAME=%INPUT%"

echo [5/7] Memeriksa server dan membuat database jika diperlukan ...
".venv\Scripts\python.exe" scripts\setup_database.py
if errorlevel 1 (
    echo.
    echo Pastikan MySQL/MariaDB aktif. Jika menggunakan Laragon, klik Start All.
    goto :failed
)

echo [6/7] Menjalankan migrasi database ...
".venv\Scripts\flask.exe" --app run.py db upgrade
if errorlevel 1 goto :failed

set "ADMIN_EMAIL=admin@kopi.local"
set "ADMIN_PASSWORD=Admin123!"
echo.
set /p "INPUT=Email admin [admin@kopi.local]: "
if defined INPUT set "ADMIN_EMAIL=%INPUT%"
set "INPUT="
set /p "INPUT=Password admin [Admin123!]: "
if defined INPUT set "ADMIN_PASSWORD=%INPUT%"

echo [7/7] Menjalankan seed idempoten ...
".venv\Scripts\flask.exe" --app run.py init-db --admin-email "%ADMIN_EMAIL%" --admin-password "%ADMIN_PASSWORD%" --refresh-seed
if errorlevel 1 goto :failed

echo.
echo ============================================================
echo  INSTALASI BERHASIL
echo ============================================================
echo Database : %INSTALL_DB_NAME%
echo Admin    : %ADMIN_EMAIL%
echo Jalankan : start.bat
echo.
pause
exit /b 0

:failed
echo.
echo [GAGAL] Instalasi dihentikan. Periksa pesan kesalahan di atas.
pause
exit /b 1
