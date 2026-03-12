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
    NSApplicationActivationPolicyRegular,
    NSApplicationActivationPolicyAccessory,
    NSAttributedString,
    NSForegroundColorAttributeName,
    NSFontAttributeName,
    NSMutableParagraphStyle,
    NSParagraphStyleAttributeName,
    NSCenterTextAlignment,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSSquareStatusItemLength,
    NSMenu, NSMenuItem,
    NSEvent,
    NSPasteboard,
    NSImage,
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

def send_key(keycode, flags=0):
    """キーを押して離す"""
    down = CGEventCreateKeyboardEvent(None, keycode, True)
    up = CGEventCreateKeyboardEvent(None, keycode, False)
    if flags:
        CGEventSetFlags(down, flags)
        CGEventSetFlags(up, flags)
    CGEventPost(kCGHIDEventTap, down)
    CGEventPost(kCGHIDEventTap, up)


def type_text(text):
    """テキストをUnicode入力として1文字ずつ送信"""
    for ch in text:
        down = CGEventCreateKeyboardEvent(None, 0, True)
        up = CGEventCreateKeyboardEvent(None, 0, False)
        CGEventKeyboardSetUnicodeString(down, 1, ch)
        CGEventKeyboardSetUnicodeString(up, 1, ch)
        CGEventPost(kCGHIDEventTap, down)
        CGEventPost(kCGHIDEventTap, up)
        time.sleep(0.005)


