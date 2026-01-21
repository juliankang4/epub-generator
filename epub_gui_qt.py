import sys
import os
import json
import threading
from datetime import datetime

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QFileDialog, QMessageBox, QProgressBar, QTabWidget,
                             QListWidget, QListWidgetItem, QDialog, QSpinBox,
                             QComboBox, QGroupBox, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QSettings
from PyQt6.QtGui import QFont

from epub_gen import EpubGenerator
from text_extractor import ExtractionError, MissingLibraryError

VERSION = "2.1.0"

# 설정 파일 경로
def get_config_path():
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/EPUB-Generator")
    return os.path.expanduser("~/.epub-generator")

def ensure_config_dir():
    path = get_config_path()
    os.makedirs(path, exist_ok=True)
    return path


class RecentFiles:
    """최근 파일 관리"""
    def __init__(self, max_files=10):
        self.max_files = max_files
        self.config_path = os.path.join(ensure_config_dir(), "recent_files.json")
        self.files = self._load()

    def _load(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.files, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add(self, file_path, title="", author=""):
        # 기존 항목 제거
        self.files = [f for f in self.files if f.get('path') != file_path]
        # 새 항목 추가
        self.files.insert(0, {
            'path': file_path,
            'title': title,
            'author': author,
            'date': datetime.now().isoformat()
        })
        # 최대 개수 유지
        self.files = self.files[:self.max_files]
        self._save()

    def get_all(self):
        return self.files

    def clear(self):
        self.files = []
        self._save()


class WorkerSignals(QObject):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int, str)
    preview_ready = pyqtSignal(dict)
    batch_progress = pyqtSignal(int, int, str)  # current, total, filename


class DropZone(QLabel):
    file_dropped = pyqtSignal(str)
    files_dropped = pyqtSignal(list)  # 일괄 변환용

    def __init__(self, multi=False):
        super().__init__()
        self.multi = multi
        self.update_text()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(100)
        self.reset_style()
        self.setAcceptDrops(True)

    def update_text(self):
        if self.multi:
            self.setText("여러 파일을 드래그하여\n일괄 변환하세요")
        else:
            self.setText("파일을 이곳에 드래그하거나\n아래 버튼으로 선택하세요")

    def reset_style(self):
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

    def dragLeaveEvent(self, event):
        self.reset_style()

    def dragMoveEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        self.reset_style()
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        valid_ext = ['.txt', '.hwp', '.hwpx', '.pdf', '.docx']
        valid_files = [f for f in files if os.path.splitext(f)[1].lower() in valid_ext]

        if valid_files:
            if self.multi:
                self.files_dropped.emit(valid_files)
            else:
                self.file_dropped.emit(valid_files[0])
            event.acceptProposedAction()
        else:
            QMessageBox.warning(self, "지원하지 않는 파일", "지원되는 형식: TXT, HWP, HWPX, PDF, DOCX")


class PreviewDialog(QDialog):
    """미리보기 다이얼로그"""
    def __init__(self, preview_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("변환 미리보기")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        # 요약 정보
        summary = QLabel(f"총 {preview_data['total_chapters']}개 챕터 | 약 {preview_data['total_words']:,}자")
        summary.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(summary)

        # 챕터 목록
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        for i, chapter in enumerate(preview_data['chapters']):
            frame = QFrame()
            frame.setStyleSheet("QFrame { background: white; border-radius: 8px; padding: 10px; margin: 5px; }")
            frame_layout = QVBoxLayout(frame)

            title = QLabel(f"📖 {chapter['title']}")
            title.setStyleSheet("font-weight: bold; font-size: 14px;")
            frame_layout.addWidget(title)

            info = QLabel(f"약 {chapter['word_count']:,}자")
            info.setStyleSheet("color: #666; font-size: 12px;")
            frame_layout.addWidget(info)

            preview_text = QLabel(chapter['preview'])
            preview_text.setWordWrap(True)
            preview_text.setStyleSheet("color: #333; font-size: 12px; padding: 5px; background: #f5f5f5; border-radius: 4px;")
            frame_layout.addWidget(preview_text)

            content_layout.addWidget(frame)

        if preview_data['total_chapters'] > len(preview_data['chapters']):
            more = QLabel(f"... 외 {preview_data['total_chapters'] - len(preview_data['chapters'])}개 챕터")
            more.setStyleSheet("color: #666; font-style: italic; padding: 10px;")
            content_layout.addWidget(more)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # 버튼
        btn_layout = QHBoxLayout()
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.close)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)


