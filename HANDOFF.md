# 引き継ぎメモ (HANDOFF)

## 現在の状況
- 透明キーボード v1 は完成・動作中
- 全PC (Dropbox同期) で使える状態
- EXE (PyInstaller) でビルド済み
- install_keyboard.bat でショートカット作成済み

## 直近の問題: タスクバーアイコンが出ない
- **原因**: `WS_EX_TOOLWINDOW` + `overrideredirect(True)` がタスクバー表示を抑制
- **影響**: 起動中かどうか見た目でわからない
- **推奨解決策**: システムトレイ（通知領域）にアイコンを追加する
  - `pystray` ライブラリが最も手軽
  - トレイアイコンから「終了」「テーマ変更」等のメニューも出せる
  - `WS_EX_TOOLWINDOW` はそのまま維持（Alt+Tabに出さない設計は正しい）

## 次のアクション
1. **システムトレイアイコン実装** — `pystray` + `Pillow` で通知領域にピンクアイコン常駐
2. トレイアイコンの右クリックメニュー（終了、テーマ切替）
3. EXE再ビルド → 全PCに自動配布（Dropbox同期）

## ファイル構成
- `transparent_keyboard.py` — メインソース（全ロジックが1ファイル）
- `transparent_keyboard.ico` — アイコンファイル
- `透明キーボード.exe` — ビルド済みEXE
- `install_keyboard.bat` — ショートカット作成

## 技術メモ
- キー送信: SendInput API (ctypes)
- コピペ: Ctrl+Ins / Shift+Ins（リモートデスクトップ対応）
- 重複起動防止: Windows Mutex
- フォーカス制御: WS_EX_NOACTIVATE（クリックしてもフォーカスを奪わない）
