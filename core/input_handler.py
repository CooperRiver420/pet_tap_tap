# -*- coding: utf-8 -*-
"""
B-01: 全局键盘监听模块
使用 pynput 实现跨窗口键盘监听，支持战斗快捷键检测
"""

import time
import threading
from typing import Callable
from pynput import keyboard


# ---- 修饰键 & 功能键列表（不计入计数）----
MODIFIER_KEYS = {
    keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
    keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r,
    keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r,
    keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r,
}
FUNCTION_KEYS = {
    keyboard.Key.f1, keyboard.Key.f2, keyboard.Key.f3,
    keyboard.Key.f4, keyboard.Key.f5, keyboard.Key.f6,
    keyboard.Key.f7, keyboard.Key.f8, keyboard.Key.f9,
    keyboard.Key.f10, keyboard.Key.f11, keyboard.Key.f12,
}
SPECIAL_KEYS = {
    keyboard.Key.tab, keyboard.Key.caps_lock, keyboard.Key.num_lock,
    keyboard.Key.scroll_lock, keyboard.Key.print_screen,
    keyboard.Key.insert, keyboard.Key.delete, keyboard.Key.home,
    keyboard.Key.end, keyboard.Key.page_up, keyboard.Key.page_down,
    keyboard.Key.up, keyboard.Key.down, keyboard.Key.left, keyboard.Key.right,
    keyboard.Key.menu,  # 上下文键
}


class KeyEvent:
    __slots__ = ("key", "timestamp", "is_pressed")

    def __init__(self, key, is_pressed: bool, timestamp: float | None = None):
        self.key = key
        self.is_pressed = is_pressed
        self.timestamp = timestamp if timestamp is not None else time.time()


class GlobalKeyboardListener:
    """
    B-01: 全局键盘监听器（pynput）
    - 跨窗口监听
    - 100ms 防抖（相同按键连续触发在阈值内只计一次）
    - Ctrl/Shift/Alt/F1-F12 不计入战斗计数
    - 快捷键 Ctrl+Shift+B 切换战斗状态
    """

    def __init__(self, debounce_ms: int = 100):
        self._debounce_ms = debounce_ms / 1000.0
        self._last_key_time: dict[str, float] = {}
        self._listener: keyboard.Listener | None = None
        self._running = False
        self._lock = threading.Lock()

        # 当前按住的修饰键（用于快捷键检测）
        self._pressed_modifiers: set[keyboard.Key] = set()

        # 回调
        self._battle_toggle_callbacks: list[Callable[[], None]] = []
        self._key_count_callbacks: list[Callable[[], None]] = []

        # 战斗状态计数
        self._count = 0

    # ---- 公开 API ----

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
            suppress=False,
        )
        self._listener.start()

    def stop(self) -> None:
        self._running = False
        if self._listener:
            self._listener.stop()
            self._listener = None

    def reset_count(self) -> None:
        with self._lock:
            self._count = 0

    @property
    def count(self) -> int:
        return self._count

    def increment_count(self) -> int:
        with self._lock:
            self._count += 1
            return self._count

    def on_battle_toggle(self, cb: Callable[[], None]) -> None:
        self._battle_toggle_callbacks.append(cb)

    def on_key_count(self, cb: Callable[[], None]) -> None:
        self._key_count_callbacks.append(cb)

    # ---- 内部处理 ----

    def _on_press(self, key) -> None:
        if not self._running:
            return

        # 记录修饰键按下状态
        if key in MODIFIER_KEYS:
            self._pressed_modifiers.add(key)

        # 快捷键检测: Ctrl+Shift+B
        if self._is_battle_toggle(key):
            self._fire_battle_toggle()
            return

        # 过滤修饰键、功能键、特殊键
        if self._is_excluded_key(key):
            return

        # 防抖
        key_str = self._key_str(key)
        now = time.time()
        if key_str in self._last_key_time:
            if now - self._last_key_time[key_str] < self._debounce_ms:
                return
        self._last_key_time[key_str] = now

        # 触发计数回调
        for cb in self._key_count_callbacks:
            try:
                cb()
            except Exception:
                pass

    def _on_release(self, key) -> None:
        # 清除修饰键状态
        self._pressed_modifiers.discard(key)

    def _is_battle_toggle(self, key) -> bool:
        try:
            k = key.char if hasattr(key, 'char') else None
            if k and k.lower() == 'b':
                # 检查 Ctrl 和 Shift 是否按住（使用 _pressed_modifiers）
                ctrl = keyboard.Key.ctrl_l in self._pressed_modifiers or keyboard.Key.ctrl_r in self._pressed_modifiers
                shift = keyboard.Key.shift_l in self._pressed_modifiers or keyboard.Key.shift_r in self._pressed_modifiers
                return ctrl and shift
        except (AttributeError, TypeError):
            pass
        return False

    def _is_excluded_key(self, key) -> bool:
        if key in MODIFIER_KEYS:
            return True
        if key in FUNCTION_KEYS:
            return True
        if key in SPECIAL_KEYS:
            return True
        return False

    def _key_str(self, key) -> str:
        if hasattr(key, 'char') and key.char is not None:
            return key.char.lower()
        return str(key)

    def _fire_battle_toggle(self) -> None:
        for cb in self._battle_toggle_callbacks:
            try:
                cb()
            except Exception:
                pass