class SettingsDialog(QDialog):
    """설정 다이얼로그"""
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("EPUB 설정")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # 스타일 설정
        style_group = QGroupBox("스타일 설정")
        style_layout = QVBoxLayout(style_group)

        # 폰트 크기
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("폰트 크기:"))
        self.font_size = QSpinBox()
        self.font_size.setRange(12, 24)
        self.font_size.setValue(settings.value("font_size", 16, int))
        self.font_size.setSuffix("px")
        font_layout.addWidget(self.font_size)
        font_layout.addStretch()
        style_layout.addLayout(font_layout)

        # 줄 간격
        line_layout = QHBoxLayout()
        line_layout.addWidget(QLabel("줄 간격:"))
        self.line_height = QComboBox()
        self.line_height.addItems(["1.5", "1.6", "1.8", "2.0", "2.2"])
        self.line_height.setCurrentText(settings.value("line_height", "1.8"))
        line_layout.addWidget(self.line_height)
        line_layout.addStretch()
        style_layout.addLayout(line_layout)

        # UI 배율
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("UI 배율:"))
        self.ui_scale = QComboBox()
        self.ui_scale.addItems(["100%", "125%", "150%", "175%", "200%"])
        self.ui_scale.setCurrentText(settings.value("ui_scale", "150%"))
        scale_layout.addWidget(self.ui_scale)
        scale_layout.addStretch()
        style_layout.addLayout(scale_layout)

        layout.addWidget(style_group)

        # 메타데이터 기본값
        meta_group = QGroupBox("메타데이터 기본값")
        meta_layout = QVBoxLayout(meta_group)

        self.default_author = QLineEdit(settings.value("default_author", ""))
        self.default_author.setPlaceholderText("기본 작가명")
        meta_layout.addWidget(self.default_author)

        self.default_publisher = QLineEdit(settings.value("default_publisher", ""))
        self.default_publisher.setPlaceholderText("기본 출판사")
        meta_layout.addWidget(self.default_publisher)

        layout.addWidget(meta_group)

        # 버튼
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("저장")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def save_settings(self):
        self.settings.setValue("font_size", self.font_size.value())
        self.settings.setValue("line_height", self.line_height.currentText())
        self.settings.setValue("ui_scale", self.ui_scale.currentText())
        self.settings.setValue("default_author", self.default_author.text())
        self.settings.setValue("default_publisher", self.default_publisher.text())
        self.accept()


