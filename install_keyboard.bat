@echo off
chcp 65001 >nul
echo ========================================
echo   透明キーボード インストーラ
echo ========================================
echo.

set "EXE_PATH=G:\マイドライブ\_Apps2026\透明キーボード\透明キーボード.exe"
set "ICO_PATH=G:\マイドライブ\_Apps2026\透明キーボード\transparent_keyboard.ico"
set "SHORTCUT_NAME=透明キーボード"

REM EXE存在確認
if not exist "%EXE_PATH%" (
    echo ERROR: EXEが見つかりません
    echo %EXE_PATH%
    echo Googleドライブの同期を確認してください
    pause
    exit /b 1
)

REM 実行中の透明キーボードを終了
echo [0/4] 実行中の透明キーボードを終了中...
taskkill /F /FI "WINDOWTITLE eq 透明キーボード" >nul 2>&1
timeout /t 1 /nobreak >nul
echo   OK

REM スタートメニューにショートカット作成
echo [1/4] スタートメニューにショートカット作成中...
set "START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%START_MENU%\%SHORTCUT_NAME%.lnk'); $sc.TargetPath = '%EXE_PATH%'; $sc.IconLocation = '%ICO_PATH%'; $sc.Description = '透明キーボード オーバーレイ'; $sc.Save()"
echo   OK

REM デスクトップにショートカット作成
echo [2/4] デスクトップにショートカット作成中...
set "DESKTOP=%USERPROFILE%\Desktop"
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%DESKTOP%\%SHORTCUT_NAME%.lnk'); $sc.TargetPath = '%EXE_PATH%'; $sc.IconLocation = '%ICO_PATH%'; $sc.Description = '透明キーボード オーバーレイ'; $sc.Save()"
echo   OK

REM スタートアップにショートカット作成（PC起動時に自動起動）
echo [3/4] スタートアップにショートカット作成中...
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%STARTUP%\%SHORTCUT_NAME%.lnk'); $sc.TargetPath = '%EXE_PATH%'; $sc.IconLocation = '%ICO_PATH%'; $sc.Description = '透明キーボード オーバーレイ'; $sc.Save()"
echo   OK

REM 新しいEXEを起動
echo [4/4] 透明キーボードを起動中...
start "" "%EXE_PATH%"
echo   OK

echo.
echo ========================================
echo   インストール完了!
echo.
echo   Googleドライブから直接起動するので
echo   EXE更新時もこのbatを再実行するだけ
echo.
echo   タスクバーにピン留めするには:
echo   デスクトップの「透明キーボード」を
echo   右クリック → タスクバーにピン留め
echo ========================================
echo.
pause
