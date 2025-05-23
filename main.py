
import sys
import os
import json
import cv2
import threading
import time
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton, 
                           QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QScrollArea, QGridLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Player")
        self.setGeometry(100, 100, 800, 600)
        
        layout = QVBoxLayout()
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        # Settings button
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.open_settings)
        layout.addWidget(settings_btn)
        
        # Start button
        start_btn = QPushButton("Start")
        start_btn.clicked.connect(self.open_start)
        layout.addWidget(start_btn)

    def open_settings(self):
        self.settings_window = SettingsWindow()
        self.settings_window.show()
        
    def open_start(self):
        self.start_window = StartWindow()
        self.start_window.show()

class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Settings")
        self.setGeometry(150, 150, 500, 300)
        
        layout = QVBoxLayout()
        
        # URL input
        url_layout = QHBoxLayout()
        url_label = QLabel("Video URL:")
        self.url_input = QLineEdit()
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)
        
        # Name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Name:")
        self.name_input = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Preview button
        preview_btn = QPushButton("Generate Preview")
        preview_btn.clicked.connect(self.generate_preview)
        layout.addWidget(preview_btn)
        
        # Save button
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_video)
        layout.addWidget(save_btn)
        
        # Preview label
        self.preview_label = QLabel()
        layout.addWidget(self.preview_label)
        
        self.setLayout(layout)
        
        # Create thumbnails directory
        if not os.path.exists("thumbnails"):
            os.makedirs("thumbnails")
            
    def generate_preview(self):
        url = self.url_input.text()
        name = self.name_input.text()
        if not url or not name:
            return
            
        try:
            cap = cv2.VideoCapture(url)
            ret, frame = cap.read()
            if ret:
                preview_path = f"thumbnails/{name}.jpg"
                cv2.imwrite(preview_path, frame)
                pixmap = QPixmap(preview_path)
                self.preview_label.setPixmap(pixmap.scaled(200, 150, Qt.AspectRatioMode.KeepAspectRatio))
            cap.release()
        except Exception as e:
            print(f"Error generating preview: {e}")
            
    def save_video(self):
        url = self.url_input.text()
        name = self.name_input.text()
        if not url or not name:
            return
            
        preview_path = f"thumbnails/{name}.jpg"
        video_data = {
            "url": url,
            "name": name,
            "preview": preview_path if os.path.exists(preview_path) else ""
        }
        
        videos = []
        if os.path.exists("videos.json"):
            with open("videos.json", "r") as f:
                videos = json.load(f)
                
        videos.append(video_data)
        with open("videos.json", "w") as f:
            json.dump(videos, f)
            
        self.close()

class StartWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Start")
        self.setGeometry(200, 200, 600, 400)
        
        main_layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        grid_layout = QGridLayout()
        
        # Load saved videos
        videos = []
        if os.path.exists("videos.json"):
            with open("videos.json", "r") as f:
                videos = json.load(f)
                
        # Create buttons for each video
        row = 0
        col = 0
        for video in videos:
            btn = QPushButton(video["name"])
            if video["preview"] and os.path.exists(video["preview"]):
                pixmap = QPixmap(video["preview"])
                btn.setIcon(pixmap)
                btn.setIconSize(pixmap.size())
            btn.clicked.connect(lambda checked, url=video["url"]: self.play_video(url))
            grid_layout.addWidget(btn, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1
                
        scroll_content.setLayout(grid_layout)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)
        
    def play_video(self, url):
        self.video_window = QWidget()
        self.video_window.setWindowTitle("Video Player")
        self.video_window.setGeometry(300, 300, 800, 600)
        
        # Create controls
        controls_layout = QHBoxLayout()
        self.play_pause_btn = QPushButton("Pause")
        slower_btn = QPushButton("Slower")
        faster_btn = QPushButton("Faster")
        reset_speed_btn = QPushButton("Reset Speed")
        self.speed_label = QLabel("1.0x")
        
        controls_layout.addWidget(self.play_pause_btn)
        controls_layout.addWidget(slower_btn)
        controls_layout.addWidget(self.speed_label)
        controls_layout.addWidget(faster_btn)
        controls_layout.addWidget(reset_speed_btn)
        
        main_layout = QVBoxLayout()
        self.video_label = QLabel()
        main_layout.addWidget(self.video_label)
        main_layout.addLayout(controls_layout)
        self.video_window.setLayout(main_layout)
        self.video_window.show()
        
        # Video playback setup
        self.cap = cv2.VideoCapture(url)
        self.playing = True
        self.current_speed = 1.0
        self.frame_delay = 1 / (self.cap.get(cv2.CAP_PROP_FPS) * self.current_speed)
        
        # Connect buttons
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        slower_btn.clicked.connect(lambda: self.change_speed(-0.25))
        faster_btn.clicked.connect(lambda: self.change_speed(0.25))
        reset_speed_btn.clicked.connect(self.reset_speed)
        
        # Start video thread
        self.video_thread = threading.Thread(target=self.update_frame)
        self.video_thread.daemon = True
        self.video_thread.start()
    
    def update_frame(self):
        while self.cap.isOpened():
            if self.playing:
                ret, frame = self.cap.read()
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = frame.shape
                    bytes_per_line = ch * w
                    qt_image = QPixmap.fromImage(QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888))
                    scaled_pixmap = qt_image.scaled(self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio)
                    self.video_label.setPixmap(scaled_pixmap)
                    time.sleep(self.frame_delay)
                else:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            else:
                time.sleep(0.1)
    
    def toggle_play_pause(self):
        self.playing = not self.playing
        self.play_pause_btn.setText("Pause" if self.playing else "Play")
        
    def change_speed(self, delta):
        self.current_speed = max(0.25, self.current_speed + delta)
        self.frame_delay = 1 / (self.cap.get(cv2.CAP_PROP_FPS) * self.current_speed)
        self.speed_label.setText(f"{self.current_speed:.2f}x")
        
    def reset_speed(self):
        self.current_speed = 1.0
        self.frame_delay = 1 / self.cap.get(cv2.CAP_PROP_FPS)
        self.speed_label.setText("1.0x")
        
    def change_speed(self, delta):
        self.current_speed = max(0.25, self.current_speed + delta)
        self.player.speed = self.current_speed
        self.speed_label.setText(f"{self.current_speed:.2f}x")
        
    def reset_speed(self):
        self.current_speed = 1.0
        self.player.speed = self.current_speed
        self.speed_label.setText("1.0x")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
