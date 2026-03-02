"""
透明キーボード - デスクトップオーバーレイ
クリックでキーボード入力を代替する。フォーカスを奪わずにキー送信。
"""

import tkinter as tk
import ctypes
from ctypes import wintypes
import time
import sys
import os
import subprocess
import tempfile

# AppUserModelIDを設定（タスクバーでアプリを正しく識別し、ピン留めを可能にする）
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TransparentKeyboard.App.1")

# 重複起動防止（Windows Mutex）
_mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "TransparentKeyboard_SingleInstance")
if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
    sys.exit(0)

# Windows API
user32 = ctypes.windll.user32

# 定数
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000

# ウィンドウスタイル（フレーム除去用）
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000

# SetWindowPos フラグ
SWP_FRAMECHANGED = 0x0020
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

# 仮想キーコード
VK_RETURN = 0x0D
VK_BACK = 0x08
VK_DELETE = 0x2E
VK_CONTROL = 0x11
VK_C = 0x43
VK_V = 0x56
VK_U = 0x55
VK_L = 0x4C
VK_SNAPSHOT = 0x2C
VK_SHIFT = 0x10
VK_INSERT = 0x2D
VK_HOME = 0x24
VK_F13 = 0x7C
VK_END = 0x23
VK_KANJI = 0x19
VK_ESCAPE = 0x1B
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28


# --- SendInput 構造体 ---
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


def _send_input(*inputs):
    arr = (INPUT * len(inputs))(*inputs)
    user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))


def _key_down(vk, flags=0):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.dwFlags = flags
    return inp


def _key_up(vk, flags=0):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.dwFlags = KEYEVENTF_KEYUP | flags
    return inp


# 拡張キー（フラグなしだとテンキー側と解釈される）
EXTENDED_KEYS = {VK_DELETE, VK_INSERT, VK_HOME, VK_END}


def send_key(vk):
    """キーを押して離す"""
    flags = KEYEVENTF_EXTENDEDKEY if vk in EXTENDED_KEYS else 0
    _send_input(_key_down(vk, flags), _key_up(vk, flags))


def send_combo(mod_vk, key_vk):
    """修飾キー + キーのコンボ"""
    flags = KEYEVENTF_EXTENDEDKEY if key_vk in EXTENDED_KEYS else 0
    _send_input(
        _key_down(mod_vk),
        _key_down(key_vk, flags),
        _key_up(key_vk, flags),
        _key_up(mod_vk),
    )


def send_triple_combo(mod1_vk, mod2_vk, key_vk):
    """修飾キー2つ + キーのコンボ（Ctrl+Shift+C等）"""
    _send_input(
        _key_down(mod1_vk),
        _key_down(mod2_vk),
        _key_down(key_vk),
        _key_up(key_vk),
        _key_up(mod2_vk),
        _key_up(mod1_vk),
    )


def type_text(text):
    """テキストをUnicode入力として1文字ずつ送信"""
    for ch in text:
        down = INPUT()
        down.type = INPUT_KEYBOARD
        down.union.ki.wScan = ord(ch)
        down.union.ki.dwFlags = KEYEVENTF_UNICODE

        up = INPUT()
        up.type = INPUT_KEYBOARD
        up.union.ki.wScan = ord(ch)
        up.union.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP

        _send_input(down, up)
        time.sleep(0.005)


def paste_latest_screenshot():
    """クリップボードの画像をファイルに保存してパスを入力欄に貼り付け"""
    # PowerShellでクリップボードの画像を一時ファイルに保存
    ss_dir = os.path.join(tempfile.gettempdir(), 'claude_screenshots')
    os.makedirs(ss_dir, exist_ok=True)
    # タイムスタンプ付きファイル名
    import datetime
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(ss_dir, f'ss_{ts}.png')
    # PowerShellでクリップボード画像を保存
    ps_cmd = f'''
$img = Get-Clipboard -Format Image
if ($img) {{
    $img.Save('{path}')
    Write-Host 'OK'
}} else {{
    Write-Host 'NO_IMAGE'
}}
'''
    result = subprocess.run(
        ['powershell', '-Command', ps_cmd],
        capture_output=True, text=True, timeout=5
    )
    if 'OK' in result.stdout:
        type_text(path)


