# -*- coding: utf-8 -*-
import math
import random
"""
TapPet Phase-1 主入口
组装：Config + StateMachine + WindowManager + KeyboardListener + BattleEngine
"""

import sys
import os
import threading

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem, QGraphicsItem, QGraphicsTextItem, QGraphicsEllipseItem
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSlot, QObject
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QPixmap, QImage,
    QTransform, QPainterPath
)

from core import (
    Config, StateMachine, PetState,
    WindowManager, GlobalKeyboardListener, BattleEngine,
)


# =============================================================================
# 渲染层（代码绘制占位角色 / 敌人，PNG资源到位后替换）
# =============================================================================

class CharacterGraphicsItem(QGraphicsPixmapItem):
    """角色图元：支持缩放/位移动画"""

    def __init__(self, size: int = 64):
        super().__init__()
        self._size = size
        self._base_pixmap = self._create_placeholder()
        self.setPixmap(self._base_pixmap)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setTransformOriginPoint(self._size // 2, self._size // 2)

    def _create_placeholder(self) -> QPixmap:
        """占位角色：橙色猫头（64x64）"""
        pm = QPixmap(self._size, self._size)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # 身体
        painter.setBrush(QBrush(QColor("#FFB347")))
        painter.setPen(QPen(QColor("#CC8800"), 2))
        painter.drawEllipse(4, 4, self._size - 8, self._size - 8)
        # 耳朵
        painter.drawPolygon([
            QPointF(8, 8), QPointF(2, -4), QPointF(18, 2),
        ])
        painter.drawPolygon([
            QPointF(self._size - 8, 8), QPointF(self._size - 2, -4),
            QPointF(self._size - 18, 2),
        ])
        # 眼睛
        painter.setBrush(QBrush(QColor("#333333")))
        er = 4
        painter.drawEllipse(18, 24, er, er)
        painter.drawEllipse(self._size - 18 - er, 24, er, er)
        # 嘴巴
        painter.setPen(QPen(QColor("#CC6600"), 1.5))
        cx = self._size // 2
        painter.drawLine(cx - 5, 38, cx, 43)
        painter.drawLine(cx, 43, cx + 5, 38)
        painter.end()
        return pm

    def set_scale(self, s: float) -> None:
        self.setTransformOriginPoint(self._size // 2, self._size // 2)
        self.setScale(s)

    def set_opacity_f(self, op: float) -> None:
        self.setOpacity(op)


class EnemyGraphicsItem(QGraphicsPixmapItem):
    """敌人图元：红色气球，支持缩放抖动"""

    def __init__(self, size: int = 48):
        super().__init__()
        self._size = size
        self._base_pixmap = self._create_balloon()
        self.setPixmap(self._base_pixmap)
        self.setTransformOriginPoint(self._size // 2, self._size // 2)

    def _create_balloon(self) -> QPixmap:
        """占位气球：红色圆形+高光"""
        s = self._size
        pm = QPixmap(s, s)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # 气球主体
        painter.setBrush(QBrush(QColor("#FF4444")))
        painter.setPen(QPen(QColor("#CC2222"), 2))
        cx, cy = s // 2, s // 2 - 2
        r = s // 2 - 4
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)
        # 高光
        painter.setBrush(QBrush(QColor("#FF9999")))
        painter.setPen(Qt.PenStyle.NoPen)
        hl_r = r // 3
        painter.drawEllipse(cx - r // 2 - hl_r, cy - r // 2 - hl_r, hl_r * 2, hl_r * 2)
        # 底部三角
        painter.setBrush(QBrush(QColor("#CC2222")))
        painter.setPen(QPen(QColor("#AA0000"), 1))
        path = QPainterPath()
        path.moveTo(cx - 4, cy + r)
        path.lineTo(cx + 4, cy + r)
        path.lineTo(cx, cy + r + 8)
        path.closeSubpath()
        painter.drawPath(path)
        # 气球嘴
        painter.drawLine(cx, cy + r + 8, cx, cy + r + 14)
        painter.end()
        return pm

    def update_from_enemy(self, ex: float, ey: float, scale: float, opacity: float) -> None:
        self.setPos(ex - self._size // 2, ey - self._size // 2)
        self.setTransformOriginPoint(self._size // 2, self._size // 2)
        self.setScale(scale)
        self.setOpacity(opacity)


class GroundGraphicsItem(QGraphicsItem):
    """地面层（棕色平台条）"""

    def __init__(self, width: int, height: int, ground_height: int):
        super().__init__()
        self._w = width
        self._h = ground_height
        self.setPos(0, height - ground_height)
        self.setZValue(10)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._w, self._h)

    def paint(self, painter: QPainter, option=None, widget=None) -> None:
        painter.setBrush(QBrush(QColor("#8B4513")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, self._w, self._h)
        # 草地
        painter.setBrush(QBrush(QColor("#228B22")))
        painter.drawRect(0, 0, self._w, 6)


class FloatingTextItem(QGraphicsTextItem):
    """飘字图元"""

    def __init__(self, text: str, color: str, x: float, y: float):
        super().__init__(text)
        self._start_y = y
        self._elapsed = 0
        self._duration = 500  # ms
        self.setPos(x - 20, y)
        self.setDefaultTextColor(QColor(color))
        font = self.font()
        font.setBold(True)
        font.setPixelSize(16 if "击破" not in text else 24)
        self.setFont(font)
        self.setZValue(100)

    def animate(self) -> None:
        self._elapsed += 16
        t = min(1.0, self._elapsed / self._duration)
        # 向上飘动
        new_y = self._start_y - 20 * t
        self.setPos(self.pos().x(), new_y)
        # 透明度渐隐
        self.setOpacity(1.0 - self._ease_in_cubic(t))
        if t < 1.0:
            QTimer.singleShot(16, self.animate)
        else:
            self.scene().removeItem(self)

    @staticmethod
    def _ease_in_cubic(t: float) -> float:
        return t ** 3


class ExplosionParticle(QGraphicsEllipseItem):
    """爆炸粒子"""

    def __init__(self, cx: float, cy: float, vx: float, vy: float,
                 color: str, size: float = 6):
        super().__init__(cx - size / 2, cy - size / 2, size, size)
        self._vx = vx
        self._vy = vy
        self._elapsed = 0
        self._duration = 300
        self.setBrush(QBrush(QColor(color)))
        self.setPen(Qt.PenStyle.NoPen)
        self.setZValue(90)
        self._start_cx = cx
        self._start_cy = cy

    def animate(self) -> None:
        self._elapsed += 16
        t = min(1.0, self._elapsed / self._duration)
        gravity = 0.3
        self._vy += gravity * t
        dx = self._vx * t * 100
        dy = self._vy * t * 100 - 0.5 * 9.8 * (t ** 2) * 50
        self.setPos(self._start_cx + dx - self.rect().width() / 2,
                    self._start_cy + dy - self.rect().height() / 2)
        self.setOpacity(1.0 - t)
        if t < 1.0:
            QTimer.singleShot(16, self.animate)
        else:
            scene = self.scene()
            if scene:
                scene.removeItem(self)


# =============================================================================
# 主程序
# =============================================================================

class TapPetApp(QObject):
    """TapPet 主应用"""

    def __init__(self):
        # 配置
        self._cfg = Config()

        # 状态机
        self._sm = StateMachine()

        # 窗口管理器
        self._wm = WindowManager(self._cfg)

        # 键盘监听
        self._kb = GlobalKeyboardListener(debounce_ms=self._cfg.key_debounce_ms)

        # 战斗引擎
        self._battle = BattleEngine(self._cfg, self._sm)

        # QApplication
        # QApplication（必须在 QObject 子类之前创建）
        self._app = self._wm.init_app()
        self._app.setQuitOnLastWindowClosed(False)

        # 视图
        self._view = self._wm.create_window()

        # 场景元素
        self._scene = self._view.scene
        self._setup_scene()

        # 键盘监听启动
        self._kb.start()
        self._kb.on_key_count(self._on_key_count)
        self._kb.on_battle_toggle(self._on_battle_toggle)

        # 窗口管理器回调
        self._wm.on_battle_toggle(self._on_battle_toggle)
        self._wm.on_quit(self._on_quit)

        # 战斗引擎信号
        self._battle.count_changed.connect(self._on_count_changed)
        self._battle.phase_changed.connect(self._on_phase_changed)
        self._battle.enemy_spawned.connect(self._on_enemy_spawned)
        self._battle.enemy_hit.connect(self._on_enemy_hit)
        self._battle.enemy_killed.connect(self._on_enemy_killed)
        self._battle.character_walk.connect(self._on_character_walk)
        self._battle.character_return.connect(self._on_character_return)
        self._battle.floating_text.connect(self._on_floating_text)
        self._battle.explosion.connect(self._on_explosion)
        self._battle.kill_added.connect(self._on_kill_added)

        # 状态机回调
        self._sm.on_transition(self._on_state_transition)

        # 窗口关闭按钮行为
        self._view.closeEvent = lambda e: (e.ignore(), self._wm.hide())

        # 托盘
        self._wm.setup_tray()

    def _setup_scene(self) -> None:
        s = self._scene
        w = self._cfg.game_width
        h = self._cfg.game_height
        gh = self._cfg.ground_height
        cs = self._cfg.character_size

        s.setSceneRect(0, 0, w, h)
        s.setBackgroundBrush(QBrush(QColor("#87CEEB")))  # 天空蓝

        # 地面
        ground = GroundGraphicsItem(w, h, gh)
        s.addItem(ground)

        # 角色
        ground_y = h - gh
        char_y = ground_y - cs // 2
        self._battle.set_character_y(char_y)
        self._char_item = CharacterGraphicsItem(cs)
        self._char_item.setPos(self._cfg.character_start_x, char_y)
        self._char_item.setZValue(20)
        s.addItem(self._char_item)

        # 敌人placeholder
        self._enemy_item: EnemyGraphicsItem | None = None

    # ---- 事件处理 ----

    def _on_key_count(self) -> None:
        if self._sm.is_battle:
            self._battle.on_key_press()

    def _on_battle_toggle(self) -> None:
        if self._sm.is_battle:
            self._sm.exit_battle(reason="快捷键切换")
            self._battle.deactivate()
        else:
            if self._sm.can_enter_battle():
                self._sm.enter_battle(reason="快捷键切换")
                self._battle.activate()
                self._wm.show()

    def _on_quit(self) -> None:
        self._kb.stop()
        self._cfg.save()
        self._sm.persistence.save()
        self._app.quit()

    def _on_count_changed(self, count: int) -> None:
        pass  # UI 可订阅

    def _on_phase_changed(self, phase: str) -> None:
        pass

    def _on_enemy_spawned(self, data: dict) -> None:
        if self._enemy_item is None:
            self._enemy_item = EnemyGraphicsItem(self._cfg.enemy_size)
            self._scene.addItem(self._enemy_item)
        self._enemy_item.update_from_enemy(
            data["x"], data["y"], data["scale"], data["opacity"]
        )

    def _on_enemy_hit(self, damage: int, ex: float, ey: float) -> None:
        # 更新敌人缩放（抖动效果由battle_engine计算，这里只负责更新图元）
        enemy = self._battle.get_enemy()
        if enemy and self._enemy_item:
            self._enemy_item.update_from_enemy(
                enemy.x, enemy.y, enemy.scale, enemy.opacity
            )

    def _on_enemy_killed(self) -> None:
        pass

    def _on_character_walk(self, x: float) -> None:
        cs = self._cfg.character_size
        # 无用行，已在下面用 ground_y 
        ground_y = self._scene.sceneRect().height() - self._cfg.ground_height
        self._char_item.setPos(x, ground_y - cs // 2)

    def _on_character_return(self) -> None:
        cs = self._cfg.character_size
        ground_y = self._scene.sceneRect().height() - self._cfg.ground_height
        self._char_item.setPos(self._battle.get_character_x(), ground_y - cs // 2)

    def _on_floating_text(self, text: str, color: str, x: float, y: float) -> None:
        item = FloatingTextItem(text, color, x, y)
        self._scene.addItem(item)
        item.animate()

    def _on_explosion(self, x: float, y: float) -> None:
        colors = ["#FF4444", "#FF6666", "#FFAAAA", "#CC0000"]
        for _ in range(10):
            angle = random.uniform(0, 2 * 3.14159)
            speed = random.uniform(0.05, 0.2)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 0.1
            color = random.choice(colors)
            p = ExplosionParticle(x, y, vx, vy, color)
            self._scene.addItem(p)
            p.animate()

    def _on_kill_added(self, total: int) -> None:
        pass

    def _on_state_transition(self, t) -> None:
        pass

    def run(self) -> int:
        # 初始显示窗口（淡入）
        self._wm.show()
        return self._wm.exec()


if __name__ == "__main__":
    import math
    import random
    app = TapPetApp()
    sys.exit(app.run())
