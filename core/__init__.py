# -*- coding: utf-8 -*-
"""
TapPet Phase-1 Core Modules

Backend (this agent):
  Config, StateMachine, PetState, BattleStats, DataPersistence,
  WindowManager, PetGraphicsView, TrayManager, GlobalKeyboardListener,
  BattleEngine, BattlePhase

Frontend (frontend agent):
  CharacterManager, Character, get_character_manager,
  AnimationEngine, AnimationState,
  Enemy, CharacterBattleController, ExplosionEffect,
  GameView, GameWidget
"""

# Backend modules
from .config import Config
from .state_machine import StateMachine, PetState, StateTransition, BattleStats, DataPersistence
from .window import WindowManager, PetGraphicsView, TrayManager, dock_to_corner
from .input_handler import GlobalKeyboardListener
from .battle_engine import BattleEngine, BattlePhase

# Frontend modules (if available)
try:
    from .character_manager import CharacterManager, Character, get_character_manager
except ImportError:
    pass

try:
    from .animation_engine import AnimationEngine, AnimationState
except ImportError:
    pass

try:
    from .battle_components import (
        Enemy as EnemyComponent,
        CharacterBattleController,
        ExplosionEffect,
    )
    Enemy = EnemyComponent  # Also available as Enemy for frontend
except ImportError:
    pass

try:
    from .game_view import GameView, GameWidget
except ImportError:
    pass

__all__ = [
    # Backend
    "Config",
    "StateMachine",
    "PetState",
    "StateTransition",
    "BattleStats",
    "DataPersistence",
    "WindowManager",
    "PetGraphicsView",
    "TrayManager",
    "dock_to_corner",
    "GlobalKeyboardListener",
    "BattleEngine",
    "BattlePhase",
    # Frontend
    "CharacterManager",
    "Character",
    "get_character_manager",
    "AnimationEngine",
    "AnimationState",
    "EnemyComponent",
    "Enemy",
    "CharacterBattleController",
    "ExplosionEffect",
    "GameView",
    "GameWidget",
]
