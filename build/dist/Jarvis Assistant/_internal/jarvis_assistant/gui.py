from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QScrollArea, QFrame, QGraphicsDropShadowEffect, 
    QDialog, QFormLayout, QLineEdit, QComboBox, QSlider, QDialogButtonBox,
    QCheckBox, QProgressBar, QTabWidget
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, 
    QPoint, QPointF, QRectF, QSize, pyqtProperty, QRect
)
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QRadialGradient, 
    QLinearGradient, QFont, QPainterPath
)
import threading
from .config import cfg, COLOR_BACKGROUND, COLOR_ACCENT_CYAN, COLOR_ACCENT_TEAL
from .utils import logger
from .utils import logger

from .ui_framework import (
    GOLDEN_RATIO, BioMechCasing, COLOR_CHASSIS_DARK, COLOR_CHASSIS_MID,
    COLOR_ELECTRIC_BLUE, COLOR_SCREEN_BG, COLOR_AMBER_ALERT, BreathingAnim, KineticAnim
)

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
        self._spin_angle = 0.0
        
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
            import random
            # Simulate voice amplitude with noise-like jitter
            target = random.uniform(0.1, 0.9)
            # Smoothly interpolate towards target
            self._voice_amplitude = self._voice_amplitude * 0.7 + target * 0.3
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
            
        # 3b. Speaking Animation: Reactive Sound Waves
        if self.state == self.STATE_SPEAKING:
            for i in range(3):
                wave_r = self._core_size * (1.1 + (i * 0.3) + (self._voice_amplitude * 0.5))
                opacity = int(200 * (1 - (i/3.0)) * self._voice_amplitude)
                if opacity < 0: opacity = 0
                w_col = QColor(COLOR_ELECTRIC_BLUE)
                w_col.setAlpha(opacity)
                painter.setPen(QPen(w_col, 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(center, wave_r, wave_r)

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
        label.setFont(QFont("Consolas", 12)) 
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

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(750, 920)
        
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
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet(f"color: #DDD; background: transparent; border: none; font-size: 16px;")
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
        self._init_llm_page()
        self._init_speech_page()
        self._init_ha_page()
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"color: #888; font-weight: bold; border: none; padding: 10px 20px;")
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
        self.update_ui_state(cfg.api_provider)
        
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
        
        layout.addWidget(QLabel("Speech Rate"))
        self.rate_slider = QSlider(Qt.Orientation.Horizontal)
        self.rate_slider.setRange(100, 300)
        self.rate_slider.setValue(cfg.tts_rate)
        self.rate_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid #BBB;
                height: 6px;
                background: #DDD;
                margin: 2px 0;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #EEE, stop:1 #AAA);
                border: 1px solid #777;
                width: 18px;
                margin: -7px 0;
                border-radius: 9px;
            }}
            QSlider::add-page:horizontal {{ background: #DDD; }}
            QSlider::sub-page:horizontal {{ background: {COLOR_ELECTRIC_BLUE}; }}
        """)
        layout.addWidget(self.rate_slider)
        
        # Wake Word
        layout.addSpacing(10)
        self.wake_word_checkbox = QCheckBox("Enable Wake Word")
        self.wake_word_checkbox.setChecked(cfg.wake_word_enabled)
        self.wake_word_checkbox.setStyleSheet(f"""
            QCheckBox {{ color: #333; font-weight: bold; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; border: 1px solid #AAA; border-radius: 4px; background: white; }}
            QCheckBox::indicator:checked {{ background: {COLOR_ELECTRIC_BLUE}; border-color: {COLOR_ELECTRIC_BLUE}; }}
        """)
        layout.addWidget(self.wake_word_checkbox)
        
        self.wake_word_edit = QLineEdit(cfg.wake_word)
        self.wake_word_edit.setPlaceholderText("Wake word...")
        self.wake_word_edit.setEnabled(cfg.wake_word_enabled)
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
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            self.voice_combo.clear()
            
            saved_voice_id = cfg.tts_voice_id
            target_index = -1
            
            for i, v in enumerate(voices):
                name = getattr(v, "name", "voice")
                self.voice_combo.addItem(name, v.id)
                if saved_voice_id and v.id == saved_voice_id:
                    target_index = i
            
            if target_index >= 0:
                self.voice_combo.setCurrentIndex(target_index)
            elif self.voice_combo.count() > 0:
                self.voice_combo.setCurrentIndex(0)
                
        except Exception as e:
            logger.error(f"Failed to populate voices: {e}")
            self.voice_combo.clear()

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
        # We can't easily hide the layout headers without keeping refs, 
        # but for now let's just handle the inputs.
        
        if is_opencode:
             self.model_edit.clear()
             self.model_edit.addItems(["grok-code", "big-pickle", "minimax", "glm-4.7"])
        elif is_ollama:
             self.refresh_installed_models()
        else:
             self.model_edit.clear()
             if provider == "openai": self.model_edit.addItems(["gpt-4o", "gpt-3.5-turbo"])
             if provider == "gemini": self.model_edit.addItems(["gemini-pro"])

    def save_settings(self):
        logger.info("Saving settings...")
        cfg.api_provider = self.provider_combo.currentText()
        cfg.api_key = self.api_key_edit.text()
        cfg.ollama_model = self.model_edit.currentText()
        cfg.whisper_model = self.whisper_combo.currentText()
        
        l_text = self.language_combo.currentText()
        if l_text == "English": cfg.language = "en"
        elif l_text == "German": cfg.language = "de"
        else: cfg.language = None
        
        cfg.tts_rate = self.rate_slider.value()
        cfg.tts_voice_id = self.voice_combo.currentData()
        cfg.wake_word_enabled = self.wake_word_checkbox.isChecked()
        cfg.wake_word = self.wake_word_edit.text()
        cfg.ha_url = self.ha_url_edit.text()
        cfg.ha_token = self.ha_token_edit.text()
        
        cfg.save()
        logger.info(f"Settings saved to: {cfg.tts_voice_id}")
        self.accept()

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
        for m in matches[:5]: # Limit to 5
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
        self.model_status.setText(f"Downloading {name}...")
        def t():
            self.llm_worker.pull_model(name)
            QTimer.singleShot(0, lambda: self.model_status.setText("Download Complete."))
            QTimer.singleShot(100, self.refresh_installed_models)
        threading.Thread(target=t, daemon=True).start()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.default_height = 650
        self.collapsed_height = 420
        self.resize(500, self.default_height)
        
        central = BioMechCasing(squircle=True)
        self.setCentralWidget(central)
        # Layout
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(50, 60, 50, 50) # Safe margins for Squircle 
        
        # Header
        header = QHBoxLayout()
        title = QLabel("JARVIS")
        title.setFont(QFont("Impact", 24))
        title.setStyleSheet(f"color: #444; letter-spacing: 2px;")
        
        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(30, 30)
        settings_btn.setStyleSheet("color: #444; background: transparent; border: 1px solid #999; border-radius: 6px; font-size: 18px;")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.clicked.connect(self.open_settings)

        self.toggle_history_btn = QPushButton("Hide Chat")
        self.toggle_history_btn.setFixedHeight(28)
        self.toggle_history_btn.setStyleSheet("color: #444; background: transparent; border: 1px solid #999; border-radius: 6px; font-size: 12px; padding: 2px 8px;")
        self.toggle_history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_history_btn.clicked.connect(self.toggle_history)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("color: #444; background: transparent; border: 1px solid #999; border-radius: 6px; font-size: 18px;")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.toggle_history_btn)
        header.addWidget(settings_btn)
        header.addWidget(close_btn)
        layout.addLayout(header)
        layout.addStretch() # Center spacer

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
        
        # Control Deck
        deck_layout = QVBoxLayout()
        self.mic_btn = MicButton()
        deck_layout.addWidget(self.mic_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.status_label = QLabel("SYSTEM IDLE")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"color: #666; font-family: Consolas; font-weight: bold; font-size: 11px; margin-top: 10px; letter-spacing: 1px;")
        deck_layout.addWidget(self.status_label)
        
        layout.addLayout(deck_layout)
        layout.addStretch() # Bottom spacer
        
        # Dragging logic
        self.old_pos = None

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.text().lower() == 'm':
            # Trigger mic button click
            self.mic_btn.clicked.emit()
        else:
            super().keyPressEvent(event)

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

    def add_message(self, text, is_user):
        bubble = ChatBubble(text, is_user)
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, bubble)
        QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum()))

    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    def toggle_history(self):
        self.history_visible = not self.history_visible
        
        target_height = self.default_height if self.history_visible else self.collapsed_height
        
        # Animate Geometry
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(500)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuint)
        
        start_rect = self.geometry()
        # Keep center or just grow down? 
        # Usually growing down/up feels better for pods.
        end_rect = QRect(start_rect.x(), start_rect.y(), start_rect.width(), target_height)
        
        self.anim.setStartValue(start_rect)
        self.anim.setEndValue(end_rect)
        
        if self.history_visible:
            self.screen_frame.setVisible(True)
            self.toggle_history_btn.setText("Hide Chat")
        else:
            self.anim.finished.connect(lambda: self.screen_frame.setVisible(False))
            self.toggle_history_btn.setText("Show Chat")
 
        self.anim.start()

    def set_status(self, text):
        self.status_label.setText(text.upper())
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
