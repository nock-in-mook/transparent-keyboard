#!/bin/bash
# 透明キーボード Mac版 起動・インストールスクリプト
# --install: LaunchAgentを設定（GDriveから直接実行、ローカルコピーなし）
# 引数なし: 直接起動

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/transparent_keyboard_mac.py"
PLIST="$HOME/Library/LaunchAgents/com.nock.transparent-keyboard.plist"

install() {
    # 古いローカルコピーがあれば削除
    OLD_DEST="$HOME/.local/bin/transparent_keyboard_mac.py"
    if [ -f "$OLD_DEST" ]; then
        rm "$OLD_DEST"
        echo "古いローカルコピーを削除: $OLD_DEST"
    fi

    # LaunchAgent plist を作成（GDriveのスクリプトを直接参照）
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

    # LaunchAgent を登録
    launchctl unload "$PLIST" 2>/dev/null
    launchctl load "$PLIST"
    echo "LaunchAgent 登録完了（GDriveから直接実行）"
    echo "今すぐ起動します..."
    exec /usr/bin/python3 "$SRC"
}

if [ "$1" = "--install" ]; then
    install
else
    cd "$SCRIPT_DIR"
    python3 transparent_keyboard_mac.py
fi
