# -*- coding: utf-8 -*-
"""
B-02, B-05, B-06, B-09: 战斗引擎模块
- B-02: 计数逻辑（0→10阈值，100ms防抖，Ctrl/Shift/Alt/F1-F12不计入）
- B-05: 攻击判定 + 扣血逻辑
- B-06: 敌人行为（出现滑入、待机浮动）
- B-09: 计数重置 + 角色返回起点
"""

import time
import random
import math
import threading
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Callable

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QPointF, Qt
from PyQt6.QtGui import QColor, QBrush, QPen, QPainter, QPixmap

from .config import Config
from .state_machine import StateMachine, PetState, BattleStats


# ---- 战斗子状态 ----
class BattlePhase(Enum):
    """战斗子阶段（在同一场战斗内）"""
    IDLE = auto()      # 0-9计数待机
    WALKING = auto()   # 第10次触发行走
    SPAWNING = auto()  # 敌人出现滑入
    ATTACKING = auto() # 第11次起攻击
    HIT_FEEDBACK = auto()  # 受击抖动
    DYING = auto()     # 击杀中（爆炸）
    RETURNING = auto() # 角色返回起点


@dataclass
class Enemy:
    """敌人实体"""
    hp: int
    max_hp: int
    x: float
    y: float
    base_y: float  # 浮动基准Y
    alive: bool = True
    # 动画状态
    scale: float = 1.0
    opacity: float = 1.0
    offset_y: float = 0.0  # 浮动偏移


@dataclass
class BattleEvents:
    """战斗事件信号（pyqtSignal 发射用）"""
    count_changed: int = 0          # 计数变化
    phase_changed: BattlePhase = BattlePhase.IDLE
    enemy_spawned: "Enemy | None" = None
    enemy_hit: int = 0              # 扣血量
    enemy_killed: bool = False
    character_returned: bool = False
    kill_added: bool = False


