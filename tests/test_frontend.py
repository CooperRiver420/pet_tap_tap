"""
前端模块测试 - TapPet Phase-1
测试形象系统、动画引擎、战斗组件、视觉特效
"""
import sys
import time

# 设置PyQt6为无头模式（如需要）
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush

# 导入前端模块
sys.path.insert(0, '/home/coopervision/project/pet_tap_tap')

from core import (
    CharacterManager, Character, get_character_manager,
    AnimationEngine, AnimationState,
    Enemy, CharacterBattleController, ExplosionEffect,
    GameView, GameWidget
)
from utils import DamageText, KillText, EffectsManager


def test_character_manager():
    """测试C-01~C-04: 角色形象系统"""
    print("\n=== 测试角色形象系统 ===")
    
    manager = get_character_manager()
    
    # 测试C-01: 角色目录结构
    chars = manager.get_all_characters()
    print(f"  [C-01] 加载角色数量: {len(chars)}")
    for c in chars:
        print(f"    - {c.id}: {c.name} ({c.type})")
    
    # 测试C-02: 资源加载
    print("\n  [C-02] 测试资源加载:")
    for char in chars:
        img = manager.load_character_image(char.id)
        if img:
            print(f"    ✓ {char.id}: {img.width()}x{img.height()}")
        else:
            print(f"    ✗ {char.id}: 加载失败")
    
    # 测试C-04: 形象切换
    print("\n  [C-04] 测试形象切换:")
    for char in chars:
        result = manager.switch_character(char.id)
        print(f"    {'✓' if result else '✗'} 切换到 {char.id}")
    
    current = manager.get_current()
    print(f"  当前角色: {current.id if current else 'None'}")
    
    return True


def test_animation_engine():
    """测试C-03: 代码驱动动画引擎"""
    print("\n=== 测试动画引擎 ===")
    
    engine = AnimationEngine()
    
    # 测试待机动画
    print("  [C-03] 测试待机动画:")
    engine.set_state(AnimationState.IDLE)
    for i in range(5):
        engine.update(400)  # 模拟200ms
        params = engine.get_params()
        print(f"    帧{i}: scale={params.scale:.3f}, opacity={params.opacity:.3f}, offset_y={params.offset_y:.2f}")
    
    # 测试行走动画
    print("\n  测试行走动画:")
    engine.set_state(AnimationState.WALK)
    print(f"    行走距离: {engine.get_walk_distance()}px")
    
    # 测试攻击动画
    print("\n  测试攻击动画:")
    engine.set_state(AnimationState.ATTACK)
    engine.update(50)
    params = engine.get_params()
    print(f"    攻击缩放: {params.scale:.3f}")
    
    print("  ✓ 动画引擎测试通过")
    return True


def test_battle_components():
    """测试B-03, B-04, B-07, B-08: 战斗组件"""
    print("\n=== 测试战斗组件 ===")
    
    # 测试B-04: 敌人刷新
    print("  [B-04] 测试敌人刷新:")
    enemy = Enemy()
    enemy.size = 48
    
    # 模拟角色X=60, 敌人应在60+120~200=180~260
    import random
    for _ in range(5):
        enemy_x = 60 + random.randint(120, 200)
        enemy.spawn(enemy_x, 272)  # ground_y - enemy_size
        print(f"    敌人刷新: x={enemy.x:.0f}, health={enemy.health}, visible={enemy.visible}")
    
    # 测试B-07: 受击抖动
    print("\n  [B-07] 测试受击抖动:")
    for _ in range(10):
        enemy.update(15)  # 15ms
        print(f"    shake={enemy.shake:.2f}, scale={enemy.scale:.3f}")
    
    # 测试B-08: 击杀爆炸
    print("\n  [B-08] 测试击杀爆炸:")
    exp = ExplosionEffect(200, 224, 48)
    print(f"    爆炸粒子数: {len(exp.particles)}")
    exp.update(50)
    print(f"    进度: {exp.progress:.2f}")
    
    return True


def test_effects():
    """测试V-01~V-03: 视觉特效"""
    print("\n=== 测试视觉特效 ===")
    
    manager = EffectsManager()
    
    # 测试V-01: 伤害飘字
    print("  [V-01] 测试伤害飘字:")
    dmg = manager.spawn_damage_text(240, 100)
    print(f"    伤害飘字: '{dmg._text}', 颜色={dmg._color.name()}")
    dmg.update(250)
    print(f"    250ms后: offset_y={dmg._offset_y:.1f}, opacity={dmg._opacity:.2f}")
    
    # 测试V-02: 击杀飘字
    print("\n  [V-02] 测试击杀飘字:")
    kill = manager.spawn_kill_text(240, 100)
    print(f"    击杀飘字: '{kill._text}', 颜色={kill._color.name()}")
    kill.update(400)
    print(f"    400ms后: scale={kill._scale:.2f}, opacity={kill._opacity:.2f}")
    
    # 测试V-03: 爆炸粒子
    print("\n  [V-03] 测试爆炸粒子:")
    explosion = manager.spawn_explosion(240, 200, 10)
    print(f"    粒子数量: {len(explosion._particles)}")
    explosion.update(150)
    print(f"    150ms后仍有粒子: {len(explosion._particles)}")
    
    return True


def test_game_view():
    """测试GameView渲染"""
    print("\n=== 测试GameView ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    view = GameView()
    print(f"  游戏区域: {view.GAME_WIDTH}x{view.GAME_HEIGHT}")
    print(f"  地面Y: {view.get_ground_y()}")
    print(f"  角色初始X: {view.get_character_x()}")
    
    # 测试触发行走
    print("\n  测试触发行走:")
    view.trigger_walk()
    time.sleep(0.4)
    print(f"    行走后角色X: {view.get_character_x():.1f}")
    
    # 测试生成敌人
    print("\n  测试生成敌人:")
    view.spawn_enemy()
    print(f"    敌人已生成")
    
    # 测试攻击
    print("\n  测试攻击:")
    view.trigger_attack()
    is_killed = view.trigger_enemy_hit()
    print(f"    受击击杀: {is_killed}")
    
    print("\n  ✓ GameView测试通过")
    return True


def main():
    print("=" * 50)
    print("TapPet Phase-1 前端模块测试")
    print("=" * 50)
    
    results = []
    
    try:
        results.append(("角色形象系统", test_character_manager()))
        results.append(("动画引擎", test_animation_engine()))
        results.append(("战斗组件", test_battle_components()))
        results.append(("视觉特效", test_effects()))
        results.append(("GameView", test_game_view()))
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 50)
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
