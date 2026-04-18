# -*- coding: utf-8 -*-
"""
S-01~S-04: 状态机模块
互斥五状态：Idle / Battle / Rest / Pomodoro / OCR
"""

import os
import json
import threading
from pathlib import Path
from enum import Enum, auto
from typing import Callable
from dataclasses import dataclass, field


class PetState(Enum):
    """Pet 五种互斥状态"""
    IDLE = auto()      # 待机（默认）
    BATTLE = auto()    # 战斗
    REST = auto()      # 休息
    POMODORO = auto()  # 番茄钟
    OCR = auto()       # OCR识别


@dataclass
class StateTransition:
    """状态转换事件"""
    from_state: PetState | None
    to_state: PetState
    reason: str = ""


@dataclass
class BattleStats:
    """内存中的战斗数据"""
    kill_count: int = 0
    max_combo: int = 0
    battle_time_seconds: int = 0  # 当天累计战斗时长


class DataPersistence:
    """CFG-02: 战斗数据持久化（battle_stats.json）"""

    def __init__(self, data_dir: str | None = None):
        if data_dir is None:
            base = os.environ.get("TAPPET_HOME", str(Path.home()))
            data_dir = os.path.join(base, ".tappet", "userdata")
        self._dir = Path(data_dir)
        self._stats_file = self._dir / "battle_stats.json"
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if self._stats_file.exists():
            try:
                with open(self._stats_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._kill_count = data.get("killCount", 0)
                self._max_combo = data.get("maxCombo", 0)
                self._battle_time_seconds = data.get("battleTime", 0)
            except (json.JSONDecodeError, IOError):
                self._reset()
        else:
            self._reset()

    def _reset(self) -> None:
        self._kill_count = 0
        self._max_combo = 0
        self._battle_time_seconds = 0

    def save(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        data = {
            "killCount": self._kill_count,
            "maxCombo": self._max_combo,
            "battleTime": self._battle_time_seconds,
        }
        with self._lock:
            with open(self._stats_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

    def add_kill(self) -> None:
        self._kill_count += 1
        # 每击杀10个敌人写入一次
        if self._kill_count % 10 == 0:
            self.save()

    @property
    def kill_count(self) -> int:
        return self._kill_count

    @property
    def max_combo(self) -> int:
        return self._max_combo

    @property
    def battle_time_seconds(self) -> int:
        return self._battle_time_seconds

    def add_battle_time(self, seconds: int) -> None:
        self._battle_time_seconds += seconds


class StateMachine:
    """
    S-01~S-04: 五状态互斥状态机
    - 单例模式，管理全局宠物状态
    - 线程安全
    - 状态转换时派发事件回调
    """

    _instance: "StateMachine | None" = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> "StateMachine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, persistence: DataPersistence | None = None):
        if self._initialized:
            return
        self._initialized = True
        self._state = PetState.IDLE
        self._persistence = persistence or DataPersistence()
        self._battle_stats = BattleStats()
        # 状态转换回调: List[Callable[[StateTransition], None]]
        self._transition_callbacks: list[Callable[[StateTransition], None]] = []
        self._cb_lock = threading.Lock()

    # ---- 状态查询 ----

    @property
    def current_state(self) -> PetState:
        return self._state

    @property
    def is_battle(self) -> bool:
        return self._state == PetState.BATTLE

    @property
    def is_idle(self) -> bool:
        return self._state == PetState.IDLE

    @property
    def battle_stats(self) -> BattleStats:
        return self._battle_stats

    @property
    def persistence(self) -> DataPersistence:
        return self._persistence

    # ---- 状态互斥处理（S-03） ----

    def can_enter_battle(self) -> bool:
        """S-03: Battle ↔ Rest/Pomodoro 互斥"""
        return self._state not in (PetState.BATTLE, PetState.REST, PetState.POMODORO)

    def enter_battle(self, reason: str = "") -> bool:
        """
        进入战斗状态。
        若当前是 Rest 或 Pomodoro，先退出再进入。
        """
        if self._state == PetState.BATTLE:
            return False  # 已在战斗

        prev = self._state

        # S-03: 互斥处理：Rest/Pomodoro -> 先退出
        if self._state in (PetState.REST, PetState.POMODORO):
            self._notify_transition(StateTransition(
                from_state=self._state,
                to_state=PetState.BATTLE,
                reason=f"{reason} (from {self._state.name})"
            ))

        self._state = PetState.BATTLE
        self._notify_transition(StateTransition(from_state=prev, to_state=self._state, reason=reason))
        return True

    def exit_battle(self, to_state: PetState = PetState.IDLE, reason: str = "") -> bool:
        """
        退出战斗状态。
        S-03: 只能转到 Idle / Rest / Pomodoro（不由 Battle 直接转 OCR）
        """
        if self._state != PetState.BATTLE:
            return False
        if to_state not in (PetState.IDLE, PetState.REST, PetState.POMODORO):
            to_state = PetState.IDLE

        prev = self._state
        self._state = to_state
        self._notify_transition(StateTransition(from_state=prev, to_state=to_state, reason=reason))
        return True

    def set_state(self, state: PetState, reason: str = "") -> bool:
        """通用状态切换（带互斥检查）"""
        if self._state == state:
            return False

        # S-03: Battle ↔ Rest/Pomodoro 互斥
        if state == PetState.BATTLE:
            return self.enter_battle(reason)
        if self._state == PetState.BATTLE:
            return self.exit_battle(to_state=state, reason=reason)

        prev = self._state
        self._state = state
        self._notify_transition(StateTransition(from_state=prev, to_state=state, reason=reason))
        return True

    # ---- 战斗数据操作 ----

    def add_kill(self) -> None:
        self._persistence.add_kill()
        self._battle_stats.kill_count = self._persistence.kill_count

    # ---- 回调注册 ----

    def on_transition(self, callback: Callable[[StateTransition], None]) -> None:
        with self._cb_lock:
            self._transition_callbacks.append(callback)

    def _notify_transition(self, t: StateTransition) -> None:
        with self._cb_lock:
            for cb in self._transition_callbacks[:]:
                try:
                    cb(t)
                except Exception:
                    pass  # 不让回调异常影响状态机

    @classmethod
    def reset_instance(cls) -> None:
        """测试用：重置单例"""
        with cls._lock:
            cls._instance = None
