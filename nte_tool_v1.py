import sys
import json
import socket
import threading
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QFrame, QLineEdit, QGraphicsScene, 
                             QGraphicsView, QGraphicsPathItem, QGraphicsProxyWidget, 
                             QGraphicsLineItem, QPushButton, QListWidget, QListWidgetItem,
                             QGraphicsTextItem, QSlider, QTextEdit)
from PyQt6.QtGui import QColor, QBrush, QPen, QFont, QPolygonF, QPainter, QPainterPath, QTextOption
from PyQt6.QtCore import Qt, QPointF, pyqtSignal, QObject
import math

# --- Constants ---
APP_BG_COLOR, PRIMARY_TEXT_COLOR, ACCENT_COLOR = "#1e1e1e", "#e0e0e0", "#d9534f"
FRAME_BG_COLOR, FRAME_BORDER_COLOR = "#2a2a2a", "#444444"
HEX_ARCHETYPE_COLOR, HEX_QUALITY_COLOR, HEX_ABILITY_COLOR = QColor(ACCENT_COLOR), QColor("#5a5a5a"), QColor("#3c3c3c")
HEX_BORDER_COLOR = QColor("#1a1a1a")
LINE_COLOR = QColor("#4a4a4a")

class HeroSheetHexagon(QGraphicsPathItem):
    """A display-only hexagon with text wrapping."""
    def __init__(self, hex_type="Ability"):
        super().__init__()
        self.hex_type = hex_type
        self.set_colors()
        self.setPen(QPen(HEX_BORDER_COLOR, 2))
        
        # --- FIX: Using QTextEdit for better alignment and wrapping control ---
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_edit.setStyleSheet("background-color: transparent; border: none; color: #e0e0e0;")
        
        proxy = QGraphicsProxyWidget(self)
        proxy.setWidget(self.text_edit)

    def update_geometry(self, pos, size):
        path = self.create_rounded_hexagon_path(size)
        self.setPath(path)
        self.setPos(pos)
        
        font = QFont("Roboto", max(8, int(size / 6)), QFont.Weight.Bold)
        self.text_edit.setFont(font)
        
        # Position and size the text edit within the hexagon
        proxy = self.childItems()[0]
        proxy.setPos(-size * 0.75, -size * 0.75)
        proxy.resize(size * 1.5, size * 1.5)
        self.text_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_text(self, text):
        self.text_edit.setText(text)
        self.text_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_colors(self):
        color_map = {"Archetype": HEX_ARCHETYPE_COLOR, "Quality": HEX_QUALITY_COLOR, "Ability": HEX_ABILITY_COLOR}
        self.setBrush(QBrush(color_map.get(self.hex_type, HEX_ABILITY_COLOR)))

    def create_rounded_hexagon_path(self, size, radius_ratio=0.1):
        path = QPainterPath()
        radius = size * radius_ratio
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
        for i in range(6):
            path.quadTo(vertices[i], edge_points[i][0])
            path.lineTo(edge_points[i][1])
            
        return path

