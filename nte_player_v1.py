import sys
import json
import socket
import threading
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QFrame, QLineEdit, QGraphicsScene, 
                             QGraphicsView, QGraphicsPathItem, QGraphicsProxyWidget, 
                             QGraphicsLineItem, QPushButton, QFileDialog, QListWidget,
                             QListWidgetItem, QDialog, QDialogButtonBox, QCheckBox,
                             QStackedWidget, QGraphicsTextItem, QTextEdit)
from PyQt6.QtGui import QColor, QBrush, QPen, QFont, QPolygonF, QPainter, QPainterPath, QTextOption
from PyQt6.QtCore import Qt, QPointF, pyqtSignal, QObject
import math

# --- Constants ---
APP_BG_COLOR, PRIMARY_TEXT_COLOR, ACCENT_COLOR = "#1e1e1e", "#e0e0e0", "#d9534f"
FRAME_BG_COLOR, FRAME_BORDER_COLOR = "#2a2a2a", "#444444"
HEX_ARCHETYPE_COLOR, HEX_QUALITY_COLOR, HEX_ABILITY_COLOR = QColor(ACCENT_COLOR), QColor("#5a5a5a"), QColor("#3c3c3c")
HEX_BORDER_COLOR, LINE_COLOR = QColor("#1a1a1a"), QColor("#4a4a4a")
SUCCESS_COLOR, COMPLICATION_COLOR = QColor("#ffffff"), QColor(ACCENT_COLOR)
TILE_BACK_COLOR, TILE_BORDER_COLOR = QColor("#3c3c3c"), QColor("#555555")
TILE_TYPE_SUCCESS, TILE_TYPE_COMPLICATION = 1, 2
SELECT_BORDER_COLOR = QColor("#f0ad4e")

class EditableHexagon(QGraphicsPathItem):
    """A clickable, editable hexagon on the Hero Sheet with text wrapping."""
    def __init__(self, hex_type="Ability", placeholder_text="ABILITY"):
        super().__init__()
        self.is_selectable = False; self.is_selected = False; self.is_locked = True
        self.hex_type = hex_type; self.placeholder_text = placeholder_text
        self.set_colors(); self.setPen(QPen(HEX_BORDER_COLOR, 2)); self.setAcceptHoverEvents(True)
        
        self.text_item = QGraphicsTextItem(self)
        self.text_item.setDefaultTextColor(QColor(PRIMARY_TEXT_COLOR))
        
        option = self.text_item.document().defaultTextOption()
        option.setWrapMode(QTextOption.WrapMode.WordWrap)
        option.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_item.document().setDefaultTextOption(option)
        
        self.set_locked(True)
    
    def mousePressEvent(self, event):
        if self.is_selectable and self.get_text(): self.set_selected(not self.is_selected)
        if not self.is_locked: self.text_item.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        super().mousePressEvent(event) 

    def set_selectable(self, selectable):
        self.is_selectable = selectable
        if not selectable: self.set_selected(False)

    def set_selected(self, selected):
        self.is_selected = selected
        if self.is_selected: self.setPen(QPen(SELECT_BORDER_COLOR, 4))
        else: self.setPen(QPen(HEX_BORDER_COLOR, 2))

    def update_geometry(self, pos, size):
        self.setPath(self.create_rounded_hexagon_path(size)); self.setPos(pos)
        font = QFont("Roboto", max(8, int(size / 6)), QFont.Weight.Bold)
        self.text_item.setFont(font)
        
        self.text_item.setTextWidth(size * 1.5)
        text_rect = self.text_item.boundingRect()
        self.text_item.setPos(-text_rect.width() / 2, -text_rect.height() / 2)

    def set_locked(self, locked):
        self.is_locked = locked
        current_text = self.get_text()
        if locked:
            self.text_item.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            if current_text == self.placeholder_text:
                self.text_item.setPlainText("")
        else:
            self.text_item.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
            if not current_text:
                self.text_item.setPlainText(self.placeholder_text)
    
    def get_text(self): 
        text = self.text_item.toPlainText().strip()
        return text if text != self.placeholder_text else ""
        
    def set_text(self, text):
        self.text_item.setPlainText(text)
        self.set_locked(self.is_locked)

    def set_colors(self):
        color_map = {"Archetype": HEX_ARCHETYPE_COLOR, "Quality": HEX_QUALITY_COLOR, "Ability": HEX_ABILITY_COLOR}
        self.setBrush(QBrush(color_map.get(self.hex_type, HEX_ABILITY_COLOR)))
    
    def create_rounded_hexagon_path(self, size, radius_ratio=0.1):
        path = QPainterPath(); radius = size * radius_ratio
        vertices = [QPointF(size * math.cos(math.pi / 180 * i), size * math.sin(math.pi / 180 * i)) for i in range(0, 360, 60)]
        if not vertices: return path
        edge_points = []
        for i in range(6):
            p_current, p_next = vertices[i], vertices[(i + 1) % 6]
            vec = p_next - p_current; length = math.hypot(vec.x(), vec.y())
            if length == 0: continue
            vec_unit = vec / length
            edge_points.append((p_current + vec_unit * radius, p_next - vec_unit * radius))
        if not edge_points: return path
        path.moveTo(edge_points[5][1])
        for i in range(6): path.quadTo(vertices[i], edge_points[i][0]); path.lineTo(edge_points[i][1])
        return path

