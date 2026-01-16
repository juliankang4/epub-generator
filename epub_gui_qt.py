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
    from PyQt6.QtCore import Qt, pyqtSignal, QObject, QMimeData
    from PyQt6.QtGui import QFont, QIcon, QDragEnterEvent, QDropEvent
    from epub_gen import EpubGenerator
except Exception as e:
    log_error(f"Import error: {str(e)}")
    sys.exit(1)

def check_mac_permissions():
    """
    Checks if the app is running in a quarantined state (macOS) and tries to remove it
    by asking for password via native prompt.
    """
    if sys.platform != "darwin":
        return

    try:
        # Determine App Bundle Path
        # In PyInstaller, sys.executable is .../EPUB-Generator.app/Contents/MacOS/EPUB-Generator
        # We want .../EPUB-Generator.app
        
        exe_path = sys.executable
        if ".app/Contents/MacOS" in exe_path:
            app_bundle_path = exe_path.split(".app/Contents/MacOS")[0] + ".app"
            
            # Check quarantine status
            # xattr -p com.apple.quarantine <path> returns 0 if exists, 1 if not
            import subprocess
            result = subprocess.run(
                ["xattr", "-p", "com.apple.quarantine", app_bundle_path], 
                capture_output=True
            )
            
            if result.returncode == 0:
                # Quarantine exists! Ask user to remove it.
                script = f'''
                display dialog "앱의 원활한 실행을 위해 보안 설정을 업데이트해야 합니다.\\n(관리자 권한이 필요합니다)" buttons {{"확인", "취소"}} default button "확인" with icon caution
                if button returned of result is "확인" then
                    do shell script "xattr -r -d com.apple.quarantine '{app_bundle_path}'" with administrator privileges
                    display dialog "✅ 설정이 완료되었습니다! 앱을 다시 실행해 주세요." buttons {{"종료"}} default button "종료"
                else
                    error number -128
                end if
                '''
                subprocess.run(["osascript", "-e", script])
                sys.exit(0) # Restart required
    except Exception as e:
        log_error(f"Permission check failed: {e}")

class WorkerSignals(QObject):
    finished = pyqtSignal(bool, str)

class DropZone(QLabel):
    file_dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setText("파일을 이곳에 드래그하거나\n아래 버튼으로 선택하세요")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                background-color: #f0f0f0;
                color: #555;
                font-size: 13px;
                padding: 20px;
            }
            QLabel:hover {
                border-color: #0071e3;
                background-color: #eef7ff;
            }
        """)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QLabel {
                    border: 2px dashed #0071e3;
                    border-radius: 10px;
                    background-color: #eef7ff;
                    color: #0071e3;
                    font-size: 13px;
                    padding: 20px;
                }
            """)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                background-color: #f0f0f0;
                color: #555;
                font-size: 13px;
                padding: 20px;
            }
            QLabel:hover {
                border-color: #0071e3;
                background-color: #eef7ff;
            }
        """)

    def dragMoveEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        # Reset style
        self.dragLeaveEvent(event)
        
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            file_path = files[0] # Take the first file
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.txt', '.epub', '.hwp', '.hwpx', '.pdf', '.docx']:
                self.file_dropped.emit(file_path)
                event.acceptProposedAction()
            else:
                QMessageBox.warning(self, "지원하지 않는 파일", "지원되는 형식이 아닙니다.\n(TXT, HWP, HWPX, PDF, DOCX)")
                event.ignore()

class EpubGuiQt(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Check permissions on startup
        check_mac_permissions()
        
        self.setWindowTitle("웹소설 EPUB 생성기 - Premium")
        self.setFixedSize(500, 480) # Increased height for DropZone
        
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
        
        # Dedicated Drop Zone
        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self.set_file)
        self.layout.addWidget(self.drop_zone)

        # File
        file_layout = QHBoxLayout()
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("지원: TXT, PDF, HWP, DOCX")
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



    def set_file(self, file_path):
        self.file_input.setText(file_path)
        base = os.path.basename(file_path)
        # Remove extension for title guessing
        self.title_input.setText(os.path.splitext(base)[0])

    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, 
            "원고 파일 선택", 
            "", 
            "Supported Files (*.txt *.hwp *.hwpx *.pdf *.docx);;Text Files (*.txt);;HWP Files (*.hwp *.hwpx);;All Files (*)"
        )
        if file_name:
            self.set_file(file_name)

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
            # FIX: Do not open file here directly. Use EpubGenerator to handle different formats.
            # with open(input_path, "r", encoding="utf-8") as f:
            #    content = f.read()
            
            gen = EpubGenerator(title, author)
            
            # Step 1: Extract Text
            content = gen.extract_text(input_path)
            
            # Check if extraction returned an error message (starting with "Error") or empty
            if content.startswith("Error") or not content.strip():
                raise Exception(f"Failed to extract text: {content[:100]}...")

            # Step 2: Process & Generate
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
