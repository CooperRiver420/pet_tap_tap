"""
BattleComponents - 战斗相关组件
B-03: 角色行走动画（第10次触发行走60-80px）
B-04: 敌人刷新（随机X=角色X+120~200px，代码绘制红色圆形气球）
B-07: 受击抖动反馈（0.8x→1x 重复1次）
B-08: 击杀爆炸（缩放1x→1.3x + 透明度渐隐 + 粒子散射）
"""
from typing import Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QElapsedTimer
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush
import random
import math


class Enemy:
    """
    敌人类
    B-04: 敌人刷新（随机X=角色X+120~200px，代码绘制红色圆形气球）
    """
    
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.health = 1
        self.max_health = 1
        self.visible = False
        
        # 动画参数
        self.scale = 1.0
        self.opacity = 1.0
        self.shake = 0.0
        self.float_offset = 0.0
        self.float_phase = 0.0
        
        # 外观
        self.color = QColor(255, 68, 68)  # 红色
        self.size = 48
    
    def spawn(self, x: float, y: float):
        """刷新敌人"""
        self.x = x
        self.y = y
        self.health = self.max_health
        self.visible = True
        self.scale = 0.0  # 从0开始出现动画
        self.opacity = 0.0
        self.float_offset = 0.0
        self.float_phase = random.uniform(0, math.pi * 2)
    
    def despawn(self):
        """消失"""
        self.visible = False
    
    def take_damage(self):
        """受伤害"""
        self.health -= 1
        return self.health <= 0  # 返回是否死亡
    
    def update(self, delta_ms: float):
        """更新敌人状态"""
        if not self.visible:
            return
        
        # 出现动画
        if self.scale < 1.0:
            self.scale = min(1.0, self.scale + delta_ms / 300)  # 0.3秒出现
            self.opacity = min(1.0, self.opacity + delta_ms / 300)
        
        # 待机浮动
        self.float_phase += delta_ms / 1000.0 * 3.0  # 上下浮动周期
        self.float_offset = 3 * math.sin(self.float_phase)
        
        # 抖动衰减
        if self.shake > 0:
            self.shake *= 0.85
            if self.shake < 0.1:
                self.shake = 0.0
    
    def trigger_hit_reaction(self):
        """
        触发受击反应
        B-07: 受击抖动反馈（0.8x→1x 重复1次）
        """
        self.shake = 5.0  # 初始抖动幅度
    
    def draw(self, painter: QPainter):
        """绘制敌人"""
        if not self.visible:
            return
        
        painter.save()
        
        # 应用透明度
        painter.setOpacity(self.opacity)
        
        # 位置（含浮动）
        draw_x = self.x + self.shake * math.sin(self.shake * 10)
        draw_y = self.y + self.float_offset
        
        # 应用缩放
        painter.translate(draw_x + self.size/2, draw_y + self.size/2)
        painter.scale(self.scale, self.scale)
        painter.translate(-self.size/2, -self.size/2)
        
        # 绘制气球
        pen = QPen(self.color.darker(150), 2)
        painter.setPen(pen)
        brush = QBrush(self.color.lighter(120))
        painter.setBrush(brush)
        painter.drawEllipse(0, 0, self.size, self.size)
        
        # 高光
        highlight = QColor(255, 255, 255, 80)
        painter.setBrush(QBrush(highlight))
        painter.setPen(QPen())
        painter.drawEllipse(self.size//4, self.size//4, self.size//4, self.size//4)
        
        # 拴绳
        painter.setPen(QPen(self.color.darker(150), 1))
        painter.drawLine(self.size//2, self.size, self.size//2, self.size + 8)
        
        # 表情：愤怒
        painter.setBrush(QBrush(QColor(50, 50, 50)))
        eye_size = 4
        # 愤怒的眉毛
        painter.setPen(QPen(QColor(50, 50, 50), 2))
        painter.drawLine(self.size//3 - 4, self.size//3 - 2, self.size//3 + 4, self.size//3 + 2)
        painter.drawLine(self.size*2//3 - 4, self.size//3 + 2, self.size*2//3 + 4, self.size//3 - 2)
        # 眼睛
        painter.setPen(QPen())
        painter.setBrush(QBrush(QColor(50, 50, 50)))
        painter.drawEllipse(self.size//3 - eye_size//2, self.size//3 - eye_size//2, eye_size, eye_size)
        painter.drawEllipse(self.size*2//3 - eye_size//2, self.size//3 - eye_size//2, eye_size, eye_size)
        
        painter.restore()


class CharacterBattleController(QObject):
    """
    角色战斗控制器
    B-03: 角色行走动画（第10次触发行走60-80px）
    B-07: 受击抖动反馈
    """
    
    # 布局参数
    WALK_DISTANCE_MIN = 60
    WALK_DISTANCE_MAX = 80
    WALK_DURATION = 300  # 0.3秒
    
    finished = pyqtSignal()  # 动画完成信号
    
    def __init__(self, start_x: float, start_y: float):
        super().__init__()
        
        self.start_x = start_x
        self.start_y = start_y
        
        # 当前状态
        self.x = start_x
        self.y = start_y
        self.scale = 1.0
        self.shake = 0.0
        
        # 行走参数
        self.walk_distance = random.randint(self.WALK_DISTANCE_MIN, self.WALK_DISTANCE_MAX)
        self._walk_progress = 0.0
        
        # 当前状态
        self.is_walking = False
        self.is_attacking = False
        self.is_hurt = False
        self.is_victory = False
        self.is_returning = False
    
    def trigger_walk(self):
        """触发行走"""
        self.walk_distance = random.randint(self.WALK_DISTANCE_MIN, self.WALK_DISTANCE_MAX)
        self.is_walking = True
        self._walk_progress = 0.0
    
    def trigger_attack(self):
        """触发攻击"""
        self.is_attacking = True
        self._attack_progress = 0.0
    
    def trigger_hurt(self):
        """触发受击"""
        self.is_hurt = True
        self._hurt_progress = 0.0
        self.shake = 8.0
    
    def trigger_victory(self):
        """触发胜利"""
        self.is_victory = True
        self._victory_progress = 0.0
    
    def trigger_return(self):
        """触发返回起点"""
        self.is_returning = True
        self._return_progress = 0.0
        self._return_start_x = self.x
    
    def update(self, delta_ms: float):
        """更新状态"""
        # 抖动衰减
        if self.shake > 0:
            self.shake *= 0.8
            if self.shake < 0.1:
                self.shake = 0.0
        
        # 行走
        if self.is_walking:
            self._update_walk(delta_ms)
        
        # 攻击
        if self.is_attacking:
            self._update_attack(delta_ms)
        
        # 受击
        if self.is_hurt:
            self._update_hurt(delta_ms)
        
        # 胜利
        if self.is_victory:
            self._update_victory(delta_ms)
        
        # 返回
        if self.is_returning:
            self._update_return(delta_ms)
    
    def _update_walk(self, delta_ms: float):
        """更新行走动画"""
        self._walk_progress += delta_ms / self.WALK_DURATION
        
        if self._walk_progress >= 1.0:
            self._walk_progress = 1.0
            self.x = self.start_x + self.walk_distance
            self.is_walking = False
            self.finished.emit()
        else:
            # 缓动
            t = self._ease_out_quad(self._walk_progress)
            self.x = self.start_x + self.walk_distance * t
            self.scale = 1.0 - 0.1 * t  # 行走时缩小一点
    
    def _update_attack(self, delta_ms: float):
        """更新攻击动画"""
        self._attack_progress += delta_ms / 200  # 0.2秒
        
        if self._attack_progress >= 1.0:
            self.is_attacking = False
        else:
            # 0.9x→1.1x快速抖动
            t = self._attack_progress
            if t < 0.5:
                self.scale = 0.9 + 0.4 * t
            else:
                self.scale = 1.1 - 0.2 * (t - 0.5) * 2
    
    def _update_hurt(self, delta_ms: float):
        """更新受击动画"""
        self._hurt_progress += delta_ms / 150  # 0.15秒
        
        if self._hurt_progress >= 1.0:
            self.is_hurt = False
        else:
            # 0.8x→1x 重复1次
            cycle = self._hurt_progress * 2
            if cycle < 1.0:
                self.scale = 0.8 + 0.2 * cycle
            else:
                self.scale = 1.0
    
    def _update_victory(self, delta_ms: float):
        """更新胜利动画"""
        self._victory_progress += delta_ms / 500  # 0.5秒
        
        if self._victory_progress >= 1.0:
            self.is_victory = False
        else:
            t = self._ease_out_quad(self._victory_progress)
            self.scale = 1.0 + 0.2 * t  # 放大到1.2x
    
    def _update_return(self, delta_ms: float):
        """更新返回动画"""
        self._return_progress += delta_ms / 400  # 0.4秒
        
        if self._return_progress >= 1.0:
            self._return_progress = 1.0
            self.x = self.start_x
            self.is_returning = False
            self.scale = 1.0
            self.finished.emit()
        else:
            t = self._ease_in_out_quad(self._return_progress)
            self.x = self._return_start_x + (self.start_x - self._return_start_x) * t
    
    def _ease_out_quad(self, t: float) -> float:
        return t * (2 - t)
    
    def _ease_in_out_quad(self, t: float) -> float:
        if t < 0.5:
            return 2 * t * t
        return -1 + (4 - 2 * t) * t
    
    def reset_position(self):
        """重置位置到起点"""
        self.x = self.start_x
        self.y = self.start_y
        self.scale = 1.0
        self.shake = 0.0


class ExplosionEffect:
    """
    击杀爆炸效果
    B-08: 击杀爆炸（缩放1x→1.3x + 透明度渐隐 + 粒子散射）
    """
    
    def __init__(self, x: float, y: float, size: int = 48):
        self.x = x
        self.y = y
        self.size = size
        
        self.progress = 0.0
        self.duration = 300  # 0.3秒
        self.visible = True
        
        # 粒子数据
        self.particles = []
        self._spawn_particles()
    
    def _spawn_particles(self):
        """生成粒子"""
        colors = [QColor(255, 68, 68), QColor(255, 102, 102), QColor(255, 136, 136)]
        
        for _ in range(10):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(80, 180)
            
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle) - 100
            
            color = random.choice(colors)
            size = random.uniform(3, 7)
            
            self.particles.append({
                'x': self.x + self.size / 2,
                'y': self.y + self.size / 2,
                'vx': vx,
                'vy': vy,
                'color': color,
                'size': size
            })
    
    def update(self, delta_ms: float):
        """更新爆炸效果"""
        if not self.visible:
            return
        
        self.progress += delta_ms / self.duration
        
        # 粒子更新
        dt = delta_ms / 1000.0
        for p in self.particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['vy'] += 200 * dt  # 重力
        
        if self.progress >= 1.0:
            self.visible = False
    
    def draw(self, painter: QPainter):
        """绘制爆炸效果"""
        if not self.visible:
            return
        
        painter.save()
        
        t = self.progress
        
        # 绘制主体缩放+渐隐
        if t < 0.5:
            scale = 1.0 + 0.6 * t * 2  # 1.0 → 1.3
            opacity = 1.0 - t * 2
        else:
            scale = 1.3
            opacity = 0.0
        
        painter.setOpacity(opacity)
        
        # 绘制放大的气球残影
        painter.translate(self.x + self.size/2, self.y + self.size/2)
        painter.scale(scale, scale)
        painter.translate(-self.size/2, -self.size/2)
        
        # 残影
        painter.setBrush(QBrush(QColor(255, 68, 68, 150)))
        painter.setPen(QPen())
        painter.drawEllipse(0, 0, self.size, self.size)
        
        painter.restore()
        
        # 绘制粒子
        painter.save()
        particle_opacity = 1.0 - t
        for p in self.particles:
            painter.setOpacity(particle_opacity)
            painter.setBrush(QBrush(p['color']))
            painter.setPen(QPen(p['color'].darker(120), 1))
            painter.drawEllipse(
                int(p['x'] - p['size']/2),
                int(p['y'] - p['size']/2),
                int(p['size']),
                int(p['size'])
            )
        painter.restore()
    
    def is_finished(self) -> bool:
        return not self.visible
