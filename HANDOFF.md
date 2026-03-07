# 引き継ぎメモ (HANDOFF)

## 現在の状況
- Windows版 v2.2: ShowAll(🪟🪟)機能追加、EXE再ビルド済み（Python 3.14 + PyInstaller 6.19.0）
- Mac版 v1.0: Windows版に合わせて書き直し済み、動作確認OK、LaunchAgent登録済み
- 全PC (Dropbox同期) で使える状態

## 今回の変更（2026-03-08）
### Mac版
- Windows版の最新機能に合わせて全面書き直し
- コンパクト化: 横幅312px、縦幅160px、フォント小さめ
- Home → Ctrl+A（シェル行頭）、End → Ctrl+E（シェル行末）に変更
- 📸 → PrScr（文字表記）、🪟🪟 → Term（白文字）に変更
- 最小化ボタン追加（反対色で目立たせる）
- NSObject継承のMenuDelegateで「Show Keyboard」メニュー実装
- LaunchAgent (`com.nock.transparent-keyboard.plist`) でログイン時自動起動
- メニューバー ⌨ アイコンから復帰可能

## 次のアクション
1. **Windows版: システムトレイアイコン** — `pystray` + `Pillow` で通知領域にアイコン常駐（未着手）
2. **Mac版: テスト継続** — 実使用での不具合洗い出し

## ファイル構成
- `transparent_keyboard.py` — Windows版メインソース
- `transparent_keyboard.ico` — アプリアイコン
- `透明キーボード.exe` — ビルド済みEXE（gitignore対象、Dropbox同期で配布）
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
