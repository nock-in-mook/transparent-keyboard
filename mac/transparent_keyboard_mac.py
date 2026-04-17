"""
透明キーボード Mac版 - デスクトップオーバーレイ
フォーカスを奪わずにキー送信するmacOS用オーバーレイキーボード。
Windows版と同じレイアウト・機能を提供。

必要:
  pip3 install pyobjc-framework-Cocoa pyobjc-framework-Quartz

権限:
  システム設定 → プライバシーとセキュリティ → アクセシビリティ で許可が必要
"""

import subprocess
import time
import os
import sys
import tempfile
import datetime
import fcntl
import json

import objc
from Foundation import NSObject, NSMakeRect, NSMakePoint, NSPointInRect, NSTimer
from AppKit import (
    NSApplication,
    NSPanel, NSView,
    NSColor, NSFont, NSBezierPath,
    NSScreen,
    NSBackingStoreBuffered,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
    NSWindowStyleMaskUtilityWindow,
    NSFloatingWindowLevel,
    NSApplicationActivationPolicyAccessory,
    NSAttributedString,
    NSForegroundColorAttributeName,
    NSFontAttributeName,
    NSMutableParagraphStyle,
    NSParagraphStyleAttributeName,
    NSCenterTextAlignment,
    NSEvent,
    NSPasteboard,
)
from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    kCGHIDEventTap,
    CGEventSetFlags,
    CGEventKeyboardSetUnicodeString,
    kCGEventFlagMaskCommand,
    kCGEventFlagMaskShift,
    kCGEventFlagMaskControl,
)


# =============================================
# Mac仮想キーコード
# =============================================
KC = {
    'return': 36,
    'delete': 51,        # Backspace
    'fwd_delete': 117,   # Forward Delete
    'escape': 53,
    'left': 123, 'right': 124, 'up': 126, 'down': 125,
    'home': 115, 'end': 119,
    'space': 49,
    'f13': 105,
    'tab': 48,
    'a': 0, 'c': 8, 'e': 14, 'v': 9, 'z': 6, 'u': 32,
    '0': 29, '1': 18, '2': 19, '3': 20, '4': 21,
    '5': 23, '6': 22, '7': 26, '8': 28, '9': 25,
}

MOD_CMD = kCGEventFlagMaskCommand
MOD_SHIFT = kCGEventFlagMaskShift
MOD_CTRL = kCGEventFlagMaskControl


# =============================================
# キー送信
# =============================================

def _osascript(script):
    """AppleScript を osascript で実行。
    CGEventPost と違い別プロセス起動なので、Pythonプロセス自体の
    アクセシビリティ権限ではなく System Events の権限が使われる。
    macOS の TCC キャッシュ問題で CGEventPost が無言で失敗する症状の回避策。"""
    subprocess.run(['osascript', '-e', script], check=False, capture_output=True)


def send_key(keycode, flags=0):
    """キーを押して離す（osascript 経由）"""
    modifiers = []
    if flags & MOD_CMD:
        modifiers.append('command down')
    if flags & MOD_SHIFT:
        modifiers.append('shift down')
    if flags & MOD_CTRL:
        modifiers.append('control down')
    if modifiers:
        script = f'tell application "System Events" to key code {keycode} using {{{", ".join(modifiers)}}}'
    else:
        script = f'tell application "System Events" to key code {keycode}'
    _osascript(script)


def type_text(text):
    """テキストを送信（pbcopy + Cmd+V のペースト方式、IME回避）。
    osascript の keystroke は IME を経由するので、日本語入力ON時に
    "/exit" が "/えぃｔ" に化ける。クリップボード経由のペーストなら
    IME を完全に回避でき、漢字・絵文字を含む任意文字列を安全に送れる。
    元のクリップボード内容は退避→復元する。"""
    if not text:
        return
    # 元のクリップボードを退避
    saved = subprocess.run(['pbpaste'], capture_output=True).stdout
    # 万一の IME バッファ干渉を避けるため英数モードに切替
    _osascript('tell application "System Events" to key code 102')
    # テキストをクリップボードに設定
    p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
    p.communicate(input=text.encode('utf-8'))
    # Cmd+V でペースト
    _osascript('tell application "System Events" to keystroke "v" using {command down}')
    # ペースト完了を待ってから元のクリップボードに戻す
    time.sleep(0.15)
    p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
    p.communicate(input=saved)


