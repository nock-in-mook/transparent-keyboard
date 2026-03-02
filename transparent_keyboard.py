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

# 重複起動防止（Windows Mutex）
_mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "TransparentKeyboard_SingleInstance")
if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
    sys.exit(0)

# Windows API
user32 = ctypes.windll.user32

# 定数
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

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
VK_END = 0x23
VK_KANJI = 0x19


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
        self.root.overrideredirect(True)
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
        self._setup_noactivate()
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

    def _cycle_theme(self, event=None):
        """次の背景色に切り替え"""
        self.theme_idx = (self.theme_idx + 1) % len(self.THEMES)
        self._apply_theme()

    def _setup_noactivate(self):
        """ウィンドウがフォーカスを奪わないように設定"""
        self.root.update_idletasks()
        self.my_hwnd = user32.GetParent(self.root.winfo_id())
        ex = user32.GetWindowLongW(self.my_hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(
            self.my_hwnd, GWL_EXSTYLE,
            ex | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        )

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
        if self.last_target:
            user32.SetForegroundWindow(self.last_target)
            time.sleep(0.05)
        action()

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
            kw['font'] = ('Segoe UI', 14, 'bold')
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

        lbl = self._reg(tk.Label(hdr, text='⌨', font=('Segoe UI', 8), fg='#555'), 'header')
        lbl.pack(side='left', padx=4)

        x_btn = self._reg(tk.Label(hdr, text='✕', font=('Segoe UI', 8, 'bold'),
                         fg='#ddd', cursor='hand2'), 'header')
        x_btn.pack(side='right', padx=4)
        x_btn.bind('<Button-1>', lambda e: self.root.destroy())

        # テーマ切り替えボタン（次の色を表示）
        self.theme_btn = tk.Label(hdr, text='●', font=('Segoe UI', 10),
                                  cursor='hand2', fg='#fff')
        self.theme_btn.pack(side='right', padx=2)
        self.theme_btn.bind('<Button-1>', self._cycle_theme)

        for w in (hdr, lbl):
            w.bind('<Button-1>', self._drag_start)
            w.bind('<B1-Motion>', self._drag_move)

        # メインエリア: 左ボタン群 + PrtSc + Enter
        body = self._reg(tk.Frame(self.root, padx=3, pady=3))
        body.pack(fill='both')

        # 右端: Enter（縦に大きく、先にpackして右端に固定）
        enter_btn = tk.Button(
            body, text='Enter\n⏎',
            font=('Segoe UI', 13, 'bold'),
            bg='#2a4a6c', fg=self.BTN_FG,
            activebackground='#3a6a9c', activeforeground='#fff',
            relief='solid', bd=1,
            padx=12, cursor='hand2',
            command=lambda: self._act(lambda: send_key(VK_RETURN)),
        )
        enter_btn.pack(side='right', fill='y', padx=(2, 0), pady=0)

        left = self._reg(tk.Frame(body))
        left.pack(side='left', fill='both')

        # 上段1行目: 1 2 3 4 5 📷↑ 半/全（同じフレームで揃える）
        r1a = self._reg(tk.Frame(left))
        r1a.pack(fill='x', pady=1)
        for n in '12345':
            self._btn(r1a, n, lambda c=n: self._act(lambda: type_text(c)),
                      style='num').pack(side='left', padx=1, fill='y')
        self._btn(r1a, '📷↑', lambda: self._act(paste_latest_screenshot),
                  style='icon').pack(side='left', padx=1, fill='both', expand=True)
        hz_btn = self._btn(r1a, '半/全', lambda: self._act(lambda: send_key(VK_KANJI)))
        hz_btn.configure(font=('Meiryo UI', 11, 'bold'))
        hz_btn.pack(side='left', padx=1, fill='both', expand=True)

        # 上段2行目: 6 7 8 9 0 📁 PrtSc
        r1b = self._reg(tk.Frame(left))
        r1b.pack(fill='x', pady=1)
        for n in '67890':
            self._btn(r1b, n, lambda c=n: self._act(lambda: type_text(c)),
                      style='num').pack(side='left', padx=1, fill='y')
        self._btn(r1b, '📁', lambda: open_screenshot_folder(),
                  style='icon').pack(side='left', padx=1, fill='both', expand=True)
        self._btn(r1b, 'PrtSc', lambda: self._act(lambda: send_key(VK_SNAPSHOT)),
                  style='normal').pack(side='left', padx=1, fill='both', expand=True)

        # Row 2: コピペ + 特殊キー（5キーで横幅いっぱいに）
        r2 = self._reg(tk.Frame(left))
        r2.pack(fill='x', pady=1)
        keys = [
            ('Copy', lambda: self._act(lambda: send_combo(VK_CONTROL, VK_INSERT))),
            ('Paste', lambda: self._act(lambda: send_combo(VK_SHIFT, VK_INSERT))),
            ('|←←Del', lambda: self._act(lambda: send_combo(VK_CONTROL, VK_U))),
            ('Home',  lambda: self._act(lambda: send_key(VK_HOME))),
            ('End',   lambda: self._act(lambda: send_key(VK_END))),
            ('BS',    lambda: self._act(lambda: send_key(VK_BACK))),
        ]
        for label, cmd in keys:
            self._btn(r2, label, cmd).pack(side='left', padx=1, fill='x', expand=True)

        # Row 3: テキスト入力コマンド
        r3 = self._reg(tk.Frame(left))
        r3.pack(fill='x', pady=1)

        def type_cmd(text):
            """テキストを入力してEnter"""
            def action():
                type_text(text)
                time.sleep(0.02)
                send_key(VK_RETURN)
            self._act(action)

        self._btn(r3, '/remote-control', lambda: type_cmd('/remote-control'),
                  style='normal').pack(side='left', padx=1, fill='x', expand=True)
        self._btn(r3, '/resume', lambda: type_cmd('/resume'),
                  style='normal').pack(side='left', padx=1, fill='x', expand=True)

    def _drag_start(self, e):
        self.drag_x = e.x_root - self.root.winfo_x()
        self.drag_y = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        self.root.geometry(f'+{e.x_root - self.drag_x}+{e.y_root - self.drag_y}')

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    TransparentKeyboard().run()
