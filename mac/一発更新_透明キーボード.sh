#!/bin/bash
# 一発更新: 透明キーボードMac版
# 既存プロセスをkill → LaunchAgentをGDrive直接実行に再設定 → 再起動

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/transparent_keyboard_mac.py"
PLIST="$HOME/Library/LaunchAgents/com.nock.transparent-keyboard.plist"

echo "=== 透明キーボード 一発更新 ==="

# 1. 既存プロセスを全てkill
echo "既存プロセスを停止中..."
pkill -f 'transparent_keyboard_mac.py' 2>/dev/null
sleep 1

# 2. 古いローカルコピーを削除
OLD_DEST="$HOME/.local/bin/transparent_keyboard_mac.py"
if [ -f "$OLD_DEST" ]; then
    rm "$OLD_DEST"
    echo "古いローカルコピーを削除: $OLD_DEST"
fi

# 3. LaunchAgent plist を再作成（GDrive直接参照）
cat > "$PLIST" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.nock.transparent-keyboard</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$SRC</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
</dict>
</plist>
PLIST_EOF

# 4. LaunchAgent再登録
launchctl unload "$PLIST" 2>/dev/null
launchctl load "$PLIST"

echo "LaunchAgent 更新完了（GDriveから直接実行に変更）"
echo ""
echo "=== 完了！透明キーボードが再起動されます ==="