class HeroSheetView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setBackgroundBrush(QBrush(QColor(FRAME_BG_COLOR)))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.archetype_hex, self.quality_hexes, self.ability_hexes, self.connecting_lines = None, [], [], []
        self.create_hero_sheet_items()
    
    def create_hero_sheet_items(self):
        self.archetype_hex = HeroSheetHexagon("Archetype")
        for _ in range(6): self.quality_hexes.append(HeroSheetHexagon("Quality"))
        for _ in range(12): self.ability_hexes.append(HeroSheetHexagon("Ability"))
        line_pen = QPen(LINE_COLOR, 2, Qt.PenStyle.SolidLine)
        for _ in range(18):
            line = self.scene.addLine(0,0,0,0, line_pen); line.setZValue(-1); self.connecting_lines.append(line)
        for item in [self.archetype_hex] + self.quality_hexes + self.ability_hexes: self.scene.addItem(item)
    
    def populate_sheet(self, char_data):
        self.archetype_hex.set_text(char_data.get("archetype", ""))
        qualities = char_data.get("qualities", [""]*6)
        for i, q_hex in enumerate(self.quality_hexes):
            q_hex.set_text(qualities[i] if i < len(qualities) else "")
        abilities = char_data.get("abilities", [""]*12)
        for i, a_hex in enumerate(self.ability_hexes):
            a_hex.set_text(abilities[i] if i < len(abilities) else "")
        self.update_layout()

    def clear_sheet(self):
        self.populate_sheet({})

    def resizeEvent(self, event): self.update_layout(); super().resizeEvent(event)

    def update_layout(self):
        rect = self.viewport().rect()
        if rect.width() <= 1 or rect.height() <= 1: return
        size_h, size_w = rect.height() / 5.2, rect.width() / 4.6
        size = min(size_h, size_w) * 0.98
        if size < 10: return
        spacing = size * 0.1
        v_dist, h_dist = (size * math.sqrt(3)) + spacing, (size * 1.5) + (spacing * 0.75)
        pos_a = QPointF(0, 0)
        pos_q = [QPointF(0, -v_dist), QPointF(h_dist, -v_dist/2), QPointF(h_dist, v_dist/2), QPointF(0, v_dist), QPointF(-h_dist, v_dist/2), QPointF(-h_dist, -v_dist/2)]
        pos_ab = [QPointF(0, -v_dist*2), QPointF(h_dist, -v_dist*1.5), QPointF(h_dist*2, -v_dist), QPointF(h_dist*2, 0), QPointF(h_dist*2, v_dist), QPointF(h_dist, v_dist*1.5), QPointF(0, v_dist*2), QPointF(-h_dist, v_dist*1.5), QPointF(-h_dist*2, v_dist), QPointF(-h_dist*2, 0), QPointF(-h_dist*2, -v_dist), QPointF(-h_dist, -v_dist*1.5)]
        self.archetype_hex.update_geometry(pos_a, size)
        for i, h in enumerate(self.quality_hexes): h.update_geometry(pos_q[i], size)
        for i, h in enumerate(self.ability_hexes): h.update_geometry(pos_ab[i], size)
        conn_map = {0:[11,0,1], 1:[1,2,3], 2:[3,4,5], 3:[5,6,7], 4:[7,8,9], 5:[9,10,11]}
        line_idx = 0
        for q_idx, a_indices in conn_map.items():
            for a_idx in a_indices:
                if line_idx < len(self.connecting_lines):
                    self.connecting_lines[line_idx].setLine(pos_q[q_idx].x(), pos_q[q_idx].y(), pos_ab[a_idx].x(), pos_ab[a_idx].y())
                    line_idx += 1
        self.setSceneRect(self.scene.itemsBoundingRect())
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

class NetworkSignalEmitter(QObject):
    player_connected = pyqtSignal(str, object)
    player_disconnected = pyqtSignal(str)
    message_received = pyqtSignal(str, object)
    status_updated = pyqtSignal(str)

class NetworkServer:
    def __init__(self, signals):
        self.signals = signals; self.server_socket = None; self.running = False; self.clients = {}
    def start(self, host='0.0.0.0', port=12345):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM); self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((host, port)); self.server_socket.listen(5); self.running = True
            self.signals.status_updated.emit(f"Listening on {host}:{port}..."); threading.Thread(target=self.accept_clients, daemon=True).start()
        except Exception as e: self.signals.status_updated.emit(f"Error: {e}")
    def accept_clients(self):
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept(); client_id = f"{addr[0]}:{addr[1]}"
                self.signals.status_updated.emit(f"Accepted connection from {client_id}")
                threading.Thread(target=self.handle_client, args=(client_socket, client_id), daemon=True).start()
            except OSError: break
    def handle_client(self, client_socket, client_id):
        self.clients[client_id] = {"socket": client_socket}
        try:
            while self.running:
                data_bytes = client_socket.recv(4096)
                if not data_bytes: break
                message = json.loads(data_bytes.decode('utf-8'))
                command = message.get("command")
                if command == "connect":
                    self.clients[client_id]["data"] = message.get("data")
                    self.signals.player_connected.emit(client_id, message.get("data"))
                else:
                    self.signals.message_received.emit(client_id, message)
        except (ConnectionResetError, json.JSONDecodeError): pass
        finally:
            self.signals.player_disconnected.emit(client_id)
            if client_id in self.clients: del self.clients[client_id]
            client_socket.close()
    def send_to_client(self, client_id, message):
        if client_id in self.clients:
            try: self.clients[client_id]["socket"].sendall(json.dumps(message).encode('utf-8'))
            except Exception as e: print(f"Failed to send to {client_id}: {e}")
    def stop(self):
        self.running = False
        if self.server_socket: self.server_socket.close()
        for client_id in self.clients.values(): client_id["socket"].close()
        self.signals.status_updated.emit("Server stopped.")

class NarratorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Not The End - Narrator Console"); self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(self.load_stylesheet())
        self.main_layout = QHBoxLayout(); self.setLayout(self.main_layout)
        self.signals = NetworkSignalEmitter()
        self.signals.player_connected.connect(self.add_player_to_roster)
        self.signals.player_disconnected.connect(self.remove_player_from_roster)
        self.signals.message_received.connect(self.handle_player_message)
        self.signals.status_updated.connect(self.update_status_label)
        self.server = NetworkServer(self.signals)
        self.main_layout.addWidget(self.create_left_panel())
        self.main_layout.addWidget(self.create_center_panel())
        self.main_layout.addWidget(self.create_right_panel())
        
    def create_left_panel(self):
        panel = QFrame(); panel.setFrameShape(QFrame.Shape.StyledPanel); panel.setFixedWidth(350); layout = QVBoxLayout(); panel.setLayout(layout)
        server_label = QLabel("SERVER CONTROLS"); server_label.setObjectName("Header"); layout.addWidget(server_label)
        server_button_layout = QHBoxLayout()
        self.start_server_button = QPushButton("Start Server"); self.start_server_button.clicked.connect(self.start_server)
        self.stop_server_button = QPushButton("Stop Server"); self.stop_server_button.clicked.connect(self.stop_server); self.stop_server_button.setEnabled(False)
        server_button_layout.addWidget(self.start_server_button)
        server_button_layout.addWidget(self.stop_server_button)
        layout.addLayout(server_button_layout)
        self.status_label = QLabel("Status: Idle"); layout.addWidget(self.status_label)
        roster_label = QLabel("PLAYER ROSTER"); roster_label.setObjectName("Header"); layout.addWidget(roster_label)
        self.player_list = QListWidget(); self.player_list.currentItemChanged.connect(self.on_player_changed); layout.addWidget(self.player_list)
        history_label = QLabel("HISTORY LOG"); history_label.setObjectName("Header"); layout.addWidget(history_label)
        self.history_log = QListWidget(); layout.addWidget(self.history_log)
        return panel

    def create_center_panel(self):
        panel = QFrame(); panel.setFrameShape(QFrame.Shape.StyledPanel); layout = QVBoxLayout(); panel.setLayout(layout)
        self.hero_sheet_view = HeroSheetView(); layout.addWidget(self.hero_sheet_view)
        return panel

    def create_right_panel(self):
        panel = QFrame(); panel.setFrameShape(QFrame.Shape.StyledPanel); panel.setFixedWidth(350); layout = QVBoxLayout(); panel.setLayout(layout)
        test_setup_label = QLabel("TEST SETUP"); test_setup_label.setObjectName("Header"); layout.addWidget(test_setup_label)
        
        self.difficulty_label = QLabel("Difficulty: 1")
        self.difficulty_slider = QSlider(Qt.Orientation.Horizontal); self.difficulty_slider.setRange(1, 6); self.difficulty_slider.valueChanged.connect(lambda v: self.difficulty_label.setText(f"Difficulty: {v}"))
        
        self.danger_label = QLabel("Danger: 0 (Not Dangerous)")
        self.danger_slider = QSlider(Qt.Orientation.Horizontal); self.danger_slider.setRange(0, 4); self.danger_slider.valueChanged.connect(self.update_danger_label)
        
        self.send_test_button = QPushButton("Send Test to Player"); self.send_test_button.clicked.connect(self.initiate_test)
        
        layout.addWidget(self.difficulty_label); layout.addWidget(self.difficulty_slider)
        layout.addWidget(self.danger_label); layout.addWidget(self.danger_slider)
        layout.addStretch(1)
        layout.addWidget(self.send_test_button)
        return panel
        
    def update_danger_label(self, value):
        danger_text = {0: "Not Dangerous", 1: "Extremely (1+)", 2: "Very (2+)", 3: "Fairly (3+)", 4: "Slightly (4+)"}.get(value, "Unknown")
        self.danger_label.setText(f"Danger: {value} ({danger_text})")

    def start_server(self): 
        self.server.start()
        self.start_server_button.setEnabled(False); self.stop_server_button.setEnabled(True)
    
    def stop_server(self):
        self.server.stop()
        self.start_server_button.setEnabled(True); self.stop_server_button.setEnabled(False)

    def add_log_entry(self, text): self.history_log.addItem(QListWidgetItem(text)); self.history_log.scrollToBottom()
    def update_status_label(self, text): self.status_label.setText(f"Status: {text}")

    def add_player_to_roster(self, client_id, char_data):
        player_name = char_data.get("name", "Unknown Player")
        item = QListWidgetItem(player_name); item.setData(Qt.ItemDataRole.UserRole, client_id)
        self.player_list.addItem(item); self.add_log_entry(f"PLAYER CONNECTED: {player_name}")
        if self.player_list.count() == 1: self.player_list.setCurrentRow(0)

    def remove_player_from_roster(self, client_id):
        for i in range(self.player_list.count()):
            item = self.player_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == client_id:
                player_name = item.text(); self.player_list.takeItem(i)
                self.add_log_entry(f"PLAYER DISCONNECTED: {player_name}"); break
        if self.player_list.count() == 0: self.hero_sheet_view.clear_sheet()

    def on_player_changed(self, current, previous):
        if not current: self.hero_sheet_view.clear_sheet(); return
        client_id = current.data(Qt.ItemDataRole.UserRole)
        if client_id in self.server.clients:
            char_data = self.server.clients[client_id].get("data")
            if char_data: self.hero_sheet_view.populate_sheet(char_data)

    def initiate_test(self):
        current_item = self.player_list.currentItem()
        if not current_item: self.add_log_entry("ERROR: No player selected."); return
        client_id = current_item.data(Qt.ItemDataRole.UserRole)
        difficulty, danger = self.difficulty_slider.value(), self.danger_slider.value()
        message = {"command": "start_test", "difficulty": difficulty, "danger": danger}
        self.server.send_to_client(client_id, message)
        self.add_log_entry(f"NARRATOR: Sent test to {current_item.text()} (Diff: {difficulty}, Danger: {danger})")

    def handle_player_message(self, client_id, message):
        command = message.get("command")
        if command == "draw_result":
            player_name = "Unknown"
            for i in range(self.player_list.count()):
                item = self.player_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == client_id: player_name = item.text(); break
            successes, complications = message.get("successes"), message.get("complications")
            self.add_log_entry(f"PLAYER ({player_name}): Drew {successes} Successes, {complications} Complications.")
        elif command == "update_sheet": # Handle live updates
             if client_id in self.server.clients:
                self.server.clients[client_id]["data"] = message.get("data")
                # If the updated player is the one selected, refresh the view
                if self.player_list.currentItem() and self.player_list.currentItem().data(Qt.ItemDataRole.UserRole) == client_id:
                    self.hero_sheet_view.populate_sheet(message.get("data"))


    def closeEvent(self, event): self.server.stop(); super().closeEvent(event)
    
    def load_stylesheet(self): 
        return f"""
            QWidget {{ background-color: {APP_BG_COLOR}; color: {PRIMARY_TEXT_COLOR}; font-family: Roboto, sans-serif; }}
            QFrame {{ background-color: {FRAME_BG_COLOR}; border: 1px solid {FRAME_BORDER_COLOR}; border-radius: 8px; padding: 10px; }}
            QLabel#Header {{ font-size: 16px; font-weight: bold; color: {ACCENT_COLOR}; padding-bottom: 5px; border: none; border-bottom: 2px solid {FRAME_BORDER_COLOR}; margin-bottom: 10px; }}
            QLabel {{ font-size: 14px; }}
            QPushButton {{ background-color: {ACCENT_COLOR}; color: white; border: none; padding: 8px 16px; border-radius: 5px; font-weight: bold; }}
            QPushButton:hover {{ background-color: #c9302c; }}
            QPushButton:disabled {{ background-color: #555; }}
            QListWidget {{ background-color: {FRAME_BG_COLOR}; border: none; font-size: 14px; }}
            QListWidget::item {{ padding: 10px; border-bottom: 1px solid {FRAME_BORDER_COLOR}; }}
            QListWidget::item:selected {{ background-color: {ACCENT_COLOR}; color: white; }}
            QSlider::groove:horizontal {{ border: 1px solid #555; height: 8px; background: #333; margin: 2px 0; border-radius: 4px; }}
            QSlider::handle:horizontal {{ background: {ACCENT_COLOR}; border: 1px solid {ACCENT_COLOR}; width: 18px; margin: -5px 0; border-radius: 9px; }}
        """

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = NarratorApp()
    window.show()
    sys.exit(app.exec())
