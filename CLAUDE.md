# 透明キーボード (Transparent Keyboard)

## プロジェクト概要
Windows用の透明オーバーレイキーボード。
リモートデスクトップやスマホからPCを操作する際、フォーカスを奪わずにキー入力を送信する。
Claudeのリモートセッションで、スマホからPCのClaude Codeを操作するために開発。

## 技術スタック
- Python (tkinter)
- Windows API (ctypes: SendInput, SetWindowLongW)
- PyInstaller でEXE化

## 主な機能
- 数字キー (0-9)
- コピー/ペースト (Ctrl+Ins / Shift+Ins で実装、SendInput方式)
- Enter / BS / Home / End / Del
- PrtSc / スクショ貼り付け (PowerShellでクリップボード画像をファイル保存→パス入力)
- 半角/全角切替
- `/remote-control` `/resume` のワンタップ入力
- テーマ切り替え (6色: ピンク, ブルー, グリーン, パープル, オレンジ, ダーク)
- ドラッグ移動

## アーキテクチャ
### ウィンドウ特性
- `overrideredirect(True)` — ウィンドウ枠なし
- `WS_EX_NOACTIVATE` — クリックしてもフォーカスを奪わない
- `WS_EX_TOOLWINDOW` — タスクバーに表示しない、Alt+Tabに出ない
- `-topmost True` — 常に最前面
- `-alpha 0.4` — 40%不透明度
- Mutex による重複起動防止

### キー送信方式
- `SendInput` API で仮想キーコードを送信
- Unicode テキスト入力は `KEYEVENTF_UNICODE` フラグで1文字ずつ送信
- 拡張キー (Delete, Insert, Home, End) は `KEYEVENTF_EXTENDEDKEY` フラグが必要

### コピー/ペースト
- `Ctrl+C` / `Ctrl+V` ではなく `Ctrl+Ins` / `Shift+Ins` を使用
- 理由: リモートデスクトップ経由でCtrl系が効かないケースがある

## ファイル構成
```
透明キーボード/
├── transparent_keyboard.py   # メインソース
├── transparent_keyboard.ico  # アプリアイコン (ピンク背景のキーボード)
├── 透明キーボード.exe         # PyInstaller ビルド済みEXE
├── 一発更新_透明キーボード.bat # 他PC用の一発更新（終了→ショートカット→起動）
├── CLAUDE.md                 # このファイル
├── HANDOFF.md                # 引き継ぎメモ
├── ROADMAP.md                # ロードマップ
├── DEVLOG.md                 # 開発ログ
└── .gitignore
```

## EXE ビルド方法
```bash
# プロジェクトディレクトリで実行
PYTHONUTF8=1 py -m PyInstaller --onefile --windowed --icon=transparent_keyboard.ico --name="透明キーボード" transparent_keyboard.py
# 出力: dist/透明キーボード.exe をプロジェクトルートにコピー
```

## 配布方式
- Googleドライブ で全PCに自動同期
- EXE を直接起動（インストール不要）
- `一発更新_透明キーボード.bat` でデスクトップとスタートメニューにショートカット作成
- グローバル CLAUDE.md のセッション開始チェックリスト (Step 4) でショートカット有無を確認

## 既知の問題

### タスクバーにアイコンが表示されない
**原因特定済み**: `WS_EX_TOOLWINDOW` フラグと `overrideredirect(True)` の組み合わせにより、
Windowsがタスクバーにアイコンを表示しない。これは意図的な設計だが、
起動中かどうかわかりにくい問題がある。
**対策案**: システムトレイ（通知領域）にアイコンを常駐させる。
`WS_EX_TOOLWINDOW` を外すとAlt+Tabに出てしまうので、トレイアイコンが最適解。

### タスクバーにピン留めしても動作しない可能性
ショートカット経由でタスクバーにピン留めしても、`overrideredirect(True)` のため
Windowsがウィンドウを認識できず、ピン留めアイコンと実行中ウィンドウが紐付かない。
トレイアイコン実装で解決する方針。

## ★「ビルドして」で全自動デプロイ（確認不要・即実行）
ユーザーが「ビルドして」「ビルド」「デプロイ」「EXE更新」等と言ったら、以下を全て自動実行：
1. `taskkill /F /IM 透明キーボード.exe` で既存プロセスを終了（Pythonのsubprocess経由、encoding='cp932'）
2. `py -3.14 -m PyInstaller` でEXEビルド
3. `dist/透明キーボード.exe` をプロジェクトルートにコピー（Pythonのshutil経由）
4. スタートメニュー・スタートアップのショートカットを上書き（PowerShell経由）
5. 新EXEを起動
6. コミット＆プッシュ

### プロセス終了の注意
- `taskkill /FI "WINDOWTITLE eq ..."` は**使わない**（マッチしない）
- `taskkill /F /IM 透明キーボード.exe` を使う
- Git Bashでは `/IM` `/FI` がパスに変換されるため、Python subprocess経由で実行する

## 開発時の注意
- ★ 文字化け防止ルール: PYTHONUTF8=1 設定、encoding='utf-8' 必須
- Python実行は `py` コマンド（Microsoft Store リダイレクト回避）
- バッチファイルに日本語を直接書くなら `chcp 65001` 必須
