from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QScrollArea, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
    QDialog, QFormLayout, QLineEdit, QComboBox, QSlider, QDialogButtonBox,
    QCheckBox, QProgressBar, QTabWidget, QMessageBox, QInputDialog, QListWidget, QToolButton, QSizePolicy
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
import json
import os
import sys
import psutil
import subprocess
import re
import textwrap
from pathlib import Path
from .config import cfg, COLOR_BACKGROUND, COLOR_ACCENT_CYAN, COLOR_ACCENT_TEAL
from .profile_paths import remove_profile_files
from .utils import logger
from .llm_client import LLMWorker

from .ui_framework import (
    GOLDEN_RATIO, BioMechCasing, COLOR_CHASSIS_DARK, COLOR_CHASSIS_MID,
    COLOR_ELECTRIC_BLUE, COLOR_SCREEN_BG, COLOR_PLASMA_CYAN, COLOR_AMBER_ALERT, BreathingAnim, KineticAnim
)

ICON_DIR = Path(__file__).resolve().parent / "assets" / "icons"

def _load_icon(name: str) -> QIcon:
    return QIcon(str(ICON_DIR / name))

_SETTINGS_LLM_WORKER = None


def _get_settings_llm_worker() -> LLMWorker:
    global _SETTINGS_LLM_WORKER
    if _SETTINGS_LLM_WORKER is None:
        _SETTINGS_LLM_WORKER = LLMWorker()
    return _SETTINGS_LLM_WORKER


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
        self.mouse_pos = QPoint(-100, -100)
        self.setMouseTracking(True)
        self.letters = list(self.text)
        self.font = QFont("Impact", 26)
        self._letter_gap = 4
        self._update_geometry()

    def _update_geometry(self):
        fm = QFontMetrics(self.font)
        char_width_total = sum(fm.horizontalAdvance(ch) for ch in self.letters)
        width = char_width_total + (self._letter_gap * max(0, len(self.letters) - 1)) + 14
        width = max(150, min(260, width))
        self.setFixedSize(width, 44)

    def update_text(self):
        self.text = cfg.assistant_name
        self.letters = list(self.text)
        self._update_geometry()
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
        start_x = 2
        gap = self._letter_gap
        fm = QFontMetrics(self.font)
        
        current_x = start_x
        
        for i, char in enumerate(self.letters):
            char_width = fm.horizontalAdvance(char)
            
            # center of this letter for hit testing
            center_x = current_x + (char_width / 2)
            y = 33 # Baseline
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
            completed = subprocess.run(
                ["ioreg", "-r", "-c", "IOAccelerator"],
                capture_output=True,
                text=True,
                check=False,
            )
            output = completed.stdout or ""
            match = re.search(r'"Device Utilization %"=(\d+)', output)
            if match:
                val = int(match.group(1))
                self.gpu_bar.set_percent(val)
        except Exception as e:
            logger.debug(f"GPU stats fetch failed: {e}")

