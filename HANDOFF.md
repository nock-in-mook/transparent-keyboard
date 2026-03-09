# 引き継ぎメモ (HANDOFF)

## 現在の状況
- Windows版 v2.3: サイズ縮小（横70%・縦60%）、EXE再ビルド済み
- Mac版 v1.2: 即ランチャー連携・Gドライブ対応済み、動作確認OK
- 全PC (Googleドライブ同期) で使える状態

## 今回の変更（2026-03-09）
### Mac版: 即ランチャーShowAll連携
- `bring_terminals_to_front()` を自前AppleScript実装から即ランチャー(`folder_launcher.py --show-all`)呼び出しに変更
- 即ランチャーMac版にも `--show-all` 引数を追加（Windows版と統一）
- 即ランチャーが見つからない場合はAppleScriptフォールバック付き
- Dropbox参照は全てGoogleドライブに移行済み（前回対応分含め確認済み）

## 完了済みTODO
- ✅ Mac版 `bring_terminals_to_front()` → 即ランチャー連携
- ✅ Mac版 `open_apps_folder()` → Googleドライブパス
- ✅ スクショ関連 → `/tmp/claude_screenshots/` でDropbox非依存

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

