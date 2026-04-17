# 透明キーボード 開発ログ

## 2026-04-17 - Mac版: キー送信を CGEventPost → osascript に切替（永続バグ修正）

**症状**: 「テキスト送信ボタンが反応しない（けどスクショボタンは動く）。一度ハマると macOS 再起動するまで戻らない」が長年続いてた。

**調査でわかったこと**:
- 透明キーボードは Xcode 内 Python（`/Applications/Xcode.app/.../Python.app`）で動いてる
- TCC.db に `com.apple.python3` を追加して許可しても、 `CGEventPost(kCGHIDEventTap, ...)` が無言で失敗するケースがある
- スクショボタンが動くのは `subprocess.Popen(['screencapture', '-i', ...])` で別プロセス起動だから（自プロセスのアクセシビリティ権限を経由しない）
- 即ランチャー本体／透明キーボードを TCC 更新後に再起動しても直らないケースあり = macOS 側の TCC キャッシュ／code signature 不整合バグの疑い
- macOS 再起動で一度治る理由：再起動で TCC キャッシュが完全 clear されるから

**修正**: `mac/transparent_keyboard_mac.py:83-103` の `send_key()` / `type_text()` を osascript 版に置き換え。
- `_osascript()` ヘルパーで `subprocess.run(['osascript', '-e', ...])` を呼ぶ
- `send_key`: `tell application "System Events" to key code N using {command down, ...}`
- `type_text`: `tell application "System Events" to keystroke "..."`（改行は `key code 36` で別送信）
- スクショと同じく **別プロセス起動方式** になるので、Python 自身のアクセシビリティ権限は不要、System Events の権限が使われる
- System Events のアクセシビリティ許可は安定（Apple純正）なので、TCC キャッシュ問題の影響を受けない

**効果**: 再起動なしで安定してキー送信できるようになった。

**注**: CGEventPost より osascript の方がプロセス起動コスト分わずかに遅いが、ボタン押下毎の単発送信なので体感差なし。Quartz の CGEvent 系 import は将来の参照用にそのまま残してある。

### 同日追記: type_text を pbcopy + Cmd+V のペースト方式に変更

osascript の `keystroke` 方式に切り替えたら、**日本語IME ON 時に `/exit` が `/えぃｔ` に化ける**バグが発覚。
- 原因: AppleScript の `keystroke` は IME を経由する。CGEventPost + `CGEventKeyboardSetUnicodeString` は IME バイパスだったので問題なかった
- 対策: `type_text()` を `pbpaste`（退避）→ 英数キー → `pbcopy`（テキスト設定）→ `Cmd+V`（ペースト）→ `pbcopy`（クリップボード復元）に変更
- メリット: IME を完全回避、漢字・絵文字を含む任意文字列を安全に送信可能、改行も含めて1回のペーストで完結
- 副作用: ユーザーのクリップボードを 150ms 借用するが、終了時に元の内容を復元するので実害なし
- `send_key()` は `key code` 経由で IME バイパスされるので変更不要

## 2026-02-27 - v1.0 初期実装
- tkinter + ctypes でフォーカスを奪わない透明キーボードを実装
- SendInput API でキー送信
- WS_EX_NOACTIVATE + WS_EX_TOOLWINDOW でオーバーレイ動作
- テーマ切り替え (6色) 実装
- PyInstaller でEXE化、install_keyboard.bat でショートカット作成

## 2026-03-12 - IME半角固定バグ修正 + topmost廃止
- 起動時にフォーカスを奪いIMEが壊れる問題を修正（前面ウィンドウを記録→復元）
- 整列時（_realign_all）にもフォーカス復元を追加
- 常時topmost維持を廃止、起動・整列時に一瞬だけtopmost→即解除に変更
- _on_restore、_tray_showからもtopmost削除

## 2026-03-02 - プロジェクト独立化
- Kanji_Stroke プロジェクトから分離して独立リポジトリ化
- CLAUDE.md, HANDOFF.md, ROADMAP.md, DEVLOG.md 作成
- タスクバーアイコン非表示問題を特定:
  - 原因: WS_EX_TOOLWINDOW + overrideredirect(True)
  - 対策: システムトレイアイコン実装 (v1.1で対応予定)