def open_screenshot_folder():
    """スクショ保存フォルダをエクスプローラーで開く"""
    ss_dir = os.path.join(tempfile.gettempdir(), 'claude_screenshots')
    os.makedirs(ss_dir, exist_ok=True)
    os.startfile(ss_dir)


def open_apps_folder():
    """自作アプリフォルダをエクスプローラーで開く"""
    apps_dir = r'D:\Dropbox\.★自作アプリ2026-★'
    if os.path.exists(apps_dir):
        os.startfile(apps_dir)


class TransparentKeyboard:
    # 背景色プリセット（名前, 背景色, ヘッダ色）
    THEMES = [
        ('pink',   '#e88aa0', '#cc7090'),
        ('blue',   '#5fb8d9', '#4a9fbf'),
        ('green',  '#6bc98a', '#55b070'),
        ('purple', '#a88ad9', '#9070cc'),
        ('orange', '#e8a855', '#cc9040'),
        ('dark',   '#3a3a5e', '#2a2a44'),
    ]

    BTN_BG = '#1e2d3d'
    BTN_FG = '#f0f0f0'
    BTN_ACTIVE = '#2a5070'
    CMD_BG = '#1a3a5c'

    def __init__(self):
        self.root = tk.Tk()
        self.root.title('透明キーボード')
        # 起動時のゴーストウィンドウ防止: 非表示状態でUI構築→スタイル変更→表示
        self.root.withdraw()
        # アイコン設定（タスクバー表示用）
        self._set_icon()
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.4)

        self.theme_idx = 0  # ピンクから開始
        self.bg_widgets = []  # 背景色を変えるウィジェット一覧

        self.last_target = None
        self.my_hwnd = None
        self.drag_x = 0
        self.drag_y = 0

        self._build_ui()
        self._apply_theme()
        self._position()
        self._setup_frameless()
        # フレームレス化完了後に表示
        self.root.deiconify()
        # 復元時にtopmostを再適用
        self.root.bind('<Map>', self._on_restore)
        # タスクバークリック最小化: マウス位置で判定（起動直後は無効）
        self._taskbar_guard_ready = False
        self._taskbar_bound = False
        self.root.after(500, self._enable_taskbar_guard)
        self._poll()

    def _apply_theme(self):
        """現在のテーマを全ウィジェットに適用"""
        _, bg, hdr_bg = self.THEMES[self.theme_idx]
        self.root.configure(bg=bg)
        for w, kind in self.bg_widgets:
            try:
                w.configure(bg=hdr_bg if kind == 'header' else bg)
            except tk.TclError:
                pass
        # テーマボタンの色を次のテーマに更新
        if hasattr(self, 'theme_btn'):
            next_idx = (self.theme_idx + 1) % len(self.THEMES)
            self.theme_btn.configure(bg=self.THEMES[next_idx][1])
        # 最小化ボタンの背景を反対色に（6色の対角 = +3）
        if hasattr(self, 'min_btn'):
            opposite_idx = (self.theme_idx + 3) % len(self.THEMES)
            self.min_btn.configure(bg=self.THEMES[opposite_idx][2])

    def _cycle_theme(self, event=None):
        """次の背景色に切り替え"""
        self.theme_idx = (self.theme_idx + 1) % len(self.THEMES)
        self._apply_theme()

    def _set_icon(self):
        """ウィンドウアイコンを設定（タスクバー表示用）"""
        # .icoファイルのパスを探す
        candidates = []
        if getattr(sys, 'frozen', False):
            candidates.append(os.path.join(os.path.dirname(sys.executable), 'transparent_keyboard.ico'))
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'transparent_keyboard.ico'))
        for icon_path in candidates:
            if os.path.exists(icon_path):
                self._icon_path = icon_path
                try:
                    self.root.iconbitmap(icon_path)
                except tk.TclError:
                    pass
                break

    def _setup_frameless(self):
        """フレームレス化 + フォーカス非奪取 + タスクバー表示"""
        self.root.update_idletasks()
        # wm_frame() で正しいトップレベルHWNDを取得
        self.my_hwnd = int(self.root.wm_frame(), 16)
        # ウィンドウスタイルからフレーム（タイトルバー・枠）を除去
        style = user32.GetWindowLongW(self.my_hwnd, GWL_STYLE) & 0xFFFFFFFF
        # WS_MINIMIZEBOX は残す（タスクバークリックでの最小化/復元に必要）
        style = style & ~(WS_CAPTION | WS_THICKFRAME | WS_MAXIMIZEBOX | WS_SYSMENU)
        user32.SetWindowLongW(self.my_hwnd, GWL_STYLE, style)
        # 拡張スタイル: タスクバー表示（WS_EX_NOACTIVATEは使わない＝タスクバー操作と互換性がないため）
        ex = user32.GetWindowLongW(self.my_hwnd, GWL_EXSTYLE) & 0xFFFFFFFF
        ex = (ex | WS_EX_APPWINDOW) & ~(WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
        user32.SetWindowLongW(self.my_hwnd, GWL_EXSTYLE, ex)
        # スタイル変更をシステムに反映し、コンテンツサイズにフィットさせる
        self.root.update_idletasks()
        cw = self.root.winfo_reqwidth()
        ch = self.root.winfo_reqheight()
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        user32.SetWindowPos(
            self.my_hwnd, 0, x, y, cw, ch,
            SWP_FRAMECHANGED | SWP_NOZORDER | SWP_NOACTIVATE
        )
        # Win32 APIで直接アイコンを設定（tkinterのiconbitmapはHWNDに反映されないため）
        self._set_hwnd_icon()

    def _set_hwnd_icon(self):
        """Win32 APIでHWNDに直接アイコンを設定"""
        icon_path = getattr(self, '_icon_path', None)
        if not icon_path or not os.path.exists(icon_path):
            return
        # LoadImageW でアイコンを読み込み
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010
        LR_DEFAULTSIZE = 0x0040
        LoadImageW = ctypes.windll.user32.LoadImageW
        LoadImageW.restype = ctypes.c_void_p
        # 大アイコン (32x32) と小アイコン (16x16)
        icon_big = LoadImageW(None, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        icon_small = LoadImageW(None, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
        # WM_SETICON でウィンドウに設定
        WM_SETICON = 0x0080
        ICON_BIG = 1
        ICON_SMALL = 0
        if icon_big:
            user32.SendMessageW(self.my_hwnd, WM_SETICON, ICON_BIG, icon_big)
        if icon_small:
            user32.SendMessageW(self.my_hwnd, WM_SETICON, ICON_SMALL, icon_small)

    def _on_restore(self, event=None):
        """最小化から復元されたときにtopmostを再適用"""
        # 復元直後のFocusInで再最小化されないようガードを一時無効化
        self._taskbar_guard_ready = False
        self.root.attributes('-topmost', True)
        # 復元後、フォーカスを元のウィンドウに返す
        if self.last_target:
            self.root.after(50, lambda: user32.SetForegroundWindow(self.last_target))
        # 500ms後にガードを再有効化
        self.root.after(500, self._enable_taskbar_guard)

    def _enable_taskbar_guard(self):
        """タスクバークリック検知を有効化"""
        self._taskbar_guard_ready = True
        if not self._taskbar_bound:
            self.root.bind('<FocusIn>', self._on_focus_in)
            self._taskbar_bound = True

    def _on_focus_in(self, event=None):
        """フォーカス取得時: マウスがタスクバー領域にあるなら → 最小化"""
        if not self._taskbar_guard_ready:
            return
        try:
            mx = self.root.winfo_pointerx()
            my = self.root.winfo_pointery()
            wx = self.root.winfo_rootx()
            wy = self.root.winfo_rooty()
            ww = self.root.winfo_width()
            wh = self.root.winfo_height()
            if wx <= mx <= wx + ww and wy <= my <= wy + wh:
                return  # マウスがウィンドウ上 → ボタンクリック
            # タスクバー領域（画面最下部48px）にマウスがある場合のみ最小化
            sh = self.root.winfo_screenheight()
            if my < sh - 48:
                return  # タスクバー外 → 他アプリのクリック、無視
        except tk.TclError:
            return
        # マウスがタスクバー上 → タスクバークリック → 最小化
        self.root.after(10, self.root.iconify)

    def _poll(self):
        """前面ウィンドウを150msごとに記録"""
        hwnd = user32.GetForegroundWindow()
        if self.my_hwnd and hwnd != self.my_hwnd:
            self.last_target = hwnd
        self.root.after(150, self._poll)

    def _position(self):
        """画面下部中央に配置"""
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f'+{(sw - w) // 2}+{sh - h - 60}')

    def _act(self, action):
        """フォーカスを元のウィンドウに戻してからアクション実行"""
        self._clicking = True
        try:
            if self.last_target:
                user32.SetForegroundWindow(self.last_target)
                time.sleep(0.05)
            action()
        finally:
            self._clicking = False


    def _btn(self, parent, text, command, width=None, style='normal'):
        kw = {
            'font': ('Segoe UI', 11, 'bold'),
            'bg': self.CMD_BG if style == 'cmd' else self.BTN_BG,
            'fg': self.BTN_FG,
            'activebackground': self.BTN_ACTIVE,
            'activeforeground': '#fff',
            'relief': 'solid',
            'bd': 1,
            'padx': 5,
            'pady': 4,
            'cursor': 'hand2',
            'command': command,
        }
        if style == 'num':
            kw['font'] = ('Segoe UI', 12, 'bold')
            kw['padx'] = 2
            kw['pady'] = 2
        if style == 'icon':
            kw['font'] = ('Segoe UI Emoji', 13)
            kw['pady'] = 0
        b = tk.Button(parent, text=text, **kw)
        if width:
            b.configure(width=width)
        return b

    def _reg(self, widget, kind='body'):
        """ウィジェットをテーマ変更対象に登録"""
        self.bg_widgets.append((widget, kind))
        return widget

    def _build_ui(self):
        # ヘッダ（ドラッグ用）
        hdr = self._reg(tk.Frame(self.root, height=20, cursor='fleur'), 'header')
        hdr.pack(fill='x')
        hdr.pack_propagate(False)

        # 左端: テーマ切り替えボタン
        self.theme_btn = self._reg(tk.Label(hdr, text='●', font=('Segoe UI', 10),
                                  cursor='hand2', fg='#fff'), 'header')
        self.theme_btn.pack(side='left', padx=4)
        self.theme_btn.bind('<Button-1>', self._cycle_theme)

        # 右端: 閉じるボタン
        x_btn = self._reg(tk.Label(hdr, text='✕', font=('Segoe UI', 8, 'bold'),
                         fg='#ddd', cursor='hand2'), 'header')
        x_btn.pack(side='right', padx=4)
        x_btn.bind('<Button-1>', lambda e: self.root.destroy())

        # 最小化ボタン（閉じるボタンから離す、反対色で目立たせる）
        self.min_btn = tk.Label(hdr, text='━', font=('Segoe UI', 7, 'bold'),
                               fg='#fff', cursor='hand2', relief='solid', bd=1)
        self.min_btn.pack(side='right', padx=(2, 12))
        self.min_btn.bind('<Button-1>', lambda e: self.root.iconify())

        for w in (hdr,):
            w.bind('<Button-1>', self._drag_start)
            w.bind('<B1-Motion>', self._drag_move)

        # メインエリア: Enter(右) + 左キー群
        body = self._reg(tk.Frame(self.root))
        body.pack(fill='both', expand=True, padx=0, pady=0)

        # Enter: 右端に縦いっぱい
        enter_btn = tk.Button(
            body, text='Enter\n⏎',
            font=('Segoe UI', 13, 'bold'),
            bg='#2a4a6c', fg=self.BTN_FG,
            activebackground='#3a6a9c', activeforeground='#fff',
            relief='solid', bd=1,
            padx=10, cursor='hand2',
            command=lambda: self._act(lambda: send_key(VK_RETURN)),
        )
        enter_btn.pack(side='right', fill='y', padx=(0, 1), pady=1)

        left = self._reg(tk.Frame(body))
        left.pack(side='left', fill='both', expand=True)

        NUM_W = 3    # 数字キー幅(小)
        FUNC_W = 5   # 機能キー幅(大): 📷↑, 半/全, 📁, PrtSc 共通

        # Row 0: ESC ← ↓ ↑ → | ★Apps
        r_nav = self._reg(tk.Frame(left))
        r_nav.pack(fill='x', pady=1)
        self._btn(r_nav, 'ESC', lambda: self._act(lambda: send_key(VK_ESCAPE)),
                  style='num').pack(side='left', padx=1, fill='both', expand=True)
        for arrow, vk in [('←', VK_LEFT), ('↓', VK_DOWN), ('↑', VK_UP), ('→', VK_RIGHT)]:
            b = self._btn(r_nav, arrow, lambda v=vk: self._act(lambda: send_key(v)), style='num')
            b.pack(side='left', padx=1, fill='both', expand=True)
        self._btn(r_nav, '★Apps', lambda: open_apps_folder(),
                  style='num').pack(side='left', padx=1, fill='both', expand=True)

        # Row 1: 1 2 3 4 5 | 📷↑ 半/全
        r0 = self._reg(tk.Frame(left))
        r0.pack(fill='x', pady=1)
        for n in '12345':
            b = self._btn(r0, n, lambda c=n: self._act(lambda: type_text(c)), style='num')
            b.configure(width=NUM_W)
            b.pack(side='left', padx=1, fill='both', expand=False)
        b = self._btn(r0, '📷↑', lambda: self._act(paste_latest_screenshot), style='num')
        b.configure(width=FUNC_W)
        b.pack(side='left', padx=1, fill='both', expand=False)
        hz_btn = self._btn(r0, '半/全', lambda: self._act(lambda: send_key(VK_KANJI)),
                           style='num')
        hz_btn.configure(font=('Meiryo UI', 12, 'bold'), width=FUNC_W)
        hz_btn.pack(side='left', padx=1, fill='both', expand=True)

        # Row 1: 6 7 8 9 0 | 📁 PrtSc
        r1 = self._reg(tk.Frame(left))
        r1.pack(fill='x', pady=1)
        for n in '67890':
            b = self._btn(r1, n, lambda c=n: self._act(lambda: type_text(c)), style='num')
            b.configure(width=NUM_W)
            b.pack(side='left', padx=1, fill='both', expand=False)
        b = self._btn(r1, '📁', lambda: open_screenshot_folder(), style='num')
        b.configure(width=FUNC_W)
        b.pack(side='left', padx=1, fill='both', expand=False)
        b = self._btn(r1, 'PrtSc', lambda: self._act(lambda: send_key(VK_SNAPSHOT)), style='num')
        b.configure(width=FUNC_W)
        b.pack(side='left', padx=1, fill='both', expand=True)

        # Row 2: Copy Paste |←←Del | Home End BS（右3つで残りを三等分）
        r2 = self._reg(tk.Frame(left))
        r2.pack(fill='x', pady=1)
        big_keys = [
            ('Copy', lambda: self._act(lambda: send_combo(VK_CONTROL, VK_INSERT))),
            ('Paste', lambda: self._act(lambda: send_combo(VK_SHIFT, VK_INSERT))),
            ('|←←Del', lambda: self._act(lambda: send_combo(VK_CONTROL, VK_U))),
        ]
        small_keys = [
            ('Home', lambda: self._act(lambda: send_key(VK_HOME))),
            ('End',  lambda: self._act(lambda: send_key(VK_END))),
            ('BS',   lambda: self._act(lambda: send_key(VK_BACK))),
        ]
        for label, cmd in big_keys:
            b = self._btn(r2, label, cmd)
            b.configure(width=FUNC_W)
            b.pack(side='left', padx=1, fill='both', expand=False)
        for label, cmd in small_keys:
            b = self._btn(r2, label, cmd)
            b.pack(side='left', padx=1, fill='both', expand=True)

        # Row 3: F13 /remote-control /resume
        r3 = self._reg(tk.Frame(left))
        r3.pack(fill='x', pady=(1, 0))

        def type_cmd(text):
            """テキストを入力してEnter"""
            def action():
                type_text(text)
                time.sleep(0.02)
                send_key(VK_RETURN)
            self._act(action)

        self._btn(r3, 'F13', lambda: self._act(lambda: send_key(VK_F13)),
                  style='normal').pack(side='left', padx=1, fill='x')
        self._btn(r3, '/remote-control', lambda: type_cmd('/remote-control'),
                  style='normal').pack(side='left', padx=1, fill='x', expand=True)
        self._btn(r3, '/resume', lambda: type_cmd('/resume'),
                  style='normal').pack(side='left', padx=1, fill='x', expand=True)

    def _drag_start(self, e):
        self.drag_x = e.x_root - self.root.winfo_x()
        self.drag_y = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        x = e.x_root - self.drag_x
        y = e.y_root - self.drag_y
        # Win32 APIで直接移動（tkinterのgeometryより高速、描画遅延を防止）
        user32.SetWindowPos(
            self.my_hwnd, 0, x, y, 0, 0,
            SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE
        )

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    TransparentKeyboard().run()
