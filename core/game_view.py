"""
GameView - 游戏主视图
整合所有组件的完整游戏画面

布局参数（来自SPEC.md）：
- 游戏区域：480x320px
- 地面高度：距底部40px
- 角色尺寸：64x64px（渲染时缩放）
- 敌人尺寸：48x48px
- 角色初始X：60px
"""
from typing import Optional, List
from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal, QElapsedTimer
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QImage
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QLabel
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from .animation_engine import AnimationEngine, AnimationState
from .battle_components import Enemy, CharacterBattleController, ExplosionEffect
from utils.effects import EffectsManager, DamageText, KillText, ExplosionParticles


class GameView(QGraphicsView):
    """
    游戏主视图
    整合角色、敌人、特效的完整游戏画面渲染
    基于QGraphicsView + QPainter
    """
    
    # 布局参数常量
    GAME_WIDTH = 480
    GAME_HEIGHT = 320
    GROUND_MARGIN = 40
    CHARACTER_SIZE = 64
    ENEMY_SIZE = 48
    CHARACTER_START_X = 60
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        # 创建场景
        self._scene = QGraphicsScene(0, 0, self.GAME_WIDTH, self.GAME_HEIGHT)
        self.setScene(self._scene)
        
        # 设置视图参数
        self.setFixedSize(self.GAME_WIDTH, self.GAME_HEIGHT)
        self.setSceneRect(0, 0, self.GAME_WIDTH, self.GAME_HEIGHT)
        self.setBackgroundBrush(QBrush(QColor(255, 255, 255, 0)))
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 地面Y坐标
        self._ground_y = self.GAME_HEIGHT - self.GROUND_MARGIN
        self._character_base_y = self._ground_y - self.CHARACTER_SIZE
        self._enemy_base_y = self._ground_y - self.ENEMY_SIZE
        
        # 角色控制器
        self._character = CharacterBattleController(self.CHARACTER_START_X, self._character_base_y)
        
        # 敌人
        self._enemy = Enemy()
        self._enemy.size = self.ENEMY_SIZE
        self._enemy.y = self._enemy_base_y
        
        # 动画引擎
        self._anim_engine = AnimationEngine(self)
        
        # 特效管理器
        self._effects = EffectsManager(self)
        
        # 爆炸效果列表
        self._explosions: List[ExplosionEffect] = []
        
        # 背景卷轴偏移
        self._cloud_offset = 0.0
        
        # UI数据
        self._kill_count = 0
        self._count = 0
        self._max_count = 10
        
        # 定时器用于动画更新
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_update)
        self._timer.start(16)  # ~60fps
        
        self._last_time = QElapsedTimer()
        self._last_time.start()
    
    def _on_update(self):
        """更新所有动画"""
        current_time = QElapsedTimer()
        current_time.start()
        delta_ms = self._last_time.elapsed()
        self._last_time = current_time
        
        # 更新角色控制器
        self._character.update(delta_ms)
        
        # 更新敌人
        self._enemy.update(delta_ms)
        
        # 更新特效
        self._effects.update(delta_ms)
        
        # 更新爆炸效果
        for exp in self._explosions:
            exp.update(delta_ms)
        self._explosions = [e for e in self._explosions if not e.is_finished()]
        
        # 更新UI
        self.update()
    
    def get_ground_y(self) -> int:
        return self._ground_y
    
    def get_character_x(self) -> float:
        return self._character.x
    
    def get_character_y(self) -> float:
        return self._character.y
    
    def set_kill_count(self, count: int):
        self._kill_count = count
    
    def set_count(self, count: int):
        self._count = count
    
    def trigger_walk(self):
        """触发行走"""
        self._character.trigger_walk()
    
    def trigger_attack(self):
        """触发攻击"""
        self._character.trigger_attack()
    
    def trigger_enemy_hit(self) -> bool:
        """
        触发敌人受击
        返回是否击杀
        """
        is_killed = self._enemy.take_damage()
        
        if is_killed:
            # 触发死亡
            self._enemy.visible = False
            
            # 触发击杀特效
            self._spawn_kill_effect()
            
            # 触发角色胜利
            self._character.trigger_victory()
            
            # 触发爆炸
            exp = ExplosionEffect(self._enemy.x, self._enemy.y, self.ENEMY_SIZE)
            self._explosions.append(exp)
            
            return True
        else:
            # 触发受击抖动
            self._enemy.trigger_hit_reaction()
            
            # 显示伤害飘字
            self._effects.spawn_damage_text(
                self._enemy.x + self.ENEMY_SIZE / 2,
                self._enemy.y
            )
            
            return False
    
    def _spawn_kill_effect(self):
        """生成击杀特效"""
        # 击杀飘字（游戏区中央偏上）
        self._effects.spawn_kill_text(self.GAME_WIDTH / 2, self.GAME_HEIGHT / 3)
        
        # 击杀数增加
        self._kill_count += 1
    
    def spawn_enemy(self):
        """
        生成敌人
        B-04: 随机X=角色X+120~200px
        """
        char_x = self._character.x
        
        # 计算敌人位置：角色X + 120~200px
        import random
        enemy_x = char_x + random.randint(120, 200)
        
        # 限制在游戏区域内
        enemy_x = min(enemy_x, self.GAME_WIDTH - self.ENEMY_SIZE)
        
        self._enemy.spawn(enemy_x, self._enemy_base_y)
        self._enemy.visible = True
        self._enemy.scale = 0.0
        self._enemy.opacity = 0.0
    
    def trigger_return(self):
        """触发返回起点"""
        self._character.trigger_return()
    
    def reset_character_position(self):
        """重置角色位置"""
        self._character.reset_position()
    
    def reset_count(self):
        """重置计数"""
        self._count = 0
    
    def scroll_background(self):
        """
        卷轴滚动
        V-06: 背景层卷轴移动（击杀后云层移动20px）
        """
        self._cloud_offset += 20
        if self._cloud_offset > 480:
            self._cloud_offset = 0.0
    
    def paintEvent(self, event):
        """绘制游戏画面"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景
        self._draw_background(painter)
        
        # 绘制地面
        self._draw_ground(painter)
        
        # 绘制敌人
        self._enemy.draw(painter)
        
        # 绘制角色
        self._draw_character(painter)
        
        # 绘制爆炸效果
        for exp in self._explosions:
            exp.draw(painter)
        
        # 绘制特效
        self._effects.draw(painter)
        
        # 绘制UI
        self._draw_ui(painter)
    
    def _draw_background(self, painter: QPainter):
        """绘制背景层"""
        # 天空渐变
        gradient = QLinearGradient(0, 0, 0, self._ground_y)
        gradient.setColorAt(0, QColor(135, 206, 235))  # 天蓝色
        gradient.setColorAt(1, QColor(255, 255, 224))  # 浅黄色
        painter.fillRect(0, 0, self.GAME_WIDTH, self._ground_y, gradient)
        
        # 云层
        painter.setOpacity(0.4)
        self._draw_clouds(painter)
        painter.setOpacity(1.0)
    
    def _draw_clouds(self, painter: QPainter):
        """绘制云层"""
        cloud_y = self._ground_y // 3
        cloud_positions = [
            (50, cloud_y, 40),
            (150, cloud_y - 10, 50),
            (280, cloud_y + 5, 45),
            (400, cloud_y - 5, 55),
        ]
        
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setPen(Qt.PenStyle.NoPen)
        
        offset = int(self._cloud_offset) % 480
        
        for base_x, y, radius in cloud_positions:
            x = (base_x + offset) % (self.GAME_WIDTH + 100) - 50
            painter.drawEllipse(int(x), int(y), radius, radius // 2)
            painter.drawEllipse(int(x + radius//3), int(y - radius//4), radius//2, radius//3)
    
    def _draw_ground(self, painter: QPainter):
        """绘制地面"""
        # 地面棕色
        ground_color = QColor(139, 90, 43)
        painter.fillRect(0, self._ground_y, self.GAME_WIDTH, self.GAME_HEIGHT - self._ground_y, ground_color)
        
        # 地面线
        pen = QPen(ground_color.darker(120), 3)
        painter.setPen(pen)
        painter.drawLine(0, self._ground_y, self.GAME_WIDTH, self._ground_y)
    
    def _draw_character(self, painter: QPainter):
        """绘制角色（占位圆形）"""
        x = self._character.x
        y = self._character.y
        scale = self._character.scale
        shake = self._character.shake
        
        size = self.CHARACTER_SIZE
        
        painter.save()
        
        # 应用缩放
        painter.translate(x + size/2, y + size/2)
        painter.scale(scale, scale)
        
        # 应用抖动
        if shake > 0:
            import math
            shake_x = shake * math.sin(shake * 10)
            painter.translate(shake_x, 0)
        
        painter.translate(-size/2, -size/2)
        
        # 绘制圆形角色（蓝色）
        color = QColor(100, 150, 255)
        pen = QPen(color.darker(150), 2)
        painter.setPen(pen)
        brush = QBrush(color)
        painter.setBrush(brush)
        painter.drawEllipse(0, 0, size, size)
        
        # 眼睛
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        eye_size = 6
        painter.drawEllipse(size//4 - eye_size//2, size//3 - eye_size//2, eye_size, eye_size)
        painter.drawEllipse(size*3//4 - eye_size//2, size//3 - eye_size//2, eye_size, eye_size)
        
        painter.restore()
    
    def _draw_ui(self, painter: QPainter):
        """绘制UI"""
        painter.save()
        
        font = QFont("Arial", 14)
        font.setBold(True)
        painter.setFont(font)
        
        # 顶部状态栏
        y = 15
        
        # 击杀数 🏆
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawText(10, y + 18, f"🏆 {self._kill_count}")
        
        # 计数进度
        count_text = f"{self._count}/{self._max_count}"
        painter.drawText(self.GAME_WIDTH - 70, y + 18, count_text)
        
        # 底部进度条
        self._draw_progress_bar(painter)
        
        painter.restore()
    
    def _draw_progress_bar(self, painter: QPainter):
        """绘制底部进度条"""
        bar_height = 6
        bar_y = self.GAME_HEIGHT - 20
        bar_width = self.GAME_WIDTH - 40
        bar_x = 20
        
        # 背景
        painter.fillRect(bar_x, bar_y, bar_width, bar_height, QColor(68, 68, 68))
        
        # 进度
        progress = self._count / self._max_count if self._max_count > 0 else 0
        fill_width = int(bar_width * progress)
        
        if fill_width > 0:
            painter.fillRect(bar_x, bar_y, fill_width, bar_height, QColor(68, 255, 68))
        
        # 圆角
        painter.setPen(Qt.PenStyle.NoPen)
        from PyQt6.QtCore import QRectF
        rect = QRectF(bar_x, bar_y, bar_width, bar_height)
        painter.drawRoundedRect(rect, 3, 3)
        
        # 计数文字
        small_font = QFont("Arial", 12)
        painter.setFont(small_font)
        text = f"{self._count}/{self._max_count}"
        text_w = painter.fontMetrics().horizontalAdvance(text)
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawText(self.GAME_WIDTH - 20 - text_w, bar_y + bar_height + 16, text)


from PyQt6.QtGui import QLinearGradient


class GameWidget(QWidget):
    """
    游戏主控件（整合视图和控制逻辑）
    用于嵌入到主窗口
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self._view = GameView(self)
        layout.addWidget(self._view)
    
    def get_view(self) -> GameView:
        return self._view
