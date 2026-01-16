import sys
import os
import threading
import datetime

# Logging setup for debugging
def log_error(msg):
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    log_path = os.path.join(desktop, "epub_generator_debug.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now()}] {msg}\n")

try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                 QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                                 QFileDialog, QMessageBox, QProgressBar)
    from PyQt6.QtCore import Qt, pyqtSignal, QObject
    from PyQt6.QtGui import QFont, QIcon
    from epub_gen import EpubGenerator
except Exception as e:
    log_error(f"Import error: {str(e)}")
    sys.exit(1)

class WorkerSignals(QObject):
    finished = pyqtSignal(bool, str)

class EpubGuiQt(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("웹소설 EPUB 생성기 - Premium")
        self.setFixedSize(500, 400)
        
        # UI Setup
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(15)

        # Style
        self.setStyleSheet("""
            QMainWindow { background-color: #f5f5f7; }
            QLabel { color: #1d1d1f; font-size: 14px; }
            QLineEdit { 
                padding: 10px; 
                border: 1px solid #d2d2d7; 
                border-radius: 8px; 
                background: white;
            }
            QPushButton { 
                padding: 12px; 
                background-color: #0071e3; 
                color: white; 
                border-radius: 8px; 
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #0077ed; }
            QPushButton#browse { 
                background-color: #86868b; 
                padding: 8px 15px; 
            }
            QPushButton#browse:hover { background-color: #99999f; }
            QProgressBar {
                border: 1px solid #d2d2d7;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #0071e3;
                border-radius: 4px;
            }
        """)

        # Components
        title_label = QLabel("웹소설 원고를 EPUB로 변환")
        title_label.setFont(QFont("Apple SD Gothic Neo", 20, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(title_label)
        self.layout.addSpacing(10)

        # File
        file_layout = QHBoxLayout()
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("원고 파일(.txt)을 선택하세요")
        self.file_input.setReadOnly(True)
        browse_btn = QPushButton("파일 찾기")
        browse_btn.setObjectName("browse")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_input)
        file_layout.addWidget(browse_btn)
        self.layout.addLayout(file_layout)

        # Meta
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("소설 제목")
        self.layout.addWidget(self.title_input)

        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("작가명")
        self.layout.addWidget(self.author_input)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0) # Indeterminate
        self.progress.hide()
        self.layout.addWidget(self.progress)

        # Run
        self.run_btn = QPushButton("EPUB 파일 생성하기")
        self.run_btn.clicked.connect(self.start_conversion)
        self.layout.addWidget(self.run_btn)

        # Status
        self.status = QLabel("대기 중...")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("color: #86868b; font-size: 12px;")
        self.layout.addWidget(self.status)

        self.signals = WorkerSignals()
        self.signals.finished.connect(self.on_finished)

    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "원고 파일 선택", "", "Text Files (*.txt);;All Files (*)")
        if file_name:
            self.file_input.setText(file_name)
            base = os.path.basename(file_name)
            self.title_input.setText(os.path.splitext(base)[0])

    def start_conversion(self):
        input_path = self.file_input.text()
        if not input_path:
            QMessageBox.warning(self, "경고", "원고 파일을 먼저 선택해 주세요.")
            return

        title = self.title_input.text() or "제목 없음"
        author = self.author_input.text() or "작가 미상"

        output_path, _ = QFileDialog.getSaveFileName(self, "EPUB 저장 위치 선택", f"{title}.epub", "EPUB Files (*.epub)")
        if not output_path:
            return

        self.run_btn.setEnabled(False)
        self.progress.show()
        self.status.setText("변환 중... 잠시만 기다려 주세요.")
        
        threading.Thread(target=self.run_logic, args=(input_path, output_path, title, author), daemon=True).start()

    def run_logic(self, input_path, output_path, title, author):
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            gen = EpubGenerator(title, author)
            gen.process_text(content)
            gen.generate(output_path)
            self.signals.finished.emit(True, output_path)
        except Exception as e:
            self.signals.finished.emit(False, str(e))

    def on_finished(self, success, result):
        self.run_btn.setEnabled(True)
        self.progress.hide()
        if success:
            self.status.setText("변환 완료!")
            QMessageBox.information(self, "성공", f"EPUB 파일이 생성되었습니다!\n\n파일: {result}")
        else:
            self.status.setText("오류 발생")
            QMessageBox.critical(self, "오류", f"변환 중 오류가 발생했습니다:\n{result}")

if __name__ == "__main__":
    try:
        log_error("--- New Execution ---")
        log_error("Starting application...")
        app = QApplication(sys.argv)
        log_error("QApplication created.")
        window = EpubGuiQt()
        log_error("Window object created.")
        window.show()
        log_error("window.show() called.")
        sys.exit(app.exec())
    except Exception as e:
        log_error(f"Runtime error: {str(e)}")
        import traceback
        log_error(traceback.format_exc())
