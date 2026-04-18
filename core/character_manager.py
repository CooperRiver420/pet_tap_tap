"""
CharacterManager - 角色形象管理器
负责5个预设角色的资源加载、缓存、切换
使用代码绘制占位图形等待PNG资源
"""
from typing import Dict, Optional, List
from PyQt6.QtGui import QImage, QPainter, QColor, QPen, QBrush
from PyQt6.QtCore import QSize, Qt
import os


class Character:
    """角色数据类"""
    
    # 角色类型枚举
    TYPE_CAT = "cat"
    TYPE_DOG = "dog"
    TYPE_RABBIT = "rabbit"
    TYPE_FOX = "fox"
    TYPE_ROBOT = "robot"
    
    # 角色名称映射
    CHARACTER_NAMES = {
        TYPE_CAT: "小猫",
        TYPE_DOG: "小狗",
        TYPE_RABBIT: "兔子",
        TYPE_FOX: "狐狸",
        TYPE_ROBOT: "机器人",
    }
    
    def __init__(self, char_id: str, char_type: str):
        self.id = char_id
        self.type = char_type
        self.name = self.CHARACTER_NAMES.get(char_type, char_type)
        self.base_image: Optional[QImage] = None
        self.frames: Dict[str, QImage] = {}
        self.scale = 1.0
    
    @property
    def display_name(self) -> str:
        return self.name


