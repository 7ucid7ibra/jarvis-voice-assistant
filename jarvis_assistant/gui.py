from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QScrollArea, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
    QDialog, QFormLayout, QLineEdit, QComboBox, QSlider, QDialogButtonBox,
    QCheckBox, QProgressBar, QTabWidget, QMessageBox, QInputDialog
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, 
    QPoint, QPointF, QRectF, QSize, pyqtProperty, QRect,
    QParallelAnimationGroup
)
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QRadialGradient, 
    QLinearGradient, QFont, QPainterPath, QFontMetrics, QIcon
)
import threading
import os
import psutil
import subprocess
import re
from pathlib import Path
from .config import cfg, COLOR_BACKGROUND, COLOR_ACCENT_CYAN, COLOR_ACCENT_TEAL
from .utils import logger
from .utils import logger

from .ui_framework import (
    GOLDEN_RATIO, BioMechCasing, COLOR_CHASSIS_DARK, COLOR_CHASSIS_MID,
    COLOR_ELECTRIC_BLUE, COLOR_SCREEN_BG, COLOR_PLASMA_CYAN, COLOR_AMBER_ALERT, BreathingAnim, KineticAnim
)

ICON_DIR = Path(__file__).resolve().parent / "assets" / "icons"

def _load_icon(name: str) -> QIcon:
    return QIcon(str(ICON_DIR / name))

class MicButton(QWidget):
    clicked = pyqtSignal()
    
    STATE_IDLE = 0
    STATE_LISTENING = 1
    STATE_THINKING = 2
    STATE_SPEAKING = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(int(110 * GOLDEN_RATIO), int(110 * GOLDEN_RATIO)) 
        self.state = self.STATE_IDLE
        self._glow_factor = 0.0
        self._core_size = 50.0
        self._voice_amplitude = 0.0
        self._voice_amplitude = 0.0
        self._spin_angle = 0.0
        self.is_hovering = False
        
        self.breather = BreathingAnim(self)
        self.breather.value_changed.connect(self._on_breathe)
        
        # Frame timer for active animations
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self._on_frame)
        self.frame_timer.setInterval(16) # ~60 FPS
        
        # State transition handling
        self.current_anim = None

    # -- Properties --
    @pyqtProperty(float)
    def glow_factor(self): return self._glow_factor
    @glow_factor.setter
    def glow_factor(self, val):
        self._glow_factor = val
        self.update()

    @pyqtProperty(float)
    def core_size(self): return self._core_size
    @core_size.setter
    def core_size(self, val):
        self._core_size = val
        self.update()

    @pyqtProperty(float)
    def voice_amplitude(self): return self._voice_amplitude
    @voice_amplitude.setter
    def voice_amplitude(self, val):
        self._voice_amplitude = val
        self.update()
        
    def _on_breathe(self, val):
        if self.state == self.STATE_IDLE:
             self._glow_factor = 0.3 + (val * 0.4) 
             self.update()

    def _on_frame(self):
        if self.state == self.STATE_THINKING:
            self._spin_angle = (self._spin_angle + 5) % 360
            # Pulse glow factor faster
            import math
            import time
            self._glow_factor = (math.sin(time.time() * 10) + 1) / 2
            self.update()
        elif self.state == self.STATE_SPEAKING:
            # Pulse glow like thinking, but in blue (no rotation)
            import math
            import time
            self._glow_factor = (math.sin(time.time() * 10) + 1) / 2
            self.update()

    def set_state(self, state):
        if self.state == state: return
        self.state = state
        
        # Animate transitions
        target_size = 50.0
        if state == self.STATE_LISTENING: 
            target_size = 75.0
            self.frame_timer.stop()
        elif state == self.STATE_THINKING: 
            target_size = 45.0
            self.frame_timer.start()
        elif state == self.STATE_SPEAKING:
            target_size = 55.0
            self._voice_amplitude = 0.0
            self.frame_timer.start()
        else: # IDLE
            self.frame_timer.stop()
            
        anim = KineticAnim(self, b"core_size", duration=600)
        anim.setStartValue(self._core_size)
        anim.setEndValue(target_size)
        anim.start()
        self.current_anim = anim
        self.update()

    def mousePressEvent(self, event):
        self.clicked.emit()

    def enterEvent(self, event):
        self.is_hovering = True
        self.update()

    def leaveEvent(self, event):
        self.is_hovering = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        center = QPointF(w/2, h/2)
        
        # 1. Bezel (Chrome Ring)
        bezel_grad = QLinearGradient(0, 0, w, h)
        bezel_grad.setColorAt(0, QColor("#DDD")) # Chrome light
        bezel_grad.setColorAt(1, QColor("#888")) # Chrome dark
        painter.setBrush(QBrush(bezel_grad))
        painter.setPen(QPen(QColor("#555"), 1))
        painter.drawEllipse(center, w/2 - 2, h/2 - 2)
        
        # 2. Inner Recess (Where core sits)
        painter.setBrush(QBrush(QColor("#000")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, w/2 - 8, h/2 - 8)
        
        # 3. Reactor Core (The glowing part)
        core_col = QColor(COLOR_ELECTRIC_BLUE)
        if self.state == self.STATE_THINKING:
            core_col = QColor(COLOR_AMBER_ALERT) 
        elif self.state == self.STATE_LISTENING:
            core_col = QColor(COLOR_PLASMA_CYAN)
        elif self.state == self.STATE_IDLE and self.is_hovering:
            core_col = QColor(COLOR_ELECTRIC_BLUE)
            
        # 3a. Thinking Animation: Rotating Pulse Ring
        if self.state == self.STATE_THINKING:
            painter.save()
            painter.translate(center)
            painter.rotate(self._spin_angle)
            pen = QPen(QColor(COLOR_AMBER_ALERT), 4)
            pen.setDashPattern([10, 15])
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            r = self._core_size * 1.4
            painter.drawEllipse(QPointF(0,0), r, r)
            painter.restore()
            
        # Core Glow
        glow_radius = self._core_size * (1.2 + self._glow_factor * 0.5)
        glow = QRadialGradient(center, glow_radius)
        c = QColor(core_col)
        c.setAlpha(int(155 * (0.6 + self._glow_factor * 0.4)))
        glow.setColorAt(0, c)
        glow.setColorAt(1, Qt.GlobalColor.transparent)
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, glow_radius, glow_radius)
        
        # Core Interior
        painter.setBrush(QBrush(core_col))
        painter.drawEllipse(center, self._core_size * 0.65, self._core_size * 0.65)
        
        # Gloss Shine on Core
        shine_radius = self._core_size * 0.25
        shine = QRadialGradient(center - QPointF(shine_radius*0.5, shine_radius*0.5), shine_radius)
        shine.setColorAt(0, QColor(255,255,255, 180))
        shine.setColorAt(1, QColor(255,255,255, 0))
        painter.setBrush(QBrush(shine))
        painter.drawEllipse(center - QPointF(shine_radius*0.5, shine_radius*0.5), shine_radius, shine_radius)

