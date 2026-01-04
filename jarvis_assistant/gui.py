from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QScrollArea, QFrame, QGraphicsDropShadowEffect, 
    QDialog, QFormLayout, QLineEdit, QComboBox, QSlider, QDialogButtonBox,
    QCheckBox, QProgressBar, QTabWidget
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, 
    QPoint, QPointF, QRectF, QSize
)
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QRadialGradient, 
    QLinearGradient, QFont, QPainterPath
)
import threading
from .config import cfg, COLOR_BACKGROUND, COLOR_ACCENT_CYAN, COLOR_ACCENT_TEAL

class MicButton(QWidget):
    clicked = pyqtSignal()
    
    STATE_IDLE = 0
    STATE_LISTENING = 1
    STATE_THINKING = 2
    STATE_SPEAKING = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120)
        self.state = self.STATE_IDLE
        self.angle = 0
        self.pulse_factor = 0.0
        self.pulse_direction = 1
        
        # Animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)  # ~60 FPS

    def set_state(self, state):
        self.state = state
        self.update()

    def mousePressEvent(self, event):
        self.clicked.emit()

    def update_animation(self):
        # Pulse logic
        if self.state in [self.STATE_IDLE, self.STATE_LISTENING, self.STATE_SPEAKING]:
            speed = 0.02 if self.state == self.STATE_IDLE else 0.05
            if self.state == self.STATE_SPEAKING:
                speed = 0.08
            
            self.pulse_factor += speed * self.pulse_direction
            if self.pulse_factor > 1.0:
                self.pulse_factor = 1.0
                self.pulse_direction = -1
            elif self.pulse_factor < 0.0:
                self.pulse_factor = 0.0
                self.pulse_direction = 1
        
        # Rotation logic
        if self.state == self.STATE_THINKING:
            self.angle = (self.angle + 5) % 360
            
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = QPoint(self.width() // 2, self.height() // 2)
        radius = 40
        
        # Glow effect
        glow_radius = radius + (10 * self.pulse_factor)
        if self.state == self.STATE_LISTENING:
            glow_radius = radius + (20 * self.pulse_factor)
        
        glow_color = QColor(COLOR_ACCENT_CYAN)
        glow_color.setAlpha(100)
        
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Draw outer glow
        gradient = QRadialGradient(QPointF(center), glow_radius)
        gradient.setColorAt(0, glow_color)
        gradient.setColorAt(1, Qt.GlobalColor.transparent)
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(QPointF(center), glow_radius, glow_radius)
        
        # Draw main circle
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        pen = QPen(QColor(COLOR_ACCENT_CYAN))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(center, radius, radius)
        
        # Draw Icon (Simple Mic)
        painter.setPen(QPen(QColor(COLOR_ACCENT_CYAN), 2))
        painter.setBrush(QBrush(QColor(COLOR_ACCENT_CYAN)))
        # Simple mic shape
        mic_rect = QRectF(center.x() - 10, center.y() - 15, 20, 30)
        painter.drawRoundedRect(mic_rect, 10, 10)
        
        # Draw Thinking Spinner
        if self.state == self.STATE_THINKING:
            painter.setPen(QPen(QColor(COLOR_ACCENT_TEAL), 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            path = QPainterPath()
            path.arcMoveTo(QRectF(center.x()-50, center.y()-50, 100, 100), self.angle)
            path.arcTo(QRectF(center.x()-50, center.y()-50, 100, 100), self.angle, 90)
            painter.drawPath(path)

class ChatBubble(QFrame):
    def __init__(self, text, is_user=False):
        super().__init__()
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.is_user = is_user
        
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        self.setLayout(layout)
        
        label = QLabel(text)
        label.setWordWrap(True)
        label.setFont(QFont("Segoe UI", 12))
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        label.setStyleSheet(f"color: white; padding: 10px; border-radius: 15px; background-color: {'#0b1018' if is_user else '#0f1520'}; border: 1px solid {COLOR_ACCENT_CYAN if is_user else '#333'};")
        
        if is_user:
            layout.addStretch()
            layout.addWidget(label)
        else:
            layout.addWidget(label)
            layout.addStretch()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setStyleSheet(f"background-color: {COLOR_BACKGROUND}; color: white;")
        self.setMinimumWidth(640)
        self.setMinimumHeight(720)
        self.resize(700, 760)
        self.llm_worker = None
        self.installed_models = []
        self.catalog_models = []
        
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        tabs = QTabWidget()
        tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #333; border-radius: 6px; } QTabBar::tab { padding: 8px 14px; }")

        # --- LLM Settings ---
        from PyQt6.QtWidgets import QGroupBox
        llm_page = QWidget()
        llm_page_layout = QVBoxLayout(llm_page)
        llm_page_layout.setContentsMargins(10, 10, 10, 10)
        llm_group = QGroupBox("LLM Settings")
        llm_group.setStyleSheet(f"QGroupBox {{ border: 1px solid #333; border-radius: 5px; margin-top: 10px; font-weight: bold; }} QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; }}")
        llm_layout = QVBoxLayout()
        llm_layout.setSpacing(10)
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["ollama", "opencode", "openai", "gemini"])
        self.provider_combo.setCurrentText(cfg.api_provider)
        self.provider_combo.currentTextChanged.connect(self.update_ui_state)
        
        self.api_key_edit = QLineEdit(cfg.api_key)
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("sk-...")
        
        form = QFormLayout()
        form.setSpacing(10)
        self.api_key_label = QLabel("API Key:")
        form.addRow("Provider:", self.provider_combo)
        form.addRow(self.api_key_label, self.api_key_edit)
        llm_layout.addLayout(form)

        # Model Selection (installed dropdown)
        self.model_edit = QComboBox()
        self.model_edit.setEditable(False)
        self.model_edit.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

        dropdown_row = QFormLayout()
        dropdown_row.addRow("Current Model:", self.model_edit)
        llm_layout.addLayout(dropdown_row)

        # Model browser (installed + catalog)
        from .llm_client import LLMWorker
        self.llm_worker = LLMWorker()
        self.catalog_models = self.llm_worker.load_catalog()

        self.model_search = QLineEdit()
        self.model_search.setPlaceholderText("Search models (e.g., qwen, llama3, mistral)...")
        self.model_search.textChanged.connect(self.render_catalog_models)

        self.model_status = QLabel("")
        self.model_status.setStyleSheet("color: #7dd3fc;")

        self.installed_container = QVBoxLayout()
        self.catalog_container = QVBoxLayout()

        llm_layout.addWidget(QLabel("Installed Models"))
        installed_widget = QWidget()
        installed_widget.setLayout(self.installed_container)
        installed_widget.setStyleSheet("border: 1px solid #333; border-radius: 6px; padding: 8px;")
        llm_layout.addWidget(installed_widget)

        llm_layout.addWidget(QLabel("Find & Manage Models"))
        llm_layout.addWidget(self.model_search)
        catalog_widget = QWidget()
        catalog_widget.setLayout(self.catalog_container)
        catalog_widget.setStyleSheet("border: 1px solid #333; border-radius: 6px; padding: 8px;")
        llm_layout.addWidget(catalog_widget)
        llm_layout.addWidget(self.model_status)

        llm_group.setLayout(llm_layout)
        llm_page_layout.addWidget(llm_group)
        tabs.addTab(llm_page, "LLM")

        # --- Speech Settings ---
        speech_page = QWidget()
        speech_page_layout = QVBoxLayout(speech_page)
        speech_page_layout.setContentsMargins(10, 10, 10, 10)
        speech_group = QGroupBox("Speech Settings")
        speech_group.setStyleSheet(f"QGroupBox {{ border: 1px solid #333; border-radius: 5px; margin-top: 10px; font-weight: bold; }} QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; }}")
        speech_layout = QFormLayout()
        speech_layout.setSpacing(10)
        
        self.whisper_combo = QComboBox()
        self.whisper_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.whisper_combo.setCurrentText(cfg.whisper_model)
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Auto", "English", "German"])
        current_lang = cfg.language
        if current_lang == "en":
            self.language_combo.setCurrentText("English")
        elif current_lang == "de":
            self.language_combo.setCurrentText("German")
        else:
            self.language_combo.setCurrentText("Auto")

        self.rate_slider = QSlider(Qt.Orientation.Horizontal)
        self.rate_slider.setRange(100, 300)
        self.rate_slider.setValue(cfg.tts_rate)
        self.voice_combo = QComboBox()
        self.voice_combo.setEditable(False)
        self._populate_voices()
        
        self.wake_word_checkbox = QCheckBox("Enable Wake Word")
        self.wake_word_checkbox.setChecked(cfg.wake_word_enabled)
        self.wake_word_checkbox.setStyleSheet("color: white;")
        
        self.wake_word_edit = QLineEdit(cfg.wake_word)
        self.wake_word_edit.setPlaceholderText("Wake word (e.g., jarvis)")
        self.wake_word_edit.setEnabled(cfg.wake_word_enabled)
        self.wake_word_checkbox.toggled.connect(self.wake_word_edit.setEnabled)
        
        wake_layout = QHBoxLayout()
        wake_layout.addWidget(self.wake_word_checkbox)
        wake_layout.addWidget(self.wake_word_edit)
        
        speech_layout.addRow("Whisper:", self.whisper_combo)
        speech_layout.addRow("Language:", self.language_combo)
        speech_layout.addRow("TTS Rate:", self.rate_slider)
        speech_layout.addRow("Voice:", self.voice_combo)
        speech_layout.addRow("Wake Word:", wake_layout)
        speech_group.setLayout(speech_layout)
        speech_page_layout.addWidget(speech_group)
        tabs.addTab(speech_page, "Speech")

        # --- Home Assistant ---
        ha_page = QWidget()
        ha_page_layout = QVBoxLayout(ha_page)
        ha_page_layout.setContentsMargins(10, 10, 10, 10)
        ha_group = QGroupBox("Home Assistant")
        ha_group.setStyleSheet(f"QGroupBox {{ border: 1px solid #333; border-radius: 5px; margin-top: 10px; font-weight: bold; }} QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; }}")
        ha_layout = QFormLayout()
        ha_layout.setSpacing(10)
        
        self.ha_url_edit = QLineEdit(cfg.ha_url)
        self.ha_token_edit = QLineEdit(cfg.ha_token)
        self.ha_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        
        ha_layout.addRow("URL:", self.ha_url_edit)
        ha_layout.addRow("Token:", self.ha_token_edit)
        ha_group.setLayout(ha_layout)
        ha_page_layout.addWidget(ha_group)
        tabs.addTab(ha_page, "Home Assistant")

        main_layout.addWidget(tabs)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)
        
        # Initialize model listings before showing
        self.refresh_installed_models()
        scroll.setWidget(content_widget)
        root_layout.addWidget(scroll)

        self.update_ui_state(cfg.api_provider)

    def _populate_voices(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            self.voice_combo.clear()
            for v in voices:
                name = getattr(v, "name", "voice")
                self.voice_combo.addItem(name, v.id)
            # Select current voice if set
            if cfg.tts_voice_id:
                idx = self.voice_combo.findData(cfg.tts_voice_id)
                if idx >= 0:
                    self.voice_combo.setCurrentIndex(idx)
        except Exception:
            # Fallback: leave empty
            self.voice_combo.clear()
    def update_ui_state(self, provider):
        is_ollama = provider == "ollama"
        is_opencode = provider.startswith("opencode")
        is_openai = provider == "openai"
        is_gemini = provider == "gemini"

        # API key: disabled for opencode-grok, enabled otherwise (but only meaningful for openai/gemini)
        self.api_key_edit.setEnabled(not is_opencode and not is_ollama)
        self.api_key_label.setVisible(not is_ollama)
        self.api_key_edit.setVisible(not is_ollama)
        if is_opencode:
            self.api_key_edit.setPlaceholderText("Not required for Grok (OpenCode)")
            self.api_key_edit.setText("")
        elif is_ollama:
            self.api_key_edit.setPlaceholderText("sk-... (not used by Ollama)")
            self.api_key_edit.setText("")
        else:
            self.api_key_edit.setPlaceholderText("sk-...")

        # Model dropdown content/behavior by provider
        if is_opencode:
            self.model_edit.setEditable(False)
            self.model_edit.clear()
            self.model_edit.addItems(["grok-code", "big-pickle"])
            self.model_edit.setCurrentText("grok-code")
        elif is_ollama:
            self.model_edit.setEditable(False)
            self.model_edit.clear()
            if self.installed_models:
                self.model_edit.addItems([m["name"] for m in self.installed_models])
            else:
                self.model_edit.addItems(["qwen2.5:0.5b", "llama3.2:1b"])
            self.model_edit.setCurrentText(cfg.ollama_model)
        else:
            # openai/gemini: offer curated dropdown
            self.model_edit.setEditable(False)
            self.model_edit.clear()
            if is_openai:
                models = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
            elif is_gemini:
                models = ["gemini-2.5-flash", "gemini-2.5-pro"]
            else:
                models = []
            if models:
                self.model_edit.addItems(models)
                self.model_edit.setCurrentIndex(0)
            else:
                self.model_edit.addItem(cfg.ollama_model)

        if hasattr(self, "model_search"):
            self.model_search.setEnabled(is_ollama)
        # Show/hide model browser widgets for clarity (only for Ollama)
        for widget in [getattr(self, "model_search", None), getattr(self, "model_status", None)]:
            if widget:
                widget.setVisible(is_ollama)
        if hasattr(self, "installed_container"):
            self._set_layout_children_visible(self.installed_container, is_ollama)
        if hasattr(self, "catalog_container"):
            self._set_layout_children_visible(self.catalog_container, is_ollama)

    def save_settings(self):
        cfg.api_provider = self.provider_combo.currentText()
        cfg.api_key = self.api_key_edit.text()
        cfg.ollama_model = self.model_edit.currentText()
        cfg.whisper_model = self.whisper_combo.currentText()
        
        lang_text = self.language_combo.currentText()
        if lang_text == "English":
            cfg.language = "en"
        elif lang_text == "German":
            cfg.language = "de"
        else:
            cfg.language = None
            
        cfg.tts_rate = self.rate_slider.value()
        cfg.tts_voice_id = self.voice_combo.currentData()
        cfg.wake_word_enabled = self.wake_word_checkbox.isChecked()
        cfg.wake_word = self.wake_word_edit.text()
        
        cfg.ha_url = self.ha_url_edit.text()
        cfg.ha_token = self.ha_token_edit.text()
        
        cfg.save()
        self.accept()

    # --- Model management helpers ---
    def _clear_layout(self, layout: QVBoxLayout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

    def _set_layout_children_visible(self, layout: QVBoxLayout, visible: bool):
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget():
                item.widget().setVisible(visible)
            elif item.layout():
                self._set_layout_children_visible(item.layout(), visible)

    def render_installed_models(self):
        self._clear_layout(self.installed_container)
        if not self.installed_models:
            lbl = QLabel("No models installed yet.")
            lbl.setStyleSheet("color: #888;")
            self.installed_container.addWidget(lbl)
            return
        for model in self.installed_models:
            row = self._model_row(model, installed=True)
            self.installed_container.addWidget(row)

    def render_catalog_models(self):
        text = self.model_search.text().strip().lower() if hasattr(self, "model_search") else ""
        matches = []
        for m in self.catalog_models:
            if text and text not in m.get("name", "").lower():
                continue
            matches.append(m)
        if text and not matches:
            # Provide a generic pull option for unknown models
            matches.append({"name": text, "size": "unknown", "hardware": "Unknown requirements", "note": "Not in catalog; will attempt direct pull."})

        self._clear_layout(self.catalog_container)
        if not matches:
            lbl = QLabel("Type to search common models.")
            lbl.setStyleSheet("color: #888;")
            self.catalog_container.addWidget(lbl)
            return

        installed_names = {m["name"] for m in self.installed_models}
        for m in matches:
            row = self._model_row(
                m,
                installed=m.get("name") in installed_names
            )
            self.catalog_container.addWidget(row)

    def _model_row(self, model_info: dict, installed: bool):
        name = model_info.get("name", "unknown")
        size = model_info.get("size", "unknown")
        hardware = model_info.get("hardware", "Requirements unknown")
        note = model_info.get("note", "")

        row_widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        label = QLabel(f"{name} — {size} • {hardware}")
        label.setStyleSheet("color: white;")
        label.setToolTip(note)
        layout.addWidget(label)
        layout.addStretch()

        if installed:
            use_btn = QPushButton("Use")
            use_btn.setStyleSheet("padding: 4px 10px;")
            use_btn.clicked.connect(lambda _, n=name: self.model_edit.setCurrentText(n))
            layout.addWidget(use_btn)

            remove_btn = QPushButton("Remove")
            remove_btn.setStyleSheet("padding: 4px 10px;")
            remove_btn.clicked.connect(lambda _, n=name: self.remove_model(n))
            layout.addWidget(remove_btn)
        else:
            download_btn = QPushButton("Download")
            download_btn.setStyleSheet("padding: 4px 10px;")
            download_btn.clicked.connect(lambda _, n=name: self.download_model(n))
            layout.addWidget(download_btn)

        row_widget.setLayout(layout)
        return row_widget

    def refresh_installed_models(self):
        if not self.llm_worker:
            return
        self.installed_models = self.llm_worker.list_models_detailed()
        # Update dropdown
        self.model_edit.clear()
        if self.installed_models:
            self.model_edit.addItems([m["name"] for m in self.installed_models])
        else:
            self.model_edit.addItems(["qwen2.5:0.5b", "llama3.2:1b"])
        self.model_edit.setCurrentText(cfg.ollama_model)
        self.render_installed_models()
        self.render_catalog_models()

    def download_model(self, name: str):
        if not self.llm_worker:
            return
        self.model_status.setText(f"Downloading {name}...")

        def task():
            res = self.llm_worker.pull_model(name)

            def finish():
                if res.get("status") == "success":
                    self.model_status.setText(f"Downloaded {name}.")
                    self.refresh_installed_models()
                    self.model_edit.setCurrentText(name)
                else:
                    self.model_status.setText(f"Download failed: {res.get('error', 'unknown error')}")
            QTimer.singleShot(0, finish)

        threading.Thread(target=task, daemon=True).start()

    def remove_model(self, name: str):
        if not self.llm_worker:
            return
        if name == self.model_edit.currentText():
            self.model_status.setText("Cannot remove the currently selected model.")
            return
        self.model_status.setText(f"Removing {name}...")

        def task():
            res = self.llm_worker.remove_model(name)

            def finish():
                if res.get("status") == "success":
                    self.model_status.setText(f"Removed {name}.")
                    self.refresh_installed_models()
                else:
                    self.model_status.setText(f"Remove failed: {res.get('error', 'unknown error')}")
            QTimer.singleShot(0, finish)

        threading.Thread(target=task, daemon=True).start()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.default_height = 700
        self.collapsed_height = 320
        self.resize(500, self.default_height)
        
        # Central Widget
        central = QFrame()
        central.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BACKGROUND};
                border-radius: 20px;
                border: 1px solid #333;
            }}
        """)
        self.setCentralWidget(central)
        
        # Layout
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("JARVIS")
        title.setFont(QFont("Impact", 24))
        title.setStyleSheet(f"color: {COLOR_ACCENT_CYAN}; letter-spacing: 2px;")
        
        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(30, 30)
        settings_btn.setStyleSheet("color: white; background: transparent; border: none; font-size: 18px;")
        settings_btn.clicked.connect(self.open_settings)

        self.toggle_history_btn = QPushButton("Hide History")
        self.toggle_history_btn.setFixedHeight(28)
        self.toggle_history_btn.setStyleSheet("color: white; background: transparent; border: 1px solid #444; border-radius: 6px; font-size: 12px; padding: 2px 8px;")
        self.toggle_history_btn.clicked.connect(self.toggle_history)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("color: white; background: transparent; border: none; font-size: 18px;")
        close_btn.clicked.connect(self.close)
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.toggle_history_btn)
        header.addWidget(settings_btn)
        header.addWidget(close_btn)
        layout.addLayout(header)
        
        # Chat Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)
        self.history_visible = True
        
        # Mic Area
        mic_layout = QVBoxLayout()
        self.mic_btn = MicButton()
        mic_layout.addWidget(self.mic_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.status_label = QLabel("Idle")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #888; font-size: 12px; margin-top: 10px;")
        mic_layout.addWidget(self.status_label)
        
        layout.addLayout(mic_layout)
        
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
        self.scroll_area.setVisible(self.history_visible)
        self.toggle_history_btn.setText("Show History" if not self.history_visible else "Hide History")
        target_height = self.collapsed_height if not self.history_visible else self.default_height
        self.resize(self.width(), target_height)

    def set_status(self, text):
        self.status_label.setText(text)