class CharacterManager:
    """
    角色形象管理器
    C-01: 角色资源目录结构（5角色目录）
    C-02: 资源加载（PNG或代码绘制占位）
    C-04: 形象切换接口
    """
    
    # 布局参数（来自SPEC.md）
    RENDER_SIZE = QSize(64, 64)  # 角色渲染尺寸
    BASE_SIZE = QSize(64, 64)    # 基础尺寸
    ASSETS_DIR = "assets/characters"
    
    # 预设角色列表（5个核心角色）
    PRESET_CHARACTERS = [
        {"id": "cat_orange", "type": Character.TYPE_CAT, "color": QColor(255, 165, 0)},      # 橘猫
        {"id": "dog_yellow", "type": Character.TYPE_DOG, "color": QColor(255, 215, 0)},      # 黄狗
        {"id": "rabbit_white", "type": Character.TYPE_RABBIT, "color": QColor(255, 255, 255)}, # 白兔
        {"id": "fox_orange", "type": Character.TYPE_FOX, "color": QColor(255, 140, 0)},      # 橙狐
        {"id": "robot_silver", "type": Character.TYPE_ROBOT, "color": QColor(192, 192, 192)}, # 银机器人
    ]
    
    def __init__(self):
        self._characters: Dict[str, Character] = {}
        self._current: Optional[Character] = None
        self._image_cache: Dict[str, QImage] = {}
        self._load_preset_characters()
    
    def _load_preset_characters(self):
        """加载5个预设角色"""
        for char_info in self.PRESET_CHARACTERS:
            char = Character(char_info["id"], char_info["type"])
            char.color = char_info["color"]
            self._characters[char.id] = char
        
        # 默认选择第一个角色
        if self.PRESET_CHARACTERS:
            first_id = self.PRESET_CHARACTERS[0]["id"]
            self._current = self._characters.get(first_id)
    
    def load_character_image(self, char_id: str) -> Optional[QImage]:
        """
        加载角色图片
        优先从PNG加载，如果不存在则生成占位图形
        C-02: 资源加载
        """
        # 检查缓存
        if char_id in self._image_cache:
            return self._image_cache[char_id]
        
        # 尝试加载PNG
        char = self._characters.get(char_id)
        if not char:
            return None
        
        # 构造PNG路径
        png_path = os.path.join(
            self.ASSETS_DIR,
            char.type,
            f"{char_id}.png"
        )
        
        image = QImage(png_path) if os.path.exists(png_path) else None
        
        # 如果PNG不存在，生成占位图形
        if image is None or image.isNull():
            image = self._generate_placeholder(char)
        
        # 缓存
        if image and not image.isNull():
            self._image_cache[char_id] = image
            char.base_image = image
        
        return image if image and not image.isNull() else None
    
    def _generate_placeholder(self, char: Character) -> QImage:
        """
        生成占位图形
        使用代码绘制简单形状，等待PNG资源到位
        """
        size = self.BASE_SIZE
        image = QImage(size, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = getattr(char, 'color', QColor(200, 200, 200))
        center = size.width() // 2
        radius = size.width() // 2 - 4
        
        if char.type == Character.TYPE_ROBOT:
            # 机器人：方头+天线
            pen = QPen(color.darker(150), 2)
            painter.setPen(pen)
            brush = QBrush(color.lighter(120))
            painter.setBrush(brush)
            
            # 方形头部
            margin = 8
            painter.drawRect(margin, margin, size.width() - margin*2, size.height() - margin*2)
            
            # 天线
            painter.drawLine(center, margin - 6, center, margin)
            painter.drawEllipse(center - 4, margin - 10, 8, 8)
            
            # 眼睛
            eye_color = QColor(0, 255, 0)
            painter.setBrush(QBrush(eye_color))
            painter.drawEllipse(center - 16, center + 4, 8, 8)
            painter.drawEllipse(center + 8, center + 4, 8, 8)
        
        elif char.type == Character.TYPE_RABBIT:
            # 兔子：圆形头+长耳朵
            pen = QPen(color.darker(120), 2)
            painter.setPen(pen)
            brush = QBrush(color)
            painter.setBrush(brush)
            
            # 耳朵
            ear_color = color.lighter(110)
            painter.setBrush(QBrush(ear_color))
            painter.drawEllipse(center - 14, 2, 10, 22)
            painter.drawEllipse(center + 4, 2, 10, 22)
            
            # 头部
            painter.setBrush(QBrush(color))
            painter.drawEllipse(center - radius, center - radius//2, radius*2, radius*2)
            
            # 眼睛
            painter.setBrush(QBrush(QColor(255, 0, 0)))
            painter.drawEllipse(center - 12, center - 4, 6, 6)
            painter.drawEllipse(center + 6, center - 4, 6, 6)
        
        else:
            # 其他角色：圆形头（猫、狗、狐狸）
            pen = QPen(color.darker(120), 2)
            painter.setPen(pen)
            brush = QBrush(color)
            painter.setBrush(brush)
            painter.drawEllipse(center - radius, center - radius//2, radius*2, radius*2)
            
            # 眼睛
            painter.setBrush(QBrush(QColor(0, 0, 0)))
            eye_y = center
            eye_size = 4
            painter.drawEllipse(center - 12, eye_y, eye_size, eye_size)
            painter.drawEllipse(center + 8, eye_y, eye_size, eye_size)
        
        painter.end()
        return image
    
    def get_character(self, char_id: str) -> Optional[Character]:
        """获取角色对象"""
        return self._characters.get(char_id)
    
    def get_current(self) -> Optional[Character]:
        """获取当前角色"""
        return self._current
    
    def switch_character(self, char_id: str) -> bool:
        """
        切换形象
        C-04: 形象切换接口
        """
        if char_id not in self._characters:
            return False
        
        self._current = self._characters[char_id]
        self.load_character_image(char_id)
        return True
    
    def get_all_characters(self) -> List[Character]:
        """获取所有角色列表"""
        return list(self._characters.values())
    
    def get_current_image(self) -> Optional[QImage]:
        """获取当前角色的图片"""
        if self._current:
            return self.load_character_image(self._current.id)
        return None
    
    def preload_all(self):
        """预加载所有角色图片到缓存"""
        for char_id in self._characters:
            self.load_character_image(char_id)


# 单例模式
_manager_instance = None

def get_character_manager() -> CharacterManager:
    """获取角色管理器单例"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = CharacterManager()
    return _manager_instance