class SingleConvertTab(QWidget):
    """단일 파일 변환 탭"""
    def __init__(self, recent_files, settings, parent=None):
        super().__init__(parent)
        self.recent_files = recent_files
        self.settings = settings
        self.cover_path = None
        self.current_preview = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # 드롭존
        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self.set_file)
        layout.addWidget(self.drop_zone)

        # 파일 선택
        file_layout = QHBoxLayout()
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("지원: TXT, PDF, HWP, HWPX, DOCX")
        self.file_input.setReadOnly(True)
        browse_btn = QPushButton("파일 찾기")
        browse_btn.setObjectName("secondary")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_input)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)

        # 메타데이터
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("소설 제목")
        layout.addWidget(self.title_input)

        meta_layout = QHBoxLayout()
        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("작가명")
        self.author_input.setText(settings.value("default_author", ""))
        meta_layout.addWidget(self.author_input)

        self.publisher_input = QLineEdit()
        self.publisher_input.setPlaceholderText("출판사 (선택)")
        self.publisher_input.setText(settings.value("default_publisher", ""))
        meta_layout.addWidget(self.publisher_input)
        layout.addLayout(meta_layout)

        # 시리즈 정보
        series_layout = QHBoxLayout()
        self.series_input = QLineEdit()
        self.series_input.setPlaceholderText("시리즈명 (선택)")
        series_layout.addWidget(self.series_input)

        self.series_num = QSpinBox()
        self.series_num.setRange(0, 999)
        self.series_num.setSpecialValueText("권수")
        self.series_num.setPrefix("제 ")
        self.series_num.setSuffix(" 권")
        series_layout.addWidget(self.series_num)
        layout.addLayout(series_layout)

        # 표지 이미지
        cover_layout = QHBoxLayout()
        self.cover_label = QLabel("표지 이미지: 없음")
        self.cover_label.setStyleSheet("color: #666;")
        cover_btn = QPushButton("표지 선택")
        cover_btn.setObjectName("secondary")
        cover_btn.clicked.connect(self.browse_cover)
        clear_cover_btn = QPushButton("제거")
        clear_cover_btn.setObjectName("secondary")
        clear_cover_btn.clicked.connect(self.clear_cover)
        cover_layout.addWidget(self.cover_label)
        cover_layout.addStretch()
        cover_layout.addWidget(cover_btn)
        cover_layout.addWidget(clear_cover_btn)
        layout.addLayout(cover_layout)

        # 버튼들
        btn_layout = QHBoxLayout()
        self.preview_btn = QPushButton("미리보기")
        self.preview_btn.setObjectName("secondary")
        self.preview_btn.clicked.connect(self.show_preview)
        btn_layout.addWidget(self.preview_btn)

        btn_layout.addStretch()

        self.run_btn = QPushButton("EPUB 생성")
        self.run_btn.clicked.connect(self.start_conversion)
        btn_layout.addWidget(self.run_btn)
        layout.addLayout(btn_layout)

        # 진행률
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)

        # 상태
        self.status = QLabel("대기 중...")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("color: #86868b; font-size: 12px;")
        layout.addWidget(self.status)

        layout.addStretch()

        # 시그널
        self.signals = WorkerSignals()
        self.signals.finished.connect(self.on_finished)
        self.signals.preview_ready.connect(self.on_preview_ready)

    def set_file(self, file_path):
        self.file_input.setText(file_path)
        base = os.path.basename(file_path)
        self.title_input.setText(os.path.splitext(base)[0])

    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "원고 파일 선택", "",
            "지원 형식 (*.txt *.hwp *.hwpx *.pdf *.docx);;모든 파일 (*)"
        )
        if file_name:
            self.set_file(file_name)

    def browse_cover(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "표지 이미지 선택", "",
            "이미지 (*.jpg *.jpeg *.png *.gif);;모든 파일 (*)"
        )
        if file_name:
            self.cover_path = file_name
            self.cover_label.setText(f"표지: {os.path.basename(file_name)}")
            self.cover_label.setStyleSheet("color: #0071e3;")

    def clear_cover(self):
        self.cover_path = None
        self.cover_label.setText("표지 이미지: 없음")
        self.cover_label.setStyleSheet("color: #666;")

    def show_preview(self):
        input_path = self.file_input.text()
        if not input_path:
            QMessageBox.warning(self, "경고", "파일을 먼저 선택해 주세요.")
            return

        self.status.setText("미리보기 생성 중...")
        threading.Thread(target=self._generate_preview, args=(input_path,), daemon=True).start()

    def _generate_preview(self, input_path):
        try:
            gen = EpubGenerator("Preview", "")
            content = gen.extract_text(input_path)
            if content and content.strip():
                preview = gen.get_chapter_preview(content)
                self.signals.preview_ready.emit(preview)
            else:
                self.signals.preview_ready.emit({'error': '텍스트를 추출할 수 없습니다.'})
        except Exception as e:
            self.signals.preview_ready.emit({'error': str(e)})

    def on_preview_ready(self, preview_data):
        self.status.setText("대기 중...")
        if 'error' in preview_data:
            QMessageBox.warning(self, "미리보기 오류", preview_data['error'])
        else:
            dialog = PreviewDialog(preview_data, self)
            dialog.exec()

    def start_conversion(self):
        input_path = self.file_input.text()
        if not input_path:
            QMessageBox.warning(self, "경고", "원고 파일을 먼저 선택해 주세요.")
            return

        title = self.title_input.text() or "제목 없음"
        author = self.author_input.text() or "작가 미상"

        output_path, _ = QFileDialog.getSaveFileName(
            self, "EPUB 저장 위치", f"{title}.epub", "EPUB (*.epub)"
        )
        if not output_path:
            return

        self.run_btn.setEnabled(False)
        self.progress.show()
        self.status.setText("변환 중...")

        # 메타데이터 수집
        metadata = {
            'publisher': self.publisher_input.text(),
            'series': self.series_input.text(),
            'series_num': self.series_num.value() if self.series_num.value() > 0 else None,
            'cover': self.cover_path
        }

        threading.Thread(
            target=self.run_logic,
            args=(input_path, output_path, title, author, metadata),
            daemon=True
        ).start()

    def run_logic(self, input_path, output_path, title, author, metadata):
        try:
            gen = EpubGenerator(title, author)

            # 추가 메타데이터 설정
            if metadata.get('publisher'):
                gen.book.add_metadata('DC', 'publisher', metadata['publisher'])
            if metadata.get('series'):
                gen.book.add_metadata(None, 'meta', metadata['series'],
                                      {'name': 'calibre:series'})
                if metadata.get('series_num'):
                    gen.book.add_metadata(None, 'meta', str(metadata['series_num']),
                                          {'name': 'calibre:series_index'})

            # 표지 설정
            if metadata.get('cover'):
                gen.set_cover(metadata['cover'])

            # 스타일 적용
            font_size = self.settings.value("font_size", 16, int)
            line_height = self.settings.value("line_height", "1.8")
            gen.style = gen.style.replace("line-height: 1.8", f"line-height: {line_height}")

            content = gen.extract_text(input_path)
            if not content or not content.strip():
                raise ExtractionError("텍스트를 추출하지 못했습니다.")

            gen.process_text(content)
            gen.generate(output_path)

            # 최근 파일에 추가
            self.recent_files.add(input_path, title, author)

            self.signals.finished.emit(True, output_path)
        except Exception as e:
            self.signals.finished.emit(False, str(e))

    def on_finished(self, success, result):
        self.run_btn.setEnabled(True)
        self.progress.hide()
        if success:
            self.status.setText("변환 완료!")
            QMessageBox.information(self, "성공", f"EPUB 생성 완료!\n\n{result}")
        else:
            self.status.setText("오류 발생")
            QMessageBox.critical(self, "오류", f"변환 실패:\n{result}")