def type_text_enter(text):
    """テキスト入力してEnter"""
    type_text(text)
    time.sleep(0.02)
    send_key(KC['return'])


def _get_current_input_source():
    """ctypes経由でTIS APIから現在の入力ソースIDを取得"""
    import ctypes
    carbon = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/Carbon.framework/Carbon')
    cf = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
    carbon.TISCopyCurrentKeyboardInputSource.restype = ctypes.c_void_p
    carbon.TISGetInputSourceProperty.restype = ctypes.c_void_p
    carbon.TISGetInputSourceProperty.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    cf.CFStringCreateWithCString.restype = ctypes.c_void_p
    cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
    cf.CFStringGetCStringPtr.restype = ctypes.c_char_p
    cf.CFStringGetCStringPtr.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kTISPropertyInputSourceID = cf.CFStringCreateWithCString(None, b'TISPropertyInputSourceID', 0x08000100)
    current = carbon.TISCopyCurrentKeyboardInputSource()
    source_id = carbon.TISGetInputSourceProperty(current, kTISPropertyInputSourceID)
    result = cf.CFStringGetCStringPtr(source_id, 0x08000100)
    return result.decode() if result else ''


def toggle_input_source():
    """英数/かなをトグル切り替え（ポップアップなし）"""
    current = _get_current_input_source()
    if 'Japanese' in current or 'Kotoeri' in current:
        send_key(102)  # 英数キー（日本語→英語へ）
    else:
        send_key(104)  # かなキー（英語→日本語へ）


def get_screenshot_dir():
    """スクショ保存先ディレクトリを返す"""
    ss_dir = os.path.join(tempfile.gettempdir(), 'claude_screenshots')
    os.makedirs(ss_dir, exist_ok=True)
    return ss_dir


def take_screenshot():
    """screencapture -i で範囲選択スクショを撮って即保存"""
    ss_dir = get_screenshot_dir()
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(ss_dir, f'ss_{ts}.png')
    subprocess.Popen(['screencapture', '-i', path])


def paste_latest_screenshot():
    """保存先フォルダの最新画像のパスをターミナルに入力"""
    ss_dir = get_screenshot_dir()
    pngs = sorted(
        [os.path.join(ss_dir, f) for f in os.listdir(ss_dir) if f.endswith('.png')],
        key=os.path.getmtime
    )
    if pngs:
        type_text(pngs[-1])


def open_screenshot_folder():
    """スクショフォルダをFinderで開く"""
    subprocess.Popen(['open', get_screenshot_dir()])


def open_apps_folder():
    """アプリフォルダをFinderで開く"""
    candidates = [
        os.path.expanduser('~/Library/CloudStorage/GoogleDrive-yagukyou@gmail.com/マイドライブ/_Apps2026'),
    ]
    for path in candidates:
        if os.path.exists(path):
            subprocess.Popen(['open', path])
            return
    subprocess.Popen(['open', os.path.expanduser('~')])


def bring_terminals_to_front():
    """即ランチャーのShowAll機能で全ターミナルを最前面に出す"""
    launcher = os.path.expanduser(
        '~/Library/CloudStorage/GoogleDrive-yagukyou@gmail.com/マイドライブ/_Apps2026/terminal_copy/folder_launcher.py'
    )
    if os.path.exists(launcher):
        subprocess.Popen(['python3', launcher, '--show-all'])
    else:
        # フォールバック: 即ランチャーが見つからない場合はAppleScriptで直接操作
        script = '''
        tell application "System Events"
            if exists process "Terminal" then
                tell process "Terminal" to set frontmost to true
            end if
        end tell
        '''
        subprocess.Popen(['osascript', '-e', script])


