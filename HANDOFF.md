# 引き継ぎメモ (HANDOFF)

## 現在の状況
- Windows版 v3.0: UI大幅改善、ドロップシャドウ補正、EXE再ビルド済み
- Mac版 v1.2: 即ランチャー連携・Gドライブ対応済み
- 全PC (Googleドライブ同期) で使える状態
- install_keyboard.bat で一発全更新対応

## 今回の変更（2026-03-09）セッション011
### UI改善
- ボタンbd=0でオーバーフロー解消、行間テーマカラー復元
- 📷↑→🎞↑に変更、縦2行結合（📁キー削除）
- 矢印キーを◀▼▲▶の塗りつぶし三角に変更
- ★Apps→Apps
- 半角→半/全（IMEトグル方式に変更、ImmSetOpenStatusはWT非対応のため）
- タイトルバー高さ10→15px

### ドロップシャドウ補正
- ターミナル配置: 右端の影を画面外に押し出す（x = sw + SHADOW_INSET）
- キーボード配置: ターミナルの影に食い込ませる（kb_y -= SHADOW_INSET）
- キーボード高さ: SHADOW_INSET分を加算

### その他
- install_keyboard.bat: 実行中終了→ショートカット3箇所作成→新EXE起動の一発更新
- SendMessageW argtypes修正（Python 3.14互換）
- 即ランチャーROADMAP.mdに影補正実装依頼メモを追記

## 次のアクション
1. **即ランチャー**: ドロップシャドウ補正の実装（ROADMAP.mdにメモ済み）
2. **Mac版**: テスト継続、サイズ縮小（未着手）

## ファイル構成
- `transparent_keyboard.py` — Windows版メインソース
- `transparent_keyboard.ico` — アプリアイコン
- `透明キーボード.exe` — ビルド済みEXE（gitignore対象、Googleドライブ同期で配布）
- `install_keyboard.bat` — 一発全更新スクリプト
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

### Mac
- キー送信: CGEvent (Quartz)
- コピペ: Cmd+C / Cmd+V
- Home/End: Ctrl+A / Ctrl+E
- 自動起動: LaunchAgent
- アクセシビリティ権限が必須