def type_text_enter(text):
    """テキスト入力してEnter"""
    type_text(text)
    time.sleep(0.02)
    send_key(KC['return'])


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
        """ボタン配置（コンパクト版）"""
        W = self.frame().size.width
        HDR_H = 18
        BTN_H = 28
        PAD = 1
        ENTER_W = 36
        body_w = W - ENTER_W - PAD

        self._buttons = []

        # --- ヘッダ ---
        self._header_rect = NSMakeRect(0, 0, W, HDR_H)
        self._buttons.append((
            NSMakeRect(PAD, 1, 16, HDR_H - 2),
            '●', lambda: self._keyboard.cycle_theme(), 'theme'
        ))
        self._buttons.append((
            NSMakeRect(W - 38, 1, 16, HDR_H - 2),
            '━', lambda: self._keyboard.minimize(), 'minimize'
        ))
        self._buttons.append((
            NSMakeRect(W - 18, 1, 16, HDR_H - 2),
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
            ('Apps',  lambda: open_apps_folder()),
        ]
        bw = body_w / len(row0)
        for i, (label, action) in enumerate(row0):
            self._buttons.append((
                NSMakeRect(i * bw + PAD, y + PAD, bw - PAD * 2, BTN_H - PAD),
                label, action, 'key'
            ))
        y += BTN_H

        # --- Row 1: 1 2 3 4 5 | 📷↑ 英/日 ---
        num_w = body_w * 0.6 / 5
        func_w = body_w * 0.4 / 2
        x = PAD
        for n in '12345':
            self._buttons.append((
                NSMakeRect(x, y + PAD, num_w - PAD, BTN_H - PAD),
                n, lambda c=n: type_text(c), 'num'
            ))
            x += num_w
        self._buttons.append((
            NSMakeRect(x, y + PAD, func_w - PAD, BTN_H - PAD),
            '📷↑', lambda: paste_latest_screenshot(), 'key'
        ))
        x += func_w
        self._buttons.append((
            NSMakeRect(x, y + PAD, func_w - PAD, BTN_H - PAD),
            '英/日', lambda: send_key(KC['space'], MOD_CTRL), 'key'
        ))
        y += BTN_H

        # --- Row 2: 6 7 8 9 0 | 📁 PrScr ---
        x = PAD
        for n in '67890':
            self._buttons.append((
                NSMakeRect(x, y + PAD, num_w - PAD, BTN_H - PAD),
                n, lambda c=n: type_text(c), 'num'
            ))
            x += num_w
        self._buttons.append((
            NSMakeRect(x, y + PAD, func_w - PAD, BTN_H - PAD),
            '📁', lambda: open_screenshot_folder(), 'key'
        ))
        x += func_w
        self._buttons.append((
            NSMakeRect(x, y + PAD, func_w - PAD, BTN_H - PAD),
            'PrScr', lambda: take_screenshot(), 'key'
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

        # --- Row 4: Term ⌘A /remote /resume ---
        cmd_keys = [
            ('Term',     lambda: bring_terminals_to_front(),           0.14),
            ('⌘A',       lambda: send_key(KC['a'], MOD_CMD),          0.14),
            ('/remote',  lambda: type_text_enter('/remote-control'),   0.38),
            ('/resume',  lambda: type_text_enter('/resume'),           0.34),
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
                color = rgb(*BTN_ACTIVE)
            elif style == 'enter':
                color = rgb(*ENTER_BG)
            elif style == 'cmd':
                color = rgb(*CMD_BG)
            else:
                color = rgb(*BTN_BG)

            color.setFill()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                rect, 3, 3
            ).fill()

            # テキスト描画
            font_size = 12 if style in ('num', 'enter') else 10
            if style in ('theme', 'close', 'minimize'):
                font_size = 9

            # Termボタンは白文字で目立たせる
            fg_color = rgb(1.0, 1.0, 1.0) if label == 'Term' else rgb(*BTN_FG)

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
# メニューバー用デリゲート（ObjCランタイムに認識される）
# =============================================
class MenuDelegate(NSObject):
    def init(self):
        self = objc.super(MenuDelegate, self).init()
        self._keyboard = None
        return self

    @objc.IBAction
    def toggleKeyboard_(self, sender):
        if self._keyboard:
            self._keyboard.toggle()

    @objc.IBAction
    def quitApp_(self, sender):
        NSApplication.sharedApplication().terminate_(None)


# =============================================
# メインクラス
# =============================================
class TransparentKeyboardMac:
    WIDTH = 312
    HEIGHT = 160   # header(18) + 5 rows(28*5) + padding

    def __init__(self, init_x=None, init_y=None, hidden=False):
        self.theme_idx = 0
        self._visible = False
        self.app = NSApplication.sharedApplication()
        # Dockに表示しない（メニューバー常駐のみ）
        self.app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

        # 位置決定: 引数指定があればそこ、なければ画面下部中央
        screen = NSScreen.mainScreen()
        sf = screen.visibleFrame()
        if init_x is not None and init_y is not None:
            x = init_x
            y = init_y - self.HEIGHT
        else:
            x = sf.origin.x + (sf.size.width - self.WIDTH) / 2
            y = sf.origin.y + 30

        rect = NSMakeRect(x, y, self.WIDTH, self.HEIGHT)

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
        self.panel.setAlphaValue_(0.4)
        self.panel.setHasShadow_(True)

        # キーボードビュー
        content_rect = NSMakeRect(0, 0, self.WIDTH, self.HEIGHT)
        self.view = KeyboardView.alloc().initWithFrame_(content_rect)
        self.view.setup(self)
        self.panel.setContentView_(self.view)

        # メニューバーアイコン
        self._setup_menu_bar()

        # 初期表示（--hidden でなければ表示）
        if not hidden:
            self.panel.orderFront_(None)
            self._visible = True

    def _setup_menu_bar(self):
        """メニューバーに常駐アイコン表示"""
        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSSquareStatusItemLength
        )
        # キーボードアイコンをNSImageで描画
        icon = NSImage.alloc().initWithSize_((22, 22))
        icon.lockFocus()
        # キーボード本体（角丸四角・枠線のみ）
        NSColor.colorWithCalibratedWhite_alpha_(0.2, 1.0).setStroke()
        body_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            NSMakeRect(1, 4, 20, 13), 2.5, 2.5
        )
        body_path.setLineWidth_(1.5)
        body_path.stroke()
        # 上段キー: 5個
        NSColor.colorWithCalibratedWhite_alpha_(0.2, 1.0).setFill()
        for col in range(5):
            NSBezierPath.fillRect_(NSMakeRect(3 + col * 3.5, 12, 2.5, 2.5))
        # 中段キー: 4個（少しずらす）
        for col in range(4):
            NSBezierPath.fillRect_(NSMakeRect(4.5 + col * 3.5, 8.5, 2.5, 2.5))
        # 下段: スペースバー
        NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            NSMakeRect(5, 5.5, 12, 2), 1, 1
        ).fill()
        icon.unlockFocus()
        icon.setTemplate_(True)
        self.status_item.button().setImage_(icon)

        menu = NSMenu.alloc().init()

        # ObjCランタイムに認識されるデリゲートを使う
        self._menu_delegate = MenuDelegate.alloc().init()
        self._menu_delegate._keyboard = self

        self._toggle_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            'Show Keyboard', 'toggleKeyboard:', ''
        )
        self._toggle_item.setTarget_(self._menu_delegate)
        menu.addItem_(self._toggle_item)
        self.status_item.setMenu_(menu)

    def cycle_theme(self):
        self.theme_idx = (self.theme_idx + 1) % len(THEMES)
        self.view.setNeedsDisplay_(True)

    def toggle(self):
        """キーボードの表示/非表示を切り替え"""
        if self._visible:
            self.panel.orderOut_(None)
            self._visible = False
            self._toggle_item.setTitle_('Show Keyboard')
        else:
            self.panel.orderFront_(None)
            self._visible = True
            self._toggle_item.setTitle_('Hide Keyboard')

    def minimize(self):
        """パネルを隠す（メニューバーから復帰）"""
        self.panel.orderOut_(None)
        self._visible = False
        self._toggle_item.setTitle_('Show Keyboard')

    def close(self):
        NSApplication.sharedApplication().terminate_(None)

    def run(self):
        self.app.run()


MAX_INSTANCES = 3

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
    _hidden = '--hidden' in sys.argv
    args = sys.argv[1:]
    for j in range(len(args) - 1):
        if args[j] == '--x':
            _init_x = float(args[j + 1])
        elif args[j] == '--y':
            _init_y = float(args[j + 1])
    TransparentKeyboardMac(init_x=_init_x, init_y=_init_y, hidden=_hidden).run()
