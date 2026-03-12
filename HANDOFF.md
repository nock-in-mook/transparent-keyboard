# 引き継ぎメモ (HANDOFF)

## 現在の状況
- Windows版 v3.2: 復元バグ修正、右端配置、自動複数起動
- Mac版 v1.4: メニューバー常駐方式、ローカルインストール、LaunchAgent自動起動
- 全PC (Googleドライブ同期) で使える状態

## 今回の変更（2026-03-12）
### Mac版: メニューバー常駐方式に変更
- Dockに表示しない（`NSApplicationActivationPolicyAccessory`）
- Mac起動時はメニューバーに⌨アイコンだけ常駐（キーボード非表示）
- メニューから Show/Hide をトグルで切り替え
- Quitメニュー削除（誤操作防止）
- アイコンをキーボード型NSImage描画に変更（Template対応でダークモードOK）
- `--hidden` オプションでLaunchAgentから非表示起動

### Mac版: ローカルインストール方式
- Sandbox問題でGoogleドライブ上のスクリプトをLaunchAgentから直接実行不可
- `~/.local/bin/` にコピーして実行する方式
- `run.sh --install` で再インストール可能

## 次のアクション
1. **即ランチャー**: ドロップシャドウ補正の実装（ROADMAP.mdにメモ済み）
2. **Mac版**: テスト継続、サイズ縮小（未着手）

## ファイル構成
- `transparent_keyboard.py` — Windows版メインソース
- `transparent_keyboard.ico` — アプリアイコン
- `透明キーボード.exe` — ビルド済みEXE（gitignore対象、Googleドライブ同期で配布）
- `一発更新_透明キーボード.bat` — 他PC用一発更新スクリプト
- `mac/transparent_keyboard_mac.py` — Mac版メインソース
- `mac/run.sh` — Mac版起動・インストールスクリプト（--installでローカルインストール）
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
- 復元ガード: `<Map>`イベントで`_on_restore`をバインド、FocusInによる再最小化を防止

### Mac
- キー送信: CGEvent (Quartz)
- コピペ: Cmd+C / Cmd+V
- Home/End: Ctrl+A / Ctrl+E
- 自動起動: LaunchAgent → `~/.local/bin/` のローカルコピーを `--hidden` で実行
- メニューバー: NSStatusBar + NSImage描画（キーボード型アイコン、Template対応）
- Sandbox問題: Googleドライブ上のファイルはLaunchAgentから直接アクセス不可
- アクセシビリティ権限が必須
