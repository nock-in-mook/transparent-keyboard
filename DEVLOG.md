# 透明キーボード 開発ログ

## 2026-02-27 - v1.0 初期実装
- tkinter + ctypes でフォーカスを奪わない透明キーボードを実装
- SendInput API でキー送信
- WS_EX_NOACTIVATE + WS_EX_TOOLWINDOW でオーバーレイ動作
- テーマ切り替え (6色) 実装
- PyInstaller でEXE化、install_keyboard.bat でショートカット作成

## 2026-03-02 - プロジェクト独立化
- Kanji_Stroke プロジェクトから分離して独立リポジトリ化
- CLAUDE.md, HANDOFF.md, ROADMAP.md, DEVLOG.md 作成
- タスクバーアイコン非表示問題を特定:
  - 原因: WS_EX_TOOLWINDOW + overrideredirect(True)
  - 対策: システムトレイアイコン実装 (v1.1で対応予定)
