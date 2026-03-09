"""
透明キーボード - デスクトップオーバーレイ
クリックでキーボード入力を代替する。フォーカスを奪わずにキー送信。
最大3つまで同時起動可能。
"""

import tkinter as tk
import ctypes
from ctypes import wintypes
import time
import sys
import os
import subprocess
import tempfile
import threading

# AppUserModelIDを設定（タスクバーでアプリを正しく識別し、ピン留めを可能にする）
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TransparentKeyboard.App.1")

# 最大3インスタンスまで許可（スロット制で管理）
MAX_INSTANCES = 3
_instance_slot = -1
_slot_mutex = None
for i in range(MAX_INSTANCES):
    m = ctypes.windll.kernel32.CreateMutexW(None, True, f"TransparentKeyboard_Slot_{i}")
    if ctypes.windll.kernel32.GetLastError() != 183:  # スロット確保成功
        _instance_slot = i
        _slot_mutex = m
        break
if _instance_slot == -1:
    # 3つとも埋まっている
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
    apps_dir = r'G:\マイドライブ\_Apps2026'
    if os.path.exists(apps_dir):
        os.startfile(apps_dir)


def toggle_ime():
    """半角/全角キーを送信してIMEをトグル"""
    send_key(VK_KANJI)


def bring_terminals_to_front():
    """即ランチャーのShowAll機能を呼び出す（再配置＋最前面）"""
    launcher_dir = r'G:\マイドライブ\_Apps2026\terminal_copy'
    exe = os.path.join(launcher_dir, '即ランチャー.exe')
    script = os.path.join(launcher_dir, 'folder_launcher_win.pyw')
    if os.path.exists(exe):
        subprocess.Popen([exe, script, '--show-all'], cwd=launcher_dir)
    elif os.path.exists(script):
        subprocess.Popen(['pythonw', script, '--show-all'], cwd=launcher_dir)


