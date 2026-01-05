from PyQt6.QtCore import (
    QObject, QTimer, QPropertyAnimation, QEasingCurve, 
    QRectF, QPointF, pyqtProperty, pyqtSignal, Qt
)
from PyQt6.QtGui import (
    QColor, QPainter, QPainterPath, QLinearGradient, 
    QPen, QBrush, QRadialGradient, QPolygonF
)
from PyQt6.QtWidgets import QFrame, QGraphicsOpacityEffect

# --- 1. Bio-Mech Constants (Silver/Titanium Edition) ---
GOLDEN_RATIO = 1.61803398875

# Palette: "Titanium Pod" -> "Y2K Gloss White"
COLOR_CHASSIS_DARK  = "#B0B5BA"   # Soft grey shadow (was #889098)
COLOR_CHASSIS_LIGHT = "#FFFFFF"   # Pure white highlight
COLOR_CHASSIS_MID   = "#E0E5EB"   # Glossy white/blue-grey tint

COLOR_SCREEN_BG     = "#050A14"   # Deep Glossy Blue-Black
COLOR_ELECTRIC_BLUE = "#007AFF"   # Deep Sky Blue (Apple-like)
COLOR_PLASMA_CYAN   = "#00DDFF"   # Cyan highlight
COLOR_AMBER_ALERT   = "#FF9500"   # Warm amber

COLOR_TEXT_MAIN     = "#333333"   # Dark Grey
COLOR_TEXT_SCREEN   = "#00AAFF"   # Blue text

def get_squircle_path(rect: QRectF, radius: float, n: float = 4.0) -> QPainterPath:
    path = QPainterPath()
    w, h = rect.width(), rect.height()
    x, y = rect.x(), rect.y()
    if w < 1 or h < 1: return path

    half_w = w / 2.0
    half_h = h / 2.0
    center_x = x + half_w
    center_y = y + half_h
    
    points = []
    import math
    steps = 60
    
    for i in range(steps + 1):
        theta = (2 * math.pi * i) / steps
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        px = half_w * (abs(cos_t) ** (2/n)) * (1 if cos_t >= 0 else -1)
        py = half_h * (abs(sin_t) ** (2/n)) * (1 if sin_t >= 0 else -1)
        points.append(QPointF(center_x + px, center_y + py))
        
    path.addPolygon(QPolygonF(points))
    path.closeSubpath()
    return path

# --- 2. BioMechCasing (Refined for Glossy Light Reflection) ---
class BioMechCasing(QFrame):
    def __init__(self, parent=None, squircle=True):
        super().__init__(parent)
        self.squircle = squircle
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = QRectF(self.rect())
        rect.adjust(2, 2, -2, -2) 
        
        if self.squircle:
            path = get_squircle_path(rect, 0, n=4.0)
        else:
            path = QPainterPath()
            path.addRoundedRect(rect, 20, 20)
            
        base_col = self.bg_color if hasattr(self, 'bg_color') else QColor(COLOR_CHASSIS_MID)
        
        # 1. Main Body Gradient (Top-Left Light -> Bottom-Right Shadow)
        # Soft, pearlescent gradient
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor("#FFFFFF")) 
        grad.setColorAt(0.4, base_col)
        grad.setColorAt(1.0, QColor(COLOR_CHASSIS_DARK))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawPath(path)
        
        # 2. Specular Reflection (The "Gloss" look)
        # Large white soft gloss on top
        gloss_path = QPainterPath()
        gloss_rect = QRectF(rect.x(), rect.y(), rect.width(), rect.height() * 0.5)
        if self.squircle:
             # Clip gloss to top half of squircle? 
             # Simpler: Radial gradient at top left
             pass
             
        gloss = QRadialGradient(rect.topLeft() + QPointF(rect.width()*0.3, rect.height()*0.3), rect.width() * 0.8)
        gloss.setColorAt(0, QColor(255, 255, 255, 180))
        gloss.setColorAt(1, QColor(255, 255, 255, 0))
        
        painter.setBrush(QBrush(gloss))
        painter.drawPath(path)

        # 3. Chrome/Plastic Edge Seam
        stroke_path = get_squircle_path(rect.adjusted(1,1,-1,-1), 0, n=4.0) if self.squircle else QPainterPath()
        if not self.squircle: stroke_path.addRoundedRect(rect.adjusted(1,1,-1,-1), 20, 20)
            
        edge_grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        edge_grad.setColorAt(0, QColor(255, 255, 255, 255)) 
        edge_grad.setColorAt(1, QColor(100, 100, 100, 100))
        
        painter.setPen(QPen(QBrush(edge_grad), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(stroke_path)

# --- 3. Kinetic Animation Controller ---
class KineticAnim(QPropertyAnimation):
    def __init__(self, target, prop, duration=600):
        super().__init__(target, prop)
        self.setDuration(duration)
        self.setEasingCurve(QEasingCurve.Type.OutQuint)

class BreathingAnim(QObject):
    value_changed = pyqtSignal(float)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update)
        self.timer.start(16)
        self.current_t = 0
    def _update(self):
        self.current_t += 16
        import math
        period = 4000 
        angle = (self.current_t % period) / period * 2 * math.pi
        val = (math.sin(angle - math.pi/2) + 1) / 2
        self.value_changed.emit(val)
