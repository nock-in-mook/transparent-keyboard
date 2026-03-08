# 引き継ぎメモ (HANDOFF)

## 現在の状況
- Windows版 v2.3: サイズ縮小（横70%・縦60%）、EXE再ビルド済み
- Mac版 v1.1: スクショ即保存・多重起動防止を追加、動作確認OK
- 全PC (Googleドライブ同期) で使える状態

## 今回の変更（2026-03-08）
### Mac版: スクショ即保存・多重起動防止
- PrScrボタン: `send_key(KC['4'], MOD_CMD | MOD_SHIFT)` → `screencapture -i` で範囲選択→即ファイル保存に変更
- 📷↑ボタン: クリップボード画像保存→最新スクショのパスをターミナルに入力する方式に変更
- 📁ボタン: 同じ保存先フォルダ (`/tmp/claude_screenshots/`) をFinderで開く（変更なし）
- `fcntl.flock` による多重起動防止を追加
- コミット・プッシュ済み

## Mac版: 要変更（Macで作業すること）
Windows版で実施済みの変更をMac版にも反映する。

### 1. `bring_terminals_to_front()` の変更
- **現状**: AppleScriptでTerminal/iTerm2を最前面に出すだけ（158-172行目）
- **変更**: Mac版の即ランチャー（`terminal_copy/folder_launcher.py`）にも `--show-all` 引数を追加し、それを呼ぶ方式に変更
- Mac版即ランチャーのパス: `~/Library/CloudStorage/GoogleDrive-yagukyou@gmail.com/マイドライブ/_Apps2026/terminal_copy/folder_launcher.py`
- 呼び出し例: `subprocess.Popen(['python3', script, '--show-all'])`

### 2. `open_apps_folder()` のパス確認
- 既にGoogleドライブパスに変更済み（149行目）→ 問題なし

## 次のアクション
1. **Windows版: システムトレイアイコン** — `pystray` + `Pillow` で通知領域にアイコン常駐（未着手）
2. **Mac版: テスト継続** — 実使用での不具合洗い出し
3. **Mac版: サイズ縮小** — Windows版に合わせてコンパクト化（未着手）

## ファイル構成
- `transparent_keyboard.py` — Windows版メインソース
- `transparent_keyboard.ico` — アプリアイコン
- `透明キーボード.exe` — ビルド済みEXE（gitignore対象、Googleドライブ同期で配布）
- `install_keyboard.bat` — ショートカット作成
- `mac/transparent_keyboard_mac.py` — Mac版メインソース
- `mac/run.sh` — Mac版起動スクリプト
- `mac/README.md` — Mac版セットアップ手順
- `~/Library/LaunchAgents/com.nock.transparent-keyboard.plist` — Mac版自動起動設定

## 技術メモ
### Windows
- キー送信: SendInput API (ctypes)
- コピペ: Ctrl+Ins / Shift+Ins（リモートデスクトップ対応）
- 重複起動防止: Windows Mutex
- EXEビルド: `py -3.14` が必要（デフォルトの `py` はランタイム見つからないエラー）

### Mac
- キー送信: CGEvent (Quartz)
- コピペ: Cmd+C / Cmd+V（標準方式で問題なし）
- Home/End: Ctrl+A / Ctrl+E（シェル互換）
- ウィンドウ: NSPanel + NSWindowStyleMaskNonactivatingPanel
- メニュー: NSObject継承のMenuDelegateでObjCランタイム対応
- 自動起動: LaunchAgent (com.nock.transparent-keyboard.plist)
- アクセシビリティ権限が必須
- スクショ: `screencapture -i` で即ファイル保存、保存先は `/tmp/claude_screenshots/`
- 多重起動防止: `fcntl.flock` でロックファイル

