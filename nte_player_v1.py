import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QFrame, QLineEdit, QGraphicsScene, 
                             QGraphicsView, QGraphicsPolygonItem, QGraphicsTextItem, 
                             QGraphicsProxyWidget)
from PyQt6.QtGui import QColor, QBrush, QPen, QFont, QPolygonF, QPainter, QTextOption
from PyQt6.QtCore import Qt, QPointF
import math

# --- Constants and Configuration ---
APP_BG_COLOR = "#1e1e1e"
PRIMARY_TEXT_COLOR = "#e0e0e0"
ACCENT_COLOR = "#d9534f"
FRAME_BG_COLOR = "#2a2a2a"
FRAME_BORDER_COLOR = "#444444"

HEX_ARCHETYPE_COLOR = QColor(ACCENT_COLOR)
HEX_QUALITY_COLOR = QColor("#5a5a5a")
HEX_ABILITY_COLOR = QColor("#3c3c3c")
HEX_BORDER_COLOR = QColor("#1a1a1a")

class EditableHexagon(QGraphicsPolygonItem):
    """An interactive hexagon on the Hero Sheet for entering traits."""
    def __init__(self, x, y, size, hex_type="Ability", placeholder_text="ABILITY"):
        super().__init__()
        
        self.setPos(x, y)
        self.hex_type = hex_type
        
        # Create the hexagon shape
        polygon = self.create_hexagon_polygon(size)
        self.setPolygon(polygon)
        
        # Set colors based on type
        self.set_colors()
        self.setPen(QPen(HEX_BORDER_COLOR, 2))
        
        # Create an editable text item and embed it
        self.text_item = QLineEdit()
        self.text_item.setPlaceholderText(placeholder_text.upper())
        self.text_item.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_item.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                color: #e0e0e0;
                font-size: 10px;
                font-weight: bold;
            }
        """)
        
        # Use a proxy widget to place the QLineEdit onto the QGraphicsScene
        proxy = QGraphicsProxyWidget(self)
        proxy.setWidget(self.text_item)
        
        # Center the text edit area within the hexagon
        proxy.setPos(-size * 0.8, -size * 0.5)
        proxy.resize(size * 1.6, size)

    def set_colors(self):
        """Sets the hexagon's fill color based on its type."""
        color_map = {
            "Archetype": HEX_ARCHETYPE_COLOR,
            "Quality": HEX_QUALITY_COLOR,
            "Ability": HEX_ABILITY_COLOR
        }
        fill_color = color_map.get(self.hex_type, HEX_ABILITY_COLOR)
        self.setBrush(QBrush(fill_color))

    def create_hexagon_polygon(self, size):
        """Creates the QPolygonF for a flat-topped hexagon."""
        polygon = QPolygonF()
        for i in range(6):
            angle = math.pi / 180 * (60 * i)
            polygon.append(QPointF(size * math.cos(angle), size * math.sin(angle)))
        return polygon

class HeroSheetView(QGraphicsView):
    """A view that displays the entire interactive Hero Sheet."""
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setBackgroundBrush(QBrush(QColor(FRAME_BG_COLOR)))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        self.draw_hero_sheet_layout()
    
    def draw_hero_sheet_layout(self):
        """Creates and places all the hexagons for the character sheet."""
        self.scene.clear()
        
        size = 60
        spacing = 8
        hex_height = size * math.sqrt(3)
        v_dist = hex_height + spacing
        h_dist = (size * 2 * 0.75) + (spacing * 0.75)

        # Create Archetype (center)
        self.scene.addItem(EditableHexagon(0, 0, size, "Archetype", "ARCHETYPE"))
        
        # --- FIX: Create all 6 Qualities (inner ring) ---
        quality_positions = [
            QPointF(0, -v_dist),
            QPointF(h_dist, -v_dist / 2),
            QPointF(h_dist, v_dist / 2),
            QPointF(0, v_dist),
            QPointF(-h_dist, v_dist / 2),
            QPointF(-h_dist, -v_dist / 2),
        ]
        for pos in quality_positions:
            self.scene.addItem(EditableHexagon(pos.x(), pos.y(), size, "Quality", "QUALITY"))

        # --- FIX: Create all 12 Abilities (outer ring) ---
        ability_positions = [
            QPointF(0, -v_dist * 2),
            QPointF(h_dist, -v_dist * 1.5),
            QPointF(h_dist * 2, -v_dist),
            QPointF(h_dist * 2, 0),
            QPointF(h_dist * 2, v_dist),
            QPointF(h_dist, v_dist * 1.5),
            QPointF(0, v_dist * 2),
            QPointF(-h_dist, v_dist * 1.5),
            QPointF(-h_dist * 2, v_dist),
            QPointF(-h_dist * 2, 0),
            QPointF(-h_dist * 2, -v_dist),
            QPointF(-h_dist, -v_dist * 1.5),
        ]
        for pos in ability_positions:
            self.scene.addItem(EditableHexagon(pos.x(), pos.y(), size, "Ability", "ABILITY"))

        items_rect = self.scene.itemsBoundingRect()
        self.setSceneRect(items_rect.adjusted(-20, -20, 20, 20))

    def resizeEvent(self, event):
        """Re-centers the view on resize."""
        super().resizeEvent(event)
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

class PlayerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Not The End - Hero Sheet")
        self.setGeometry(150, 150, 1000, 900)
        self.setStyleSheet(self.load_stylesheet())

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        
        # --- Top Info Panel ---
        top_panel = self.create_top_info_panel()
        self.main_layout.addWidget(top_panel)

        # --- Center: Hero Sheet Hive ---
        self.hero_sheet_view = HeroSheetView()
        self.main_layout.addWidget(self.hero_sheet_view, 1)

        # --- Bottom: Status Panel ---
        bottom_panel = self.create_bottom_status_panel()
        self.main_layout.addWidget(bottom_panel)

    def create_top_info_panel(self):
        """Creates the widget with character name and motivation."""
        panel = QFrame()
        panel_layout = QHBoxLayout()
        panel.setLayout(panel_layout)
        
        name_label = QLabel("MY NAME IS:")
        self.name_input = QLineEdit()
        
        risk_label = QLabel("I WOULD RISK EVERYTHING FOR:")
        self.risk_input = QLineEdit()
        
        panel_layout.addWidget(name_label)
        panel_layout.addWidget(self.name_input, 1)
        panel_layout.addSpacing(40)
        panel_layout.addWidget(risk_label)
        panel_layout.addWidget(self.risk_input, 2)
        
        return panel

    def create_bottom_status_panel(self):
        """Creates the widget for Misfortunes and Mind Statuses."""
        panel = QFrame()
        panel_layout = QHBoxLayout()
        panel.setLayout(panel_layout)

        # Misfortunes Section
        misfortunes_frame = QFrame()
        misfortunes_layout = QVBoxLayout()
        misfortunes_frame.setLayout(misfortunes_layout)
        misfortunes_label = QLabel("WHAT MISFORTUNES AFFLICT ME?")
        misfortunes_label.setObjectName("Header")
        misfortunes_layout.addWidget(misfortunes_label)
        
        misfortunes_grid = QHBoxLayout()
        for i in range(4):
            misfortunes_grid.addWidget(QLineEdit(placeholderText=f"Misfortune {i+1}"))
        misfortunes_layout.addLayout(misfortunes_grid)
        
        # Mind Status Section
        mind_frame = QFrame()
        mind_layout = QVBoxLayout()
        mind_frame.setLayout(mind_layout)
        mind_label = QLabel("WHAT'S GOING ON WITH MY MIND?")
        mind_label.setObjectName("Header")
        mind_layout.addWidget(mind_label)
        
        mind_grid = QHBoxLayout()
        confusion_label = QLabel("<b>CONFUSION</b><br>In the next TEST add 🎲 instead of ⚪ to the BAG.")
        adrenaline_label = QLabel("<b>ADRENALINE</b><br>In the next TEST you must draw at least 4 🎲.")
        mind_grid.addWidget(confusion_label)
        mind_grid.addWidget(adrenaline_label)
        mind_layout.addLayout(mind_grid)

        panel_layout.addWidget(misfortunes_frame, 2)
        panel_layout.addWidget(mind_frame, 1)
        
        return panel

    def load_stylesheet(self):
        """Loads the QSS for styling the application."""
        return f"""
            QWidget {{
                background-color: {APP_BG_COLOR};
                color: {PRIMARY_TEXT_COLOR};
                font-family: Roboto, sans-serif;
            }}
            QFrame {{
                background-color: {FRAME_BG_COLOR};
                border: 1px solid {FRAME_BORDER_COLOR};
                border-radius: 8px;
                padding: 10px;
            }}
            QLabel#Header {{
                font-size: 16px; font-weight: bold; color: {ACCENT_COLOR};
                padding-bottom: 5px; border: none; border-bottom: 2px solid {FRAME_BORDER_COLOR}; margin-bottom: 10px;
            }}
            QLabel {{
                font-size: 14px;
            }}
            QLineEdit {{
                background-color: #333;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                font-size: 14px;
            }}
        """

# --- Main execution block ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PlayerApp()
    window.show()
    sys.exit(app.exec())
