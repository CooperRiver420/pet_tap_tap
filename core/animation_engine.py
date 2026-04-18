"""
AnimationEngine - 代码驱动动画引擎
负责待机/行走/攻击/胜利等动画的QPainter驱动

动画规格（来自SPEC.md）：
- 待机：透明度/位置微小变化
- 行走：QPainter位移+缩放，0.3秒
- 攻击：QPainter缩放0.9x→1.1x快速抖动，0.2秒
- 胜利：QPainter缩放1.2x + 透明度，0.5秒
- 返回起点：QPainter插值位移
"""
from enum import Enum, auto
from typing import Callable, Optional
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QElapsedTimer
from PyQt6.QtGui import QPainter, QImage


class AnimationState(Enum):
    """动画状态枚举"""
    IDLE = auto()        # 待机
    WALK = auto()       # 行走
    ATTACK = auto()     # 攻击
    VICTORY = auto()    # 胜利
    HURT = auto()       # 受击
    RETURN = auto()     # 返回起点


class AnimationParams:
    """动画参数数据类"""
    
    def __init__(self):
        self.scale = 1.0          # 缩放
        self.offset_x = 0.0        # X偏移
        self.offset_y = 0.0       # Y偏移
        self.opacity = 1.0        # 透明度
        self.shake_x = 0.0        # 抖动X
        self.shake_y = 0.0        # 抖动Y


