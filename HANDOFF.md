# 引き継ぎメモ (HANDOFF)

## 現在の状況
- Windows版 v3.1: 整列ボタン修正、一発更新bat統一済み
- Mac版 v1.2: 即ランチャー連携・Gドライブ対応済み
- 全PC (Googleドライブ同期) で使える状態

## 今回の変更（2026-03-12）即ランチャーセッションから修正
### IME半角固定バグ修正
- 透明キーボード起動時にフォーカスを奪い、IMEが半角英数に固定される問題を修正
- `deiconify`前に前面ウィンドウを記録し、表示後に即`SetForegroundWindow`で復元
- `_realign_all`整列後にも同様にフォーカスを復元

### 最前面維持をやめる
- 常時`-topmost=True`を廃止
- 起動時・整列時（Show All等）に一瞬だけtopmost → 即解除に変更
- `_on_restore`（最小化復元時）、`_tray_show`（トレイ復元時）からもtopmost削除

## 次のアクション
1. **即ランチャー**: ドロップシャドウ補正の実装（ROADMAP.mdにメモ済み）
2. **Mac版**: テスト継続、サイズ縮小（未着手）

## ファイル構成
- `transparent_keyboard.py` — Windows版メインソース
- `transparent_keyboard.ico` — アプリアイコン
- `透明キーボード.exe` — ビルド済みEXE（gitignore対象、Googleドライブ同期で配布）
- `一発更新_透明キーボード.bat` — 他PC用一発更新スクリプト
- `mac/transparent_keyboard_mac.py` — Mac版メインソース
- `mac/run.sh` — Mac版起動スクリプト
- `mac/README.md` — Mac版セットアップ手順

## 技術メモ
### Windows
- キー送信: SendInput API (ctypes)
- コピペ: Ctrl+Ins / Shift+Ins（リモートデスクトップ対応）
- 重複起動防止: スロット制Mutex（最大3インスタンス）
- IMEトグル: VK_KANJI送信（ImmSetOpenStatusはWindows Terminal非対応）
- ドロップシャドウ: SHADOW_INSET=7px、影を画面外に押し出して実体を端に寄せる
- EXEビルド: `py -3.14` が必要（デフォルトの `py` はTclバージョン競合）
- タスクバー: WS_EX_APPWINDOW + AppUserModelID
- トレイアイコン: pystray + Pillow（threaded）
- プロセス終了: `taskkill /F /IM 透明キーボード.exe`（WINDOWTITLE方式は不可）

### Mac
- キー送信: CGEvent (Quartz)
- コピペ: Cmd+C / Cmd+V
- Home/End: Ctrl+A / Ctrl+E
- 自動起動: LaunchAgent
- アクセシビリティ権限が必須
