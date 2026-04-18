"""
视觉特效模块 - TapPet Phase-1
V-01: 伤害飘字（-1，红色，向上飘动消失）
V-02: 击杀飘字（击破！，金色，放大消失）
V-03: 爆炸粒子（8-12个碎片，飞散+下落）
"""
from typing import List, Optional
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QImage, QPainterPath
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsTextItem, QGraphicsWidget


# ==================== 伤害飘字 ====================

class DamageText(QObject):
    """
    伤害飘字特效
    V-01: "-1"，红色，向上飘动消失
    """
    
    finished = pyqtSignal()
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self._text = "-1"
        self._color = QColor(255, 68, 68)  # 红色 #FF4444
        self._x = 0.0
        self._y = 0.0
        
        self._opacity = 1.0
        self._offset_y = 0.0
        self._progress = 0.0
        
        self._duration = 500  # 0.5秒
        self._speed = 40.0    # 向上速度 40px/s
        
        self._font = QFont("Arial", 16)
        self._font.setBold(True)
    
    def set_position(self, x: float, y: float):
        """设置位置"""
        self._x = x
        self._y = y
    
    def update(self, delta_ms: float):
        """更新特效"""
        self._progress += delta_ms
        t = min(1.0, self._progress / self._duration)
        
        # 向上飘动
        self._offset_y = self._speed * (t)
        
        # 透明度渐隐
        self._opacity = 1.0 - t
    
    def draw(self, painter: QPainter):
        """绘制"""
        if self._opacity <= 0:
            return
        
        painter.save()
        painter.setOpacity(self._opacity)
        
        # 设置字体和颜色
        painter.setFont(self._font)
        painter.setPen(QPen(self._color, 2))
        
        # 绘制文字
        painter.drawText(
            int(self._x),
            int(self._y - self._offset_y),
            self._text
        )
        
        painter.restore()
    
    def is_finished(self) -> bool:
        """是否完成"""
        return self._progress >= self._duration


# ==================== 击杀飘字 ====================

class KillText(QObject):
    """
    击杀飘字特效
    V-02: "击破！"，金色，放大消失
    """
    
    finished = pyqtSignal()
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self._text = "击破！"
        self._color = QColor(255, 215, 0)  # 金色 #FFD700
        self._x = 0.0
        self._y = 0.0
        
        self._opacity = 1.0
        self._scale = 1.0
        self._progress = 0.0
        
        self._duration = 800  # 0.8秒
        self._font = QFont("Arial", 24)
        self._font.setBold(True)
    
    def set_position(self, x: float, y: float):
        """设置位置（游戏区中央偏上）"""
        self._x = x
        self._y = y
    
    def update(self, delta_ms: float):
        """更新特效"""
        self._progress += delta_ms
        t = min(1.0, self._progress / self._duration)
        
        # 放大 1 -> 1.2 -> 1
        if t < 0.3:
            self._scale = 1.0 + 0.2 * (t / 0.3)
        else:
            self._scale = 1.2
        
        # 透明度渐隐
        self._opacity = 1.0 - t
    
    def draw(self, painter: QPainter):
        """绘制"""
        if self._opacity <= 0:
            return
        
        painter.save()
        painter.setOpacity(self._opacity)
        
        # 应用缩放变换
        painter.translate(self._x, self._y)
        painter.scale(self._scale, self._scale)
        painter.translate(-self._x, -self._y)
        
        # 设置字体和颜色
        painter.setFont(self._font)
        painter.setPen(QPen(self._color, 2))
        
        # 绘制文字（居中）
        text_width = painter.fontMetrics().horizontalAdvance(self._text)
        painter.drawText(
            int(self._x - text_width / 2),
            int(self._y),
            self._text
        )
        
        painter.restore()
    
    def is_finished(self) -> bool:
        """是否完成"""
        return self._progress >= self._duration


# ==================== 爆炸粒子 ====================

class Particle:
    """单个粒子数据类"""
    
    def __init__(self, x: float, y: float, vx: float, vy: float, 
                 color: QColor, size: float):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.opacity = 1.0
        self.gravity = 200.0  # 重力加速度 px/s²