class HexTileItem(QGraphicsPathItem):
    def __init__(self, size, tile_type):
        super().__init__()
        self.tile_type = tile_type; self.is_revealed = False
        self.setPath(self.create_rounded_hexagon_path(size))
        self.setBrush(QBrush(TILE_BACK_COLOR)); self.setPen(QPen(TILE_BORDER_COLOR, 2))
        self.setAcceptHoverEvents(True)
    def reveal(self):
        if self.is_revealed: return
        self.is_revealed = True
        color = SUCCESS_COLOR if self.tile_type == TILE_TYPE_SUCCESS else COMPLICATION_COLOR
        self.setBrush(QBrush(color))
    def hoverEnterEvent(self, event): self.setPen(QPen(SUCCESS_COLOR, 3)); super().hoverEnterEvent(event)
    def hoverLeaveEvent(self, event): self.setPen(QPen(TILE_BORDER_COLOR, 2)); super().hoverLeaveEvent(event)
    def create_rounded_hexagon_path(self, size, radius_ratio=0.1): 
        path = QPainterPath(); radius = size * radius_ratio
        vertices = [QPointF(size * math.cos(math.pi / 180 * i), size * math.sin(math.pi / 180 * i)) for i in range(0, 360, 60)]
        if not vertices: return path
        edge_points = []
        for i in range(6):
            p_current, p_next = vertices[i], vertices[(i+1)%6]
            vec = p_next-p_current; length = math.hypot(vec.x(), vec.y())
            if length == 0: continue
            vec_unit = vec / length
            edge_points.append((p_current + vec_unit * radius, p_next - vec_unit * radius))
        if not edge_points: return path
        path.moveTo(edge_points[5][1])
        for i in range(6): path.quadTo(vertices[i], edge_points[i][0]); path.lineTo(edge_points[i][1])
        return path