class BattleEngine(QObject):
    """
    战斗引擎核心类
    管理键盘计数、角色行为、敌人行为、击杀循环
    """

    # Qt 信号
    count_changed = pyqtSignal(int)            # 当前计数
    phase_changed = pyqtSignal(str)            # BattlePhase name
    enemy_spawned = pyqtSignal(dict)          # enemy data dict
    enemy_hit = pyqtSignal(int, float, float) # damage, x, y
    enemy_killed = pyqtSignal()
    character_walk = pyqtSignal(float)       # 目标x
    character_return = pyqtSignal()
    floating_text = pyqtSignal(str, str, float, float)  # text, color, x, y
    explosion = pyqtSignal(float, float)      # x, y
    kill_added = pyqtSignal(int)              # 总击杀数

    def __init__(
        self,
        config: Config,
        state_machine: StateMachine,
        parent=None
    ):
        super().__init__(parent)
        self._cfg = config
        self._sm = state_machine

        # 计数
        self._count = 0
        self._active = False  # 战斗状态是否激活
        self._pending_attack = False  # WALKING期间是否等待攻击

        # 角色位置
        self._char_x = config.character_start_x
        self._char_y: float | None = None  # 由外部设置（地面Y）

        # 敌人
        self._enemy: Enemy | None = None

        # 战斗子阶段
        self._phase = BattlePhase.IDLE

        # 动画定时器
        self._anim_timers: list[QTimer] = []

        # 回调
        self._on_kill_callbacks: list[Callable[[int], None]] = []

    # ---- 外部调用 API ----

    def activate(self) -> None:
        """开启战斗状态响应"""
        self._active = True
        self._count = 0
        self._phase = BattlePhase.IDLE
        self._emit_count()
        # 角色回到起点
        self._reset_to_start()

    def deactivate(self) -> None:
        """关闭战斗状态响应"""
        self._active = False
        self._count = 0
        self._stop_all_timers()
        self._emit_count()

    def on_key_press(self) -> None:
        """
        B-02: 每次有效按键调用此方法
        计数逻辑：0→10阈值判断
        """
        if not self._active:
            return

        self._count += 1
        self._emit_count()

        if self._phase == BattlePhase.IDLE:
            if self._count >= self._cfg.walk_threshold:
                # 第10次：触发行走+刷新敌人
                self._trigger_walk()
            else:
                pass  # 继续累积

        elif self._phase == BattlePhase.WALKING:
            # 行走动画期间：标记需要攻击，行走结束后自动触发
            self._pending_attack = True

        elif self._phase == BattlePhase.ATTACKING:
            # 第11次起：每次按键都是攻击
            self._trigger_attack()

        elif self._phase == BattlePhase.HIT_FEEDBACK:
            # 抖动期间忽略输入
            pass

        elif self._phase == BattlePhase.DYING:
            # 死亡动画期间忽略
            pass

        elif self._phase == BattlePhase.RETURNING:
            # 返回期间忽略
            pass

    def set_character_y(self, y: float) -> None:
        self._char_y = y

    def set_character_x(self, x: float) -> None:
        self._char_x = x

    def get_character_x(self) -> float:
        return self._char_x

    def get_enemy(self) -> Enemy | None:
        return self._enemy

    def get_phase(self) -> BattlePhase:
        return self._phase

    def get_count(self) -> int:
        return self._count

    def is_active(self) -> bool:
        return self._active

    def on_kill(self, cb: Callable[[int], None]) -> None:
        self._on_kill_callbacks.append(cb)

    # ---- 内部行为 ----

    def _trigger_walk(self) -> None:
        """B-09 部分: 第10次触发行走 + 刷新敌人"""
        self._phase = BattlePhase.WALKING

        # 计算目标X
        target_x = self._cfg.character_start_x + self._cfg.walk_distance

        # 角色行走
        self._animate_walk(target_x)

        # 刷新敌人
        self._spawn_enemy(target_x)

    def _animate_walk(self, target_x: float) -> None:
        """B-03: 角色行走动画"""
        self._emit_phase()
        start_x = self._char_x
        duration_ms = int(self._cfg.walk_duration * 1000)
        start_time = time.time()

        def step():
            elapsed = (time.time() - start_time) * 1000
            if elapsed >= duration_ms:
                self._char_x = target_x
                self.character_walk.emit(target_x)
                # 行走完成后进入攻击阶段
                QTimer.singleShot(100, self._on_walk_complete)
                return
            t = elapsed / duration_ms
            # 缓动曲线
            eased = self._ease_out_cubic(t)
            self._char_x = start_x + (target_x - start_x) * eased
            self.character_walk.emit(self._char_x)
            QTimer.singleShot(16, step)

        QTimer.singleShot(16, step)

    def _on_walk_complete(self) -> None:
        self._phase = BattlePhase.SPAWNING
        self._emit_phase()
        # 如果WALKING期间有按键，到达ATTACKING后立即攻击
        if self._pending_attack:
            self._pending_attack = False
            QTimer.singleShot(0, self._enter_attack_phase)
            QTimer.singleShot(50, self._trigger_attack)

    def _spawn_enemy(self, char_x: float) -> None:
        """B-04, B-06: 敌人刷新（随机X=char_x+120~200）+ 滑入动画"""
        spawn_x = char_x + random.uniform(
            self._cfg.enemy_spawn_x_min,
            self._cfg.enemy_spawn_x_max
        )
        if self._char_y is None:
            return
        base_y = self._char_y

        self._enemy = Enemy(
            hp=self._cfg.enemy_hp,
            max_hp=self._cfg.enemy_hp,
            x=spawn_x,
            y=base_y,
            base_y=base_y,
            alive=True,
        )

        # 滑入动画（从右侧滑入，0.3秒）
        self._animate_enemy_slide_in(spawn_x, base_y)

    def _animate_enemy_slide_in(self, target_x: float, y: float) -> None:
        if self._enemy is None:
            return
        duration_ms = 300
        start_time = time.time()
        start_x = self._cfg.game_width + 50  # 从屏幕外右侧开始

        def step():
            if self._enemy is None:
                return
            elapsed = (time.time() - start_time) * 1000
            if elapsed >= duration_ms:
                self._enemy.x = target_x
                self.enemy_spawned.emit(self._enemy_serialize(self._enemy))
                # 滑入完成，进入待机浮动 + 攻击阶段
                QTimer.singleShot(0, self._start_enemy_float)
                QTimer.singleShot(0, self._enter_attack_phase)
                return
            t = elapsed / duration_ms
            eased = self._ease_out_cubic(t)
            self._enemy.x = start_x + (target_x - start_x) * eased
            self.enemy_spawned.emit(self._enemy_serialize(self._enemy))
            QTimer.singleShot(16, step)

        QTimer.singleShot(16, step)

    def _start_enemy_float(self) -> None:
        """B-06: 敌人待机浮动（正弦位移）"""
        if self._enemy is None:
            return
        period_s = self._cfg.enemy_float_period_ms / 1000.0
        amplitude = self._cfg.enemy_float_amplitude
        start_time = time.time()

        def step():
            if self._enemy is None or not self._enemy.alive:
                return
            elapsed = time.time() - start_time
            t = (elapsed % period_s) / period_s
            angle = t * 2 * math.pi
            self._enemy.offset_y = math.sin(angle) * amplitude
            self._enemy.y = self._enemy.base_y + self._enemy.offset_y
            QTimer.singleShot(16, step)

        QTimer.singleShot(16, step)

    def _enter_attack_phase(self) -> None:
        self._phase = BattlePhase.ATTACKING
        self._emit_phase()

    def _trigger_attack(self) -> None:
        """B-05: 攻击判定 + 扣血逻辑"""
        if self._enemy is None or not self._enemy.alive:
            return

        self._enemy.hp -= 1
        damage = 1

        # 触发受击抖动
        self._phase = BattlePhase.HIT_FEEDBACK
        self._emit_phase()
        self.enemy_hit.emit(damage, self._enemy.x, self._enemy.y)
        self.floating_text.emit("-1", "#FF4444", self._enemy.x, self._enemy.y - 20)

        self._animate_hit_shake()

    def _animate_hit_shake(self) -> None:
        """B-07: 受击缩放抖动（0.8x → 1x 重复1次）"""
        if self._enemy is None:
            return
        duration_ms = self._cfg.hit_shake_duration_ms
        start_time = time.time()

        def step():
            if self._enemy is None:
                return
            elapsed = (time.time() - start_time) * 1000
            half = duration_ms / 2
            # 0→half: 0.8x→1.0x, half→duration: 1.0x→0.8x→1.0x
            if elapsed < half:
                t = elapsed / half
                self._enemy.scale = 1.0 - 0.2 * (1 - self._ease_out_cubic(t))
            else:
                t = (elapsed - half) / half
                self._enemy.scale = 0.8 + 0.2 * self._ease_in_out_cubic(t)
            # 修正到1x
            if elapsed >= duration_ms:
                self._enemy.scale = 1.0
                QTimer.singleShot(0, self._on_hit_feedback_done)
                return
            QTimer.singleShot(16, step)

        QTimer.singleShot(16, step)

    def _on_hit_feedback_done(self) -> None:
        if self._enemy is None:
            return
        self._enemy.scale = 1.0
        if self._enemy.hp <= 0:
            self._trigger_death()
        else:
            self._phase = BattlePhase.ATTACKING
            self._emit_phase()

    def _trigger_death(self) -> None:
        """B-08: 击杀判定 + 爆炸消失"""
        if self._enemy is None:
            return
        self._enemy.alive = False
        self._phase = BattlePhase.DYING
        self._emit_phase()
        self.enemy_killed.emit()
        self.floating_text.emit("击破！", "#FFD700",
                                self._cfg.game_width / 2,
                                self._cfg.game_height / 2 - 40)
        self.explosion.emit(self._enemy.x, self._enemy.y)
        self._animate_explosion()

    def _animate_explosion(self) -> None:
        """B-08: 爆炸消失动画（缩放1x→1.3x + 透明度渐隐）"""
        if self._enemy is None:
            return
        duration_ms = 300
        start_time = time.time()

        def step():
            if self._enemy is None:
                return
            elapsed = (time.time() - start_time) * 1000
            if elapsed >= duration_ms:
                self._enemy.opacity = 0
                self._enemy.scale = 1.3
                self._enemy = None
                QTimer.singleShot(0, self._on_death_complete)
                return
            t = elapsed / duration_ms
            self._enemy.scale = 1.0 + 0.3 * self._ease_in_cubic(t)
            self._enemy.opacity = 1.0 - self._ease_in_cubic(t)
            QTimer.singleShot(16, step)

        QTimer.singleShot(16, step)

    def _on_death_complete(self) -> None:
        """B-09: 击杀完成后计数重置 + 角色返回起点"""
        self._phase = BattlePhase.RETURNING
        self._emit_phase()

        # 击杀统计
        self._sm.add_kill()
        kill_count = self._sm.battle_stats.kill_count
        self.kill_added.emit(kill_count)
        for cb in self._on_kill_callbacks:
            try:
                cb(kill_count)
            except Exception:
                pass

        # 延迟后返回起点
        QTimer.singleShot(500, self._return_to_start)

    def _return_to_start(self) -> None:
        """B-09: 角色平滑返回起点"""
        start_x = self._char_x
        target_x = self._cfg.character_start_x
        duration_ms = 400
        start_time = time.time()

        def step():
            elapsed = (time.time() - start_time) * 1000
            if elapsed >= duration_ms:
                self._char_x = target_x
                self.character_return.emit()
                QTimer.singleShot(0, self._on_return_complete)
                return
            t = elapsed / duration_ms
            eased = self._ease_in_out_cubic(t)
            self._char_x = start_x + (target_x - start_x) * eased
            self.character_return.emit()
            QTimer.singleShot(16, step)

        QTimer.singleShot(16, step)

    def _on_return_complete(self) -> None:
        """B-09: 返回完成后重置计数，循环继续"""
        self._count = 0
        self._phase = BattlePhase.IDLE
        self._emit_count()
        self._emit_phase()

    def _reset_to_start(self) -> None:
        self._char_x = self._cfg.character_start_x
        self._enemy = None
        self.character_return.emit()

    def _emit_count(self) -> None:
        self.count_changed.emit(self._count)

    def _emit_phase(self) -> None:
        self.phase_changed.emit(self._phase.name)

    def _enemy_serialize(self, e: Enemy) -> dict:
        return {
            "hp": e.hp,
            "max_hp": e.max_hp,
            "x": e.x,
            "y": e.y,
            "base_y": e.base_y,
            "alive": e.alive,
            "scale": e.scale,
            "opacity": e.opacity,
        }

    # ---- 缓动函数 ----
    @staticmethod
    def _ease_out_cubic(t: float) -> float:
        return 1 - (1 - t) ** 3

    @staticmethod
    def _ease_in_cubic(t: float) -> float:
        return t ** 3

    @staticmethod
    def _ease_in_out_cubic(t: float) -> float:
        if t < 0.5:
            return 4 * t * t * t
        return 1 - ((-2 * t + 2) ** 3) / 2

    # ---- 工具 ----
    def _stop_all_timers(self) -> None:
        for t in self._anim_timers[:]:
            t.stop()
        self._anim_timers.clear()
