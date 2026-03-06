# 透明キーボード Mac版

## セットアップ

### 1. Python 3 インストール
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python3
```

### 2. 依存ライブラリ
```bash
pip3 install pyobjc-framework-Cocoa pyobjc-framework-Quartz
```

### 3. アクセシビリティ権限
システム設定 → プライバシーとセキュリティ → アクセシビリティ
→ ターミナル（または Python）を許可

### 4. 起動
```bash
cd mac/
chmod +x run.sh
./run.sh
```

## キー配置

| ボタン | 動作 |
|--------|------|
| ESC | Escape |
| ← ↓ ↑ → | 矢印キー |
| ⌘Z | 元に戻す |
| 0-9 | 数字入力 |
| 📷↑ | クリップボード画像をファイル保存→パス入力 |
| 英/日 | 入力ソース切替 (Ctrl+Space) |
| 📁 | スクショフォルダを開く |
| 📸 | 選択範囲スクショ→クリップボード |
| Copy | Cmd+C |
| Paste | Cmd+V |
| ⌃U | 行頭まで削除 (Ctrl+U) |
| Home | 行頭 (Cmd+←) |
| End | 行末 (Cmd+→) |
| BS | Backspace |
| Enter | Enter |
| F13 | F13キー |
| /remote-control | コマンド入力+Enter |
| /resume | コマンド入力+Enter |

## トラブルシューティング

### キーが送信されない
→ アクセシビリティ権限を確認。ターミナルとPythonの両方に許可が必要な場合あり。

### 英/日切替が動かない
→ macOSの入力ソース切替キーが Ctrl+Space でない場合あり。
   システム設定 → キーボード → キーボードショートカット → 入力ソース で確認。