# =============================================
# テーマ（RGB 0.0〜1.0）
# =============================================
THEMES = [
    ('pink',   (0.91, 0.54, 0.63), (0.80, 0.44, 0.56)),
    ('blue',   (0.37, 0.72, 0.85), (0.29, 0.62, 0.75)),
    ('green',  (0.42, 0.79, 0.54), (0.33, 0.69, 0.44)),
    ('purple', (0.66, 0.54, 0.85), (0.56, 0.44, 0.80)),
    ('orange', (0.91, 0.66, 0.33), (0.80, 0.56, 0.25)),
    ('yellow', (0.91, 0.85, 0.33), (0.80, 0.74, 0.25)),
    ('dark',   (0.23, 0.23, 0.37), (0.17, 0.17, 0.27)),
]

BTN_BG = (0.12, 0.18, 0.24)
BTN_FG = (0.94, 0.94, 0.94)
BTN_ACTIVE = (0.16, 0.31, 0.44)
CMD_BG = (0.10, 0.23, 0.36)
ENTER_BG = (0.16, 0.29, 0.42)


def rgb(r, g, b, a=1.0):
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a)


# =============================================
# タイマーコールバック用ヘルパー
# =============================================
class _Invoker(NSObject):
    def initWithBlock_(self, block):
        self = objc.super(_Invoker, self).init()
        if self is None:
            return None
        self._block = block
        return self

    def invoke_(self, timer):
        if self._block:
            self._block()


