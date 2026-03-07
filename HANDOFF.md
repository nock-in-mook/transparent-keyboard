# 引き継ぎメモ (HANDOFF)

## 現在の状況
- Windows版 v2.1: CtrlA追加・ダブルクリック最小化・/remote短縮、EXE再ビルド済み
- Mac版 v0.1: PyObjC版を新規作成（`mac/transparent_keyboard_mac.py`）、未テスト
- 全PC (Dropbox同期) で使える状態

## 今回の変更（2026-03-06）
### Windows版
- ヘッダのダブルクリックで最小化
- CtrlA（全選択）ボタンをF13とremoteの間に追加
- `/remote-control` → `/remote` に表示短縮（送信テキストはそのまま）
- EXE再ビルド済み

### Mac版（新規）
- PyObjC (Cocoa + Quartz) でフルネイティブ実装
- NSPanel（フォーカスを奪わない）+ CGEvent（キー送信）
- Dock表示対応、メニューバーアイコン常駐
- ダブルクリックで最小化（Dockから復元可能）
- キー配置: ESC, 矢印, ⌘Z, 数字, Copy(⌘C), Paste(⌘V), ⌃U, Home(⌘←), End(⌘→), BS, 📸(スクショ), 英/日(Ctrl+Space), ⌘A, F13, /remote, /resume, Enter

## 次のアクション
1. **Mac版テスト** — ユーザーがMacにPython3 + PyObjC環境を準備次第テスト
   - `brew install python3 && pip3 install pyobjc-framework-Cocoa pyobjc-framework-Quartz`
   - アクセシビリティ権限の許可が必要
   - 英/日切替はCtrl+Spaceだが環境により要調整（Fn/Globe等）
2. **Windows版: システムトレイアイコン** — `pystray` + `Pillow` で通知領域にアイコン常駐（未着手）

## ファイル構成
- `transparent_keyboard.py` — Windows版メインソース
- `transparent_keyboard.ico` — アプリアイコン
- `透明キーボード.exe` — ビルド済みEXE
- `install_keyboard.bat` — ショートカット作成
- `mac/transparent_keyboard_mac.py` — Mac版メインソース
- `mac/run.sh` — Mac版起動スクリプト
- `mac/README.md` — Mac版セットアップ手順

## 技術メモ
### Windows
- キー送信: SendInput API (ctypes)
- コピペ: Ctrl+Ins / Shift+Ins（リモートデスクトップ対応）
- 重複起動防止: Windows Mutex

### Mac
- キー送信: CGEvent (Quartz)
- コピペ: Cmd+C / Cmd+V（標準方式で問題なし）
- ウィンドウ: NSPanel + NSWindowStyleMaskNonactivatingPanel
- アクセシビリティ権限が必須