class BatchConvertTab(QWidget):
    """일괄 변환 탭"""
    def __init__(self, recent_files, settings, parent=None):
        super().__init__(parent)
        self.recent_files = recent_files
        self.settings = settings
        self.file_list = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # 드롭존
        self.drop_zone = DropZone(multi=True)
        self.drop_zone.files_dropped.connect(self.add_files)
        layout.addWidget(self.drop_zone)

        # 파일 목록
        list_layout = QHBoxLayout()

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("QListWidget { border-radius: 8px; }")
        list_layout.addWidget(self.list_widget)

        # 목록 버튼
        list_btn_layout = QVBoxLayout()
        add_btn = QPushButton("추가")
        add_btn.clicked.connect(self.browse_files)
        remove_btn = QPushButton("제거")
        remove_btn.clicked.connect(self.remove_selected)
        clear_btn = QPushButton("전체 삭제")
        clear_btn.clicked.connect(self.clear_list)
        list_btn_layout.addWidget(add_btn)
        list_btn_layout.addWidget(remove_btn)
        list_btn_layout.addWidget(clear_btn)
        list_btn_layout.addStretch()
        list_layout.addLayout(list_btn_layout)

        layout.addLayout(list_layout)

        # 출력 폴더
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("저장 폴더:"))
        self.output_folder = QLineEdit()
        self.output_folder.setPlaceholderText("EPUB 저장 위치 선택")
        self.output_folder.setReadOnly(True)
        output_layout.addWidget(self.output_folder)
        output_btn = QPushButton("선택")
        output_btn.setObjectName("secondary")
        output_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(output_btn)
        layout.addLayout(output_layout)

        # 진행률
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.hide()
        layout.addWidget(self.progress)

        self.status = QLabel(f"0개 파일 선택됨")
        self.status.setStyleSheet("color: #666;")
        layout.addWidget(self.status)

        # 변환 버튼
        self.run_btn = QPushButton("일괄 변환 시작")
        self.run_btn.clicked.connect(self.start_batch)
        layout.addWidget(self.run_btn)

        # 시그널
        self.signals = WorkerSignals()
        self.signals.batch_progress.connect(self.on_batch_progress)
        self.signals.finished.connect(self.on_batch_finished)

    def add_files(self, files):
        for f in files:
            if f not in self.file_list:
                self.file_list.append(f)
                self.list_widget.addItem(os.path.basename(f))
        self.update_status()

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "파일 선택", "",
            "지원 형식 (*.txt *.hwp *.hwpx *.pdf *.docx)"
        )
        if files:
            self.add_files(files)

    def remove_selected(self):
        for item in self.list_widget.selectedItems():
            idx = self.list_widget.row(item)
            self.list_widget.takeItem(idx)
            del self.file_list[idx]
        self.update_status()

    def clear_list(self):
        self.file_list.clear()
        self.list_widget.clear()
        self.update_status()

    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")
        if folder:
            self.output_folder.setText(folder)

    def update_status(self):
        self.status.setText(f"{len(self.file_list)}개 파일 선택됨")

    def start_batch(self):
        if not self.file_list:
            QMessageBox.warning(self, "경고", "변환할 파일을 추가해 주세요.")
            return

        output_folder = self.output_folder.text()
        if not output_folder:
            QMessageBox.warning(self, "경고", "저장 폴더를 선택해 주세요.")
            return

        self.run_btn.setEnabled(False)
        self.progress.show()
        self.progress.setValue(0)

        threading.Thread(
            target=self.run_batch,
            args=(self.file_list.copy(), output_folder),
            daemon=True
        ).start()

    def run_batch(self, files, output_folder):
        success_count = 0
        fail_count = 0

        for i, file_path in enumerate(files):
            filename = os.path.basename(file_path)
            self.signals.batch_progress.emit(i + 1, len(files), filename)

            try:
                title = os.path.splitext(filename)[0]
                author = self.settings.value("default_author", "작가 미상")
                output_path = os.path.join(output_folder, f"{title}.epub")

                gen = EpubGenerator(title, author)
                content = gen.extract_text(file_path)

                if content and content.strip():
                    gen.process_text(content)
                    gen.generate(output_path)
                    self.recent_files.add(file_path, title, author)
                    success_count += 1
                else:
                    fail_count += 1
            except Exception:
                fail_count += 1

        self.signals.finished.emit(True, f"완료: {success_count}개 성공, {fail_count}개 실패")

    def on_batch_progress(self, current, total, filename):
        self.progress.setValue(int(current / total * 100))
        self.status.setText(f"변환 중... ({current}/{total}) {filename}")

    def on_batch_finished(self, success, message):
        self.run_btn.setEnabled(True)
        self.progress.hide()
        self.status.setText(message)
        QMessageBox.information(self, "일괄 변환 완료", message)