# =============================================
# キーボードビュー
# =============================================
class KeyboardView(NSView):

    def initWithFrame_(self, frame):
        self = objc.super(KeyboardView, self).initWithFrame_(frame)
        if self is None:
            return None
        self._keyboard = None
        self._buttons = []
        self._pressed_idx = -1
        self._dragging = False
        self._drag_start = None
        self._header_rect = NSMakeRect(0, 0, 0, 0)
        self._last_click_time = 0
        return self

    @objc.python_method
    def setup(self, keyboard):
        self._keyboard = keyboard
        self._build_layout()

    def isFlipped(self):
        return True

    def acceptsFirstMouse_(self, event):
        return True

    @objc.python_method
    def _build_layout(self):
        """ボタン配置（動的サイズ対応）"""
        W = self.frame().size.width
        H = self.frame().size.height
        HDR_H = 36
        BTN_H = int((H - HDR_H) / 5)
        PAD = 1
        ENTER_W = max(36, int(W * 0.115))
        body_w = W - ENTER_W - PAD

        self._buttons = []

        # --- ヘッダ ---
        self._header_rect = NSMakeRect(0, 0, W, HDR_H)
        btn_y = (HDR_H - 16) / 2
        self._buttons.append((
            NSMakeRect(PAD, btn_y, 16, 16),
            '●', lambda: self._keyboard.cycle_theme(), 'theme'
        ))
        self._buttons.append((
            NSMakeRect(W - 38, btn_y, 16, 16),
            '━', lambda: self._keyboard.minimize(), 'minimize'
        ))
        self._buttons.append((
            NSMakeRect(W - 18, btn_y, 16, 16),
            '✕', lambda: self._keyboard.close(), 'close'
        ))

        y = HDR_H

        # --- Row 0: ESC ← ↓ ↑ → Apps ---
        row0 = [
            ('ESC',   lambda: send_key(KC['escape'])),
            ('←',     lambda: send_key(KC['left'])),
            ('↓',     lambda: send_key(KC['down'])),
            ('↑',     lambda: send_key(KC['up'])),
            ('→',     lambda: send_key(KC['right'])),
            ('/exit', lambda: type_text_enter('/exit')),
        ]
        bw = body_w / len(row0)
        for i, (label, action) in enumerate(row0):
            self._buttons.append((
                NSMakeRect(i * bw + PAD, y + PAD, bw - PAD * 2, BTN_H - PAD),
                label, action, 'key'
            ))
        y += BTN_H

        # --- Row 1-2: 数字キー + 📷↑(2行スパン) + 英/日 + PrScr ---
        num_w = body_w * 0.6 / 5
        func_w = body_w * 0.4 / 2
        # Row 1: 1 2 3 4 5 | 📷↑(2行) | 英/日
        x = PAD
        for n in '12345':
            self._buttons.append((
                NSMakeRect(x, y + PAD, num_w - PAD, BTN_H - PAD),
                n, lambda c=n: type_text(c), 'num'
            ))
            x += num_w
        # 📷↑: 2行にまたがる
        cam_x = x
        self._buttons.append((
            NSMakeRect(cam_x, y + PAD, func_w - PAD, BTN_H * 2 - PAD),
            '🎞↑', lambda: paste_latest_screenshot(), 'accent'
        ))
        x += func_w
        self._buttons.append((
            NSMakeRect(x, y + PAD, func_w - PAD, BTN_H - PAD),
            '📁SS', lambda: open_screenshot_folder(), 'key'
        ))
        y += BTN_H

        # Row 2: 6 7 8 9 0 | (📷↑が占有) | PrScr
        x = PAD
        for n in '67890':
            self._buttons.append((
                NSMakeRect(x, y + PAD, num_w - PAD, BTN_H - PAD),
                n, lambda c=n: type_text(c), 'num'
            ))
            x += num_w
        # col5は📷↑が占有（スキップ）
        x += func_w
        self._buttons.append((
            NSMakeRect(x, y + PAD, func_w - PAD, BTN_H - PAD),
            'PrScr', lambda: take_screenshot(), 'accent'
        ))
        y += BTN_H

        # --- Row 3: Copy Paste ⌃U | Home End BS ---
        # Home = Ctrl+A（シェル行頭）、End = Ctrl+E（シェル行末）
        left_keys = [
            ('Copy',  lambda: send_key(KC['c'], MOD_CMD)),
            ('Paste', lambda: send_key(KC['v'], MOD_CMD)),
            ('⌃U',   lambda: send_key(KC['u'], MOD_CTRL)),
        ]
        right_keys = [
            ('Home', lambda: send_key(KC['a'], MOD_CTRL)),
            ('End',  lambda: send_key(KC['e'], MOD_CTRL)),
            ('BS',   lambda: send_key(KC['delete'])),
        ]
        lw = body_w * 0.5 / len(left_keys)
        rw = body_w * 0.5 / len(right_keys)
        x = PAD
        for label, action in left_keys:
            self._buttons.append((
                NSMakeRect(x, y + PAD, lw - PAD, BTN_H - PAD),
                label, action, 'key'
            ))
            x += lw
        for label, action in right_keys:
            self._buttons.append((
                NSMakeRect(x, y + PAD, rw - PAD, BTN_H - PAD),
                label, action, 'key'
            ))
            x += rw
        y += BTN_H

        # --- Row 4: tmux復帰 ⌘A /remote /resume Claude ---
        cmd_keys = [
            ('tmux',     lambda: type_text_enter('tmux a'),            0.12),
            ('⌘A',       lambda: send_key(KC['a'], MOD_CMD),          0.12),
            ('/remote',  lambda: type_text_enter('/remote-control'),   0.26),
            ('/resume',  lambda: type_text_enter('/resume'),           0.22),
            ('Claude',   lambda: type_text_enter('claude --dangerously-skip-permissions'), 0.28),
        ]
        x = PAD
        for label, action, ratio in cmd_keys:
            w = body_w * ratio
            self._buttons.append((
                NSMakeRect(x, y + PAD, w - PAD, BTN_H - PAD),
                label, action, 'cmd'
            ))
            x += w

        # --- Enter（右端、全行スパン）---
        enter_y = HDR_H + PAD
        enter_h = BTN_H * 5 - PAD * 2
        self._buttons.append((
            NSMakeRect(body_w + PAD, enter_y, ENTER_W - PAD * 2, enter_h),
            'Ent\n⏎', lambda: send_key(KC['return']), 'enter'
        ))

    def drawRect_(self, dirty_rect):
        if self._keyboard is None:
            return

        theme = THEMES[self._keyboard.theme_idx]

        # 背景
        rgb(*theme[1]).setFill()
        NSBezierPath.fillRect_(self.bounds())

        # ヘッダ背景
        rgb(*theme[2]).setFill()
        NSBezierPath.fillRect_(self._header_rect)

        # ヘッダにフォルダ名を角丸枠付きで表示
        if self._keyboard and self._keyboard.title:
            title_attrs = {
                NSForegroundColorAttributeName: rgb(1.0, 1.0, 1.0, 0.95),
                NSFontAttributeName: NSFont.boldSystemFontOfSize_(14),
            }
            title_para = NSMutableParagraphStyle.alloc().init()
            title_para.setAlignment_(NSCenterTextAlignment)
            title_attrs[NSParagraphStyleAttributeName] = title_para
            title_str = NSAttributedString.alloc().initWithString_attributes_(
                self._keyboard.title, title_attrs
            )
            ts = title_str.size()
            hdr = self._header_rect
            # 角丸枠の背景（BTN_BG色）
            pad_x, pad_y = 10, 3
            box_w = ts.width + pad_x * 2
            box_h = ts.height + pad_y * 2
            box_x = hdr.origin.x + (hdr.size.width - box_w) / 2
            box_y = hdr.origin.y + (hdr.size.height - box_h) / 2
            box_rect = NSMakeRect(box_x, box_y, box_w, box_h)
            rgb(*BTN_BG).setFill()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                box_rect, 5, 5
            ).fill()
            # テキスト描画
            tx = box_x + pad_x
            ty = box_y + pad_y
            title_str.drawAtPoint_(NSMakePoint(tx, ty))

        # アクセント色（テーマのヘッダ色を暗くした色）
        hdr_r, hdr_g, hdr_b = theme[2]
        accent_bg = rgb(hdr_r * 0.4, hdr_g * 0.4, hdr_b * 0.4)
        bg_r, bg_g, bg_b = theme[1]
        accent_active = rgb(bg_r * 0.65, bg_g * 0.65, bg_b * 0.65)

        # 各ボタン
        for i, (rect, label, action, style) in enumerate(self._buttons):
            if style == 'theme':
                next_idx = (self._keyboard.theme_idx + 1) % len(THEMES)
                color = rgb(*THEMES[next_idx][1])
            elif style == 'close':
                color = rgb(*theme[2])
            elif style == 'minimize':
                opposite_idx = (self._keyboard.theme_idx + 3) % len(THEMES)
                color = rgb(*THEMES[opposite_idx][2])
            elif i == self._pressed_idx:
                color = accent_active if style == 'accent' else rgb(*BTN_ACTIVE)
            elif style == 'enter':
                color = rgb(*ENTER_BG)
            elif style == 'cmd':
                color = rgb(*CMD_BG)
            elif style == 'accent':
                color = accent_bg
            else:
                color = rgb(*BTN_BG)

            color.setFill()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                rect, 3, 3
            ).fill()

            # テキスト描画
            font_size = 12 if style in ('accent', 'enter') else 10
            if style in ('theme', 'close', 'minimize'):
                font_size = 9
            # 🎞↑ボタンは大きめフォント
            if label == '🎞↑':
                font_size = 18

            fg_color = rgb(*BTN_FG)

            attrs = {
                NSForegroundColorAttributeName: fg_color,
                NSFontAttributeName: NSFont.boldSystemFontOfSize_(font_size),
            }
            para = NSMutableParagraphStyle.alloc().init()
            para.setAlignment_(NSCenterTextAlignment)
            attrs[NSParagraphStyleAttributeName] = para

            astr = NSAttributedString.alloc().initWithString_attributes_(
                label, attrs
            )
            ts = astr.size()
            tx = rect.origin.x + (rect.size.width - ts.width) / 2
            ty = rect.origin.y + (rect.size.height - ts.height) / 2
            astr.drawAtPoint_(NSMakePoint(tx, ty))

    @objc.python_method
    def _hit_button(self, point):
        for i, (rect, _, _, _) in enumerate(self._buttons):
            if NSPointInRect(point, rect):
                return i
        return -1

    def mouseDown_(self, event):
        point = self.convertPoint_fromView_(event.locationInWindow(), None)
        idx = self._hit_button(point)

        if idx == -1 and NSPointInRect(point, self._header_rect):
            now = time.time()
            if now - self._last_click_time < 0.4:
                self._keyboard.minimize()
                self._last_click_time = 0
                return
            self._last_click_time = now
            self._dragging = True
            self._drag_start = event.locationInWindow()
            return

        self._pressed_idx = idx
        self.setNeedsDisplay_(True)

    def mouseDragged_(self, event):
        if not self._dragging or self._drag_start is None:
            return
        screen_point = NSEvent.mouseLocation()
        new_x = screen_point.x - self._drag_start.x
        new_y = screen_point.y - self._drag_start.y
        self.window().setFrameOrigin_(NSMakePoint(new_x, new_y))

    def mouseUp_(self, event):
        if self._dragging:
            self._dragging = False
            self._drag_start = None
            # ドラッグ終了時に位置を更新
            if hasattr(self._keyboard, '_write_bounds'):
                self._keyboard._write_bounds()
            return

        point = self.convertPoint_fromView_(event.locationInWindow(), None)
        idx = self._hit_button(point)

        if idx >= 0 and idx == self._pressed_idx:
            _, _, action, _ = self._buttons[idx]
            if action:
                action()

        self._pressed_idx = -1
        self.setNeedsDisplay_(True)