class AnimationEngine(QObject):
    """
    代码驱动动画引擎
    C-03: 代码驱动动画引擎（待机/行走/攻击/胜利动画）
    """
    
    # 动画时长配置（毫秒）
    DURATION_IDLE = 2000      # 待机循环2秒
    DURATION_WALK = 300        # 行走0.3秒
    DURATION_ATTACK = 200      # 攻击0.2秒
    DURATION_VICTORY = 500     # 胜利0.5秒
    DURATION_HURT = 150        # 受击抖动0.15秒
    DURATION_RETURN = 400      # 返回0.4秒
    
    # 动画参数配置
    IDLE_SCALE_MIN = 0.95
    IDLE_SCALE_MAX = 1.0
    IDLE_OFFSET_Y = 2         # 待机上下浮动2px
    
    WALK_DISTANCE_MIN = 60    # 行走距离60-80px
    WALK_DISTANCE_MAX = 80
    WALK_SCALE = 0.9          # 行走时缩小一点
    
    ATTACK_SCALE_MIN = 0.9    # 攻击抖动0.9x→1.1x
    ATTACK_SCALE_MAX = 1.1
    ATTACK_SHAKE = 3          # 攻击抖动3px
    
    VICTORY_SCALE = 1.2       # 胜利放大1.2x
    VICTORY_OPACITY = 0.8     # 胜利透明度
    
    RETURN_EASE = 0.15        # 返回缓动系数
    
    finished = pyqtSignal()   # 动画完成信号
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self._state = AnimationState.IDLE
        self._params = AnimationParams()
        self._target_params = AnimationParams()
        
        self._elapsed = QElapsedTimer()
        self._duration = self.DURATION_IDLE
        self._progress = 0.0
        
        self._on_complete: Optional[Callable] = None
        
        # 待机动画相位
        self._idle_phase = 0.0
        
        # 行走方向
        self._walk_direction = 1.0  # 1.0 = 向右
        self._walk_distance = 70   # 本次行走距离
    
    def set_state(self, state: AnimationState, on_complete: Optional[Callable] = None):
        """设置动画状态"""
        self._state = state
        self._on_complete = on_complete
        self._elapsed.restart()
        
        # 根据状态设置时长和目标参数
        if state == AnimationState.IDLE:
            self._duration = self.DURATION_IDLE
            self._idle_phase = 0.0
            self._reset_params()
            self._target_params.scale = 1.0
            self._target_params.opacity = 1.0
            
        elif state == AnimationState.WALK:
            self._duration = self.DURATION_WALK
            self._walk_distance = 70  # 默认70px
            self._reset_params()
            self._target_params.offset_x = self._walk_distance * self._walk_direction
            self._target_params.scale = self.WALK_SCALE
            
        elif state == AnimationState.ATTACK:
            self._duration = self.DURATION_ATTACK
            self._reset_params()
            self._target_params.scale = self.ATTACK_SCALE_MAX
            self._target_params.shake_x = self.ATTACK_SHAKE
            
        elif state == AnimationState.VICTORY:
            self._duration = self.DURATION_VICTORY
            self._reset_params()
            self._target_params.scale = self.VICTORY_SCALE
            self._target_params.opacity = self.VICTORY_OPACITY
            
        elif state == AnimationState.HURT:
            self._duration = self.DURATION_HURT
            self._reset_params()
            # 受击抖动：0.8x→1x 重复1次
            self._target_params.scale = 0.8
            
        elif state == AnimationState.RETURN:
            self._duration = self.DURATION_RETURN
            self._reset_params()
            self._target_params.offset_x = -self._walk_distance * self._walk_direction
        
        self._progress = 0.0
    
    def _reset_params(self):
        """重置参数"""
        self._params = AnimationParams()
    
    def set_walk_distance(self, distance: float):
        """设置行走距离"""
        self._walk_distance = distance
    
    def get_walk_distance(self) -> float:
        """获取行走距离"""
        return self._walk_distance
    
    def update(self, delta_ms: float):
        """更新动画（每帧调用）"""
        if self._state == AnimationState.IDLE:
            self._update_idle(delta_ms)
            return
        
        # 更新进度
        self._elapsed.start()
        self._progress = min(1.0, self._progress + delta_ms / self._duration)
        
        # 根据状态更新参数
        if self._state == AnimationState.WALK:
            self._update_walk()
        elif self._state == AnimationState.ATTACK:
            self._update_attack()
        elif self._state == AnimationState.VICTORY:
            self._update_victory()
        elif self._state == AnimationState.HURT:
            self._update_hurt()
        elif self._state == AnimationState.RETURN:
            self._update_return()
        
        # 动画完成
        if self._progress >= 1.0:
            self._on_animation_complete()
    
    def _update_idle(self, delta_ms: float):
        """更新待机动画"""
        self._idle_phase += delta_ms / 1000.0 * 2.0  # 2秒循环
        if self._idle_phase > 3.14159 * 2:
            self._idle_phase -= 3.14159 * 2
        
        # 透明度微变
        self._params.opacity = 0.95 + 0.05 * (1.0 + self._idle_phase)
        if self._params.opacity > 1.0:
            self._params.opacity = 1.0
        
        # 位置微变（呼吸感）
        self._params.offset_y = self.IDLE_OFFSET_Y * (0.5 + 0.5 * self._idle_phase / (3.14159 * 2))
        self._params.scale = self.IDLE_SCALE_MIN + (self.IDLE_SCALE_MAX - self.IDLE_SCALE_MIN) * 0.5
    
    def _update_walk(self):
        """更新行走动画 - 使用缓动函数"""
        t = self._ease_out_quad(self._progress)
        self._params.offset_x = self._target_params.offset_x * t
        self._params.scale = 1.0 - (1.0 - self.WALK_SCALE) * t
    
    def _update_attack(self):
        """更新攻击动画 - 快速抖动"""
        # 攻击：0.9x→1.1x 快速抖动
        if self._progress < 0.5:
            self._params.scale = self.ATTACK_SCALE_MIN + (self.ATTACK_SCALE_MAX - self.ATTACK_SCALE_MIN) * (self._progress * 2)
        else:
            self._params.scale = self.ATTACK_SCALE_MAX - (self.ATTACK_SCALE_MAX - 1.0) * ((self._progress - 0.5) * 2)
        
        # 抖动
        import math
        shake_freq = 30
        self._params.shake_x = self.ATTACK_SHAKE * math.sin(self._progress * shake_freq)
    
    def _update_victory(self):
        """更新胜利动画"""
        t = self._ease_out_quad(self._progress)
        self._params.scale = 1.0 + (self.VICTORY_SCALE - 1.0) * t
        self._params.offset_y = -20 * t  # 跳起
        self._params.opacity = 1.0 - (1.0 - self.VICTORY_OPACITY) * t
    
    def _update_hurt(self):
        """更新受击抖动动画 - 0.8x→1x 重复1次"""
        # 在duration内完成 0.8x→1.0x 的一次循环
        cycle = self._progress * 2  # 0→2 表示一个完整循环
        if cycle < 1.0:
            self._params.scale = 0.8 + 0.2 * cycle  # 0.8 → 1.0
        else:
            self._params.scale = 1.0  # 保持1.0
            # 轻微抖动
            import math
            self._params.shake_x = 2 * math.sin(cycle * 10)
    
    def _update_return(self):
        """更新返回动画 - 平滑插值"""
        t = self._ease_in_out_quad(self._progress)
        self._params.offset_x = self._target_params.offset_x * t
    
    def _ease_out_quad(self, t: float) -> float:
        """缓出二次函数"""
        return t * (2 - t)
    
    def _ease_in_out_quad(self, t: float) -> float:
        """缓入缓出二次函数"""
        if t < 0.5:
            return 2 * t * t
        return -1 + (4 - 2 * t) * t
    
    def _on_animation_complete(self):
        """动画完成回调"""
        self._params = AnimationParams()  # 重置
        self._progress = 0.0
        
        if self._on_complete:
            callback = self._on_complete
            self._on_complete = None
            callback()
        
        self.finished.emit()
    
    def get_params(self) -> AnimationParams:
        """获取当前动画参数"""
        return self._params
    
    def get_state(self) -> AnimationState:
        """获取当前状态"""
        return self._state
    
    def is_running(self) -> bool:
        """是否正在播放（不包括待机）"""
        return self._state != AnimationState.IDLE and self._progress < 1.0
    
    def apply_to_painter(self, painter: QPainter, x: float, y: float, 
                        image: Optional[QImage] = None, 
                        target_rect: Optional[QImage] = None):
        """
        将动画参数应用到QPainter
        用于在绘制时应用变换
        """
        params = self._params
        
        # 保存状态
        painter.save()
        
        # 应用变换
        if params.opacity < 1.0:
            painter.setOpacity(params.opacity)
        
        # 位移
        final_x = x + params.offset_x + params.shake_x
        final_y = y + params.offset_y + params.shake_y
        
        # 如果有图片，应用缩放绘制
        if image and not image.isNull():
            img_w = image.width()
            img_h = image.height()
            
            # 应用缩放
            painter.translate(final_x + img_w/2, final_y + img_h/2)
            painter.scale(params.scale, params.scale)
            painter.translate(-img_w/2, -img_h/2)
            
            painter.drawImage(0, 0, image)
        else:
            # 无图片时绘制占位方块
            size = 64
            painter.translate(final_x + size/2, final_y + size/2)
            painter.scale(params.scale, params.scale)
            painter.translate(-size/2, -size/2)
            
            # 绘制占位
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            painter.setBrush(QBrush(QColor(200, 200, 200)))
            painter.drawRect(0, 0, size, size)
        
        painter.restore()


from PyQt6.QtGui import QColor, QPen, QBrush