class TransparentKeyboard:
    # 背景色プリセット（名前, 背景色, ヘッダ色）
    THEMES = [
        ('pink',   '#e88aa0', '#cc7090'),
        ('blue',   '#5fb8d9', '#4a9fbf'),
        ('green',  '#6bc98a', '#55b070'),
        ('purple', '#a88ad9', '#9070cc'),
        ('orange', '#e8a855', '#cc9040'),
        ('yellow', '#e8d855', '#ccbc40'),
        ('dark',   '#3a3a5e', '#2a2a44'),
    ]
    # スロットごとの初期テーマ（0=ピンク, 2=グリーン, 5=イエロー）
    SLOT_THEMES = [0, 2, 5]

    BTN_BG = '#1e2d3d'
    BTN_FG = '#f0f0f0'
    BTN_ACTIVE = '#2a5070'
    CMD_BG = '#1a3a5c'

    def __init__(self, slot=0):
        self.slot = slot
        self.root = tk.Tk()
        self.root.title('透明キーボード')
        # 起動時のゴーストウィンドウ防止: 非表示状態でUI構築→スタイル変更→表示
        self.root.withdraw()
        # アイコン設定（タスクバー表示用）
        self._set_icon()
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.8)

        self.theme_idx = self.SLOT_THEMES[self.slot] if self.slot < len(self.SLOT_THEMES) else 0
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
        # 既存インスタンスも含めて全員整列
        self.root.after(200, self._realign_all)
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
        # 最小化ボタンの背景を反対色に（対角）
        if hasattr(self, 'min_btn'):
            opposite_idx = (self.theme_idx + len(self.THEMES) // 2) % len(self.THEMES)
            self.min_btn.configure(bg=self.THEMES[opposite_idx][2])
        # アクセント行のボタン色をテーマ連動の濃い色に
        if hasattr(self, '_accent_btns'):
            accent_bg = self._darken(hdr_bg)
            accent_active = self._darken(bg, 0.65)
            for b in self._accent_btns:
                try:
                    b.configure(bg=accent_bg, activebackground=accent_active)
                except tk.TclError:
                    pass

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
        # スタイル変更をシステムに反映（_positionで計算したサイズ・座標を使用）
        self.root.update_idletasks()
        x = getattr(self, '_target_x', self.root.winfo_x())
        y = getattr(self, '_target_y', self.root.winfo_y())
        cw = getattr(self, '_target_w', self.root.winfo_reqwidth())
        ch = getattr(self, '_target_h', self.root.winfo_reqheight())
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
        SendMessageW = ctypes.windll.user32.SendMessageW
        SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
        if icon_big:
            SendMessageW(self.my_hwnd, WM_SETICON, ICON_BIG, icon_big)
        if icon_small:
            SendMessageW(self.my_hwnd, WM_SETICON, ICON_SMALL, icon_small)

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

    # 即ランチャーと同じ配置定数
    SCREEN_USE_RATIO = 0.95
    MARGIN_TOP_RATIO = 0.0
    MARGIN_BOTTOM_RATIO = 0.20  # ターミナル下マージン20%（キーボード領域）
    SHADOW_OVERLAP = 14
    SHADOW_INSET = 7  # ウィンドウ影の片側幅（キーボードには影がないので補正用）
    MAX_TERMINALS = 3
    KB_HEIGHT_RATIO = 0.20  # キーボード高さ = 画面の20%

    def _calc_layout(self):
        """即ランチャーと同じ計算式でレイアウト情報を返す（タスクバー除外）"""
        # 画面全体サイズ（即ランチャーと同じ基準で幅を計算）
        sw = user32.GetSystemMetrics(0)
        sh_full = user32.GetSystemMetrics(1)
        # 作業領域（タスクバーを除いた領域）で高さ方向を計算
        work_rect = ctypes.wintypes.RECT()
        SPI_GETWORKAREA = 0x0030
        ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(work_rect), 0)
        work_top = work_rect.top
        work_h = work_rect.bottom - work_rect.top
        # 幅は画面全体ベース（即ランチャーと一致させる）
        total_w = int(sw * self.SCREEN_USE_RATIO)
        win_w = (total_w + self.SHADOW_OVERLAP * (self.MAX_TERMINALS - 1)) // self.MAX_TERMINALS
        # 高さは作業領域ベース
        margin_top = int(work_h * self.MARGIN_TOP_RATIO) + work_top
        term_h = work_h - int(work_h * self.MARGIN_TOP_RATIO) - int(work_h * self.MARGIN_BOTTOM_RATIO)
        kb_h = int(work_h * self.KB_HEIGHT_RATIO) + self.SHADOW_INSET  # 影に食い込む分を加算
        return sw, work_h, win_w, margin_top, term_h, kb_h, work_top

    @staticmethod
    def _find_wt_windows():
        """Windows Terminalのウィンドウハンドルを全て取得"""
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int))
        hwnds = []
        cls_buf = ctypes.create_unicode_buffer(256)
        def cb(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                user32.GetClassNameW(hwnd, cls_buf, 256)
                if 'CASCADIA_HOSTING_WINDOW_CLASS' in cls_buf.value:
                    hwnds.append(hwnd)
            return True
        user32.EnumWindows(WNDENUMPROC(cb), None)
        return hwnds

    @staticmethod
    def _find_kb_windows():
        """透明キーボードのウィンドウハンドルを全て取得"""
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int))
        hwnds = []
        title_buf = ctypes.create_unicode_buffer(256)
        cls_buf = ctypes.create_unicode_buffer(256)
        def cb(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                user32.GetWindowTextW(hwnd, title_buf, 256)
                user32.GetClassNameW(hwnd, cls_buf, 256)
                if title_buf.value == '透明キーボード' and cls_buf.value == 'TkTopLevel':
                    hwnds.append(hwnd)
            return True
        user32.EnumWindows(WNDENUMPROC(cb), None)
        return hwnds

    def _position(self):
        """初期配置（_realign_allで上書きされる前の仮位置）"""
        self.root.update_idletasks()
        sw, sh, win_w, _, term_h, kb_h, work_top = self._calc_layout()
        kb_w = win_w - self.SHADOW_INSET * 2
        x = sw - kb_w - (self.slot * kb_w)
        y = work_top + sh - kb_h
        self._target_x = x
        self._target_y = y
        self._target_w = kb_w
        self._target_h = kb_h
        self.root.geometry(f'{kb_w}x{kb_h}+{x}+{y}')

    def _realign_all(self):
        """ターミナル+キーボードをセットで整列"""
        sw, sh, win_w, margin_top, term_h, kb_h, work_top = self._calc_layout()

        # ターミナルを検出してx座標でソート
        wt_hwnds = self._find_wt_windows()[:self.MAX_TERMINALS]
        rect = ctypes.wintypes.RECT()
        wt_sorted = []
        for hwnd in wt_hwnds:
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            wt_sorted.append((rect.left, hwnd))
        wt_sorted.sort(key=lambda r: r[0])

        # キーボードを検出してx座標でソート
        kb_hwnds = self._find_kb_windows()
        kb_sorted = []
        for hwnd in kb_hwnds:
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            kb_sorted.append((rect.left, hwnd))
        kb_sorted.sort(key=lambda r: r[0])

        n_wt = len(wt_sorted)
        n_kb = len(kb_sorted)

        # ターミナルを右寄せで再配置（右の影を画面外に押し出す）
        x = sw + self.SHADOW_INSET
        wt_positions = []
        for i in range(n_wt - 1, -1, -1):
            x -= win_w
            if i < n_wt - 1:
                x += self.SHADOW_OVERLAP
            _, hwnd = wt_sorted[i]
            user32.MoveWindow(hwnd, x, margin_top, win_w, term_h, True)
            wt_positions.insert(0, x)

        # キーボードを配置（影の内側幅、ただし右端は影を無視して寄せる）
        kb_w = win_w - self.SHADOW_INSET * 2
        kb_y = margin_top + term_h - self.SHADOW_INSET  # ターミナルの影に食い込ませる
        for i, (_, hwnd) in enumerate(kb_sorted):
            if i < n_wt:
                # ターミナル実体の右端に合わせる
                kx = wt_positions[i] + self.SHADOW_INSET
            else:
                if n_wt > 0:
                    kx = wt_positions[0] + self.SHADOW_INSET - kb_w
                    extra = i - n_wt
                    kx -= extra * kb_w
                else:
                    kx = sw - kb_w - i * kb_w
            user32.MoveWindow(hwnd, kx, kb_y, kb_w, kb_h, True)

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
            'font': ('Segoe UI', 10, 'bold'),
            'bg': self.CMD_BG if style == 'cmd' else self.BTN_BG,
            'fg': self.BTN_FG,
            'activebackground': self.BTN_ACTIVE,
            'activeforeground': '#fff',
            'relief': 'flat',
            'bd': 0,
            'padx': 2,
            'pady': 0,
            'cursor': 'hand2',
            'command': command,
        }
        if style == 'num':
            kw['font'] = ('Segoe UI', 11, 'bold')
            kw['padx'] = 1
            kw['pady'] = 0
        if style == 'icon':
            kw['font'] = ('Segoe UI Emoji', 11)
            kw['pady'] = 0
        b = tk.Button(parent, text=text, **kw)
        if width:
            b.configure(width=width)
        return b

    def _reg(self, widget, kind='body'):
        """ウィジェットをテーマ変更対象に登録"""
        self.bg_widgets.append((widget, kind))
        return widget

    @staticmethod
    def _darken(hex_color, factor=0.4):
        """hex色を暗くする"""
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        return f'#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}'

    def _make_row(self, parent, keys, uniform_group=None, accent=False):
        """独立Frameで1行分をgrid配置（keys: [(text, command, weight), ...]）
        uniform_group: 指定すると全カラムを同じ幅グループに強制
        accent: Trueならテーマ連動の濃い色ボタン"""
        row = self._reg(tk.Frame(parent))
        btns = []
        for col, (text, cmd, weight) in enumerate(keys):
            b = self._btn(row, text, cmd)
            b.grid(row=0, column=col, padx=1, sticky='nsew')
            cfg = {'weight': weight}
            if uniform_group:
                cfg['uniform'] = f'{uniform_group}_{weight}'
            row.columnconfigure(col, **cfg)
            if accent:
                btns.append(b)
        row.rowconfigure(0, weight=1)
        if accent:
            self._accent_btns = getattr(self, '_accent_btns', []) + btns
        return row

    def _build_ui(self):
        # ヘッダ（ドラッグ用）
        hdr = self._reg(tk.Frame(self.root, height=15, cursor='fleur'), 'header')
        hdr.pack(fill='x')
        hdr.pack_propagate(False)

        # 左端: テーマ切り替えボタン
        self.theme_btn = self._reg(tk.Label(hdr, text='●', font=('Segoe UI', 7),
                                  cursor='hand2', fg='#fff'), 'header')
        self.theme_btn.pack(side='left', padx=4)
        self.theme_btn.bind('<Button-1>', self._cycle_theme)

        # 右端: 閉じるボタン
        x_btn = self._reg(tk.Label(hdr, text='✕', font=('Segoe UI', 6, 'bold'),
                         fg='#ddd', cursor='hand2'), 'header')
        x_btn.pack(side='right', padx=4)
        x_btn.bind('<Button-1>', lambda e: self._on_close())

        # 最小化ボタン（閉じるボタンから離す、反対色で目立たせる）
        self.min_btn = tk.Label(hdr, text='━', font=('Segoe UI', 5, 'bold'),
                               fg='#fff', cursor='hand2', relief='flat', bd=0)
        self.min_btn.pack(side='right', padx=(2, 12))
        self.min_btn.bind('<Button-1>', lambda e: self.root.iconify())

        for w in (hdr,):
            w.bind('<Button-1>', self._drag_start)
            w.bind('<B1-Motion>', self._drag_move)
            w.bind('<Double-Button-1>', lambda e: self.root.iconify())

        # メインエリア: キー群(左, weight=20) + Enter(右, weight=3 ≒ 1.5倍幅)
        body = self._reg(tk.Frame(self.root))
        body.pack(fill='both', expand=True, padx=2, pady=(0, 2))
        body.columnconfigure(0, weight=20)
        body.columnconfigure(1, weight=3)
        body.rowconfigure(0, weight=1)

        left = self._reg(tk.Frame(body))
        left.grid(row=0, column=0, sticky='nsew')

        enter_btn = tk.Button(
            body, text='Enter\n⏎',
            font=('Segoe UI', 11, 'bold'),
            bg='#2a4a6c', fg=self.BTN_FG,
            activebackground='#3a6a9c', activeforeground='#fff',
            relief='flat', bd=0,
            cursor='hand2',
            command=lambda: self._act(lambda: send_key(VK_RETURN)),
        )
        enter_btn.grid(row=0, column=1, sticky='nsew', padx=(1, 0))

        # left内をgridで均等配分（5論理行: row0, numgrid=2行分, row3, row4）
        for r in range(4):
            left.rowconfigure(r, weight=2 if r == 1 else 1)  # numgridは2行分
        left.columnconfigure(0, weight=1)

        # Row 0: ESC ← ↓ ↑ → ★Apps (均等)
        r0 = self._make_row(left, [
            ('ESC',    lambda: self._act(lambda: send_key(VK_ESCAPE)), 1),
            ('◀',      lambda: self._act(lambda: send_key(VK_LEFT)), 1),
            ('▼',      lambda: self._act(lambda: send_key(VK_DOWN)), 1),
            ('▲',      lambda: self._act(lambda: send_key(VK_UP)), 1),
            ('▶',      lambda: self._act(lambda: send_key(VK_RIGHT)), 1),
            ('Apps',   lambda: open_apps_folder(), 1),
        ])
        r0.grid(row=0, column=0, sticky='nsew', pady=(0, 1))
        # 矢印キー(col1-4)を大きめに
        for c in (1, 2, 3, 4):
            r0.grid_slaves(row=0, column=c)[0].configure(font=('Segoe UI', 12, 'bold'))

        # Row 1-2: 数字キー2行を1つのgridで統合（カラム幅を確実に揃える）
        numgrid = self._reg(tk.Frame(left), 'body')
        numgrid.grid(row=1, column=0, sticky='nsew', pady=1)
        numgrid.rowconfigure(0, weight=1)
        numgrid.rowconfigure(1, weight=1)
        weights = [2, 2, 2, 2, 2, 3, 3]
        for col, w in enumerate(weights):
            numgrid.columnconfigure(col, weight=w)
        # Row 1: 1 2 3 4 5 📷↑(2行分) 半角
        row1_nums = [
            ('1', lambda: self._act(lambda: type_text('1'))),
            ('2', lambda: self._act(lambda: type_text('2'))),
            ('3', lambda: self._act(lambda: type_text('3'))),
            ('4', lambda: self._act(lambda: type_text('4'))),
            ('5', lambda: self._act(lambda: type_text('5'))),
        ]
        for col, (text, cmd) in enumerate(row1_nums):
            b = self._btn(numgrid, text, cmd)
            b.grid(row=0, column=col, padx=1, pady=(0, 1), sticky='nsew')
            self._accent_btns = getattr(self, '_accent_btns', []) + [b]
        # 📷↑: 2行にまたがる
        cam_btn = self._btn(numgrid, '🎞↑', lambda: self._act(paste_latest_screenshot))
        cam_btn.configure(font=('Segoe UI Emoji', 18), anchor='center')
        cam_btn.grid(row=0, column=5, rowspan=2, padx=1, sticky='nsew')
        self._accent_btns = getattr(self, '_accent_btns', []) + [cam_btn]
        # 半/全トグル
        hanb = self._btn(numgrid, '半/全', lambda: self._act(toggle_ime))
        hanb.configure(font=('Meiryo UI', 11, 'bold'))
        hanb.grid(row=0, column=6, padx=1, pady=(0, 1), sticky='nsew')
        self._accent_btns = getattr(self, '_accent_btns', []) + [hanb]
        # Row 2: 6 7 8 9 0 (col5は📷↑が占有) PrtSc
        row2_nums = [
            ('6', lambda: self._act(lambda: type_text('6'))),
            ('7', lambda: self._act(lambda: type_text('7'))),
            ('8', lambda: self._act(lambda: type_text('8'))),
            ('9', lambda: self._act(lambda: type_text('9'))),
            ('0', lambda: self._act(lambda: type_text('0'))),
        ]
        for col, (text, cmd) in enumerate(row2_nums):
            b = self._btn(numgrid, text, cmd)
            b.grid(row=1, column=col, padx=1, sticky='nsew')
        # PrtSc（col6、ブラウン固定）
        prtsc = self._btn(numgrid, 'PrtSc', lambda: self._act(lambda: send_key(VK_SNAPSHOT)))
        prtsc.configure(bg='#68432e', activebackground='#805540')
        prtsc.grid(row=1, column=6, padx=1, sticky='nsew')

        # Row 3: Copy Paste |←←Del Home End BS (big=3, small=2, アクセント色)
        r3 = self._make_row(left, [
            ('Copy',   lambda: self._act(lambda: send_combo(VK_CONTROL, VK_INSERT)), 3),
            ('Paste',  lambda: self._act(lambda: send_combo(VK_SHIFT, VK_INSERT)), 3),
            ('|←←Del', lambda: self._act(lambda: send_combo(VK_CONTROL, VK_U)), 3),
            ('Home',   lambda: self._act(lambda: send_key(VK_HOME)), 2),
            ('End',    lambda: self._act(lambda: send_key(VK_END)), 2),
            ('BS',     lambda: self._act(lambda: send_key(VK_BACK)), 2),
        ], accent=True)
        r3.grid(row=2, column=0, sticky='nsew', pady=1)

        # Row 4: 🪟🪟 CtrlA /remote /resume (均等)
        def type_cmd(text):
            def action():
                type_text(text)
                time.sleep(0.02)
                send_key(VK_RETURN)
            self._act(action)

        r4 = self._make_row(left, [
            ('🪟🪟',    lambda: self._realign_all(), 1),
            ('CtrlA',   lambda: self._act(lambda: send_combo(VK_CONTROL, 0x41)), 1),
            ('/remote',  lambda: type_cmd('/remote-control'), 1),
            ('/resume',  lambda: type_cmd('/resume'), 1),
        ])
        r4.grid(row=3, column=0, sticky='nsew', pady=(1, 0))

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

    def _setup_tray(self):
        """システムトレイアイコンを設定"""
        try:
            import pystray
            from PIL import Image
        except ImportError:
            return  # pystray/Pillow未インストール時はトレイなし

        icon_path = getattr(self, '_icon_path', None)
        if icon_path and os.path.exists(icon_path):
            image = Image.open(icon_path)
        else:
            # フォールバック: 16x16ピンクアイコン
            image = Image.new('RGB', (16, 16), '#e88aa0')

        def on_show(icon, item):
            self.root.after(0, self._tray_show)

        def on_align(icon, item):
            self.root.after(0, self._realign_all)

        def on_quit(icon, item):
            icon.stop()
            self.root.after(0, self.root.destroy)

        menu = pystray.Menu(
            pystray.MenuItem('表示', on_show, default=True),
            pystray.MenuItem('整列', on_align),
            pystray.MenuItem('終了', on_quit),
        )
        self._tray_icon = pystray.Icon(
            'transparent_keyboard',
            image,
            '透明キーボード',
            menu,
        )
        # トレイアイコンを別スレッドで起動
        tray_thread = threading.Thread(target=self._tray_icon.run, daemon=True)
        tray_thread.start()

    def _tray_show(self):
        """トレイからの表示復元"""
        self.root.deiconify()
        self.root.attributes('-topmost', True)

    def _on_close(self):
        """閉じるボタン: トレイアイコンも停止して終了"""
        if hasattr(self, '_tray_icon'):
            try:
                self._tray_icon.stop()
            except Exception:
                pass
        self.root.destroy()

    def run(self):
        self._setup_tray()
        self.root.mainloop()


if __name__ == '__main__':
    TransparentKeyboard(slot=_instance_slot).run()