# =============================================
# メインクラス
# =============================================
class TransparentKeyboardMac:
    DEFAULT_WIDTH = 312
    DEFAULT_HEIGHT = 160
    # スロットごとの初期テーマ（pink, green, yellow, blue）
    SLOT_THEMES = [0, 2, 5, 1]

    def __init__(self, init_x=None, init_y=None, width=None, height=None, slot=0, title=''):
        self.width = width or self.DEFAULT_WIDTH
        self.height = height or self.DEFAULT_HEIGHT
        self.title = title  # ヘッダに表示するフォルダ名
        self.slot = slot
        self.theme_idx = self.SLOT_THEMES[slot] if slot < len(self.SLOT_THEMES) else 0
        self.app = NSApplication.sharedApplication()
        # Dockに表示しない
        self.app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

        # 位置決定: 引数指定があればそこ、なければ画面下部中央
        screen = NSScreen.mainScreen()
        sf = screen.visibleFrame()
        if init_x is not None and init_y is not None:
            x = init_x
            y = init_y - self.height
        else:
            x = sf.origin.x + (sf.size.width - self.width) / 2
            y = sf.origin.y + 30

        rect = NSMakeRect(x, y, self.width, self.height)

        style = (
            NSWindowStyleMaskBorderless
            | NSWindowStyleMaskNonactivatingPanel
            | NSWindowStyleMaskUtilityWindow
        )
        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, NSBackingStoreBuffered, False
        )
        self.panel.setFloatingPanel_(True)
        self.panel.setHidesOnDeactivate_(False)
        self.panel.setLevel_(NSFloatingWindowLevel)
        self.panel.setAlphaValue_(0.8)
        self.panel.setHasShadow_(True)
        self.panel.setIgnoresMouseEvents_(False)
        self.panel.setAcceptsMouseMovedEvents_(True)

        # キーボードビュー
        content_rect = NSMakeRect(0, 0, self.width, self.height)
        self.view = KeyboardView.alloc().initWithFrame_(content_rect)
        self.view.setup(self)
        self.panel.setContentView_(self.view)

        self.panel.orderFront_(None)

        # 位置を書き出す（Hammerspoon/即ランチャーが除外判定に使う）
        self._write_bounds()

        # 2秒後にフローティングレベルを解除（最前面は起動時だけ）
        self._level_invoker = _Invoker.alloc().initWithBlock_(
            lambda: self.panel.setLevel_(0)  # NSNormalWindowLevel
        )
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            2.0, self._level_invoker, 'invoke:', None, False
        )

    def cycle_theme(self):
        self.theme_idx = (self.theme_idx + 1) % len(THEMES)
        self.view.setNeedsDisplay_(True)

    def minimize(self):
        """パネルを隠す"""
        self.panel.orderOut_(None)

    def _write_bounds(self):
        """パネルのAppKit座標をCG座標（左上原点）に変換して書き出す"""
        frame = self.panel.frame()
        screen_h = NSScreen.mainScreen().frame().size.height
        # AppKitのyは左下原点、CGは左上原点
        cg_y = screen_h - frame.origin.y - frame.size.height
        _update_bounds_file(self.slot,
                            int(frame.origin.x), int(cg_y),
                            int(frame.size.width), int(frame.size.height))

    def close(self):
        _update_bounds_file(self.slot, 0, 0, 0, 0, remove=True)
        NSApplication.sharedApplication().terminate_(None)

    def run(self):
        self.app.run()