class RecentFilesTab(QWidget):
    """최근 파일 탭"""
    file_selected = pyqtSignal(str, str, str)  # path, title, author

    def __init__(self, recent_files, parent=None):
        super().__init__(parent)
        self.recent_files = recent_files

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # 목록
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.on_item_selected)
        layout.addWidget(self.list_widget)

        # 버튼
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("새로고침")
        refresh_btn.clicked.connect(self.refresh)
        clear_btn = QPushButton("목록 지우기")
        clear_btn.clicked.connect(self.clear_history)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(clear_btn)
        layout.addLayout(btn_layout)

        self.refresh()

    def refresh(self):
        self.list_widget.clear()
        for item in self.recent_files.get_all():
            path = item.get('path', '')
            title = item.get('title', os.path.basename(path))
            date = item.get('date', '')[:10]
            display = f"📄 {title}\n   {path}\n   {date}"

            list_item = QListWidgetItem(display)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.list_widget.addItem(list_item)

    def clear_history(self):
        self.recent_files.clear()
        self.refresh()

    def on_item_selected(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data and os.path.exists(data.get('path', '')):
            self.file_selected.emit(
                data.get('path', ''),
                data.get('title', ''),
                data.get('author', '')
            )


class EpubGuiQt(QMainWindow):
    def __init__(self):
        super().__init__()

        # 권한 체크
        self.check_mac_permissions()

        # 설정
        self.settings = QSettings("EPUB-Generator", "EPUB-Generator")

        # UI 배율 적용
        self.apply_ui_scale()

        self.setWindowTitle(f"웹소설 EPUB 생성기 v{VERSION}")
        self.setMinimumSize(550, 650)
        self.recent_files = RecentFiles()

        # 스타일
        self.setStyleSheet("""
            QMainWindow { background-color: #f5f5f7; }
            QLabel { color: #1d1d1f; }
            QLineEdit {
                padding: 10px;
                border: 1px solid #d2d2d7;
                border-radius: 8px;
                background: white;
            }
            QPushButton {
                padding: 12px 20px;
                background-color: #0071e3;
                color: white;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0077ed; }
            QPushButton:disabled { background-color: #d2d2d7; }
            QPushButton#secondary {
                background-color: #86868b;
                padding: 8px 15px;
            }
            QPushButton#secondary:hover { background-color: #99999f; }
            QTabWidget::pane {
                border: none;
                background: #f5f5f7;
            }
            QTabBar::tab {
                padding: 10px 20px;
                background: #e5e5ea;
                border-radius: 8px;
                margin-right: 5px;
            }
            QTabBar::tab:selected {
                background: #0071e3;
                color: white;
            }
            QProgressBar {
                border: 1px solid #d2d2d7;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: linear-gradient(90deg, #0071e3, #34c759);
                border-radius: 4px;
            }
            QListWidget {
                border: 1px solid #d2d2d7;
                border-radius: 8px;
                background: white;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #d2d2d7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
            }
        """)

        # 메인 위젯
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 헤더
        header_layout = QHBoxLayout()
        title = QLabel("EPUB 생성기")
        title.setFont(QFont("Apple SD Gothic Neo", 24, QFont.Weight.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()

        settings_btn = QPushButton("⚙️ 설정")
        settings_btn.setObjectName("secondary")
        settings_btn.clicked.connect(self.open_settings)
        header_layout.addWidget(settings_btn)
        main_layout.addLayout(header_layout)

        # 탭
        self.tabs = QTabWidget()
        self.single_tab = SingleConvertTab(self.recent_files, self.settings)
        self.batch_tab = BatchConvertTab(self.recent_files, self.settings)
        self.recent_tab = RecentFilesTab(self.recent_files)
        self.recent_tab.file_selected.connect(self.load_recent_file)

        self.tabs.addTab(self.single_tab, "단일 변환")
        self.tabs.addTab(self.batch_tab, "일괄 변환")
        self.tabs.addTab(self.recent_tab, "최근 파일")

        main_layout.addWidget(self.tabs)

        # 푸터
        footer = QLabel(f"v{VERSION} | 지원 형식: TXT, PDF, HWP, HWPX, DOCX")
        footer.setStyleSheet("color: #86868b; font-size: 11px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(footer)

    def check_mac_permissions(self):
        if sys.platform != "darwin":
            return
        try:
            exe_path = sys.executable
            if ".app/Contents/MacOS" in exe_path:
                app_bundle_path = exe_path.split(".app/Contents/MacOS")[0] + ".app"
                import subprocess
                result = subprocess.run(
                    ["xattr", "-p", "com.apple.quarantine", app_bundle_path],
                    capture_output=True
                )
                if result.returncode == 0:
                    script = f'''
                    display dialog "앱의 원활한 실행을 위해 보안 설정을 업데이트해야 합니다." buttons {{"확인", "취소"}} default button "확인" with icon caution
                    if button returned of result is "확인" then
                        do shell script "xattr -r -d com.apple.quarantine '{app_bundle_path}'" with administrator privileges
                        display dialog "설정 완료! 앱을 다시 실행해 주세요." buttons {{"종료"}} default button "종료"
                    end if
                    '''
                    subprocess.run(["osascript", "-e", script])
                    sys.exit(0)
        except Exception:
            pass

    def apply_ui_scale(self):
        # 이 메서드는 앱 시작 시 main에서 처리됨
        pass

    def open_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            QMessageBox.information(self, "알림", "배율 변경은 앱을 재시작해야 적용됩니다.")

    def load_recent_file(self, path, title, author):
        self.tabs.setCurrentIndex(0)
        self.single_tab.set_file(path)
        if title:
            self.single_tab.title_input.setText(title)
        if author:
            self.single_tab.author_input.setText(author)


def apply_scale_before_app():
    """앱 시작 전 UI 배율 적용"""
    settings = QSettings("EPUB-Generator", "EPUB-Generator")
    scale_str = settings.value("ui_scale", "150%")
    scale = int(scale_str.replace("%", "")) / 100.0
    os.environ["QT_SCALE_FACTOR"] = str(scale)


if __name__ == "__main__":
    apply_scale_before_app()
    app = QApplication(sys.argv)
    window = EpubGuiQt()
    window.show()
    sys.exit(app.exec())