class DrawView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(); self.setScene(self.scene); self.setBackgroundBrush(QBrush(QColor(FRAME_BG_COLOR)))
        self.setRenderHint(QPainter.RenderHint.Antialiasing); self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.tiles = []
    def setup_grid(self, complications, successes, tile_size):
        self.scene.clear(); self.tiles.clear()
        tile_types = ([TILE_TYPE_COMPLICATION] * complications) + ([TILE_TYPE_SUCCESS] * successes)
        random.shuffle(tile_types)
        size = tile_size; hex_height = size * math.sqrt(3); v_dist, h_dist = hex_height + 8, (size * 1.5) + 6
        positions = [QPointF(0,0)]
        for r in range(1, 10):
            for i in range(r * 6):
                angle = 2 * math.pi * i / (r * 6)
                positions.append(QPointF(r*h_dist*math.sin(angle), r*v_dist*math.cos(angle)))
        for i, tile_type in enumerate(tile_types):
            if i >= len(positions): break
            pos = positions[i]
            tile = HexTileItem(size, tile_type); tile.setPos(pos); self.scene.addItem(tile); self.tiles.append(tile)
        self.setSceneRect(self.scene.itemsBoundingRect().adjusted(-10,-10,10,10))
    def mousePressEvent(self, event):
        item = self.itemAt(event.pos()); 
        if isinstance(item, HexTileItem): item.reveal()
        super().mousePressEvent(event)
    def get_results(self):
        successes = sum(1 for t in self.tiles if t.is_revealed and t.tile_type == TILE_TYPE_SUCCESS)
        complications = sum(1 for t in self.tiles if t.is_revealed and t.tile_type == TILE_TYPE_COMPLICATION)
        return successes, complications
    def resizeEvent(self, event): self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio); super().resizeEvent(event)

class HeroSheetView(QGraphicsView):
    sheet_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__(); self.scene = QGraphicsScene(); self.setScene(self.scene); self.setBackgroundBrush(QBrush(QColor(FRAME_BG_COLOR))); self.setRenderHint(QPainter.RenderHint.Antialiasing); self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.archetype_hex, self.quality_hexes, self.ability_hexes, self.connecting_lines = None, [], [], []; self.create_hero_sheet_items()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
    def create_hero_sheet_items(self):
        self.archetype_hex = EditableHexagon("Archetype", "ARCHETYPE"); self.scene.addItem(self.archetype_hex)
        # --- FIX: Connect to the document's contentsChanged signal ---
        self.archetype_hex.text_item.document().contentsChanged.connect(self.sheet_changed.emit)
        
        for _ in range(6): 
            hex_item = EditableHexagon("Quality", "QUALITY"); self.quality_hexes.append(hex_item)
            hex_item.text_item.document().contentsChanged.connect(self.sheet_changed.emit); self.scene.addItem(hex_item)
        for _ in range(12): 
            hex_item = EditableHexagon("Ability", "ABILITY"); self.ability_hexes.append(hex_item)
            hex_item.text_item.document().contentsChanged.connect(self.sheet_changed.emit); self.scene.addItem(hex_item)

        line_pen = QPen(LINE_COLOR, 2, Qt.PenStyle.SolidLine)
        for _ in range(18): line = self.scene.addLine(0,0,0,0, line_pen); line.setZValue(-1); self.connecting_lines.append(line)
    def set_sheet_lock_state(self, locked):
        for hex_item in [self.archetype_hex] + self.quality_hexes + self.ability_hexes:
            hex_item.set_locked(locked)
    def set_selection_mode(self, enabled):
        for hex_item in [self.archetype_hex] + self.quality_hexes + self.ability_hexes:
            hex_item.set_selectable(enabled)
    def get_selected_traits_count(self):
        return sum(1 for h in [self.archetype_hex] + self.quality_hexes + self.ability_hexes if h.is_selected)
    def get_current_hex_size(self):
        if self.archetype_hex and self.archetype_hex.path().boundingRect().width() > 0:
            return self.archetype_hex.path().boundingRect().width() / 2
        return 50
    def resizeEvent(self, event): self.update_layout(); super().resizeEvent(event)
    def update_layout(self):
        rect = self.viewport().rect();
        if rect.width() <= 1 or rect.height() <= 1: return
        size_h, size_w = rect.height() / 5.2, rect.width() / 4.6; size = min(size_h, size_w) * 0.98
        if size < 10: return
        spacing = size * 0.1; v_dist, h_dist = (size * math.sqrt(3)) + spacing, (size * 1.5) + (spacing * 0.75)
        pos_a = QPointF(0, 0); pos_q = [QPointF(0, -v_dist), QPointF(h_dist, -v_dist/2), QPointF(h_dist, v_dist/2), QPointF(0, v_dist), QPointF(-h_dist, v_dist/2), QPointF(-h_dist, -v_dist/2)]; pos_ab = [QPointF(0, -v_dist*2), QPointF(h_dist, -v_dist*1.5), QPointF(h_dist*2, -v_dist), QPointF(h_dist*2, 0), QPointF(h_dist*2, v_dist), QPointF(h_dist, v_dist*1.5), QPointF(0, v_dist*2), QPointF(-h_dist, v_dist*1.5), QPointF(-h_dist*2, v_dist), QPointF(-h_dist*2, 0), QPointF(-h_dist*2, -v_dist), QPointF(-h_dist, -v_dist*1.5)]
        self.archetype_hex.update_geometry(pos_a, size)
        for i, h in enumerate(self.quality_hexes): h.update_geometry(pos_q[i], size)
        for i, h in enumerate(self.ability_hexes): h.update_geometry(pos_ab[i], size)
        conn_map = {0:[11,0,1], 1:[1,2,3], 2:[3,4,5], 3:[5,6,7], 4:[7,8,9], 5:[9,10,11]}
        line_idx = 0
        for q_idx, a_indices in conn_map.items():
            for a_idx in a_indices:
                if line_idx < len(self.connecting_lines): self.connecting_lines[line_idx].setLine(pos_q[q_idx].x(), pos_q[q_idx].y(), pos_ab[a_idx].x(), pos_ab[a_idx].y()); line_idx += 1
        self.setSceneRect(self.scene.itemsBoundingRect()); self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