MAX_INSTANCES = 4  # 即ランチャーMac版のMAX_TERMINALSと同じ
BOUNDS_FILE = '/tmp/transparent_keyboard_bounds.json'


def _update_bounds_file(slot, x, y, w, h, remove=False):
    """透明キーボードの位置をファイルに書き出す（即ランチャーが参照して除外判定する）"""
    lock_path = BOUNDS_FILE + '.lock'
    try:
        with open(lock_path, 'w') as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            data = {}
            if os.path.exists(BOUNDS_FILE):
                with open(BOUNDS_FILE, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        data = {}
            if remove:
                data.pop(str(slot), None)
            else:
                data[str(slot)] = {'x': x, 'y': y, 'w': w, 'h': h}
            with open(BOUNDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            fcntl.flock(lf, fcntl.LOCK_UN)
    except Exception:
        pass

if __name__ == '__main__':
    # 起動上限制御（ロックファイルを3つ用意、空きスロットがあれば起動）
    _lock_file = None
    for i in range(MAX_INSTANCES):
        path = os.path.join(tempfile.gettempdir(), f'transparent_keyboard_mac_{i}.lock')
        f = open(path, 'w')
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _lock_file = f  # ロック取得成功 → このスロットを使う
            break
        except IOError:
            f.close()  # このスロットは使用中
    if _lock_file is None:
        sys.exit(0)  # 全スロット使用中 → 起動しない

    # コマンドライン引数
    _init_x = None
    _init_y = None
    _width = None
    _height = None
    _slot = 0
    _title = ''
    args = sys.argv[1:]
    for j in range(len(args) - 1):
        if args[j] == '--x':
            _init_x = float(args[j + 1])
        elif args[j] == '--y':
            _init_y = float(args[j + 1])
        elif args[j] == '--width':
            _width = int(float(args[j + 1]))
        elif args[j] == '--height':
            _height = int(float(args[j + 1]))
        elif args[j] == '--slot':
            _slot = int(args[j + 1])
        elif args[j] == '--title':
            _title = args[j + 1]
    TransparentKeyboardMac(
        init_x=_init_x, init_y=_init_y,
        width=_width, height=_height, slot=_slot, title=_title
    ).run()
