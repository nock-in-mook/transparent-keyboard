# 引き継ぎメモ (HANDOFF)

## 現在の状況
- Windows版 v2.2: ShowAll(🪟🪟)機能追加、EXE再ビルド済み（Python 3.14 + PyInstaller 6.19.0）
- Mac版 v0.1: PyObjC版を新規作成（`mac/transparent_keyboard_mac.py`）、未テスト
- 全PC (Dropbox同期) で使える状態

## 今回の変更（2026-03-08）
### Windows版
- EXEを最新ソースから再ビルド（別PCで作業中のため差し替え）
- Python 3.14 + PyInstaller 6.19.0 でビルド
- ShowAll(🪟🪟)機能・レイアウト調整が反映済み

## 次のアクション
1. **Mac版テスト** — ユーザーがMacにPython3 + PyObjC環境を準備次第テスト
2. **Windows版: システムトレイアイコン** — `pystray` + `Pillow` で通知領域にアイコン常駐（未着手）

## ファイル構成
- `transparent_keyboard.py` — Windows版メインソース
- `transparent_keyboard.ico` — アプリアイコン
- `透明キーボード.exe` — ビルド済みEXE（gitignore対象、Dropbox同期で配布）
- `install_keyboard.bat` — ショートカット作成
- `mac/transparent_keyboard_mac.py` — Mac版メインソース
- `mac/run.sh` — Mac版起動スクリプト
- `mac/README.md` — Mac版セットアップ手順

## 技術メモ
### Windows
- キー送信: SendInput API (ctypes)
- コピペ: Ctrl+Ins / Shift+Ins（リモートデスクトップ対応）
- 重複起動防止: Windows Mutex
- EXEビルド: `py -3.14` が必要（デフォルトの `py` はランタイム見つからないエラー）

### Mac
- キー送信: CGEvent (Quartz)
- コピペ: Cmd+C / Cmd+V（標準方式で問題なし）
- ウィンドウ: NSPanel + NSWindowStyleMaskNonactivatingPanel
- アクセシビリティ権限が必須