class NetworkSignalEmitter(QObject):
    status_updated = pyqtSignal(str)
    test_initiated = pyqtSignal(object)
    connection_lost = pyqtSignal()

class NetworkClient:
    def __init__(self, signals, player_app_ref):
        self.signals = signals; self.player_app = player_app_ref; self.socket = None; self.running = False
    def connect(self, host, port):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM); self.socket.connect((host, port)); self.running = True
            self.signals.status_updated.emit(f"Connected to {host}:{port}"); self.send_character_data()
            threading.Thread(target=self.listen_for_messages, daemon=True).start()
        except Exception as e: self.signals.status_updated.emit(f"Connection failed: {e}"); self.signals.connection_lost.emit()
    def send_data(self, data):
        if not self.socket or not self.running: return
        try: self.socket.sendall(json.dumps(data).encode('utf-8'))
        except (socket.error, BrokenPipeError) as e: self.disconnect()
    def send_character_data(self): self.send_data({"command": "connect", "data": self.player_app.get_character_data()})
    def send_sheet_update(self): self.send_data({"command": "update_sheet", "data": self.player_app.get_character_data()})
    def listen_for_messages(self):
        while self.running:
            try:
                message_bytes = self.socket.recv(4096)
                if not message_bytes: break
                message = json.loads(message_bytes.decode('utf-8'))
                if message.get("command") == "start_test":
                    self.signals.test_initiated.emit(message)
            except (ConnectionResetError, json.JSONDecodeError, OSError): break
        self.disconnect()
    def disconnect(self):
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        self.signals.connection_lost.emit()
    def stop(self): self.disconnect()

