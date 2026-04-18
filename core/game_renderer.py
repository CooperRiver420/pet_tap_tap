"""
GameRenderer - 游戏主渲染器
整合角色、敌人、特效的完整游戏画面渲染
基于QGraphicsView + QPainter

布局参数（来自SPEC.md）：
- 游戏区域：480x320px
- 地面高度：距底部40px
- 角色尺寸：64x64px（渲染时缩放）
- 敌人尺寸：48x48px
- 角色初始X：60px
- 背景卷轴速度：20px/次
"""
from typing import Optional, Dict, List
from PyQt6.QtCore import QObject, Qt, QRectF, QPointF, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QGradient, QLinearGradient,
    QImage, QPainterPath
)
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem


class BackgroundLayer:
    """
    背景层（远景层）
    V-06: 背景层卷轴移动（击杀后云层移动20px）
    """
    
    def __init__(self):
        self._cloud_offset = 0.0
        self._scroll_speed = 20.0  # 20px/次
        self._cloud_opacity = 0.4  # 透明度30-50%
        self._ground_color = QColor(139, 90, 43)  # 棕色地面
        self._sky_color_top = QColor(135, 206, 235)  # 天蓝色
        self._sky_color_bottom = QColor(255, 255, 224)  # 浅黄色
    
    def scroll(self):
        """卷轴滚动"""
        self._cloud_offset += self._scroll_speed
        if self._cloud_offset > 480:  # 超过游戏区宽度则重置
            self._cloud_offset = 0.0
    
    def reset_offset(self):
        """重置偏移"""
        self._cloud_offset = 0.0
    
    def draw(self, painter: QPainter, width: int, height: int, ground_y: int):
        """绘制背景"""
        painter.save()
        
        # 绘制天空渐变
        gradient = QLinearGradient(0, 0, 0, ground_y)
        gradient.setColorAt(0, self._sky_color_top)
        gradient.setColorAt(1, self._sky_color_bottom)
        painter.fillRect(0, 0, width, ground_y, gradient)
        
        # 绘制云层（简单圆形）
        painter.setOpacity(self._cloud_opacity)
        self._draw_clouds(painter, width, ground_y)
        
        # 绘制地面
        painter.setOpacity(1.0)
        painter.fillRect(0, ground_y, width, height - ground_y, self._ground_color)
        
        # 地面细节线
        pen = QPen(self._ground_color.darker(120), 2)
        painter.setPen(pen)
        painter.drawLine(0, ground_y, width, ground_y)
        
        painter.restore()
    
    def _draw_clouds(self, painter: QPainter, width: int, height: int):
        """绘制云层（简化版）"""
        cloud_y = height // 3
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
            x = (base_x + offset) % (width + 100) - 50
            # 绘制云朵（多个圆形组成）
            painter.drawEllipse(int(x), int(y), radius, radius // 2)
            painter.drawEllipse(int(x + radius//3), int(y - radius//4), radius//2, radius//3)


class GameRenderer(QGraphicsView):
    """
    游戏主渲染器
    使用QGraphicsView进行高效渲染
    """
    
    # 布局参数常量
    GAME_WIDTH = 480
    GAME_HEIGHT = 320
    GROUND_MARGIN = 40  # 距底部40px
    CHARACTER_SIZE = 64
    ENEMY_SIZE = 48
    CHARACTER_START_X = 60
    CHARACTER_START_Y = GAME_HEIGHT - GROUND_MARGIN - CHARACTER_SIZE
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 创建场景
        self._scene = QGraphicsScene(0, 0, self.GAME_WIDTH, self.GAME_HEIGHT)
        self.setScene(self._scene)
        
        # 设置视图参数
        self.setFixedSize(self.GAME_WIDTH, self.GAME_HEIGHT)
        self.setSceneRect(0, 0, self.GAME_WIDTH, self.GAME_HEIGHT)
        self.setBackgroundBrush(QBrush(QColor(255, 255, 255, 0)))  # 透明
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # 背景层
        self._background = BackgroundLayer()
        
        # 游戏数据
        self._character_x = self.CHARACTER_START_X
        self._character_y = self.CHARACTER_START_Y
        self._character_scale = 1.0
        
        # 地面Y坐标
        self._ground_y = self.GAME_HEIGHT - self.GROUND_MARGIN
        
        # 敌人数据
        self._enemy_x = 0.0
        self._enemy_y = self.GROUND_Y - self.ENEMY_SIZE
        self._enemy_scale = 1.0
        self._enemy_opacity = 1.0
        self._enemy_visible = False
        
        # 动画相关
        self._character_shake = 0.0
        self._enemy_shake = 0.0
    
    @property
    def ground_y(self) -> int:
        """获取地面Y坐标"""
        return self._ground_y
    
    @property
    def character_start_x(self) -> int:
        return self.CHARACTER_START_X
    
    def set_character_position(self, x: float, y: float):
        """设置角色位置"""
        self._character_x = x
        self._character_y = y
    
    def set_character_scale(self, scale: float):
        """设置角色缩放"""
        self._character_scale = scale
    
    def set_character_shake(self, shake: float):
        """设置角色抖动"""
        self._character_shake = shake
    
    def set_enemy_visible(self, visible: bool):
        """设置敌人可见"""
        self._enemy_visible = visible
    
    def set_enemy_position(self, x: float, y: float):
        """设置敌人位置"""
        self._enemy_x = x
        self._enemy_y = y
    
    def set_enemy_scale(self, scale: float):
        """设置敌人缩放"""
        self._enemy_scale = scale
    
    def set_enemy_opacity(self, opacity: float):
        """设置敌人透明度"""
        self._enemy_opacity = opacity
    
    def set_enemy_shake(self, shake: float):
        """设置敌人抖动"""
        self._enemy_shake = shake
    
    def scroll_background(self):
        """卷轴滚动"""
        self._background.scroll()
    
    def reset_background(self):
        """重置背景偏移"""
        self._background.reset_offset()
    
    def draw_background(self, painter: QPainter):
        """绘制背景层"""
        self._background.draw(painter, self.GAME_WIDTH, self.GAME_HEIGHT, self._ground_y)
    
    def draw_character_placeholder(self, painter: QPainter, color: QColor = None):
        """绘制角色占位图形"""
        if color is None:
            color = QColor(100, 150, 255)
        
        size = self.CHARACTER_SIZE
        x = self._character_x
        y = self._character_y
        
        painter.save()
        
        # 应用缩放
        painter.translate(x + size/2, y + size/2)
        painter.scale(self._character_scale, self._character_scale)
        painter.translate(-size/2, -size/2)
        
        # 应用抖动
        if self._character_shake != 0:
            import math
            shake_x = self._character_shake * math.sin(self._character_shake * 10)
            painter.translate(shake_x, 0)
        
        # 绘制圆形角色
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
    
    def draw_enemy_placeholder(self, painter: QPainter, color: QColor = None):
        """绘制敌人占位图形（红色气球）"""
        if not self._enemy_visible:
            return
        
        if color is None:
            color = QColor(255, 68, 68)  # 红色
        
        size = self.ENEMY_SIZE
        x = self._enemy_x
        y = self._enemy_y
        
        painter.save()
        
        # 应用透明度
        painter.setOpacity(self._enemy_opacity)
        
        # 应用缩放
        painter.translate(x + size/2, y + size/2)
        painter.scale(self._enemy_scale, self._enemy_scale)
        painter.translate(-size/2, -size/2)
        
        # 应用抖动
        if self._enemy_shake != 0:
            import math
            shake_x = self._enemy_shake * math.sin(self._enemy_shake * 10)
            painter.translate(shake_x, 0)
        
        # 绘制气球（圆形 + 细线）
        pen = QPen(color.darker(150), 2)
        painter.setPen(pen)
        brush = QBrush(color.lighter(120))
        painter.setBrush(brush)
        painter.drawEllipse(0, 0, size, size)
        
        # 气球高光
        highlight = QColor(255, 255, 255, 100)
        painter.setBrush(QBrush(highlight))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(size//4, size//4, size//4, size//4)
        
        # 气球拴绳
        painter.setPen(QPen(color.darker(150), 1))
        painter.drawLine(size//2, size, size//2, size + 8)
        
        painter.restore()
    
    def draw_ground_line(self, painter: QPainter):
        """绘制地面线"""
        pen = QPen(QColor(101, 67, 33), 3)  # 深棕色
        painter.setPen(pen)
        painter.drawLine(0, self._ground_y, self.GAME_WIDTH, self._ground_y)


class UIHud:
    """
    UI组件 - 顶部状态栏和底部进度条
    V-04: 顶部状态栏（击杀数🏆/生命值❤️/计数进度）
    V-05: 底部进度条（0/10 → 10/10）
    """
    
    def __init__(self):
        # 状态数据
        self._kill_count = 0
        self._health = 5
        self._max_health = 5
        self._count = 0
        self._max_count = 10
        
        # 字体
        from PyQt6.QtGui import QFont
        self._font = QFont("Arial", 14)
        self._font.setBold(True)
        self._small_font = QFont("Arial", 12)
    
    def set_kill_count(self, count: int):
        """设置击杀数"""
        self._kill_count = count
    
    def set_health(self, health: int, max_health: int = 5):
        """设置生命值"""
        self._health = health
        self._max_health = max_health
    
    def set_count(self, count: int):
        """设置计数"""
        self._count = count
    
    def set_max_count(self, max_count: int):
        """设置最大计数"""
        self._max_count = max_count
    
    def draw_top_status_bar(self, painter: QPainter, width: int):
        """
        绘制顶部状态栏
        V-04: 击杀数🏆 | 生命值❤️ | 计数进度
        """
        painter.save()
        painter.setFont(self._font)
        
        y = 10
        x = 10
        
        # 击杀数 🏆
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        kill_text = f"🏆 {self._kill_count}"
        painter.drawText(x, y + 20, kill_text)
        
        # 生命值 ❤️
        x += 100
        health_text = f"❤️ {self._health}/{self._max_health}"
        painter.setPen(QPen(QColor(255, 100, 100), 1))
        painter.drawText(x, y + 20, health_text)
        
        # 计数进度
        x = width - 120
        count_text = f"{self._count}/{self._max_count}"
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawText(x, y + 20, count_text)
        
        painter.restore()
    
    def draw_bottom_progress_bar(self, painter: QPainter, width: int, height: int):
        """
        绘制底部进度条
        V-05: 0/10 → 10/10
        """
        painter.save()
        
        bar_height = 6
        bar_y = height - 20
        bar_width = width - 40
        bar_x = 20
        
        # 背景条（深灰）
        bg_color = QColor(68, 68, 68)
        painter.fillRect(bar_x, bar_y, bar_width, bar_height, bg_color)
        
        # 进度条（绿色）
        progress = self._count / self._max_count if self._max_count > 0 else 0
        fill_width = int(bar_width * progress)
        
        if fill_width > 0:
            gradient = QLinearGradient(bar_x, 0, bar_x + fill_width, 0)
            gradient.setColorAt(0, QColor(68, 255, 68))
            gradient.setColorAt(1, QColor(34, 200, 34))
            painter.fillRect(bar_x, bar_y, fill_width, bar_height, gradient)
        
        # 圆角
        from PyQt6.QtCore import QRectF
        rect = QRectF(bar_x, bar_y, bar_width, bar_height)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(68, 68, 68)))
        painter.drawRoundedRect(rect, 3, 3)
        
        # 重新绘制进度
        if fill_width > 0:
            rect = QRectF(bar_x, bar_y, fill_width, bar_height)
            painter.fillRect(rect, QColor(68, 255, 68))
        
        # 计数文字
        painter.setFont(self._small_font)
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        text = f"{self._count}/{self._max_count}"
        text_width = painter.fontMetrics().horizontalAdvance(text)
        painter.drawText(width - 20 - text_width, bar_y + bar_height + 16, text)
        
        painter.restore()
    
    def update(self, delta_ms: float):
        """更新UI（如果需要动态效果）"""
        pass
