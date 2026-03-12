# 引き継ぎメモ (HANDOFF)

## 現在の状況
- Windows版 v3.2: 復元バグ修正、右端配置、自動複数起動
- Mac版 v1.5: メニューバー常駐は即ランチャーに統合、単体は表示専用
- 全PC (Googleドライブ同期) で使える状態

## 今回の変更（2026-03-12）
### Mac版: 即ランチャーとの統合
- メニューバーアイコン枠の奪い合い問題（ノッチ付きMacでスペース不足）を解決
- 透明キーボードのメニューバー常駐を廃止 → 即ランチャーの「⌨ Keyboard」メニューから起動
- 単独LaunchAgent（com.nock.transparent-keyboard.plist）を削除
- 透明キーボードMac版はキーボード表示専用に簡素化（メニューバー・Dock非表示）

### 即ランチャー側の変更
- アイコンを📂絵文字 → フォルダ+キーボードのNSImage描画に変更
- メニューに「⌨ Keyboard」トグル追加（起動中なら閉じる、未起動なら起動）

## 次のアクション
1. **即ランチャー**: ドロップシャドウ補正の実装（ROADMAP.mdにメモ済み）
2. **Mac版**: テスト継続、サイズ縮小（未着手）

## ファイル構成
- `transparent_keyboard.py` — Windows版メインソース
- `transparent_keyboard.ico` — アプリアイコン
- `透明キーボード.exe` — ビルド済みEXE（gitignore対象、Googleドライブ同期で配布）
- `一発更新_透明キーボード.bat` — 他PC用一発更新スクリプト
- `mac/transparent_keyboard_mac.py` — Mac版メインソース（表示専用、メニューバー常駐なし）
- `mac/run.sh` — Mac版起動・インストールスクリプト
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
- メニューバー常駐: 即ランチャー（folder_launcher.py）に統合
- Sandbox問題: Googleドライブ上のファイルはLaunchAgentから直接アクセス不可
- アクセシビリティ権限が必須
