# -*- coding: utf-8 -*-
"""
CFG-01: 配置管理模块
管理所有可配置项，默认值定义，支持 JSON 文件持久化
"""

import json
import os
from pathlib import Path
from typing import Any


class Config:
    """全局配置管理器"""

    DEFAULT_CONFIG = {
        # 快捷键
        "battle_toggle_key": "ctrl+shift+b",
        # 音效开关
        "sound_enabled": True,
        # 攻击动画开关
        "attack_animation_enabled": True,
        # 飘字特效开关
        "floating_text_enabled": True,
        # 窗口透明度
        "window_opacity": 0.95,
        # 淡入淡出动画时长（毫秒）
        "fade_duration_ms": 300,
        # 战斗区尺寸
        "game_width": 480,
        "game_height": 320,
        # 地面高度（距底部）
        "ground_height": 40,
        # 角色初始X
        "character_start_x": 60,
        # 角色尺寸
        "character_size": 64,
        # 敌人尺寸
        "enemy_size": 48,
        # 敌人刷新X偏移范围
        "enemy_spawn_x_min": 120,
        "enemy_spawn_x_max": 200,
        # 行走距离（像素）
        "walk_distance": 70,
        # 行走耗时（秒）
        "walk_duration": 0.3,
        # 敌人血量
        "enemy_hp": 1,
        # 键盘防抖阈值（毫秒）
        "key_debounce_ms": 100,
        # 触发行走的计数阈值
        "walk_threshold": 10,
        # 敌人浮动幅度（像素）
        "enemy_float_amplitude": 8,
        # 敌人浮动周期（毫秒）
        "enemy_float_period_ms": 1500,
        # 缩放抖动持续时间（毫秒）
        "hit_shake_duration_ms": 300,
    }

    def __init__(self, config_path: str | None = None):
        if config_path is None:
            base = os.environ.get("TAPPET_HOME", str(Path.home()))
            config_path = os.path.join(base, ".tappet", "config.json")
        self._path = Path(config_path)
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self._data = {**self.DEFAULT_CONFIG, **loaded}
            except (json.JSONDecodeError, IOError):
                self._data = {**self.DEFAULT_CONFIG}
        else:
            self._data = {**self.DEFAULT_CONFIG}

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=4, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def all(self) -> dict[str, Any]:
        return dict(self._data)

    # 快捷访问属性
    @property
    def battle_toggle_key(self) -> str:
        return self.get("battle_toggle_key")

    @property
    def sound_enabled(self) -> bool:
        return self.get("sound_enabled", True)

    @property
    def attack_animation_enabled(self) -> bool:
        return self.get("attack_animation_enabled", True)

    @property
    def floating_text_enabled(self) -> bool:
        return self.get("floating_text_enabled", True)

    @property
    def window_opacity(self) -> float:
        return self.get("window_opacity", 0.95)

    @property
    def fade_duration_ms(self) -> int:
        return self.get("fade_duration_ms", 300)

    @property
    def game_width(self) -> int:
        return self.get("game_width", 480)

    @property
    def game_height(self) -> int:
        return self.get("game_height", 320)

    @property
    def ground_height(self) -> int:
        return self.get("ground_height", 40)

    @property
    def character_start_x(self) -> int:
        return self.get("character_start_x", 60)

    @property
    def character_size(self) -> int:
        return self.get("character_size", 64)

    @property
    def enemy_size(self) -> int:
        return self.get("enemy_size", 48)

    @property
    def enemy_spawn_x_min(self) -> int:
        return self.get("enemy_spawn_x_min", 120)

    @property
    def enemy_spawn_x_max(self) -> int:
        return self.get("enemy_spawn_x_max", 200)

    @property
    def walk_distance(self) -> int:
        return self.get("walk_distance", 70)

    @property
    def walk_duration(self) -> float:
        return self.get("walk_duration", 0.3)

    @property
    def enemy_hp(self) -> int:
        return self.get("enemy_hp", 1)

    @property
    def key_debounce_ms(self) -> int:
        return self.get("key_debounce_ms", 100)

    @property
    def walk_threshold(self) -> int:
        return self.get("walk_threshold", 10)

    @property
    def enemy_float_amplitude(self) -> int:
        return self.get("enemy_float_amplitude", 8)

    @property
    def enemy_float_period_ms(self) -> int:
        return self.get("enemy_float_period_ms", 1500)

    @property
    def hit_shake_duration_ms(self) -> int:
        return self.get("hit_shake_duration_ms", 300)