class ChatBubble(QFrame):
    def __init__(self, text, is_user=False):
        super().__init__()
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("background: transparent; border: none;")
        self.is_user = is_user
        
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)
        
        label = QLabel(text)
        label.setWordWrap(True)
        label.setFont(QFont("Menlo", 12)) 
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        # Tech / Console Feel (Silver vs Blue)
        if is_user:
            bg = "#D0D5DB"
            border = "#999"
            txt = "#222"
        else:
            bg = COLOR_SCREEN_BG
            border = COLOR_ELECTRIC_BLUE
            txt = COLOR_ELECTRIC_BLUE
        
        label.setStyleSheet(f"""
            color: {txt}; 
            padding: 12px; 
            background-color: {bg}; 
            border: 1px solid {border};
            border-radius: 12px;
        """)
        
        if is_user:
            layout.addStretch()
            layout.addWidget(label)
        else:
            layout.addWidget(label)
            layout.addStretch()


class ResourceBar(QWidget):
    def __init__(self, label="CPU", parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 10)
        self.label = label
        self.percent = 0
        self.bg_color = QColor(0, 0, 0, 40)
        self.bar_color = QColor(COLOR_PLASMA_CYAN) if "GPU" in label else QColor(COLOR_ELECTRIC_BLUE)
        
    def set_percent(self, p):
        self.percent = max(0, min(100, p))
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw BG
        painter.setBrush(QBrush(self.bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        rect = QRectF(self.rect())
        painter.drawRoundedRect(rect, 2, 2)
        
        # Draw Fill
        fill_width = rect.width() * (self.percent / 100.0)
        fill_rect = QRectF(rect.x(), rect.y(), fill_width, rect.height())
        painter.setBrush(QBrush(self.bar_color))
        painter.drawRoundedRect(fill_rect, 2, 2)
        
        # Label text
        painter.setPen(QPen(QColor("#555")))
        painter.setFont(QFont("Arial", 7))
        painter.drawText(rect.adjusted(2, -1, 0, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.label)
            
class InteractiveTitleLabel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text = cfg.assistant_name
        self.setFixedSize(140, 40)
        self.mouse_pos = QPoint(-100, -100)
        self.setMouseTracking(True)
        self.letters = list(self.text)
        self.font = QFont("Impact", 24)

    def update_text(self):
        self.text = cfg.assistant_name
        self.letters = list(self.text)
        self.update()
        
    def mouseMoveEvent(self, event):
        self.mouse_pos = event.pos()
        self.update()
        
    def leaveEvent(self, event):
        self.mouse_pos = QPoint(-100, -100)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self.font)
        
        # Base settings
        start_x = 0
        gap = 4 # Pixel gap between letters
        fm = QFontMetrics(self.font)
        
        current_x = start_x
        
        for i, char in enumerate(self.letters):
            char_width = fm.horizontalAdvance(char)
            
            # center of this letter for hit testing
            center_x = current_x + (char_width / 2)
            y = 30 # Baseline
            center_y = y - 10
            
            dist = ((self.mouse_pos.x() - center_x)**2 + (self.mouse_pos.y() - center_y)**2)**0.5
            
            # Base color
            base_col = QColor("#444")
            
            # Glow effect - DISCRETE logic for individual letters
            threshold = 20.0 # Slightly larger threshold for better feel
            
            if dist < threshold:
                col = QColor(COLOR_ELECTRIC_BLUE)
            else:
                col = base_col
                
            painter.setPen(QPen(col))
            painter.drawText(int(current_x), int(y), char)
            
            # Advance X position
            current_x += char_width + gap

class ResourceMonitor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(70, 26)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        self.cpu_bar = ResourceBar("CPU", self)
        self.gpu_bar = ResourceBar("GPU", self)
        
        layout.addWidget(self.cpu_bar)
        layout.addWidget(self.gpu_bar)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(2000) # 2 seconds
        
    def update_stats(self):
        # CPU
        self.cpu_bar.set_percent(psutil.cpu_percent())
        
        # GPU (Mac specific)
        threading.Thread(target=self._fetch_gpu, daemon=True).start()
        
    def _fetch_gpu(self):
        try:
            cmd = "ioreg -r -c IOAccelerator | grep -E 'Device Utilization %' | head -n 1"
            match = re.search(r'"Device Utilization %"=(\d+)', res)
            if match:
                val = int(match.group(1))
                self.gpu_bar.set_percent(val)
        except:
            pass

class SettingsDialog(QDialog):
    # Signals for thread safety
    preview_finished = pyqtSignal()
    model_deleted = pyqtSignal(str, bool, str) # name, success, error_msg

    model_deleted = pyqtSignal(str, bool, str) # name, success, error_msg

    def __init__(self, parent=None, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.preview_finished.connect(self._restore_preview_btn)
        self.model_deleted.connect(self._on_model_deleted)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(900, 850)
        
        # Main Layout container (Solid)
        from .ui_framework import BioMechCasing
        # Use simpler rounded rect for settings to avoid corner clipping issues
        self.container = BioMechCasing(self, squircle=False)
        self.container.bg_color = QColor(COLOR_CHASSIS_DARK)
        self.container.bg_color.setAlpha(255)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(self.container)
        
        # Content Layout
        content_layout = QVBoxLayout(self.container)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        # Custom Title Bar
        title_layout = QHBoxLayout()
        title_lbl = QLabel("SETTINGS")
        title_lbl.setFont(QFont("Impact", 18))
        title_lbl.setStyleSheet(f"color: {COLOR_ELECTRIC_BLUE}; letter-spacing: 2px;")
        
        close_btn = QPushButton()
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setIcon(_load_icon("close.svg"))
        close_btn.setIconSize(QSize(14, 14))
        close_btn.setStyleSheet(f"""
            QPushButton {{ color: #DDD; background: transparent; border: 1px solid #999; border-radius: 6px; font-size: 16px; font-weight: bold; }}
            QPushButton:hover {{ color: #FF6666; border-color: #FF6666; }}
            QPushButton:pressed {{ color: #FF0000; border-color: #FF0000; }}
        """)
        close_btn.clicked.connect(self.reject)
        
        title_layout.addWidget(title_lbl)
        title_layout.addStretch()
        title_layout.addWidget(close_btn)
        content_layout.addLayout(title_layout)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {COLOR_ELECTRIC_BLUE}; opacity: 0.3;")
        content_layout.addWidget(line)

        # Scroll Area for Form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")
        
        # Internal Content Widget
        self.form_widget = QWidget()
        self.form_widget.setStyleSheet("background: transparent;")
        self.form_layout = QVBoxLayout(self.form_widget)
        self.form_layout.setSpacing(25)
        self.form_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll.setWidget(self.form_widget)
        content_layout.addWidget(scroll)

        self.tabs = QTabWidget()
        self.tabs.setElideMode(Qt.TextElideMode.ElideNone)
        # Prevent tabs from being squeezed
        self.tabs.setMinimumHeight(450) 
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid #CCC; border-radius: 8px; background: #E8EBEF; }}
            QTabBar::tab {{ 
                background: #DDD; 
                color: #555; 
                padding: 12px 30px; 
                min-width: 120px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
            QTabBar::tab:selected {{ 
                background: #E8EBEF;
                color: {COLOR_ELECTRIC_BLUE}; 
                border-bottom: 2px solid #E8EBEF;
            }}
            QTabBar::tab:hover {{ color: {COLOR_ELECTRIC_BLUE}; }}
            QLabel {{ color: #222; font-size: 11px; font-weight: 600; }}
        """)
        self.form_layout.addWidget(self.tabs)

        self.llm_worker = None
        self.installed_models = []
        self.catalog_models = []

        # --- Build Pages ---
        self._init_general_page()
        self._init_llm_page()
        self._init_speech_page()
        self._init_ha_page()
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{ color: #888; font-weight: bold; border: 1px solid #999; border-radius: 6px; padding: 10px 20px; }}
            QPushButton:hover {{ color: #FF6666; border-color: #FF6666; }}
            QPushButton:pressed {{ color: #FF0000; border-color: #FF0000; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("SAVE CHANGES")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_ELECTRIC_BLUE};
                color: #000;
                font-weight: bold;
                border-radius: 6px;
                padding: 10px 25px;
            }}
            QPushButton:hover {{
                background-color: #55FFFF;
            }}
        """)
        save_btn.clicked.connect(self.save_settings)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        content_layout.addLayout(btn_layout)

        # Load models
        from .llm_client import LLMWorker
        self.llm_worker = LLMWorker()
        
        # Consolidation: update_ui_state will call refresh_installed_models
        self.llm_worker.progress.connect(self._on_model_progress)
        # Defer model loading to avoid blocking UI on dialog open
        QTimer.singleShot(100, lambda: self.update_ui_state(cfg.api_provider))
        
        # Dragging logic for frameless window
        self.old_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def _init_general_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Assistant Name Section
        layout.addWidget(self._make_header("Assistant Name"))
        self.name_edit = QLineEdit(cfg.assistant_name)
        self.name_edit.setPlaceholderText("Enter name (e.g., JARVIS, David)...")
        self._style_input(self.name_edit)
        layout.addWidget(self.name_edit)
        
        name_hint = QLabel("The name displayed in the header and used in AI responses.")
        name_hint.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(name_hint)

        # Profile Section
        layout.addSpacing(10)
        layout.addWidget(self._make_header("Session Profile"))
        
        prof_layout = QHBoxLayout()
        self.profile_combo = QComboBox()
        self._style_combo(self.profile_combo)
        self.profile_combo.addItems(cfg.profiles)
        self.profile_combo.setCurrentText(cfg.current_profile)
        
        self.add_prof_btn = QPushButton("+")
        self.add_prof_btn.setFixedSize(30, 30)
        self.add_prof_btn.clicked.connect(self._add_profile)
        self._style_mini_btn(self.add_prof_btn)
        
        self.del_prof_btn = QPushButton("🗑")
        self.del_prof_btn.setFixedSize(30, 30)
        self.del_prof_btn.clicked.connect(self._del_profile)
        self._style_mini_btn(self.del_prof_btn, destructive=True)
        
        prof_layout.addWidget(self.profile_combo)
        prof_layout.addWidget(self.add_prof_btn)
        prof_layout.addWidget(self.del_prof_btn)
        layout.addLayout(prof_layout)
        
        prof_hint = QLabel("Switching profiles instantly reloads memory and chat history.")
        prof_hint.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(prof_hint)
        
        layout.addStretch()
        self.tabs.addTab(page, "General")

    def _init_llm_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Provider Section
        layout.addWidget(self._make_header("AI Provider"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["ollama", "opencode", "openai", "gemini"])
        self.provider_combo.setCurrentText(cfg.api_provider)
        self.provider_combo.currentTextChanged.connect(self.update_ui_state)
        self._style_combo(self.provider_combo)
        layout.addWidget(self.provider_combo)
        
        self.api_key_edit = QLineEdit(cfg.api_key)
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("API Key...")
        self._style_input(self.api_key_edit)
        layout.addWidget(self.api_key_edit)

        # Model Section
        layout.addSpacing(5)
        layout.addWidget(self._make_header("Active Model"))
        self.model_edit = QComboBox()
        self._style_combo(self.model_edit)
        layout.addWidget(self.model_edit)

        # Model Manager (Tabbed)
        layout.addSpacing(10)
        layout.addWidget(self._make_header("Model Manager"))
        
        self.model_search = QLineEdit()
        self.model_search.setPlaceholderText("Search models...")
        self.model_search.textChanged.connect(self.render_catalog_models)
        self._style_input(self.model_search)
        layout.addWidget(self.model_search)
        
        self.model_status = QLabel("")
        self.model_status.setStyleSheet(f"color: {COLOR_ACCENT_TEAL}; font-size: 11px;")
        layout.addWidget(self.model_status)

        progress_layout = QHBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{ background: #DDD; border: none; border-radius: 4px; }}
            QProgressBar::chunk {{ background: {COLOR_ELECTRIC_BLUE}; border-radius: 4px; }}
        """)
        
        self.cancel_dl_btn = QPushButton()
        self.cancel_dl_btn.setFixedSize(24, 24)
        self.cancel_dl_btn.setVisible(False)
        self.cancel_dl_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_dl_btn.setToolTip("Cancel Download")
        self.cancel_dl_btn.setIcon(_load_icon("close.svg"))
        self.cancel_dl_btn.setIconSize(QSize(10, 10))
        self.cancel_dl_btn.setStyleSheet("QPushButton { color: #888; border: 1px solid #CCC; border-radius: 12px; font-weight: bold; background: white; } QPushButton:hover { color: red; border-color: red; }")
        self.cancel_dl_btn.clicked.connect(self._cancel_download)

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.cancel_dl_btn)
        layout.addLayout(progress_layout)
        
        # Sub-Tabs for Models
        self.model_tabs = QTabWidget()
        self.model_tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid #CCC; background: #E8EBEF; border-radius: 8px; }}
            QTabBar::tab {{ 
                background: #EEE; 
                padding: 6px 15px; 
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                color: #888;
            }}
            QTabBar::tab:selected {{ background: #E8EBEF; color: {COLOR_ELECTRIC_BLUE}; }}
        """)
        
        # My Models Tab
        self.inst_scroll = self._make_scroll_section()
        self.installed_container = self.inst_scroll.widget().layout()
        self.model_tabs.addTab(self.inst_scroll, "MY MODELS")
        
        # Browse Tab
        self.cat_scroll = self._make_scroll_section()
        self.catalog_container = self.cat_scroll.widget().layout()
        self.model_tabs.addTab(self.cat_scroll, "BROWSE")
        
        layout.addWidget(self.model_tabs)
        layout.addStretch()
        self.tabs.addTab(page, "Intelligence")

    def _make_scroll_section(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(240) 
        scroll.setStyleSheet(f"""
            QScrollArea {{ 
                background: #E8EBEF; 
                border: 1px solid #CCC; 
                border-radius: 10px; 
            }}
            QWidget {{ background: transparent; }}
        """)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setSpacing(10)
        lay.setContentsMargins(10, 10, 10, 10)
        scroll.setWidget(content)
        return scroll

    def _init_speech_page(self):
        page = QWidget()
        layout = QVBoxLayout(page) # Use VBox for cleaner stacking
        layout.setSpacing(15)

        layout.addWidget(self._make_header("Voice Input"))
        self.whisper_combo = QComboBox()
        self.whisper_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.whisper_combo.setCurrentText(cfg.whisper_model)
        self._style_combo(self.whisper_combo)
        layout.addWidget(QLabel("Whisper Model"))
        layout.addWidget(self.whisper_combo)
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Auto", "English", "German"])
        current_lang = cfg.language or "Auto"
        lang_map = {"en": "English", "de": "German", None: "Auto"}
        rev_map = {v: k for k, v in lang_map.items()}
        # Handle current logic... slightly clumsy mapping, simplifying:
        display_lang = "Auto"
        if cfg.language == "en": display_lang = "English"
        if cfg.language == "de": display_lang = "German"
        self.language_combo.setCurrentText(display_lang)
        self._style_combo(self.language_combo)
        layout.addWidget(QLabel("Language"))
        layout.addWidget(self.language_combo)

        layout.addSpacing(10)
        layout.addWidget(self._make_header("Voice Output"))
        
        self.voice_combo = QComboBox()
        self._populate_voices()
        self._style_combo(self.voice_combo)
        layout.addWidget(QLabel("System Voice"))
        layout.addWidget(self.voice_combo)


        # Preview voice button
        self.preview_btn = QPushButton("Preview Voice")
        self.preview_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.preview_btn.clicked.connect(self._preview_voice)
        self.preview_btn.setStyleSheet(f"""
            QPushButton {{ 
                background: transparent; 
                color: {COLOR_ELECTRIC_BLUE}; 
                font-weight: bold; 
                border: 1px solid {COLOR_ELECTRIC_BLUE}; 
                border-radius: 6px; 
                padding: 6px 12px;
            }}
            QPushButton:hover {{ 
                background: rgba(86, 226, 255, 0.1); 
            }}
        """)
        layout.addWidget(self.preview_btn)

        # Wake Word
        layout.addSpacing(10)
        self.wake_word_checkbox = QCheckBox("Enable Wake Word")
        self.wake_word_checkbox.setChecked(cfg.wake_word_enabled)
        self.wake_word_checkbox.setEnabled(False)
        self.wake_word_checkbox.setToolTip("Wake word detection is still in development.")
        self.wake_word_checkbox.setStyleSheet(f"""
            QCheckBox {{ color: #333; font-weight: bold; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; border: 1px solid #AAA; border-radius: 4px; background: white; }}
            QCheckBox::indicator:checked {{ background: {COLOR_ELECTRIC_BLUE}; border-color: {COLOR_ELECTRIC_BLUE}; }}
        """)
        layout.addWidget(self.wake_word_checkbox)
        
        self.wake_word_edit = QLineEdit(cfg.wake_word)
        self.wake_word_edit.setPlaceholderText("Wake word...")
        self.wake_word_edit.setEnabled(False)
        self.wake_word_edit.setStyleSheet(f"""
            QLineEdit {{
                background: {COLOR_SCREEN_BG};
                color: white;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 8px;
            }}
            QLineEdit:disabled {{ background: #DDD; color: #888; border: 1px solid #CCC; }}
        """)
        self.wake_word_checkbox.toggled.connect(self.wake_word_edit.setEnabled)
        layout.addWidget(self.wake_word_edit)
        
        layout.addStretch()
        self.tabs.addTab(page, "Speech")
        self.voice_combo.currentIndexChanged.connect(self._update_piper_quality_visibility)
        self._update_piper_quality_visibility()

    def _init_ha_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        layout.addWidget(self._make_header("Home Assistant Connection"))
        
        self.ha_url_edit = QLineEdit(cfg.ha_url)
        self.ha_url_edit.setPlaceholderText("http://homeassistant.local:8123")
        self._style_input(self.ha_url_edit)
        layout.addWidget(QLabel("Instance URL"))
        layout.addWidget(self.ha_url_edit)

        self.ha_token_edit = QLineEdit(cfg.ha_token)
        self.ha_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.ha_token_edit.setPlaceholderText("Long-Lived Access Token")
        self._style_input(self.ha_token_edit)
        layout.addWidget(QLabel("Access Token"))
        layout.addWidget(self.ha_token_edit)

        layout.addSpacing(12)
        layout.addWidget(self._make_header("Telegram Notifications"))

        self.telegram_token_edit = QLineEdit(cfg.telegram_bot_token)
        self.telegram_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.telegram_token_edit.setPlaceholderText("Bot Token")
        self._style_input(self.telegram_token_edit)
        layout.addWidget(QLabel("Bot Token"))
        layout.addWidget(self.telegram_token_edit)

        self.telegram_chat_id_edit = QLineEdit(cfg.telegram_chat_id)
        self.telegram_chat_id_edit.setPlaceholderText("Chat ID")
        self._style_input(self.telegram_chat_id_edit)
        layout.addWidget(QLabel("Chat ID"))
        layout.addWidget(self.telegram_chat_id_edit)

        layout.addStretch()
        self.tabs.addTab(page, "Smart Home")

    def _make_header(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {COLOR_ELECTRIC_BLUE}; font-weight: bold; font-size: 14px; text-transform: uppercase;")
        return lbl

    def _style_input(self, widget):
        widget.setStyleSheet(f"""
            QLineEdit {{
                background: {COLOR_SCREEN_BG};
                color: white;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 8px;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLOR_ELECTRIC_BLUE};
            }}
        """)

    def _style_combo(self, widget):
        widget.setStyleSheet(f"""
            QComboBox {{
                background: {COLOR_SCREEN_BG};
                color: white;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 5px;
            }}
            QComboBox::drop-down {{ border: none; }}
        """)

    # ... Include existing helpers (_populate_voices, update_ui_state, etc.) with minor tweaks if needed ...
    # For brevity in this tool call, I'm assuming helpers will be preserved or I need to include them. 
    # I WILL INCLUDE THEM TO BE SAFE since I am replacing the class.

    def _populate_voices(self):
        self.voice_combo.clear()

        saved_voice_id = cfg.tts_voice_id
        target_index = -1

        # Add Default voice first
        self.voice_combo.addItem("Default", "")
        if not saved_voice_id:
            target_index = 0

        # Add Piper voices (download on first use)
        piper_voices = [
            ("Piper (Amy) US Female", "piper:en_US-amy-medium"),
            ("Piper (Lessac) US Female", "piper:en_US-lessac-medium"),
            ("Piper (LJ) US Female", "piper:en_US-ljspeech-medium"),
            ("Piper (Ryan) US Male", "piper:en_US-ryan-medium"),
            ("Piper (Thorsten) DE Male", "piper:de_DE-thorsten-medium"),
        ]
        for label, voice_id in piper_voices:
            self.voice_combo.addItem(label, voice_id)
            if saved_voice_id == "piper" or (saved_voice_id and saved_voice_id.startswith(f"{voice_id}-")) or saved_voice_id == voice_id:
                target_index = self.voice_combo.count() - 1

        import platform
        # No additional system voices beyond Default.

        if target_index >= 0:
            self.voice_combo.setCurrentIndex(target_index)
        elif self.voice_combo.count() > 0:
            self.voice_combo.setCurrentIndex(0)

    def _preview_voice(self):
        voice_id = self.voice_combo.currentData()
        test_text = "Analysis complete. Systems nominal."
        
        # Visual feedback
        original_text = self.preview_btn.text()
        self.preview_btn.setText("playing...")
        self.preview_btn.setEnabled(False)
        self.preview_btn.setStyleSheet(f"""
            QPushButton {{ 
                background: {COLOR_ACCENT_TEAL}; 
                color: #000; 
                font-weight: bold; 
                border-radius: 6px; 
                padding: 6px 12px;
                border: none;
            }}
        """)
        
        def restore_btn():
            self.preview_btn.setText(original_text)
            self.preview_btn.setEnabled(True)
            self.preview_btn.setStyleSheet(f"""
                QPushButton {{ 
                    background: transparent; 
                    color: {COLOR_ELECTRIC_BLUE}; 
                    font-weight: bold; 
                    border: 1px solid {COLOR_ELECTRIC_BLUE}; 
                    border-radius: 6px; 
                    padding: 6px 12px;
                }}
                QPushButton:hover {{ 
                    background: rgba(86, 226, 255, 0.1); 
                }}
            """)

        def run_preview():
            try:
                if isinstance(voice_id, str) and voice_id.startswith("piper"):
                    from .tts import TTSWorker
                    original_voice = cfg.tts_voice_id
                    cfg.tts_voice_id = voice_id
                    worker = TTSWorker()
                    if worker.prepare_piper_voice(voice_id):
                        worker.speak(test_text)
                    cfg.tts_voice_id = original_voice
                else:
                    import subprocess
                    import platform
                    if platform.system() == "Darwin":
                        cmd = ["say"]
                        if voice_id:
                            voice_name = voice_id.split('.')[-1]
                            cmd.extend(["-v", voice_name])
                        cmd.append(test_text)
                        subprocess.run(cmd, check=True)
            except Exception as e:
                logger.error(f"Failed to preview voice: {e}")
            finally:
                self.preview_finished.emit() # Emit the signal from the thread

        threading.Thread(target=run_preview, daemon=True).start()

    def _restore_preview_btn(self):
        self.preview_btn.setText("Preview Voice")
        self.preview_btn.setEnabled(True)
        self.preview_btn.setStyleSheet(f"""
            QPushButton {{ 
                background: transparent; 
                color: {COLOR_ELECTRIC_BLUE}; 
                font-weight: bold; 
                border: 1px solid {COLOR_ELECTRIC_BLUE}; 
                border-radius: 6px; 
                padding: 6px 12px;
            }}
            QPushButton:hover {{ 
                background: rgba(86, 226, 255, 0.1); 
            }}
        """)

    def update_ui_state(self, provider):
        # same logic but cleaner checks
        is_ollama = (provider == "ollama")
        is_opencode = ("opencode" in provider)
        is_openai_gemini = provider in ["openai", "gemini"]
        
        # Visibility toggles
        self.model_search.setVisible(is_ollama)
        self.model_status.setVisible(is_ollama)
        self.api_key_edit.setVisible(is_openai_gemini)
        self.model_tabs.setVisible(is_ollama)
        self.progress_bar.setVisible(False) # Hide progress bar when switching providers
        # We can't easily hide the layout headers without keeping refs, 
        # but for now let's just handle the inputs.
        
        if is_opencode:
             # Align with opencode model ids from /zen docs
             # Use addItem with (display_name, data=actual_id)
             self.model_edit.clear()
             opencode_models = [("grok-code", "grok-code"), ("big-pickle", "big-pickle"), ("minimax", "minimax-m2.1-free"), ("glm-4.7", "glm-4.7-free")]
             for display, model_id in opencode_models:
                 self.model_edit.addItem(display, model_id)
             # Find and set saved model
             saved_model = cfg.ollama_model
             idx = self.model_edit.findData(saved_model)
             if idx >= 0:
                 self.model_edit.setCurrentIndex(idx)
             else:
                 self.model_edit.setCurrentIndex(0) # Default to first
        elif is_ollama:
             self.refresh_installed_models()
        else:
             self.model_edit.clear()
             if provider == "openai": self.model_edit.addItems(["gpt-4o", "gpt-3.5-turbo"])
             if provider == "gemini": self.model_edit.addItems(["gemini-pro"])

    def save_settings(self):
        logger.info("Saving settings...")
        
        # Check for profile switch
        new_profile = self.profile_combo.currentText()
        should_switch = (new_profile != cfg.current_profile)
        
        cfg.assistant_name = self.name_edit.text()
        cfg.api_provider = self.provider_combo.currentText()
        cfg.api_key = self.api_key_edit.text()
        # Use data if available (for opencode friendly names), else fall back to text
        model_data = self.model_edit.currentData()
        cfg.ollama_model = model_data if model_data else self.model_edit.currentText()
        cfg.whisper_model = self.whisper_combo.currentText()
        
        l_text = self.language_combo.currentText()
        if l_text == "English": cfg.language = "en"
        elif l_text == "German": cfg.language = "de"
        else: cfg.language = None
        
        cfg.tts_voice_id = self.voice_combo.currentData()
        cfg.wake_word_enabled = self.wake_word_checkbox.isChecked()
        cfg.wake_word = self.wake_word_edit.text()
        cfg.ha_url = self.ha_url_edit.text()
        cfg.ha_token = self.ha_token_edit.text()
        if hasattr(self, "telegram_token_edit"):
            cfg.telegram_bot_token = self.telegram_token_edit.text()
        if hasattr(self, "telegram_chat_id_edit"):
            cfg.telegram_chat_id = self.telegram_chat_id_edit.text()
        
        cfg.save()
        logger.info(f"Settings saved to: {cfg.tts_voice_id}")
        
        if should_switch and self.controller:
             try:
                 self.controller.switch_profile(new_profile)
             except Exception as e:
                 logger.error(f"Could not switch profile: {e}")
        
        self.accept()


    def _update_piper_quality_visibility(self):
        voice_id = self.voice_combo.currentData()
        is_piper = isinstance(voice_id, str) and voice_id.startswith("piper:")
        # Placeholder in case we add quality controls later.

    def _style_mini_btn(self, btn, destructive=False):
        color = "#FF6666" if destructive else COLOR_ELECTRIC_BLUE
        hover = "#FF0000" if destructive else "#0066DD"
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {color};
                border: 1px solid {color};
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: {color}22;
                border-color: {hover};
                color: {hover};
            }}
        """)

    def _add_profile(self):
        name, ok = QInputDialog.getText(self, "New Profile", "Enter profile name (e.g., 'Bobby'):")
        if ok and name:
            clean_name = name.strip().lower().replace(" ", "_")
            if clean_name in cfg.profiles:
                QMessageBox.warning(self, "Exists", "Profile already exists.")
                return
            
            # Update config immediately
            profs = cfg.profiles
            profs.append(clean_name)
            cfg.profiles = profs
            
            self.profile_combo.addItem(clean_name)
            self.profile_combo.setCurrentText(clean_name)
    
    def _del_profile(self):
        curr = self.profile_combo.currentText()
        if curr == "default":
            QMessageBox.warning(self, "Error", "Cannot delete default profile.")
            return
            
        reply = QMessageBox.question(self, "Confirm", f"Delete profile '{curr}' and all its memory?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # Cleanup files
            try:
                os.remove(f"memory_{curr}.json")
                os.remove(f"history_{curr}.json")
            except: pass
            
            profs = cfg.profiles
            if curr in profs: profs.remove(curr)
            cfg.profiles = profs
            
            # Refresh UI
            self.profile_combo.clear()
            self.profile_combo.addItems(profs)
            self.profile_combo.setCurrentText("default")

    # --- Model Helpers (Simplified for the new layout) ---
    def _clear_layout(self, layout):
        if not layout: return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def refresh_installed_models(self):
        if not self.llm_worker: return
        self.installed_models = self.llm_worker.list_models_detailed()
        
        current = self.model_edit.currentText()
        self.model_edit.clear()
        if self.installed_models:
            self.model_edit.addItems([m["name"] for m in self.installed_models])
        else:
            self.model_edit.addItems(["qwen2.5:0.5b"]) # Fallback
            
        # restore selection if possible
        if current: self.model_edit.setCurrentText(current)
            
        self.render_installed_models()
        self.render_catalog_models()

    def render_installed_models(self):
        if not hasattr(self, 'installed_container'): return
        self._clear_layout(self.installed_container)
        for m in self.installed_models:
             card = self._create_model_card(m, installed=True)
             self.installed_container.addWidget(card)
        self.installed_container.addStretch() # Keep at top

    def render_catalog_models(self):
        if not hasattr(self, 'catalog_container'): return
        self._clear_layout(self.catalog_container)
        text = self.model_search.text().lower()
        
        # Auto-switch to browse tab if searching
        if text and hasattr(self, 'model_tabs'):
            self.model_tabs.setCurrentIndex(1)
            
        if not hasattr(self, 'catalog_models') or not self.catalog_models:
             self.catalog_models = self.llm_worker.load_catalog()
        
        matches = [m for m in self.catalog_models if text in m.get("name", "").lower()]
        for m in matches: # Show all matches
             card = self._create_model_card(m, installed=False)
             self.catalog_container.addWidget(card)
        self.catalog_container.addStretch() # Keep at top

    def _create_model_card(self, m, installed):
        # Card container parented to NOTHING initially to avoid stray rendering
        card = QFrame()
        card.setMinimumHeight(65)
        card.setStyleSheet(f"""
            QFrame {{ 
                background: white; 
                border: 1px solid #CCC; 
                border-radius: 12px;
            }}
            QFrame:hover {{ border: 1px solid {COLOR_ELECTRIC_BLUE}; }}
        """)
        
        main_layout = QHBoxLayout(card)
        main_layout.setContentsMargins(15, 12, 15, 12)
        main_layout.setSpacing(15)
        
        name = m.get("name", "Unknown")
        hw = m.get("hardware", "Generic")
        size = m.get("size", "Unknown Size")
        
        # Info block (Parented to card)
        info_widget = QWidget(card)
        info_widget.setStyleSheet("background: transparent; border: none;")
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        name_lbl = QLabel(name, info_widget)
        name_lbl.setStyleSheet("color: #222; font-weight: bold; font-size: 13px; border: none;")
        
        hw_lbl = QLabel(f"{hw} • {size}", info_widget)
        hw_lbl.setStyleSheet("color: #777; font-size: 11px; border: none;")
        
        info_layout.addWidget(name_lbl)
        info_layout.addWidget(hw_lbl)
        
        main_layout.addWidget(info_widget)
        main_layout.addStretch()
        
        # Action Buttons (Parented to card)
        if installed:
            btn = QPushButton("USE", card)
            btn.setFixedSize(75, 36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{ 
                    background: #F2F4F7; 
                    color: #444; 
                    font-weight: bold; 
                    border: 1px solid #CCC; 
                    border-radius: 8px;
                }}
                QPushButton:hover {{ background: #E0E5EB; border-color: #BBB; }}
            """)
            btn.clicked.connect(lambda: self.model_edit.setCurrentText(name))
            main_layout.addWidget(btn)
            
            del_btn = QPushButton("🗑", card)
            del_btn.setFixedSize(36, 36)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setStyleSheet("QPushButton { background: transparent; color: #CCC; border: none; font-size: 20px; } QPushButton:hover { color: #FF6666; }")
            del_btn.clicked.connect(lambda: self.delete_model(name))
            main_layout.addWidget(del_btn)
        else:
            btn = QPushButton("GET", card)
            btn.setFixedSize(75, 36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{ 
                    background: {COLOR_ELECTRIC_BLUE}; 
                    color: white; 
                    font-weight: bold; 
                    border-radius: 8px;
                    border: none;
                }}
                QPushButton:hover {{ background: #0066DD; }}
            """)
            btn.clicked.connect(lambda: self.download_model(name))
            main_layout.addWidget(btn)
            
        return card
    def download_model(self, name):
        self.model_status.setText(f"Starting download: {name}...")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.cancel_dl_btn.setVisible(True) # Show cancel btn
        
        def t():
            self.llm_worker.pull_model(name)
            # Cleanup happen in _on_model_progress or here if needed, but progress handles visibility
        threading.Thread(target=t, daemon=True).start()

    def _cancel_download(self):
        self.model_status.setText("Cancelling...")
        self.llm_worker.cancel_download()
        self.cancel_dl_btn.setEnabled(False) # Prevent double click

    def delete_model(self, name):
        reply = QMessageBox.question(self, "Delete Model", f"Are you sure you want to delete '{name}'?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.model_status.setText(f"Deleting {name}...")
            def t():
                res = self.llm_worker.remove_model(name)
                success = (res.get("status") == "success")
                error = res.get("error", "")
                self.model_deleted.emit(name, success, error)
            threading.Thread(target=t, daemon=True).start()

    def _on_model_deleted(self, name, success, error):
        if success:
            self.model_status.setText(f"Deleted {name}.")
        else:
            self.model_status.setText(f"Error deleting: {error}")
            
        QTimer.singleShot(2000, lambda: self.model_status.setText(""))
        QTimer.singleShot(100, self.refresh_installed_models)

    def _on_model_progress(self, status, pct):
        self.model_status.setText(status)
        if pct >= 0:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(pct)
            self.cancel_dl_btn.setVisible(True)
            self.cancel_dl_btn.setEnabled(True)
        else:
            # Done or Error or Cancelled
            self.progress_bar.setVisible(False)
            self.cancel_dl_btn.setVisible(False)
            self.cancel_dl_btn.setEnabled(True)
            
            # If successful or cancelled, refresh logic handled here or via timer
            if "Finished" in status or "Cancelled" in status:
                QTimer.singleShot(2000, lambda: self.model_status.setText(""))
                QTimer.singleShot(100, self.refresh_installed_models)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.default_height = 650
        self.collapsed_height = 230
        self.resize(560, self.default_height + 60) # Slightly larger for margins
        
        # 1. Transparent Container to hold the Casing + Shadow
        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(container)
        
        # 2. Layout with margins for the shadow
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(30, 30, 30, 50) # Space for shadow
        
        # 3. The Actionable Casing
        self.casing = BioMechCasing(squircle=True)
        container_layout.addWidget(self.casing)
        
        # Add deep drop shadow for floating effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(50)
        shadow.setXOffset(0)
        shadow.setYOffset(15)
        shadow.setColor(QColor(0, 0, 0, 140)) # Slightly softer shadow
        self.casing.setGraphicsEffect(shadow)
        
        # Layout inside the casing
        layout = QVBoxLayout(self.casing)
        layout.setSpacing(10)
        layout.setContentsMargins(30, 40, 30, 30) # Internal margins
        
        # Header
        header = QHBoxLayout()
        # Add side spacing for squircle corners
        header.setContentsMargins(35, 10, 35, 0)
        
        header.setContentsMargins(35, 10, 35, 0)
        
        # Replaced custom widget for glowing letters
        self.title_label = InteractiveTitleLabel()
        
        settings_btn = QPushButton()
        settings_btn.setFixedSize(30, 30)
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setIcon(_load_icon("settings.svg"))
        settings_btn.setIconSize(QSize(16, 16))
        settings_btn.setStyleSheet(f"""
            QPushButton {{ 
                color: #444; background: transparent; border: 1px solid #999; border-radius: 6px; font-size: 18px; 
            }}
            QPushButton:hover {{ 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #BBB, stop:1 #EEE);
                border-top: 2px solid #777;
                border-left: 2px solid #777;
                border-bottom: 2px solid #FFF;
                border-right: 2px solid #FFF;
            }}
            QPushButton:pressed {{ 
                background: #AAA;
                padding-top: 2px;
                padding-left: 2px;
            }}
        """)
        settings_btn.clicked.connect(self.open_settings)

        self.toggle_history_btn = QPushButton("Hide Chat")
        self.toggle_history_btn.setFixedHeight(28)
        self.toggle_history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_history_btn.setStyleSheet(f"""
            QPushButton {{ 
                color: #444; background: transparent; border: 1px solid #999; border-radius: 6px; font-size: 12px; padding: 2px 8px;
            }}
            QPushButton:hover {{ 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #BBB, stop:1 #EEE);
                border-top: 2px solid #777;
                border-left: 2px solid #777;
                border-bottom: 2px solid #FFF;
                border-right: 2px solid #FFF;
                padding: 0px 6px; /* Adjust padding to compensate for border */
            }}
            QPushButton:pressed {{ 
                background: #AAA;
                padding-top: 4px; /* Adjust padding to simulate press */
                padding-left: 8px;
            }}
        """)
        self.toggle_history_btn.clicked.connect(self.toggle_history)
        
        self.mute_btn = QPushButton()
        self.mute_btn.setFixedSize(28, 28)
        self.mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mute_btn.setIcon(_load_icon("volume.svg"))
        self.mute_btn.setIconSize(QSize(16, 16))
        self.mute_btn.setStyleSheet(f"""
            QPushButton {{ 
                color: #444; background: transparent; border: 1px solid #999; border-radius: 6px; font-size: 14px;
            }}
            QPushButton:hover {{ 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #BBB, stop:1 #EEE);
                border-top: 2px solid #777;
                border-left: 2px solid #777;
                border-bottom: 2px solid #FFF;
                border-right: 2px solid #FFF;
            }}
            QPushButton:pressed {{ 
                background: #AAA;
                padding-top: 1px;
                padding-left: 1px;
            }}
        """)
        self.mute_btn.clicked.connect(self.toggle_mute)
        
        # Initialize mute state from config
        self.is_muted = (cfg.tts_volume == 0.0)
        if self.is_muted:
            self.mute_btn.setIcon(_load_icon("mute.svg"))
            self.mute_btn.setStyleSheet("color: #FF6666; background: transparent; border: 1px solid #999; border-radius: 6px; font-size: 14px;")
        
        close_btn = QPushButton()
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setIcon(_load_icon("close.svg"))
        close_btn.setIconSize(QSize(14, 14))
        close_btn.setStyleSheet(f"""
            QPushButton {{ 
                color: #444; background: transparent; border: 1px solid #999; border-radius: 6px; font-size: 18px; 
            }}
            QPushButton:hover {{ 
                color: #FF6666; 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF9999, stop:1 #FFF0F0);
                border-top: 2px solid #CC0000;
                border-left: 2px solid #CC0000;
                border-bottom: 2px solid #FFF;
                border-right: 2px solid #FFF;
            }}
            QPushButton:pressed {{ 
                color: #FF0000; 
                background: #FFCCCC;
                padding-top: 2px;
                padding-left: 2px;
            }}
        """)
        close_btn.clicked.connect(self.close)
        
        header.addWidget(self.title_label)
        header.addStretch()
        
        self.res_monitor = ResourceMonitor()
        header.addWidget(self.res_monitor)
        header.addSpacing(5)

        header.addWidget(self.toggle_history_btn)
        header.addWidget(self.mute_btn)
        header.addWidget(settings_btn)
        header.addWidget(close_btn)
        layout.addLayout(header)
        header.addWidget(close_btn)
        layout.addLayout(header)
        # removed addStretch here to let screen_frame expand

        # Screen Area (Inset LCD with Gloss Overlay)
        self.screen_frame = QFrame()
        # We need a custom paint event for the screen gloss or use a gradient background
        # Let's use a stylesheet with a radial gradient overlay if possible, or valid QSS
        
        # Deep blue screen with top shine
        self.screen_frame.setStyleSheet(f"""
            background-color: {COLOR_SCREEN_BG};
            background-image: qradialgradient(cx:0.5, cy:0, radius: 0.8, fx:0.5, fy:0, stop:0 rgba(255, 255, 255, 40), stop:1 rgba(0, 0, 0, 0));
            border: 2px solid #888;
            border-bottom: 2px solid #AAA;
            border-top: 2px solid #555;
            border-radius: 6px;
        """)
        
        screen_layout = QVBoxLayout(self.screen_frame)
        screen_layout.setContentsMargins(2,2,2,2)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_content)
        
        screen_layout.addWidget(self.scroll_area)
        layout.addWidget(self.screen_frame)
        
        self.history_visible = True
        self._bubble_anims = []
        
        # Control Deck
        deck_layout = QVBoxLayout()
        deck_layout.setContentsMargins(0, 0, 0, 5)
        deck_layout.setSpacing(5)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Direct Interface...")
        self.chat_input.setStyleSheet(f"""
            QLineEdit {{
                background: {COLOR_SCREEN_BG};
                color: {COLOR_ELECTRIC_BLUE};
                border: 1px solid #444;
                border-radius: 8px;
                padding: 10px 15px;
                font-family: 'SF Mono', Menlo, Monaco, monospace;
                font-size: 13px;
                margin-bottom: 10px;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLOR_ELECTRIC_BLUE};
                background: #001122;
            }}
        """)
        deck_layout.addWidget(self.chat_input)

        self.mic_btn = MicButton()
        deck_layout.addWidget(self.mic_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.status_label = QLabel("SYSTEM IDLE")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"color: #666; font-family: 'SF Mono', Menlo, Monaco, monospace; font-weight: bold; font-size: 11px; margin-top: 10px; letter-spacing: 1px;")
        deck_layout.addWidget(self.status_label)

        self.response_timer_label = QLabel("")
        self.response_timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.response_timer_label.setStyleSheet("color: #777; font-family: 'SF Mono', Menlo, Monaco, monospace; font-size: 10px;")
        self.response_timer_label.setVisible(False)
        # Position as overlay instead of in layout
        self.response_timer_label.setParent(self.casing)  # Parent to casing for reliable overlay
        self._position_response_timer()
        self.response_timer_label.raise_()  # Ensure it's on top

        self._response_timer_start = None
        self._response_timer = QTimer(self)
        self._response_timer.setInterval(100)
        self._response_timer.timeout.connect(self._update_response_timer)
        
        layout.addLayout(deck_layout)
        layout.addLayout(deck_layout)
        # layout.addStretch() # Removed to compact bottom
        
        # Dragging & Resizing logic
        self.old_pos = None
        self.resizing_y = False
        self.resize_margin = 12 # Pixels from bottom to trigger resize
        self.setMouseTracking(True) # Required for hover cursor update

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.text().lower() == 'm':
            # Trigger mic button click
            self.mic_btn.clicked.emit()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check for resize attempt logic
            if self.history_visible and event.position().y() > (self.height() - self.resize_margin):
                self.resizing_y = True
                self.old_pos = event.globalPosition().toPoint()
            else:
                self.resizing_y = False
                self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        # 1. Hover Update (No buttons pressed)
        if not event.buttons():
            if self.history_visible and event.position().y() > (self.height() - self.resize_margin):
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            else:
                self.unsetCursor() 
                
        # 2. Drag / Resize
        elif event.buttons() == Qt.MouseButton.LeftButton and self.old_pos:
            global_pos = event.globalPosition().toPoint()
            delta = global_pos - self.old_pos
            
            if self.resizing_y:
                new_h = int(max(self.collapsed_height, min(1200, self.height() + delta.y())))
                self.resize(self.width(), new_h)
                self.default_height = new_h # Remember this size
                self.old_pos = global_pos
            else:
                # Normal move
                self.move(self.pos() + delta)
                self.old_pos = global_pos

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_response_timer()

    def mouseReleaseEvent(self, event):
        self.old_pos = None
        self.resizing_y = False
        self.unsetCursor()

    def add_message(self, text, is_user, animate=True):
        bubble = ChatBubble(text, is_user)
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, bubble)
        if animate:
            QTimer.singleShot(0, lambda: self._animate_bubble(bubble))
        QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum()))

    def clear_chat(self):
        """Clear all chat bubbles from the scroll layout."""
        while self.scroll_layout.count() > 1:
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _animate_bubble(self, bubble):
        try:
            effect = QGraphicsOpacityEffect(bubble)
            effect.setOpacity(0.0)
            bubble.setGraphicsEffect(effect)

            fade = QPropertyAnimation(effect, b"opacity")
            fade.setDuration(220)
            fade.setStartValue(0.0)
            fade.setEndValue(1.0)
            fade.setEasingCurve(QEasingCurve.Type.OutCubic)

            def cleanup():
                if bubble.graphicsEffect() == effect:
                    bubble.setGraphicsEffect(None)
                self._bubble_anims = [a for a in self._bubble_anims if a is not fade]

            fade.finished.connect(cleanup)

            self._bubble_anims.append(fade)
            fade.start()
        except Exception:
            pass

    def open_settings(self):
        # Ensure we have a controller ref
        ctrl = getattr(self, "controller", None)
        dlg = SettingsDialog(self, controller=ctrl)
        dlg.exec()
        # Refresh title in case user changed the name
        self.title_label.update_text()

    def toggle_history(self):
        self.history_visible = not self.history_visible
        target_height = self.default_height if self.history_visible else self.collapsed_height
        
        start_h = self.height()
        import time
        start_time = time.time()
        duration = 0.25 # 250ms fixed duration for snappy feel
        
        if self.history_visible:
            self.screen_frame.setVisible(True)
            self.toggle_history_btn.setText("Hide Chat")
        else:
            self.toggle_history_btn.setText("Show Chat")
            
        def anim_loop():
            now = time.time()
            elapsed = now - start_time
            progress = elapsed / duration
            
            if progress >= 1.0:
                self.resize(self.width(), target_height)
                if not self.history_visible:
                    self.screen_frame.setVisible(False)
                return

            # Simple easing (OutQuint equivalent-ish) could be nice, but linear for now or simple ease out
            # Ease Out Cubic: 1 - pow(1 - progress, 3)
            ease = 1 - pow(1 - progress, 3)
            
            new_h = int(start_h + ((target_height - start_h) * ease))
            self.resize(self.width(), new_h)
            
            QTimer.singleShot(16, anim_loop)
        
        anim_loop()

    def toggle_mute(self):
        """Toggle TTS mute state"""
        self.is_muted = not self.is_muted
        
        if self.is_muted:
            # Mute TTS by setting volume to 0
            cfg.tts_volume = 0.0
            self.mute_btn.setIcon(_load_icon("mute.svg"))
            self.mute_btn.setStyleSheet("color: #FF6666; background: transparent; border: 1px solid #999; border-radius: 6px; font-size: 14px;")
        else:
            # Unmute TTS by restoring volume to default
            cfg.tts_volume = 1.0
            self.mute_btn.setIcon(_load_icon("volume.svg"))
            self.mute_btn.setStyleSheet("color: #444; background: transparent; border: 1px solid #999; border-radius: 6px; font-size: 14px;")
        
        cfg.save()

    def set_status(self, text):
        self.status_label.setText(text.upper())
        upper = text.upper()
        start_keys = ["THINKING", "EXECUTING", "PROCESSING", "GENERATING", "TRANSCRIBING"]
        stop_keys = ["IDLE", "SYSTEM READY", "READY", "ERROR", "LISTENING", "RECORDING"]
        if any(k in upper for k in start_keys):
            if not self._response_timer.isActive():
                import time
                self._response_timer_start = time.time()
                self.response_timer_label.setText("0.0s")
                self._position_response_timer()
                self.response_timer_label.setVisible(True)
                self.response_timer_label.setStyleSheet("color: #777; font-family: 'SF Mono', Menlo, Monaco, monospace; font-size: 10px;")
                self._response_timer.start()
        elif any(k in upper for k in stop_keys):
            if self._response_timer.isActive():
                self._response_timer.stop()
            self.response_timer_label.setVisible(False)
            self.response_timer_label.setStyleSheet("color: #777; font-family: 'SF Mono', Menlo, Monaco, monospace; font-size: 10px;")
        self._position_response_timer()
        txt = text.upper()
        
        # Robust mapping of status text to MicButton states
        thinking_keys = ["THINKING", "TRANSCRIBING", "GENERATING", "PROCESSING", "EXECUTING"]
        listening_keys = ["LISTENING", "RECORDING"]
        speaking_keys = ["SPEAKING"]
        idle_keys = ["IDLE", "SYSTEM READY", "READY"]
        
        if any(k in txt for k in thinking_keys):
             self.mic_btn.set_state(MicButton.STATE_THINKING)
        elif any(k in txt for k in listening_keys):
             self.mic_btn.set_state(MicButton.STATE_LISTENING)
        elif any(k in txt for k in speaking_keys):
             self.mic_btn.set_state(MicButton.STATE_SPEAKING)
        else:
             self.mic_btn.set_state(MicButton.STATE_IDLE)

    def _update_response_timer(self):
        if self._response_timer_start is None:
            return
        import time
        elapsed = time.time() - self._response_timer_start
        self.response_timer_label.setText(f"{elapsed:.1f}s")
        self._position_response_timer()

    def _position_response_timer(self):
        if not hasattr(self, "response_timer_label"):
            return
        self.response_timer_label.adjustSize()
        parent = self.response_timer_label.parentWidget() or self
        x = (parent.width() - self.response_timer_label.width()) // 2
        if hasattr(self, "status_label"):
            status_y = self.status_label.y() + self.status_label.height()
            y = status_y + 8
        else:
            y = parent.height() - 50
        self.response_timer_label.move(max(10, x), max(10, y))
        self.response_timer_label.raise_()
