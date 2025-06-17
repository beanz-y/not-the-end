import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QSlider, QFrame, QListWidget, 
                             QListWidgetItem, QGraphicsScene, QGraphicsView, 
                             QGraphicsPolygonItem, QGraphicsTextItem, QSpinBox)
from PyQt6.QtGui import QColor, QBrush, QPen, QFont, QFontDatabase, QPolygonF, QPainter
from PyQt6.QtCore import Qt, QPointF, pyqtSignal, QObject
import random
import math

# --- Constants and Configuration ---
APP_BG_COLOR = "#1e1e1e"
PRIMARY_TEXT_COLOR = "#e0e0e0"
ACCENT_COLOR = "#d9534f" # A muted red/orange for highlights
FRAME_BG_COLOR = "#2a2a2a"
FRAME_BORDER_COLOR = "#444444"
SUCCESS_COLOR = QColor("#ffffff")
COMPLICATION_COLOR = QColor(ACCENT_COLOR)
TILE_BACK_COLOR = QColor("#3c3c3c")
TILE_BORDER_COLOR = QColor("#555555")

# Enum-like constants for tile types
TILE_TYPE_SUCCESS = 1
TILE_TYPE_COMPLICATION = 2

class HexTileItem(QGraphicsPolygonItem):
    """
    A clickable, flippable hexagonal tile for the draw grid.
    This class is now simpler and no longer inherits from QObject.
    """
    def __init__(self, x, y, size, tile_type):
        super().__init__()
        
        polygon = self.create_hexagon_polygon(size)
        self.setPolygon(polygon)
        
        self.setPos(x, y)
        self.size = size
        self.tile_type = tile_type
        self.is_revealed = False
        self.is_active = False

        self.setBrush(QBrush(TILE_BACK_COLOR))
        self.setPen(QPen(TILE_BORDER_COLOR, 2))
        self.setAcceptHoverEvents(True)

    def create_hexagon_polygon(self, size):
        """Creates the QPolygonF for a flat-topped hexagon."""
        polygon = QPolygonF()
        for i in range(6):
            angle = math.pi / 180 * (60 * i)
            polygon.append(QPointF(size * math.cos(angle), size * math.sin(angle)))
        return polygon

    def reveal(self):
        """Flips the tile to show its type."""
        if self.is_revealed:
            return
            
        self.is_revealed = True
        color = SUCCESS_COLOR if self.tile_type == TILE_TYPE_SUCCESS else COMPLICATION_COLOR
        self.setBrush(QBrush(color))
        self.update()

    def reset(self):
        """Resets the tile to its face-down state."""
        self.is_revealed = False
        self.is_active = False
        self.setBrush(QBrush(TILE_BACK_COLOR))
        self.setPen(QPen(TILE_BORDER_COLOR, 2))
        self.update()

    def hoverEnterEvent(self, event):
        """Highlights the tile on hover if it's clickable."""
        if self.is_active and not self.is_revealed:
            self.setPen(QPen(SUCCESS_COLOR, 3))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Removes highlight when the mouse leaves."""
        self.setPen(QPen(TILE_BORDER_COLOR, 2))
        super().hoverLeaveEvent(event)

class HexGridDrawView(QGraphicsView):
    """A view to display and interact with a grid of hexagonal tiles."""
    drawFinished = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setBackgroundBrush(QBrush(QColor(FRAME_BG_COLOR)))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        self.tiles = []
        self.draw_limit = 0
        self.drawn_count = 0
        self.successes_drawn = 0
        self.complications_drawn = 0
        
        self.setMinimumHeight(250)

    def setup_grid(self, successes, complications):
        """Clears and populates the grid with new face-down tiles in a Hero Sheet-style honeycomb layout."""
        self.scene.clear()
        self.tiles.clear()

        tile_types = ([TILE_TYPE_SUCCESS] * successes) + ([TILE_TYPE_COMPLICATION] * complications)
        random.shuffle(tile_types)

        if not tile_types:
            self.scene.update()
            return

        # --- NEW: Layout logic to match the Hero Sheet's concentric rings ---
        size = 30
        spacing = 6
        hex_height = size * math.sqrt(3)
        v_dist = hex_height + spacing
        h_dist = (size * 2 * 0.75) + (spacing * 0.75)

        # Pre-calculated positions for the Hero Sheet layout
        # (Center, Ring 1, Ring 2)
        positions = [
            # Layer 0 (Center)
            QPointF(0, 0),
            # Layer 1 (Inner Ring of 6)
            QPointF(h_dist, -v_dist / 2),
            QPointF(h_dist, v_dist / 2),
            QPointF(0, v_dist),
            QPointF(-h_dist, v_dist / 2),
            QPointF(-h_dist, -v_dist / 2),
            QPointF(0, -v_dist),
            # Layer 2 (Outer Ring of 12)
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
        
        total_tiles_to_place = len(tile_types)
        for i in range(total_tiles_to_place):
            if i >= len(positions):
                # Fallback for more than 19 tiles, though not expected in this layout
                break
                
            pos = positions[i]
            tile_type = tile_types[i]
            tile = HexTileItem(pos.x(), pos.y(), size, tile_type)
            self.scene.addItem(tile)
            self.tiles.append(tile)

        items_rect = self.scene.itemsBoundingRect()
        self.setSceneRect(items_rect)
        self.centerOn(items_rect.center())

    def mousePressEvent(self, event):
        """Handles click events for the entire view, revealing tiles directly."""
        item = self.itemAt(event.pos())
        if isinstance(item, HexTileItem) and item.is_active and not item.is_revealed:
            item.reveal()
            self.on_tile_revealed(item.tile_type)
        super().mousePressEvent(event)

    def start_interactive_draw(self, num_to_draw):
        """Activates the tiles for the player to click."""
        self.draw_limit = num_to_draw
        self.drawn_count = 0
        self.successes_drawn = 0
        self.complications_drawn = 0
        for tile in self.tiles:
            tile.is_active = True
    
    def on_tile_revealed(self, tile_type):
        """Callback logic for when a tile is revealed."""
        self.drawn_count += 1
        if tile_type == TILE_TYPE_SUCCESS:
            self.successes_drawn += 1
        else:
            self.complications_drawn += 1

        if self.drawn_count >= self.draw_limit:
            for tile in self.tiles:
                tile.is_active = False
            self.drawFinished.emit(self.successes_drawn, self.complications_drawn)

    def reset_grid(self):
        """Resets all tiles to their initial state."""
        self.drawn_count = 0
        self.draw_limit = 0
        self.successes_drawn = 0
        self.complications_drawn = 0
        for tile in self.tiles:
            tile.reset()
            
    def resizeEvent(self, event):
        """Re-centers the view on resize."""
        super().resizeEvent(event)
        items_rect = self.scene.itemsBoundingRect()
        self.centerOn(items_rect.center())


class NarratorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Not The End - Narrator Console")
        self.setGeometry(100, 100, 1200, 800)
        
        self.setStyleSheet(self.load_stylesheet())

        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)

        # --- Left Panel ---
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.Shape.StyledPanel)
        left_panel.setFixedWidth(350)
        left_panel_layout = QVBoxLayout()
        left_panel.setLayout(left_panel_layout)

        player_roster_label = QLabel("PLAYER ROSTER")
        player_roster_label.setObjectName("Header")
        self.player_list = QListWidget()
        
        left_panel_layout.addWidget(player_roster_label)
        left_panel_layout.addWidget(self.player_list)
        
        selected_player_label = QLabel("CURRENT TEST")
        selected_player_label.setObjectName("Header")
        left_panel_layout.addWidget(selected_player_label)
        
        self.traits_for_test_label = QLabel("Traits Used:")
        self.traits_for_test_spinbox = QSpinBox()
        self.traits_for_test_spinbox.setRange(0, 19) # Max tiles in the layout
        self.traits_for_test_spinbox.valueChanged.connect(self.update_grid_setup)
        
        traits_layout = QHBoxLayout()
        traits_layout.addWidget(self.traits_for_test_label)
        traits_layout.addWidget(self.traits_for_test_spinbox)
        left_panel_layout.addLayout(traits_layout)

        # --- Center Panel ---
        center_panel = QFrame()
        center_panel.setFrameShape(QFrame.Shape.StyledPanel)
        center_panel_layout = QVBoxLayout()
        center_panel.setLayout(center_panel_layout)
        
        self.hex_grid_view = HexGridDrawView()
        self.hex_grid_view.drawFinished.connect(self.display_final_results)
        
        center_panel_layout.addWidget(self.hex_grid_view)
        
        self.player_list.currentItemChanged.connect(self.on_player_changed)
        
        # --- Right Panel ---
        right_panel = QFrame()
        right_panel.setFrameShape(QFrame.Shape.StyledPanel)
        right_panel.setFixedWidth(350)
        right_panel_layout = QVBoxLayout()
        right_panel.setLayout(right_panel_layout)
        
        test_setup_label = QLabel("TEST SETUP")
        test_setup_label.setObjectName("Header")
        right_panel_layout.addWidget(test_setup_label)

        self.difficulty_label = QLabel("Difficulty: 3")
        self.difficulty_slider = QSlider(Qt.Orientation.Horizontal)
        self.difficulty_slider.setRange(1, 6)
        self.difficulty_slider.setValue(3)
        self.difficulty_slider.valueChanged.connect(self.update_grid_setup)

        self.danger_label = QLabel("Danger: 0 (Not Dangerous)")
        self.danger_slider = QSlider(Qt.Orientation.Horizontal)
        self.danger_slider.setRange(0, 4)
        self.danger_slider.setValue(0)
        self.danger_slider.valueChanged.connect(self.update_grid_setup)
        
        right_panel_layout.addWidget(self.difficulty_label)
        right_panel_layout.addWidget(self.difficulty_slider)
        right_panel_layout.addWidget(self.danger_label)
        right_panel_layout.addWidget(self.danger_slider)
        
        draw_setup_label = QLabel("PERFORM DRAW")
        draw_setup_label.setObjectName("Header")
        right_panel_layout.addWidget(draw_setup_label)
        
        self.draw_count_label = QLabel("Tiles to Reveal:")
        self.draw_count_spinbox = QSpinBox()
        self.draw_count_spinbox.setRange(1, 40)
        
        draw_count_layout = QHBoxLayout()
        draw_count_layout.addWidget(self.draw_count_label)
        draw_count_layout.addWidget(self.draw_count_spinbox)
        right_panel_layout.addLayout(draw_count_layout)

        self.begin_draw_button = QPushButton("Begin Draw")
        self.begin_draw_button.clicked.connect(self.begin_interactive_draw)
        right_panel_layout.addWidget(self.begin_draw_button)
        
        self.reset_button = QPushButton("Reset Test")
        self.reset_button.clicked.connect(self.reset_test)
        self.reset_button.setEnabled(False)
        right_panel_layout.addWidget(self.reset_button)
        
        results_label = QLabel("RESULTS")
        results_label.setObjectName("Header")
        self.results_display = QLabel("Setup a test to begin...")
        self.results_display.setWordWrap(True)
        self.results_display.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        right_panel_layout.addWidget(results_label)
        right_panel_layout.addWidget(self.results_display, 1)

        self.main_layout.addWidget(left_panel)
        self.main_layout.addWidget(center_panel, 1)
        self.main_layout.addWidget(right_panel)

        # Final setup call
        self.populate_mock_players()
        if self.player_list.count() > 0:
            self.player_list.setCurrentRow(0)
        
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
            }}
            QLabel#Header {{
                font-size: 16px; font-weight: bold; color: {ACCENT_COLOR};
                padding: 5px; border-bottom: 2px solid {FRAME_BORDER_COLOR}; margin-bottom: 10px;
            }}
            QLabel {{ font-size: 14px; }}
            QPushButton {{
                background-color: {ACCENT_COLOR}; color: white; border: none;
                padding: 10px; border-radius: 5px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #c9302c; }}
            QPushButton:pressed {{ background-color: #ac2925; }}
            QPushButton:disabled {{ background-color: #555; color: #aaa; }}
            QListWidget {{ background-color: {FRAME_BG_COLOR}; border: none; font-size: 14px; }}
            QListWidget::item {{ padding: 10px; border-bottom: 1px solid {FRAME_BORDER_COLOR}; }}
            QListWidget::item:selected {{ background-color: {ACCENT_COLOR}; color: white; }}
            QSlider::groove:horizontal {{
                border: 1px solid {FRAME_BORDER_COLOR}; height: 4px; background: {FRAME_BORDER_COLOR};
                margin: 2px 0; border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {ACCENT_COLOR}; border: 1px solid {ACCENT_COLOR};
                width: 18px; height: 18px; margin: -8px 0; border-radius: 9px;
            }}
            QSpinBox {{ 
                padding: 5px; background-color: #333; border: 1px solid #555;
                border-radius: 4px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                subcontrol-origin: border;
                width: 16px;
                border-left: 1px solid #555;
            }}
            QSpinBox::up-button {{
                subcontrol-position: top right;
            }}
            QSpinBox::down-button {{
                subcontrol-position: bottom right;
            }}
            QSpinBox::up-arrow {{
                width: 10px; height: 10px;
                image: url(data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'><path d='M5 2 L2 7 L8 7 Z' fill='%23e0e0e0'/></svg>);
            }}
            QSpinBox::down-arrow {{
                width: 10px; height: 10px;
                image: url(data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'><path d='M5 8 L2 3 L8 3 Z' fill='%23e0e0e0'/></svg>);
            }}
        """

    def populate_mock_players(self):
        """Populates player list with mock data."""
        mock_data = [
            {"name": "Lothar", "total_traits": 8, "archetype": "Bounty Hunter"},
            {"name": "Etienne", "total_traits": 8, "archetype": "Revenant"},
            {"name": "Lilian", "total_traits": 8, "archetype": "Priestess"}
        ]
        for player in mock_data:
            item = QListWidgetItem(f"{player['name']} ({player['archetype']})")
            item.setData(Qt.ItemDataRole.UserRole, player)
            self.player_list.addItem(item)
            
    def on_player_changed(self):
        """Updates UI when a new player is selected."""
        current_item = self.player_list.currentItem()
        if not current_item:
            return
            
        player_data = current_item.data(Qt.ItemDataRole.UserRole)
        
        self.traits_for_test_spinbox.blockSignals(True)
        # The range is based on the total number of traits the player has.
        self.traits_for_test_spinbox.setRange(0, player_data.get('total_traits', 8))
        self.traits_for_test_spinbox.setValue(0)
        self.traits_for_test_spinbox.blockSignals(False)

        self.update_grid_setup()

    def update_grid_setup(self):
        """Updates labels and the hex grid when any test parameter changes."""
        difficulty = self.difficulty_slider.value()
        self.difficulty_label.setText(f"Difficulty: {difficulty}")

        danger_val = self.danger_slider.value()
        danger_text = {
            0: "Not Dangerous", 1: "Extremely Dangerous (Leaves on 1+)",
            2: "Very Dangerous (Leaves on 2+)", 3: "Fairly Dangerous (Leaves on 3+)",
            4: "Slightly Dangerous (Leaves on 4+)"
        }.get(danger_val, "Unknown")
        self.danger_label.setText(f"Danger: {danger_val} ({danger_text})")
        
        num_successes = self.traits_for_test_spinbox.value()
        num_complications = self.difficulty_slider.value()
        self.hex_grid_view.setup_grid(num_successes, num_complications)
        self.results_display.setText("Grid is ready. Set number of tiles to reveal and begin draw.")
        self.reset_button.setEnabled(False)
        self.begin_draw_button.setEnabled(True)

    def begin_interactive_draw(self):
        """Starts the interactive draw process."""
        num_to_draw = self.draw_count_spinbox.value()
        total_tiles = len(self.hex_grid_view.tiles)

        if num_to_draw == 0:
            self.results_display.setText("Cannot reveal 0 tiles. Please select at least 1.")
            return

        if num_to_draw > total_tiles:
            self.results_display.setText(f"Cannot draw {num_to_draw}. Only {total_tiles} tiles in grid.")
            return

        self.hex_grid_view.start_interactive_draw(num_to_draw)
        self.results_display.setText(f"Player, please reveal {num_to_draw} tile(s)...")
        self.begin_draw_button.setEnabled(False)
        self.reset_button.setEnabled(True)
    
    def reset_test(self):
        """Resets the entire test interface."""
        self.hex_grid_view.reset_grid()
        self.update_grid_setup()

    def display_final_results(self, successes, complications):
        """Displays the final results after the interactive draw is complete."""
        result_text = f"<h3>Draw Complete:</h3>"
        result_text += f"<p><b>Successes:</b> <font color='{SUCCESS_COLOR.name()}'>{successes}</font></p>"
        result_text += f"<p><b>Complications:</b> <font color='{COMPLICATION_COLOR.name()}'>{complications}</font></p>"
        
        danger_level = self.danger_slider.value()
        if danger_level > 0:
            leaves_scene = False
            if danger_level == 1 and complications >= 1: leaves_scene = True
            if danger_level == 2 and complications >= 2: leaves_scene = True
            if danger_level == 3 and complications >= 3: leaves_scene = True
            if danger_level == 4 and complications >= 4: leaves_scene = True
            
            if leaves_scene:
                result_text += f"<p><b><font color='{ACCENT_COLOR}'>The hero leaves the scene!</font></b></p>"
        
        self.results_display.setText(result_text)

# --- Main execution block ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = NarratorApp()
    window.show()
    sys.exit(app.exec())
