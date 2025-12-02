from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QScrollArea, QFrame, QGraphicsDropShadowEffect, 
    QDialog, QFormLayout, QLineEdit, QComboBox, QSlider, QDialogButtonBox
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, 
    QPoint, QPointF, QRectF, QSize
)
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QRadialGradient, 
    QLinearGradient, QFont, QPainterPath
)
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
        
        layout = QFormLayout()
        
        self.model_edit = QLineEdit(cfg.ollama_model)
        self.whisper_combo = QComboBox()
        self.whisper_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.whisper_combo.setCurrentText(cfg.whisper_model)
        
        # Language Settings
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
        
        # Wake word settings
        from PyQt6.QtWidgets import QCheckBox, QHBoxLayout
        self.wake_word_checkbox = QCheckBox("Enable Wake Word")
        self.wake_word_checkbox.setChecked(cfg.wake_word_enabled)
        self.wake_word_checkbox.setStyleSheet("color: white;")
        
        self.wake_word_edit = QLineEdit(cfg.wake_word)
        self.wake_word_edit.setPlaceholderText("Enter wake word (e.g., jarvis)")
        self.wake_word_edit.setEnabled(cfg.wake_word_enabled)
        
        # Connect checkbox to enable/disable text field
        self.wake_word_checkbox.toggled.connect(self.wake_word_edit.setEnabled)
        
        wake_word_layout = QHBoxLayout()
        wake_word_layout.addWidget(self.wake_word_checkbox)
        wake_word_layout.addWidget(self.wake_word_edit)
        
        # Home Assistant Settings
        self.ha_url_edit = QLineEdit(cfg.ha_url)
        self.ha_token_edit = QLineEdit(cfg.ha_token)
        self.ha_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        
        layout.addRow("Ollama Model:", self.model_edit)
        layout.addRow("Whisper Model:", self.whisper_combo)
        layout.addRow("Language:", self.language_combo)
        layout.addRow("TTS Rate:", self.rate_slider)
        layout.addRow("Wake Word:", wake_word_layout)
        layout.addRow("HA URL:", self.ha_url_edit)
        layout.addRow("HA Token:", self.ha_token_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        self.setLayout(layout)

    def save_settings(self):
        cfg.ollama_model = self.model_edit.text()
        cfg.whisper_model = self.whisper_combo.currentText()
        
        lang_text = self.language_combo.currentText()
        if lang_text == "English":
            cfg.language = "en"
        elif lang_text == "German":
            cfg.language = "de"
        else:
            cfg.language = None
            
        cfg.tts_rate = self.rate_slider.value()
        cfg.wake_word_enabled = self.wake_word_checkbox.isChecked()
        cfg.wake_word = self.wake_word_edit.text()
        
        cfg.ha_url = self.ha_url_edit.text()
        cfg.ha_token = self.ha_token_edit.text()
        
        cfg.save()
        self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(500, 700)
        
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
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("color: white; background: transparent; border: none; font-size: 18px;")
        close_btn.clicked.connect(self.close)
        
        header.addWidget(title)
        header.addStretch()
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

    def set_status(self, text):
        self.status_label.setText(text)