class PlayerApp(QWidget):
    test_initiated = pyqtSignal(object)

    def __init__(self):
        super().__init__(); self.setWindowTitle("Not The End - Hero Sheet"); self.setGeometry(150, 150, 1000, 900)
        self.setStyleSheet(self.load_stylesheet()); self.signals = NetworkSignalEmitter()
        self.signals.status_updated.connect(self.update_status_label)
        self.signals.test_initiated.connect(self.enter_selection_mode)
        self.signals.connection_lost.connect(self.on_connection_lost)
        self.client = NetworkClient(self.signals, self); self.main_layout = QVBoxLayout(); self.setLayout(self.main_layout)
        
        self.top_panel = self.create_top_info_panel()
        self.main_stack = QStackedWidget()
        self.hero_sheet_view = HeroSheetView()
        self.draw_view = DrawView()
        self.bottom_panel = self.create_bottom_status_panel()
        self.test_control_panel = self.create_test_control_panel()
        
        self.hero_sheet_view.sheet_changed.connect(self.on_sheet_change)
        
        self.main_stack.addWidget(self.hero_sheet_view)
        self.main_stack.addWidget(self.draw_view)

        self.main_layout.addWidget(self.top_panel)
        self.main_layout.addWidget(self.main_stack, 1)
        self.main_layout.addWidget(self.bottom_panel)
        self.main_layout.addWidget(self.test_control_panel)

        self.test_control_panel.hide()
        self.current_test_data = {}
        self.toggle_sheet_lock(self.lock_button.isChecked())
    
    def create_top_info_panel(self):
        panel = QFrame(); panel_layout = QVBoxLayout(); panel.setLayout(panel_layout)
        info_layout = QHBoxLayout(); name_label = QLabel("MY NAME IS:"); self.name_input = QLineEdit(); self.name_input.textChanged.connect(self.on_sheet_change)
        risk_label = QLabel("I WOULD RISK EVERYTHING FOR:"); self.risk_input = QLineEdit(); self.risk_input.textChanged.connect(self.on_sheet_change)
        info_layout.addWidget(name_label); info_layout.addWidget(self.name_input, 1); info_layout.addSpacing(20)
        info_layout.addWidget(risk_label); info_layout.addWidget(self.risk_input, 2); panel_layout.addLayout(info_layout)
        conn_layout = QHBoxLayout(); self.ip_input = QLineEdit("127.0.0.1"); self.port_input = QLineEdit("12345")
        self.connect_button = QPushButton("Connect"); self.connect_button.clicked.connect(self.connect_to_server)
        self.status_label = QLabel("Status: Disconnected"); conn_layout.addWidget(QLabel("Host IP:"))
        conn_layout.addWidget(self.ip_input); conn_layout.addWidget(QLabel("Port:")); conn_layout.addWidget(self.port_input)
        conn_layout.addWidget(self.connect_button); conn_layout.addStretch(1); conn_layout.addWidget(self.status_label)
        panel_layout.addLayout(conn_layout)
        file_layout = QHBoxLayout(); self.save_button = QPushButton("Save"); self.save_button.clicked.connect(self.save_character)
        self.load_button = QPushButton("Load"); self.load_button.clicked.connect(self.load_character)
        self.lock_button = QPushButton("Edit Sheet"); self.lock_button.setCheckable(True); self.lock_button.setChecked(True); self.lock_button.clicked.connect(self.toggle_sheet_lock)
        self.history_log = QListWidget(); self.history_log.setMaximumHeight(80)
        file_layout.addWidget(self.history_log, 1); file_layout.addWidget(self.lock_button); file_layout.addWidget(self.save_button); file_layout.addWidget(self.load_button)
        panel_layout.addLayout(file_layout)
        return panel

    def create_bottom_status_panel(self):
        panel = QFrame(); layout = QHBoxLayout(); panel.setLayout(layout); misfortunes_frame = QFrame(); misfortunes_layout = QVBoxLayout(); misfortunes_frame.setLayout(misfortunes_layout); misfortunes_label = QLabel("WHAT MISFORTUNES AFFLICT ME?"); misfortunes_label.setObjectName("Header"); misfortunes_layout.addWidget(misfortunes_label); self.misfortune_inputs = []; grid = QHBoxLayout();
        for i in range(4): field = QLineEdit(placeholderText=f""); field.textChanged.connect(self.on_sheet_change); self.misfortune_inputs.append(field); grid.addWidget(field)
        misfortunes_layout.addLayout(grid); mind_frame = QFrame(); mind_layout = QVBoxLayout(); mind_frame.setLayout(mind_layout); mind_label = QLabel("WHAT'S GOING ON WITH MY MIND?"); mind_label.setObjectName("Header"); mind_layout.addWidget(mind_label); mind_grid = QHBoxLayout(); mind_grid.addWidget(QLabel("<b>CONFUSION</b><br>In the next TEST add 🎲 instead of ⚪ to the BAG.")); mind_grid.addWidget(QLabel("<b>ADRENALINE</b><br>In the next TEST you must draw at least 4 🎲.")); mind_layout.addLayout(mind_grid); layout.addWidget(misfortunes_frame, 2); layout.addWidget(mind_frame, 1); return panel
    
    def create_test_control_panel(self):
        panel = QFrame(); panel.setObjectName("TestControls")
        layout = QHBoxLayout(); panel.setLayout(layout)
        self.test_info_label = QLabel("Test Initiated!")
        self.confirm_traits_button = QPushButton("Confirm Traits & Create Pile")
        self.send_results_button = QPushButton("Send Draw Results")
        self.cancel_test_button = QPushButton("Cancel Test")

        self.confirm_traits_button.clicked.connect(self.enter_draw_mode)
        self.send_results_button.clicked.connect(self.send_results)
        self.cancel_test_button.clicked.connect(self.cancel_test)
        
        layout.addWidget(self.test_info_label)
        layout.addStretch(1)
        layout.addWidget(self.confirm_traits_button)
        layout.addWidget(self.send_results_button)
        layout.addWidget(self.cancel_test_button)
        return panel

    def on_sheet_change(self):
        if self.client.running:
            self.client.send_sheet_update()

    def toggle_sheet_lock(self, checked):
        is_locked = checked
        self.hero_sheet_view.set_sheet_lock_state(is_locked)
        self.lock_button.setText("Edit Sheet" if is_locked else "Lock Sheet")
        self.name_input.setReadOnly(is_locked)
        self.risk_input.setReadOnly(is_locked)
        for field in self.misfortune_inputs: field.setReadOnly(is_locked)

    def enter_selection_mode(self, test_data):
        self.current_test_data = test_data
        self.add_log_entry(f"Test Started! Difficulty: {test_data.get('difficulty')}. Please select your traits.")
        self.hero_sheet_view.set_selection_mode(True)
        self.test_control_panel.show()
        self.confirm_traits_button.show()
        self.send_results_button.hide()
        self.main_stack.setCurrentWidget(self.hero_sheet_view)

    def enter_draw_mode(self):
        difficulty = self.current_test_data.get("difficulty", 0)
        successes = self.hero_sheet_view.get_selected_traits_count()
        self.add_log_entry(f"Created draw pile with {successes} successes and {difficulty} complications.")
        tile_size = self.hero_sheet_view.get_current_hex_size()
        self.draw_view.setup_grid(difficulty, successes, tile_size)
        self.main_stack.setCurrentWidget(self.draw_view)
        self.confirm_traits_button.hide()
        self.send_results_button.show()
    
    def send_results(self):
        successes, complications = self.draw_view.get_results()
        result_message = {"command": "draw_result", "successes": successes, "complications": complications}
        self.client.send_data(result_message)
        self.add_log_entry(f"Results sent: {successes} S, {complications} C.")
        self.cancel_test()

    def cancel_test(self):
        self.hero_sheet_view.set_selection_mode(False)
        self.test_control_panel.hide()
        self.main_stack.setCurrentWidget(self.hero_sheet_view)
        self.current_test_data = {}

    def get_character_data(self):
        return {"name": self.name_input.text(), "risk": self.risk_input.text(), "archetype": self.hero_sheet_view.archetype_hex.get_text(), "qualities": [q.get_text() for q in self.hero_sheet_view.quality_hexes], "abilities": [a.get_text() for a in self.hero_sheet_view.ability_hexes], "misfortunes": [m.text() for m in self.misfortune_inputs]}
    
    def connect_to_server(self):
        host = self.ip_input.text()
        try: port = int(self.port_input.text()); self.client.connect(host, port); self.connect_button.setEnabled(False); self.connect_button.setText("Connected")
        except ValueError: self.update_status_label("Invalid Port")
    
    def on_connection_lost(self):
        self.update_status_label("Disconnected")
        self.connect_button.setEnabled(True)
        self.connect_button.setText("Connect")
    
    def add_log_entry(self, text):
        self.history_log.addItem(QListWidgetItem(text))
        self.history_log.scrollToBottom()

    def update_status_label(self, text): self.status_label.setText(f"Status: {text}"); self.add_log_entry(text)
    
    def save_character(self):
        data = self.get_character_data(); path, _ = QFileDialog.getSaveFileName(self, "Save Character", "", "JSON Files (*.json)")
        if path:
            with open(path, 'w') as f: json.dump(data, f, indent=4)
            self.add_log_entry(f"Character saved to {path}")
    
    def load_character(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Character", "", "JSON Files (*.json)")
        if path:
            with open(path, 'r') as f: data = json.load(f)
            self.name_input.setText(data.get("name", "")); self.risk_input.setText(data.get("risk", "")); 
            self.hero_sheet_view.archetype_hex.set_text(data.get("archetype", ""))
            qualities = data.get("qualities", []); 
            for i, hex_item in enumerate(self.hero_sheet_view.quality_hexes):
                hex_item.set_text(qualities[i] if i < len(qualities) else "")
            abilities = data.get("abilities", []); 
            for i, hex_item in enumerate(self.hero_sheet_view.ability_hexes):
                hex_item.set_text(abilities[i] if i < len(abilities) else "")
            misfortunes = data.get("misfortunes", []); 
            for i, field in enumerate(self.misfortune_inputs):
                field.setText(misfortunes[i] if i < len(misfortunes) else "")

            self.add_log_entry(f"Character loaded from {path}")
            if self.client.running: self.client.send_sheet_update()
    
    def closeEvent(self, event): self.client.stop(); super().closeEvent(event)
    
    def load_stylesheet(self): 
        return f"""
            QWidget {{ background-color: {APP_BG_COLOR}; color: {PRIMARY_TEXT_COLOR}; font-family: Roboto, sans-serif; }}
            QFrame {{ background-color: {FRAME_BG_COLOR}; border: 1px solid {FRAME_BORDER_COLOR}; border-radius: 8px; padding: 10px; }}
            QFrame#TestControls {{ border-top: 2px solid {ACCENT_COLOR}; border-radius: 0; }}
            QLabel#Header {{ font-size: 16px; font-weight: bold; color: {ACCENT_COLOR}; padding-bottom: 5px; border: none; border-bottom: 2px solid {FRAME_BORDER_COLOR}; margin-bottom: 10px; }}
            QLabel {{ font-size: 14px; }}
            QLineEdit {{ background-color: #333; border: 1px solid #555; border-radius: 4px; padding: 5px; font-size: 14px; }}
            QTextEdit {{ background-color: transparent; border: 1px solid #555; border-radius: 4px; padding: 5px; font-size: 14px; }}
            QPushButton {{ background-color: {ACCENT_COLOR}; color: white; border: none; padding: 8px 16px; border-radius: 5px; font-weight: bold; }}
            QPushButton:hover {{ background-color: #c9302c; }}
            QPushButton:disabled {{ background-color: #555; }}
            QDialog {{ background-color: {APP_BG_COLOR}; }}
            QListWidget {{ background-color: #333; border-radius: 4px; border: 1px solid {FRAME_BORDER_COLOR}; }}
        """

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PlayerApp()
    window.show()
    sys.exit(app.exec())
