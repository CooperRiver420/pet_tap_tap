# -*- coding: utf-8 -*-
"""
W-01~W-04: 窗口系统模块
- W-01: 无边框透明窗口（QGraphicsView + 透明背景）
- W-02: 窗口置顶 + 角落停靠
- W-03: 托盘图标 + 托盘右键菜单
- W-04: 窗口淡入淡出动画
"""

import sys
import math
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QGraphicsView, QGraphicsScene,
    QSystemTrayIcon, QMenu, QGraphicsOpacityEffect
)
from PyQt6.QtCore import (
    Qt, QRect, QPoint, QRectF, QTimer,
    QEasingCurve, QPropertyAnimation, QSize, QByteArray
)
from PyQt6.QtGui import (
    QIcon,
    QPainter, QColor, QBrush, QPen, QScreen,
    QAction, QPixmap, QPainter, QImage
)

from .config import Config


# ---- 托盘图标用简单QPixmap生成器 ----
def _make_tray_icon(size: int = 64) -> QPixmap:
    """生成一个简单的猫咪托盘图标（64x64）"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # 猫头
    painter.setBrush(QBrush(QColor("#FFB347")))
    painter.setPen(QPen(QColor("#CC8800"), 2))
    painter.drawEllipse(8, 8, size - 16, size - 16)
    # 耳朵
    painter.drawPolygon([
        QPoint(8 + 4, 8 + 4),
        QPoint(8 - 4, 8 - 6),
        QPoint(8 + 14, 8 - 4),
    ])
    painter.drawPolygon([
        QPoint(size - 8 - 4, 8 + 4),
        QPoint(size - 8 + 4, 8 - 6),
        QPoint(size - 8 - 14, 8 - 4),
    ])
    # 眼睛
    painter.setBrush(QBrush(QColor("#333333")))
    eye_r = 4
    painter.drawEllipse(20, 28, eye_r, eye_r)
    painter.drawEllipse(size - 20 - eye_r, 28, eye_r, eye_r)
    # 嘴巴
    painter.setPen(QPen(QColor("#CC6600"), 1.5))
    painter.drawLine(size // 2 - 5, 40, size // 2, 45)
    painter.drawLine(size // 2, 45, size // 2 + 5, 40)
    painter.end()
    return pixmap


class PetGraphicsView(QGraphicsView):
    """W-01: 无边框透明窗口主视图"""

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # 透明背景
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 场景
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # 尺寸
        self.resize(config.game_width, config.game_height)
        self.setSceneRect(0, 0, config.game_width, config.game_height)

        # 透明度
        self.setWindowOpacity(config.window_opacity)

        # W-04: 淡入效果
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

    @property
    def scene(self) -> QGraphicsScene:
        return self._scene

    def paintEvent(self, event):
        """确保透明背景"""
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        super().paintEvent(event)

    # W-04: 淡入
    def fade_in(self, duration_ms: int | None = None) -> QPropertyAnimation:
        if duration_ms is None:
            duration_ms = self._config.fade_duration_ms
        anim = QPropertyAnimation(self._opacity_effect, QByteArray(b"opacity"), self)
        anim.setDuration(duration_ms)
        anim.setStartValue(0.0)
        anim.setEndValue(self._config.window_opacity)
        anim.setEasingCurve(QEasingCurve.Type.InCurve)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        return anim

    # W-04: 淡出
    def fade_out(self, duration_ms: int | None = None) -> QPropertyAnimation:
        if duration_ms is None:
            duration_ms = self._config.fade_duration_ms
        anim = QPropertyAnimation(self._opacity_effect, QByteArray(b"opacity"), self)
        anim.setDuration(duration_ms)
        anim.setStartValue(self._opacity_effect.opacity())
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCurve)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        return anim


class TrayManager:
    """W-03: 托盘图标 + 托盘右键菜单"""

    def __init__(self, icon_pixmap: QPixmap | None = None):
        if icon_pixmap is None:
            icon_pixmap = _make_tray_icon()
        self._icon_pixmap = icon_pixmap
        self._tray: QSystemTrayIcon | None = None
        self._app: QApplication | None = None
        self._menu: QMenu | None = None
        self._callbacks: dict[str, list] = {
            "show": [],
            "quit": [],
            "toggle_battle": [],
        }

    def setup(self, app: QApplication) -> None:
        self._app = app
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = QIcon(self._icon_pixmap)
        self._tray = QSystemTrayIcon(icon, app)
        self._build_menu()
        self._tray.setContextMenu(self._menu)
        self._tray.setToolTip("TapPet 🐾")
        self._tray.activated.connect(self._on_activated)
        self._tray.show()

    def _build_menu(self) -> None:
        self._menu = QMenu()
        self._menu.addAction("显示窗口", self._emit_show)
        self._menu.addAction("切换战斗", self._emit_toggle_battle)
        self._menu.addSeparator()
        self._menu.addAction("退出", self._emit_quit)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._emit_show()

    def _emit_show(self) -> None:
        for cb in self._callbacks["show"]:
            cb()

    def _emit_toggle_battle(self) -> None:
        for cb in self._callbacks["toggle_battle"]:
            cb()

    def _emit_quit(self) -> None:
        for cb in self._callbacks["quit"]:
            cb()

    def on_show(self, cb) -> None:
        self._callbacks["show"].append(cb)

    def on_quit(self, cb) -> None:
        self._callbacks["quit"].append(cb)

    def on_toggle_battle(self, cb) -> None:
        self._callbacks["toggle_battle"].append(cb)


def dock_to_corner(window: QGraphicsView, corner: str = "bottom-right") -> None:
    """W-02: 窗口角落停靠（默认右下角）"""
    if window is None:
        return
    screen: QScreen | None = window.screen()
    if screen is None:
        screens = QApplication.primaryScreen()
        if screens:
            screen = screens
    if screen is None:
        return
    sr = screen.availableGeometry()
    margin = 20
    if corner == "bottom-right":
        x = sr.right() - window.width() - margin
        y = sr.bottom() - window.height() - margin
    elif corner == "top-right":
        x = sr.right() - window.width() - margin
        y = sr.top() + margin
    elif corner == "bottom-left":
        x = sr.left() + margin
        y = sr.bottom() - window.height() - margin
    else:  # top-left
        x = sr.left() + margin
        y = sr.top() + margin
    window.move(x, y)


class WindowManager:
    """窗口系统统一管理器"""

    def __init__(self, config: Config):
        self._config = config
        self._app: QApplication | None = None
        self._view: PetGraphicsView | None = None
        self._tray: TrayManager | None = None
        self._battle_callbacks: list = []
        self._quit_callbacks: list = []
        self._show_callbacks: list = []
        self._visible = False

    def init_app(self) -> QApplication:
        QApplication.setQuitOnLastWindowClosed(False)
        self._app = QApplication([])
        self._app.setQuitOnLastWindowClosed(False)
        return self._app

    def create_window(self) -> PetGraphicsView:
        self._view = PetGraphicsView(self._config)
        dock_to_corner(self._view, "bottom-right")
        return self._view

    def setup_tray(self) -> TrayManager:
        if self._app is None:
            raise RuntimeError("init_app must be called first")
        self._tray = TrayManager()
        self._tray.setup(self._app)
        self._tray.on_show(lambda: self.show())
        self._tray.on_toggle_battle(lambda: self._emit_battle_toggle())
        self._tray.on_quit(lambda: self._emit_quit())
        return self._tray

    def show(self) -> None:
        if self._view is None:
            return
        if not self._visible:
            self._view.show()
            self._view.fade_in()
            self._visible = True
            self._emit_show()

    def hide(self) -> None:
        if self._view is None:
            return
        if self._visible:
            self._view.fade_out()
            # 等待动画结束后再hide
            QTimer.singleShot(self._config.fade_duration_ms + 50, self._view.hide)
            self._visible = False

    def toggle_visible(self) -> None:
        if self._visible:
            self.hide()
        else:
            self.show()

    @property
    def view(self) -> PetGraphicsView | None:
        return self._view

    @property
    def tray(self) -> TrayManager | None:
        return self._tray

    @property
    def is_visible(self) -> bool:
        return self._visible

    def on_battle_toggle(self, cb) -> None:
        self._battle_callbacks.append(cb)

    def on_quit(self, cb) -> None:
        self._quit_callbacks.append(cb)

    def on_show(self, cb) -> None:
        self._show_callbacks.append(cb)

    def _emit_battle_toggle(self) -> None:
        for cb in self._battle_callbacks:
            cb()

    def _emit_quit(self) -> None:
        for cb in self._quit_callbacks:
            cb()
        if self._app:
            self._app.quit()

    def _emit_show(self) -> None:
        for cb in self._show_callbacks:
            cb()

    def exec(self) -> int:
        if self._app is None:
            raise RuntimeError("init_app must be called first")
        return self._app.exec()
