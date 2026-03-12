# 引き継ぎメモ (HANDOFF)

## 現在の状況
- Windows版 v3.2: 復元バグ修正、右端配置、自動複数起動
- Mac版 v1.2: 即ランチャー連携・Gドライブ対応済み
- 全PC (Googleドライブ同期) で使える状態

## 今回の変更（2026-03-12）
### タスクバーから復元できないバグ修正
- `_on_restore` が `<Map>` イベントにバインドされておらず、復元時のタスクバーガード無効化が機能していなかった
- `<Map>` イベントにバインドし、復元時に一時的にガードを無効化して再最小化ループを防止
- `_tray_show` にもガード無効化＋topmost処理を追加

### キーボード配置を右端から割り当て
- `_realign_all` でキーボードを右端ターミナルから順に割り当てるよう変更
- 以前は左端から割り当てていたため、1台だけ起動すると真ん中に配置されていた

### ターミナル数に合わせて自動複数起動
- スロット0（最初の起動）でWindows Terminalの数を検出し、不足分を自動起動
- 1つEXEを起動するだけでターミナル数分のキーボードが揃う

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
- 復元ガード: `<Map>`イベントで`_on_restore`をバインド、FocusInによる再最小化を防止

### Mac
- キー送信: CGEvent (Quartz)
- コピペ: Cmd+C / Cmd+V
- Home/End: Ctrl+A / Ctrl+E
- 自動起動: LaunchAgent
- アクセシビリティ権限が必須