class SettingsDialog(QDialog):
    # Signals for thread safety
    preview_finished = pyqtSignal()
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
        self.llm_worker = _get_settings_llm_worker()

        # Consolidation: update_ui_state will call refresh_installed_models
        self.llm_worker.progress.connect(self._on_model_progress)
        # Defer model loading to avoid blocking UI on dialog open
        QTimer.singleShot(100, lambda: self.update_ui_state(cfg.api_provider))
        QTimer.singleShot(120, self._restore_model_download_ui_state)
        
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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "model_status"):
            self._render_model_status_preview()

    def _wrap_tab_page(self, page: QWidget) -> QScrollArea:
        """Wrap tab page content so only the active tab body scrolls."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.setWidget(page)
        return scroll

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

        layout.addSpacing(12)
        layout.addWidget(self._make_header("Web Search"))

        self.web_search_checkbox = QCheckBox("Enable Web Search (DuckDuckGo)")
        self.web_search_checkbox.setChecked(cfg.web_search_enabled)
        self.web_search_checkbox.setToolTip("Allows the assistant to search the web. Requires internet access.")
        self._style_checkbox(self.web_search_checkbox, bold=True)
        layout.addWidget(self.web_search_checkbox)

        layout.addStretch()
        self.tabs.addTab(self._wrap_tab_page(page), "General")

    def _init_llm_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Provider Section
        layout.addWidget(self._make_header("AI Provider"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["ollama", "lmstudio", "opencode", "openai", "gemini"])
        self.provider_combo.setCurrentText(cfg.api_provider)
        self.provider_combo.currentTextChanged.connect(self.update_ui_state)
        self._style_combo(self.provider_combo)
        layout.addWidget(self.provider_combo)
        
        self.api_key_edit = QLineEdit(cfg.api_key)
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("API Key...")
        self._style_input(self.api_key_edit)
        layout.addWidget(self.api_key_edit)
        llm_secret_note = QLabel("Secrets entered here are stored in macOS Keychain, not settings.json.")
        llm_secret_note.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(llm_secret_note)

        self.ollama_endpoint_header = self._make_header("Ollama Endpoint")
        layout.addWidget(self.ollama_endpoint_header)
        self.ollama_url_combo = QComboBox()
        self.ollama_url_combo.setEditable(True)
        self._style_combo(self.ollama_url_combo)
        self.ollama_url_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        for url in cfg.ollama_url_history:
            self.ollama_url_combo.addItem(url)
        current_url = cfg.ollama_api_url
        if self.ollama_url_combo.findText(current_url) < 0:
            self.ollama_url_combo.insertItem(0, current_url)
        self.ollama_url_combo.setCurrentText(current_url)
        layout.addWidget(self.ollama_url_combo)

        self.ollama_hint_lbl = QLabel("Use host:port only (e.g. http://100.74.176.49:11434). App adds /api/* automatically.")
        self.ollama_hint_lbl.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.ollama_hint_lbl)

        self.test_ollama_btn = QPushButton("Test Connection")
        self.test_ollama_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_ollama_btn.clicked.connect(self._on_test_ollama_connection)
        self.test_ollama_btn.setStyleSheet(f"""
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
        layout.addWidget(self.test_ollama_btn)

        self.lmstudio_endpoint_header = self._make_header("LM Studio Endpoint")
        layout.addWidget(self.lmstudio_endpoint_header)
        self.lmstudio_url_combo = QComboBox()
        self.lmstudio_url_combo.setEditable(True)
        self._style_combo(self.lmstudio_url_combo)
        self.lmstudio_url_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        for url in cfg.lmstudio_url_history:
            self.lmstudio_url_combo.addItem(url)
        current_lm_url = cfg.lmstudio_api_url
        if self.lmstudio_url_combo.findText(current_lm_url) < 0:
            self.lmstudio_url_combo.insertItem(0, current_lm_url)
        self.lmstudio_url_combo.setCurrentText(current_lm_url)
        layout.addWidget(self.lmstudio_url_combo)

        self.lmstudio_hint_lbl = QLabel("Use host:port only (default: http://127.0.0.1:1234). App uses /v1/* and /api/v0/* automatically.")
        self.lmstudio_hint_lbl.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.lmstudio_hint_lbl)

        self.test_lmstudio_btn = QPushButton("Test Connection")
        self.test_lmstudio_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_lmstudio_btn.clicked.connect(self._on_test_lmstudio_connection)
        self.test_lmstudio_btn.setStyleSheet(f"""
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
        layout.addWidget(self.test_lmstudio_btn)

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

        self.custom_model_key_row = QWidget()
        custom_row_layout = QHBoxLayout(self.custom_model_key_row)
        custom_row_layout.setContentsMargins(0, 0, 0, 0)
        custom_row_layout.setSpacing(8)
        self.custom_model_key_edit = QLineEdit()
        self.custom_model_key_edit.setPlaceholderText("LM Studio model key (e.g. lmstudio-community/...) ")
        self._style_input(self.custom_model_key_edit)
        self.custom_model_download_btn = QPushButton("Download Key")
        self.custom_model_download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.custom_model_download_btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {COLOR_ELECTRIC_BLUE}; font-weight: bold; border: 1px solid {COLOR_ELECTRIC_BLUE}; border-radius: 6px; padding: 6px 12px; }} QPushButton:hover {{ background: rgba(86, 226, 255, 0.1); }}")
        self.custom_model_download_btn.clicked.connect(self._on_custom_model_download)
        custom_row_layout.addWidget(self.custom_model_key_edit, 1)
        custom_row_layout.addWidget(self.custom_model_download_btn)
        layout.addWidget(self.custom_model_key_row)
        
        self.model_status = QLabel("")
        self.model_status.setWordWrap(False)
        self.model_status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.model_status.setStyleSheet("color: #4a5568; font-size: 11px;")
        layout.addWidget(self.model_status)

        self.model_status_toggle = QToolButton()
        self.model_status_toggle.setText("Show details ▾")
        self.model_status_toggle.setCheckable(True)
        self.model_status_toggle.setChecked(False)
        self.model_status_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.model_status_toggle.setStyleSheet("QToolButton { color: #6b7280; border: none; font-size: 11px; padding: 0; text-align: left; }")
        self.model_status_toggle.clicked.connect(self._on_model_status_toggle)
        self.model_status_toggle.hide()
        self._model_status_can_expand = False
        layout.addWidget(self.model_status_toggle)

        self.model_status_details = QLabel("")
        self.model_status_details.setWordWrap(True)
        self.model_status_details.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.model_status_details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.model_status_details.setStyleSheet("color: #6b7280; font-size: 11px;")
        self.model_status_details.hide()
        layout.addWidget(self.model_status_details)

        self.download_rows: dict[str, dict] = {}
        self.download_container = QWidget()
        self.download_container.setStyleSheet("background: transparent;")
        self.download_container_layout = QVBoxLayout(self.download_container)
        self.download_container_layout.setContentsMargins(0, 0, 0, 0)
        self.download_container_layout.setSpacing(6)
        layout.addWidget(self.download_container)
        
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
        self.tabs.addTab(self._wrap_tab_page(page), "Intelligence")

    def _make_scroll_section(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
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
        self.wake_word_checkbox.setToolTip("Use openWakeWord detection in idle mode.")
        self._style_checkbox(self.wake_word_checkbox, bold=True)
        layout.addWidget(self.wake_word_checkbox)

        wake_note = QLabel('Wake phrase: "Hey Jarvis" (fixed openWakeWord model).')
        wake_note.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(wake_note)
        layout.addWidget(QLabel("Wake command silence timeout (seconds)"))
        self.wake_silence_edit = QLineEdit(f"{cfg.wake_record_silence_sec:.2f}")
        self._style_input(self.wake_silence_edit)
        self.wake_word_checkbox.toggled.connect(self.wake_silence_edit.setEnabled)
        self.wake_silence_edit.setEnabled(self.wake_word_checkbox.isChecked())
        layout.addWidget(self.wake_silence_edit)

        layout.addWidget(QLabel("Wake command max duration (seconds)"))
        self.wake_max_edit = QLineEdit(f"{cfg.wake_record_max_sec:.2f}")
        self._style_input(self.wake_max_edit)
        self.wake_word_checkbox.toggled.connect(self.wake_max_edit.setEnabled)
        self.wake_max_edit.setEnabled(self.wake_word_checkbox.isChecked())
        layout.addWidget(self.wake_max_edit)

        layout.addWidget(QLabel("Wake voice threshold (RMS, advanced)"))
        self.wake_vad_edit = QLineEdit(f"{cfg.wake_vad_energy_threshold:.4f}")
        self._style_input(self.wake_vad_edit)
        self.wake_word_checkbox.toggled.connect(self.wake_vad_edit.setEnabled)
        self.wake_vad_edit.setEnabled(self.wake_word_checkbox.isChecked())
        layout.addWidget(self.wake_vad_edit)


        layout.addStretch()
        self.tabs.addTab(self._wrap_tab_page(page), "Speech")
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
        secret_note = QLabel("Secrets entered here are stored in macOS Keychain, not settings.json.")
        secret_note.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(secret_note)

        layout.addSpacing(12)
        layout.addWidget(self._make_header("Quick Commands"))

        self.quick_enabled_checkbox = QCheckBox("Enable quick commands")
        self.quick_enabled_checkbox.setChecked(cfg.quick_commands_enabled)
        self._style_checkbox(self.quick_enabled_checkbox, bold=True)
        layout.addWidget(self.quick_enabled_checkbox)

        self.quick_fuzzy_checkbox = QCheckBox("Enable fuzzy matching fallback")
        self.quick_fuzzy_checkbox.setChecked(cfg.quick_commands_fuzzy_enabled)
        self._style_checkbox(self.quick_fuzzy_checkbox)
        layout.addWidget(self.quick_fuzzy_checkbox)

        self.quick_status_lbl = QLabel("")
        self.quick_status_lbl.setStyleSheet("color: #4a5568; font-size: 11px;")
        layout.addWidget(self.quick_status_lbl)

        refresh_row = QHBoxLayout()
        self.quick_show_all_checkbox = QCheckBox("Show all entities")
        self.quick_show_all_checkbox.setChecked(False)
        self._style_checkbox(self.quick_show_all_checkbox)
        self.quick_show_all_checkbox.toggled.connect(self._on_quick_entity_filter_changed)
        refresh_row.addWidget(self.quick_show_all_checkbox)

        self.quick_refresh_btn = QPushButton("Refresh Devices")
        self.quick_refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quick_refresh_btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {COLOR_ELECTRIC_BLUE}; font-weight: bold; border: 1px solid {COLOR_ELECTRIC_BLUE}; border-radius: 6px; padding: 6px 12px; }} QPushButton:hover {{ background: rgba(86, 226, 255, 0.1); }}")
        self.quick_refresh_btn.clicked.connect(self._on_quick_devices_refresh)
        refresh_row.addWidget(self.quick_refresh_btn)
        refresh_row.addStretch()
        layout.addLayout(refresh_row)

        layout.addWidget(QLabel("Device"))
        self.quick_device_combo = QComboBox()
        self._style_combo(self.quick_device_combo)
        self.quick_device_combo.currentIndexChanged.connect(self._on_quick_device_selected)
        layout.addWidget(self.quick_device_combo)

        layout.addWidget(QLabel("Phrases (comma separated)"))
        self.quick_phrases_edit = QLineEdit()
        self.quick_phrases_edit.setPlaceholderText("kitchen light, wohnzimmer licht")
        self._style_input(self.quick_phrases_edit)
        layout.addWidget(self.quick_phrases_edit)
        self.quick_phrase_hint = QLabel("Saved canonically as: <name> an/on and <name> aus/off. Imperative forms like 'schalte ...' are matched implicitly.")
        self.quick_phrase_hint.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.quick_phrase_hint)

        self.quick_enabled_cmd_checkbox = QCheckBox("Enabled")
        self.quick_enabled_cmd_checkbox.setChecked(True)
        self._style_checkbox(self.quick_enabled_cmd_checkbox)
        layout.addWidget(self.quick_enabled_cmd_checkbox)

        self.quick_create_btn = QPushButton("Create On+Off Commands")
        self.quick_create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quick_create_btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {COLOR_ELECTRIC_BLUE}; font-weight: bold; border: 1px solid {COLOR_ELECTRIC_BLUE}; border-radius: 6px; padding: 6px 12px; }} QPushButton:hover {{ background: rgba(86, 226, 255, 0.1); }}")
        self.quick_create_btn.clicked.connect(self._on_quick_command_create_for_device)
        layout.addWidget(self.quick_create_btn)

        self.quick_list = QListWidget()
        self.quick_list.setMinimumHeight(140)
        self.quick_list.setWordWrap(True)
        self.quick_list.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.quick_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.quick_list.itemSelectionChanged.connect(self._on_quick_command_selected)
        self.quick_list.setStyleSheet("QListWidget { background: #f3f4f6; border: 1px solid #ccc; border-radius: 8px; color: #222; }")
        layout.addWidget(self.quick_list)
        self.quick_list_hint = QLabel("List shows phrase and action target.")
        self.quick_list_hint.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.quick_list_hint)

        quick_btn_row = QHBoxLayout()
        self.quick_delete_btn = QPushButton("Delete Selected")
        self.quick_delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quick_delete_btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {COLOR_ELECTRIC_BLUE}; font-weight: bold; border: 1px solid {COLOR_ELECTRIC_BLUE}; border-radius: 6px; padding: 6px 12px; }} QPushButton:hover {{ background: rgba(86, 226, 255, 0.1); }}")
        self.quick_delete_btn.clicked.connect(self._on_quick_command_delete)
        quick_btn_row.addWidget(self.quick_delete_btn)
        quick_btn_row.addStretch()
        layout.addLayout(quick_btn_row)

        self.quick_selected_id = None
        self._quick_entities = []
        self._reload_quick_commands_ui()
        self._on_quick_devices_refresh()

        layout.addStretch()
        self.tabs.addTab(self._wrap_tab_page(page), "Smart Home")

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

    def _style_checkbox(self, widget, *, bold: bool = False):
        weight = "bold" if bold else "normal"
        widget.setStyleSheet(f"""
            QCheckBox {{ color: #333; font-weight: {weight}; spacing: 6px; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; }}
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

    def _current_ollama_base_url(self) -> str:
        raw = self.ollama_url_combo.currentText() if hasattr(self, "ollama_url_combo") else cfg.ollama_api_url
        return cfg._normalize_ollama_base_url(raw)

    def _current_lmstudio_base_url(self) -> str:
        raw = self.lmstudio_url_combo.currentText() if hasattr(self, "lmstudio_url_combo") else cfg.lmstudio_api_url
        return cfg._normalize_lmstudio_base_url(raw)

    def _on_test_ollama_connection(self):
        if not self.llm_worker:
            self._set_model_status("LLM worker unavailable", "error")
            return

        base = self._current_ollama_base_url()
        result = self.llm_worker.test_ollama_connection(base)
        if result.get("ok"):
            # Apply tested endpoint immediately for this session so model list reflects it.
            cfg.ollama_api_url = base
            self._set_model_status(f"Connected: {result.get('model_count', 0)} model(s) @ {base}", "success")
            self.refresh_installed_models()
        else:
            self._set_model_status(f"Connection failed @ {base}: {result.get('error', 'unknown error')}", "error")

    def _on_test_lmstudio_connection(self):
        if not self.llm_worker:
            self._set_model_status("LLM worker unavailable", "error")
            return

        base = self._current_lmstudio_base_url()
        result = self.llm_worker.test_lmstudio_connection(base)
        if result.get("ok"):
            cfg.lmstudio_api_url = base
            v0_count = result.get("v0_model_count", result.get("model_count", 0))
            v1_count = result.get("v1_model_count", 0)
            selected_ok = result.get("selected_model_visible_in_v1", True)
            diag = (result.get("diagnostic_message") or "").strip()

            status = f"Connected: /api/v0={v0_count}, /v1={v1_count} @ {base}"
            if not selected_ok and diag:
                status = f"{status}. {diag}"
                self._set_model_status(status, "error")
            else:
                self._set_model_status(status, "success")

            self.refresh_installed_models()
        else:
            self._set_model_status(f"Connection failed @ {base}: {result.get('error', 'unknown error')}", "error")

    def update_ui_state(self, provider):
        # same logic but cleaner checks
        is_ollama = (provider == "ollama")
        is_lmstudio = (provider == "lmstudio")
        is_local_model_provider = is_ollama or is_lmstudio
        is_opencode = ("opencode" in provider)
        is_openai_gemini = provider in ["openai", "gemini"]
        
        # Visibility toggles
        self.model_search.setVisible(is_local_model_provider)
        self.model_status.setVisible(is_local_model_provider)
        if hasattr(self, "model_status_toggle"):
            can_expand = bool(getattr(self, "_model_status_can_expand", False))
            self.model_status_toggle.setVisible(is_local_model_provider and can_expand)
        if hasattr(self, "model_status_details"):
            self.model_status_details.setVisible(
                is_local_model_provider
                and bool(getattr(self, "_model_status_can_expand", False))
                and self.model_status_toggle.isChecked()
            )
        self.api_key_edit.setVisible(is_openai_gemini)
        self.model_tabs.setVisible(is_local_model_provider)
        if hasattr(self, "ollama_endpoint_header"):
            self.ollama_endpoint_header.setVisible(is_ollama)
        if hasattr(self, "ollama_url_combo"):
            self.ollama_url_combo.setVisible(is_ollama)
        if hasattr(self, "ollama_hint_lbl"):
            self.ollama_hint_lbl.setVisible(is_ollama)
        if hasattr(self, "test_ollama_btn"):
            self.test_ollama_btn.setVisible(is_ollama)
        if hasattr(self, "lmstudio_endpoint_header"):
            self.lmstudio_endpoint_header.setVisible(is_lmstudio)
        if hasattr(self, "lmstudio_url_combo"):
            self.lmstudio_url_combo.setVisible(is_lmstudio)
        if hasattr(self, "lmstudio_hint_lbl"):
            self.lmstudio_hint_lbl.setVisible(is_lmstudio)
        if hasattr(self, "test_lmstudio_btn"):
            self.test_lmstudio_btn.setVisible(is_lmstudio)
        if hasattr(self, "custom_model_key_row"):
            self.custom_model_key_row.setVisible(is_lmstudio)
        if hasattr(self, "download_container"):
            self.download_container.setVisible(is_local_model_provider)
        if not is_local_model_provider:
            self._set_model_status("", "info")
        # We can't easily hide the layout headers without keeping refs, 
        # but for now let's just handle the inputs.
        
        if is_opencode:
             # Align with opencode model ids from /zen docs
             # Use addItem with (display_name, data=actual_id)
             self.model_edit.clear()
             opencode_models = [("big-pickle", "big-pickle")]
             for display, model_id in opencode_models:
                 self.model_edit.addItem(display, model_id)
             # Find and set saved model
             saved_model = cfg.ollama_model
             idx = self.model_edit.findData(saved_model)
             if idx >= 0:
                 self.model_edit.setCurrentIndex(idx)
             else:
                 self.model_edit.setCurrentIndex(0) # Default to first
        elif is_local_model_provider:
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
        if hasattr(self, "ollama_url_combo"):
            current_base = cfg._normalize_ollama_base_url(self.ollama_url_combo.currentText())
            cfg.ollama_api_url = current_base
            history = [current_base] + [u for u in cfg.ollama_url_history if u != current_base]
            cfg.ollama_url_history = history[:5]
        if hasattr(self, "lmstudio_url_combo"):
            current_lm_base = cfg._normalize_lmstudio_base_url(self.lmstudio_url_combo.currentText())
            cfg.lmstudio_api_url = current_lm_base
            lm_history = [current_lm_base] + [u for u in cfg.lmstudio_url_history if u != current_lm_base]
            cfg.lmstudio_url_history = lm_history[:5]
        # Use data if available, else fall back to text
        model_data = self.model_edit.currentData()
        selected_model = model_data if model_data else self.model_edit.currentText()
        if cfg.api_provider == "lmstudio":
            cfg.lmstudio_model = selected_model
        else:
            cfg.ollama_model = selected_model
        cfg.whisper_model = self.whisper_combo.currentText()
        
        l_text = self.language_combo.currentText()
        if l_text == "English": cfg.language = "en"
        elif l_text == "German": cfg.language = "de"
        else: cfg.language = None
        
        cfg.tts_voice_id = self.voice_combo.currentData()
        cfg.wake_word_enabled = self.wake_word_checkbox.isChecked()
        cfg.wake_word = "hey jarvis"
        if hasattr(self, "quick_enabled_checkbox"):
            cfg.quick_commands_enabled = self.quick_enabled_checkbox.isChecked()
        if hasattr(self, "quick_fuzzy_checkbox"):
            cfg.quick_commands_fuzzy_enabled = self.quick_fuzzy_checkbox.isChecked()

        def _parse_float(value: str, fallback: float) -> float:
            try:
                return float((value or "").strip())
            except Exception:
                return fallback

        wake_silence = _parse_float(self.wake_silence_edit.text() if hasattr(self, "wake_silence_edit") else "", cfg.wake_record_silence_sec)
        wake_max = _parse_float(self.wake_max_edit.text() if hasattr(self, "wake_max_edit") else "", cfg.wake_record_max_sec)
        wake_vad = _parse_float(self.wake_vad_edit.text() if hasattr(self, "wake_vad_edit") else "", cfg.wake_vad_energy_threshold)

        wake_silence = max(0.3, min(3.0, wake_silence))
        wake_max = max(3.0, min(30.0, wake_max))
        wake_vad = max(0.001, min(0.1, wake_vad))
        if wake_max <= wake_silence:
            wake_max = min(30.0, wake_silence + 0.5)

        cfg.wake_record_silence_sec = wake_silence
        cfg.wake_record_max_sec = wake_max
        cfg.wake_vad_energy_threshold = wake_vad
        cfg.ha_url = self.ha_url_edit.text()
        cfg.ha_token = self.ha_token_edit.text()
        if hasattr(self, "telegram_token_edit"):
            cfg.telegram_bot_token = self.telegram_token_edit.text()
        if hasattr(self, "telegram_chat_id_edit"):
            cfg.telegram_chat_id = self.telegram_chat_id_edit.text()
        if hasattr(self, "web_search_checkbox"):
            cfg.web_search_enabled = self.web_search_checkbox.isChecked()

        entered_secrets = [
            self.api_key_edit.text().strip() if hasattr(self, "api_key_edit") else "",
            self.ha_token_edit.text().strip() if hasattr(self, "ha_token_edit") else "",
            self.telegram_token_edit.text().strip() if hasattr(self, "telegram_token_edit") else "",
            self.telegram_chat_id_edit.text().strip() if hasattr(self, "telegram_chat_id_edit") else "",
        ]
        if any(entered_secrets) and not cfg.keychain_available:
            self._show_keychain_warning()
        cfg.save()
        logger.info(f"Settings saved to: {cfg.tts_voice_id}")
        
        if should_switch and self.controller:
             try:
                 self.controller.switch_profile(new_profile)
             except Exception as e:
                 logger.error(f"Could not switch profile: {e}")

        if self.controller and hasattr(self.controller, "apply_runtime_settings"):
            try:
                self.controller.apply_runtime_settings()
            except Exception as e:
                logger.error(f"Could not apply runtime settings: {e}")
        
        self.accept()

    def _show_keychain_warning(self):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Keychain Unavailable")
        msg.setText(
            "Secure secret storage is currently unavailable. "
            "Set secrets with environment variables until Keychain is available."
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setModal(False)
        msg.show()
        self._keychain_warning = msg


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
                remove_profile_files(curr)
            except Exception as e:
                logger.debug(f"Profile file cleanup issue for '{curr}': {e}")
            
            profs = cfg.profiles
            if curr in profs: profs.remove(curr)
            cfg.profiles = profs
            
            # Refresh UI
            self.profile_combo.clear()
            self.profile_combo.addItems(profs)
            self.profile_combo.setCurrentText("default")

    def _set_quick_status(self, text: str, level: str = "info"):
        colors = {
            "info": "#4a5568",
            "success": "#2f855a",
            "error": "#c53030",
        }
        color = colors.get(level, colors["info"])
        self.quick_status_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
        self.quick_status_lbl.setText(text)

    def _ensure_download_row(self, model_name: str) -> dict:
        row = self.download_rows.get(model_name)
        if row:
            return row
        row_widget = QWidget(self.download_container)
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        label = QLabel(model_name)
        label.setStyleSheet("color: #555; font-size: 10px; font-weight: 600;")

        bar = QProgressBar()
        bar.setFixedHeight(8)
        bar.setTextVisible(False)
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setStyleSheet(f"""
            QProgressBar {{ background: #DDD; border: none; border-radius: 4px; }}
            QProgressBar::chunk {{ background: {COLOR_ELECTRIC_BLUE}; border-radius: 4px; }}
        """)

        cancel_btn = QPushButton()
        cancel_btn.setFixedSize(24, 24)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setToolTip(f"Cancel download: {model_name}")
        cancel_btn.setIcon(_load_icon("close.svg"))
        cancel_btn.setIconSize(QSize(10, 10))
        cancel_btn.setStyleSheet("QPushButton { color: #888; border: 1px solid #CCC; border-radius: 12px; font-weight: bold; background: white; } QPushButton:hover { color: red; border-color: red; }")
        cancel_btn.clicked.connect(lambda _=False, n=model_name: self._cancel_download(n))

        row_layout.addWidget(label)
        row_layout.addWidget(bar, 1)
        row_layout.addWidget(cancel_btn)
        self.download_container_layout.addWidget(row_widget)

        row = {"widget": row_widget, "label": label, "bar": bar, "cancel": cancel_btn}
        self.download_rows[model_name] = row
        return row

    def _update_download_row(self, model_name: str, status: str, pct: int):
        row = self._ensure_download_row(model_name)
        display_name = model_name.split("::", 1)[1] if "::" in model_name else model_name
        row["label"].setText(f"{display_name}: {status}")
        row["widget"].setVisible(True)
        if pct >= 0:
            row["bar"].setRange(0, 100)
            row["bar"].setValue(pct)
            row["cancel"].setVisible(True)
            row["cancel"].setEnabled(True)
        else:
            row["bar"].setRange(0, 100)
            row["bar"].setValue(100 if "Finished" in status else 0)
            row["cancel"].setVisible(False)

    def _restore_model_download_ui_state(self):
        if not self.llm_worker:
            return
        provider = self.provider_combo.currentText() if hasattr(self, "provider_combo") else cfg.api_provider
        if provider not in {"ollama", "lmstudio"}:
            return
        states = self.llm_worker.get_download_states() if hasattr(self.llm_worker, "get_download_states") else {}
        if not states:
            return
        active_items = [(m, st) for m, st in states.items() if st.get("active")]
        if not active_items:
            return
        provider_prefix = f"{provider}::"
        visible_items = []
        for model_name, state in active_items:
            if "::" in model_name and not model_name.startswith(provider_prefix):
                continue
            visible_items.append((model_name, state))

        for model_name, state in visible_items:
            status = state.get("status") or f"Downloading: {model_name}"
            pct = int(state.get("pct", -1) or -1)
            self._update_download_row(model_name, status, pct)

        if visible_items:
            self._set_model_status(f"Downloading {len(visible_items)} model(s)...", "info")

    def _format_model_status_details(self, text: str) -> str:
        # Hard-wrap long exception payloads so they never force horizontal growth.
        return "\n".join(textwrap.wrap(text, width=120, break_long_words=True, break_on_hyphens=False))

    def _render_model_status_preview(self):
        full = (getattr(self, "_model_status_full_text", "") or "").strip()
        if not full:
            self.model_status.setText("")
            return
        metrics = self.model_status.fontMetrics()
        width = max(50, self.model_status.width() - 8)
        self.model_status.setText(metrics.elidedText(full, Qt.TextElideMode.ElideRight, width))

    def _on_model_status_toggle(self):
        expanded = bool(self.model_status_toggle.isChecked())
        self.model_status.setVisible(not expanded)
        self.model_status_details.setVisible(expanded)
        self.model_status_toggle.setText("Hide details ▴" if expanded else "Show details ▾")
        if not expanded:
            self._render_model_status_preview()

    def _set_model_status(self, text: str, level: str = "info"):
        colors = {
            "info": "#4a5568",
            "success": "#2f855a",
            "error": "#c53030",
        }
        color = colors.get(level, colors["info"])
        self.model_status.setStyleSheet(f"color: {color}; font-size: 11px;")
        self.model_status_details.setStyleSheet(f"color: {color}; font-size: 11px;")

        clean_text = (text or "").strip()
        self._model_status_full_text = clean_text
        if not clean_text:
            self._model_status_can_expand = False
            self.model_status.setText("")
            self.model_status.show()
            self.model_status_toggle.hide()
            self.model_status_toggle.setChecked(False)
            self.model_status_details.hide()
            self.model_status_details.setText("")
            return

        self.model_status_details.setText(self._format_model_status_details(clean_text))

        needs_expand = len(clean_text) > 90
        self._model_status_can_expand = needs_expand
        self.model_status_toggle.setChecked(False)
        self.model_status.setVisible(True)
        self.model_status_details.setVisible(False)
        self._render_model_status_preview()

        if needs_expand:
            self.model_status_toggle.show()
            self.model_status_toggle.setText("Show details ▾")
        else:
            self.model_status_toggle.hide()

    def _reload_quick_commands_ui(self):
        if not self.controller or not hasattr(self, "quick_list"):
            return
        self.quick_list.clear()
        commands = self.controller.list_quick_commands()
        for cmd in commands:
            phrase_list = [str(p).strip() for p in (cmd.get("phrases", []) or []) if str(p).strip()]
            phrases = ", ".join(phrase_list) if phrase_list else "(no phrases)"
            action = cmd.get("action", {}) or {}
            service = action.get("service", "")
            target = action.get("entity_id", "")
            self.quick_list.addItem(f"{phrases} -> {service} {target}")
            item = self.quick_list.item(self.quick_list.count() - 1)
            item.setData(Qt.ItemDataRole.UserRole, cmd)
        self._set_quick_status(f"Loaded {len(commands)} quick command(s)", "info")

    def _set_quick_entities(self, entities: list[dict]):
        self._quick_entities = entities or []
        current_id = self.quick_device_combo.currentData()
        self.quick_device_combo.blockSignals(True)
        self.quick_device_combo.clear()
        for ent in self._quick_entities:
            label = f"{ent.get('name', ent.get('entity_id', ''))} ({ent.get('entity_id', '')})"
            self.quick_device_combo.addItem(label, ent.get("entity_id"))
        self.quick_device_combo.blockSignals(False)

        if self.quick_device_combo.count() == 0:
            self.quick_phrases_edit.clear()
            return

        if current_id:
            idx = self.quick_device_combo.findData(current_id)
            if idx >= 0:
                self.quick_device_combo.setCurrentIndex(idx)
            else:
                self.quick_device_combo.setCurrentIndex(0)
        else:
            self.quick_device_combo.setCurrentIndex(0)

        self._on_quick_device_selected()

    def _on_quick_entity_filter_changed(self, *_):
        self._on_quick_devices_refresh()

    def _on_quick_devices_refresh(self, *_):
        if not self.controller:
            return
        include_all = self.quick_show_all_checkbox.isChecked()
        result = self.controller.refresh_quick_command_entities(include_all=include_all)
        entities = result.get("entities", [])
        self._set_quick_entities(entities)

        if result.get("status") == "success":
            self._set_quick_status(
                f"Devices refreshed: {result.get('count', len(entities))} available",
                "success",
            )
        else:
            self._set_quick_status(
                f"Refresh failed: {result.get('error', 'unknown error')} (showing previous list)",
                "error",
            )

    def _on_quick_device_selected(self, *_):
        if not self.controller or not self._quick_entities:
            return
        entity_id = self.quick_device_combo.currentData()
        if not entity_id:
            return
        entity = next((e for e in self._quick_entities if e.get("entity_id") == entity_id), None)
        if not entity:
            return
        phrases = self.controller.suggest_quick_phrases(entity)
        self.quick_phrases_edit.setText(", ".join(phrases[:4]))

    def _on_quick_command_selected(self):
        if not self.quick_list.selectedItems():
            self.quick_selected_id = None
            return
        item = self.quick_list.selectedItems()[0]
        cmd = item.data(Qt.ItemDataRole.UserRole) or {}
        self.quick_selected_id = cmd.get("id")

        action = cmd.get("action", {}) or {}
        entity_id = action.get("entity_id")
        if entity_id:
            idx = self.quick_device_combo.findData(entity_id)
            if idx >= 0:
                self.quick_device_combo.setCurrentIndex(idx)

        phrases = cmd.get("phrases", []) or []
        if phrases:
            self.quick_phrases_edit.setText(", ".join(phrases[:8]))
            self._set_quick_status("Loaded selected command for editing.", "info")

    def _on_quick_command_create_for_device(self, *_):
        if not self.controller:
            return
        entity_id = self.quick_device_combo.currentData()
        if not entity_id:
            self._set_quick_status("No device selected.", "error")
            return
        phrases = [p.strip() for p in self.quick_phrases_edit.text().split(",") if p.strip()]
        result = self.controller.create_quick_commands_for_entity(
            entity_id=entity_id,
            phrases=phrases,
            enabled=self.quick_enabled_cmd_checkbox.isChecked(),
        )
        if result.get("status") == "success":
            self._reload_quick_commands_ui()
            self._set_quick_status(
                f"Saved quick commands: +{result.get('created', 0)} new, {result.get('updated', 0)} updated, {result.get('phrase_count', 0)} phrase(s)",
                "success",
            )
        else:
            self._set_quick_status(f"Save failed: {result.get('error', 'unknown error')}", "error")

    def _on_quick_command_delete(self, *_):
        if not self.controller or not self.quick_selected_id:
            self._set_quick_status("Select a quick command to delete.", "error")
            return
        result = self.controller.delete_quick_command(self.quick_selected_id)
        if result.get("status") == "success":
            self.quick_selected_id = None
            self._reload_quick_commands_ui()
            self._set_quick_status("Quick command deleted.", "success")
        else:
            self._set_quick_status("Command not found.", "error")

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
        if not self.llm_worker:
            return
        provider = self.provider_combo.currentText() if hasattr(self, "provider_combo") else cfg.api_provider
        self.installed_models = self.llm_worker.list_models_detailed(provider=provider)

        saved_model = cfg.lmstudio_model if provider == "lmstudio" else cfg.ollama_model
        self.model_edit.clear()
        if self.installed_models:
            for m in self.installed_models:
                self.model_edit.addItem(m.get("name", ""), m.get("name", ""))
        elif provider == "ollama":
            self.model_edit.addItems(["qwen2.5:0.5b"])

        if saved_model:
            idx = self.model_edit.findData(saved_model)
            if idx >= 0:
                self.model_edit.setCurrentIndex(idx)
            else:
                self.model_edit.setCurrentText(saved_model)

        self.render_installed_models()
        self.render_catalog_models()
        if hasattr(self, "model_status"):
            if provider == "ollama":
                self._set_model_status(f"Connected endpoint: {cfg.ollama_api_url}", "info")
            elif provider == "lmstudio":
                selected = cfg.lmstudio_model or "(none selected)"
                self._set_model_status(
                    f"Connected endpoint: {cfg.lmstudio_api_url} | model: {selected}",
                    "info",
                )

    def render_installed_models(self):
        if not hasattr(self, 'installed_container'): return
        self._clear_layout(self.installed_container)
        for m in self.installed_models:
             card = self._create_model_card(m, installed=True)
             self.installed_container.addWidget(card)
        self.installed_container.addStretch() # Keep at top

    def render_catalog_models(self):
        if not hasattr(self, 'catalog_container'):
            return
        self._clear_layout(self.catalog_container)
        text = self.model_search.text().lower().strip()

        # Auto-switch to browse tab if searching
        if text and hasattr(self, 'model_tabs'):
            self.model_tabs.setCurrentIndex(1)

        provider = self.provider_combo.currentText() if hasattr(self, "provider_combo") else cfg.api_provider
        if getattr(self, "_catalog_provider", None) != provider:
            self.catalog_models = []
            self._catalog_provider = provider

        if not hasattr(self, 'catalog_models') or not self.catalog_models:
            self.catalog_models = self.llm_worker.load_catalog(provider=provider)

        def _norm(name: str) -> str:
            n = (name or '').strip().lower()
            return n[:-7] if n.endswith(':latest') else n

        installed_names = {
            _norm((m or {}).get('name', ''))
            for m in getattr(self, 'installed_models', [])
            if isinstance(m, dict)
        }

        matches = []
        for model in self.catalog_models:
            model_name = str(model.get('name', ''))
            if text and text not in model_name.lower():
                continue
            if _norm(model_name) in installed_names:
                continue
            matches.append(model)

        if not matches:
            empty = QLabel('No models to browse (all installed or filtered).')
            empty.setStyleSheet('color: #777; font-size: 11px;')
            self.catalog_container.addWidget(empty)
        else:
            for model in matches:
                card = self._create_model_card(model, installed=False)
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
            btn.clicked.connect(lambda: self._use_model(name))
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
    def _on_custom_model_download(self):
        if not hasattr(self, "custom_model_key_edit"):
            return
        model_key = self.custom_model_key_edit.text().strip()
        if not model_key:
            self._set_model_status("Enter a LM Studio model key.", "error")
            return
        self.download_model(model_key)

    def _use_model(self, name: str):
        provider = self.provider_combo.currentText() if hasattr(self, "provider_combo") else cfg.api_provider
        if provider == "lmstudio":
            self._set_model_status(f"Loading model: {name}...", "info")
            res = self.llm_worker.load_model_lmstudio(name)
            if res.get("status") == "success":
                self.model_edit.setCurrentText(name)
                cfg.lmstudio_model = name
                self._set_model_status(f"Loaded model: {name}", "success")
            else:
                self._set_model_status(f"Load failed: {res.get('error', 'unknown error')}", "error")
            return

        self.model_edit.setCurrentText(name)

    def download_model(self, name):
        self._set_model_status(f"Starting download: {name}...", "info")
        provider = self.provider_combo.currentText() if hasattr(self, "provider_combo") else cfg.api_provider
        download_key = f"{provider}::{name}" if "::" not in name else name
        self._update_download_row(download_key, "Starting...", 0)

        def t():
            self.llm_worker.pull_model(name, provider=provider)
        threading.Thread(target=t, daemon=True).start()

    def _cancel_download(self, model_name: str | None = None):
        if model_name:
            self._set_model_status(f"Cancelling {model_name}...", "info")
            row = self.download_rows.get(model_name)
            if row:
                row["cancel"].setEnabled(False)
            self.llm_worker.cancel_download(model_name)
        else:
            self._set_model_status("Cancelling...", "info")
            self.llm_worker.cancel_download()

    def delete_model(self, name):
        reply = QMessageBox.question(self, "Delete Model", f"Are you sure you want to delete '{name}'?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._set_model_status(f"Deleting {name}...", "info")
            provider = self.provider_combo.currentText() if hasattr(self, "provider_combo") else cfg.api_provider
            def t():
                res = self.llm_worker.remove_model(name, provider=provider)
                success = (res.get("status") == "success")
                error = res.get("error", "")
                self.model_deleted.emit(name, success, error)
            threading.Thread(target=t, daemon=True).start()

    def _on_model_deleted(self, name, success, error):
        if success:
            self._set_model_status(f"Deleted {name}.", "success")
        else:
            self._set_model_status(f"Error deleting: {error}", "error")
            
        QTimer.singleShot(2000, lambda: self._set_model_status("", "info"))
        QTimer.singleShot(100, self.refresh_installed_models)

    def _on_model_progress(self, model_name, status, pct):
        display_name = model_name.split("::", 1)[1] if "::" in model_name else model_name
        self._set_model_status(f"{display_name}: {status}", "info")
        self._update_download_row(model_name, status, pct)

        if pct < 0:
            row = self.download_rows.get(model_name)
            if row and ("Finished" in status or "Cancelled" in status or status.startswith("Error:")):
                QTimer.singleShot(2500, row["widget"].hide)
            if "Finished" in status or "Cancelled" in status:
                QTimer.singleShot(2000, lambda: self._set_model_status("", "info"))
                QTimer.singleShot(100, self.refresh_installed_models)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.default_height = 640
        self.collapsed_height = 230
        self.resize(560, self.default_height + 52)
        
        # 1. Transparent Container to hold the Casing + Shadow
        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(container)
        
        # 2. Layout with margins for the shadow
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(22, 22, 22, 34)
        
        # 3. The Actionable Casing
        self.casing = BioMechCasing(squircle=False)
        container_layout.addWidget(self.casing)
        
        # macOS can show a dark contour artifact around translucent frameless widgets
        # when using an external drop shadow effect. Disable it there for a clean edge.
        if sys.platform != "darwin":
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(36)
            shadow.setXOffset(0)
            shadow.setYOffset(10)
            shadow.setColor(QColor(0, 0, 0, 95))
            self.casing.setGraphicsEffect(shadow)
        else:
            self.casing.setGraphicsEffect(None)
        
        # Layout inside the casing
        layout = QVBoxLayout(self.casing)
        layout.setSpacing(8)
        layout.setContentsMargins(22, 28, 22, 20)
        
        # Header
        header = QHBoxLayout()
        header.setContentsMargins(12, 6, 12, 0)
        
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
                font-family: Menlo, Monaco, 'Courier New', monospace;
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
        self.status_label.setStyleSheet(f"color: #666; font-family: Menlo, Monaco, 'Courier New', monospace; font-weight: bold; font-size: 11px; margin-top: 10px; letter-spacing: 1px;")
        deck_layout.addWidget(self.status_label)

        self.response_timer_label = QLabel("")
        self.response_timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.response_timer_label.setStyleSheet("color: #777; font-family: Menlo, Monaco, 'Courier New', monospace; font-size: 10px;")
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
                self.response_timer_label.setStyleSheet("color: #777; font-family: Menlo, Monaco, 'Courier New', monospace; font-size: 10px;")
                self._response_timer.start()
        elif any(k in upper for k in stop_keys):
            if self._response_timer.isActive():
                self._response_timer.stop()
            self.response_timer_label.setVisible(False)
            self.response_timer_label.setStyleSheet("color: #777; font-family: Menlo, Monaco, 'Courier New', monospace; font-size: 10px;")
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