class ExplosionParticles(QObject):
    """
    爆炸粒子特效
    V-03: 8-12个碎片，飞散+下落
    """
    
    finished = pyqtSignal()
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self._particles: List[Particle] = []
        self._progress = 0.0
        self._duration = 300  # 0.3秒
        self._center_x = 0.0
        self._center_y = 0.0
    
    def spawn(self, x: float, y: float, count: int = 10):
        """
        生成粒子
        count: 8-12个碎片
        """
        self._center_x = x
        self._center_y = y
        self._particles.clear()
        self._progress = 0.0
        
        # 粒子颜色（红色系）
        colors = [
            QColor(255, 68, 68),   # #FF4444
            QColor(255, 102, 102), # #FF6666
            QColor(255, 136, 136), # #FF8888
        ]
        
        for i in range(count):
            import random
            import math
            
            # 随机方向
            angle = random.uniform(0, 2 * 3.14159)
            speed = random.uniform(80, 180)  # 速度 80-180 px/s
            
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle) - 100  # 向上偏移
            
            color = random.choice(colors)
            size = random.uniform(3, 7)  # 大小 3-7px
            
            particle = Particle(x, y, vx, vy, color, size)
            self._particles.append(particle)
    
    def update(self, delta_ms: float):
        """更新粒子"""
        if not self._particles:
            return
        
        self._progress += delta_ms
        dt = delta_ms / 1000.0  # 转换为秒
        
        for p in self._particles:
            # 应用速度
            p.x += p.vx * dt
            p.y += p.vy * dt
            
            # 应用重力
            p.vy += p.gravity * dt
            
            # 透明度渐隐
            t = min(1.0, self._progress / self._duration)
            p.opacity = 1.0 - t
    
    def draw(self, painter: QPainter):
        """绘制粒子"""
        if not self._particles:
            return
        
        painter.save()
        
        for p in self._particles:
            painter.setOpacity(p.opacity)
            painter.setBrush(QBrush(p.color))
            painter.setPen(QPen(p.color.darker(120), 1))
            
            # 绘制圆形碎片
            painter.drawEllipse(
                int(p.x - p.size / 2),
                int(p.y - p.size / 2),
                int(p.size),
                int(p.size)
            )
        
        painter.restore()
    
    def is_finished(self) -> bool:
        """是否完成"""
        return self._progress >= self._duration and not self._particles
    
    def clear(self):
        """清除粒子"""
        self._particles.clear()


# ==================== 特效管理器 ====================

class EffectsManager(QObject):
    """
    特效管理器
    统一管理所有视觉特效
    """
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self._damage_texts: List[DamageText] = []
        self._kill_texts: List[KillText] = []
        self._explosions: List[ExplosionParticles] = []
    
    def spawn_damage_text(self, x: float, y: float) -> DamageText:
        """生成伤害飘字"""
        text = DamageText()
        text.set_position(x, y)
        self._damage_texts.append(text)
        return text
    
    def spawn_kill_text(self, x: float, y: float) -> KillText:
        """生成击杀飘字"""
        text = KillText()
        text.set_position(x, y)
        self._kill_texts.append(text)
        return text
    
    def spawn_explosion(self, x: float, y: float, count: int = 10) -> ExplosionParticles:
        """生成爆炸粒子"""
        explosion = ExplosionParticles()
        explosion.spawn(x, y, count)
        self._explosions.append(explosion)
        return explosion
    
    def update(self, delta_ms: float):
        """更新所有特效"""
        # 更新伤害飘字
        for text in self._damage_texts:
            text.update(delta_ms)
        self._damage_texts = [t for t in self._damage_texts if not t.is_finished()]
        
        # 更新击杀飘字
        for text in self._kill_texts:
            text.update(delta_ms)
        self._kill_texts = [t for t in self._kill_texts if not t.is_finished()]
        
        # 更新爆炸粒子
        for explosion in self._explosions:
            explosion.update(delta_ms)
        self._explosions = [e for e in self._explosions if not e.is_finished()]
    
    def draw(self, painter: QPainter):
        """绘制所有特效"""
        for text in self._damage_texts:
            text.draw(painter)
        
        for text in self._kill_texts:
            text.draw(painter)
        
        for explosion in self._explosions:
            explosion.draw(painter)
    
    def clear(self):
        """清除所有特效"""
        self._damage_texts.clear()
        self._kill_texts.clear()
        self._explosions.clear()
