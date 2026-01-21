import os
import sys
import webview
import threading
import json
from epub_gen import EpubGenerator
from text_extractor import ExtractionError, MissingLibraryError

# HTML/CSS/JS for the UI
HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f5f5f7;
            color: #1d1d1f;
            margin: 0;
            padding: 40px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            width: 400px;
        }
        h1 {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 30px;
            text-align: center;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            font-size: 13px;
            font-weight: 500;
            margin-bottom: 8px;
            color: #86868b;
        }
        input {
            width: 100%;
            padding: 12px;
            border: 1px solid #d2d2d7;
            border-radius: 10px;
            box-sizing: border-box;
            font-size: 15px;
            outline: none;
            transition: border-color 0.2s;
        }
        input:focus {
            border-color: #0071e3;
        }
        .file-input-container {
            display: flex;
            gap: 10px;
        }
        button {
            background-color: #0071e3;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            transition: background-color 0.2s;
        }
        button:hover {
            background-color: #0077ed;
        }
        button:disabled {
            background-color: #d2d2d7;
            cursor: not-allowed;
        }
        #browse-btn {
            background-color: #86868b;
            width: auto;
            white-space: nowrap;
        }
        #browse-btn:hover {
            background-color: #99999f;
        }
        .status {
            margin-top: 20px;
            font-size: 12px;
            text-align: center;
            color: #86868b;
        }
        .progress-bar {
            width: 100%;
            height: 6px;
            background: #e5e5ea;
            border-radius: 3px;
            margin-top: 15px;
            overflow: hidden;
            display: none;
        }
        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #0071e3, #34c759);
            width: 0%;
            transition: width 0.3s ease;
            border-radius: 3px;
        }
        .progress-bar-fill.indeterminate {
            width: 30%;
            animation: loading 1.5s infinite ease-in-out;
        }
        @keyframes loading {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(400%); }
        }
        .error { color: #ff3b30; }
        .success { color: #34c759; }
    </style>
</head>
<body>
    <div class="container">
        <h1>EPUB 생성기</h1>
        <div class="form-group">
            <label>원고 파일 (txt, pdf, docx, hwp)</label>
            <div class="file-input-container">
                <input type="text" id="file-path" readonly placeholder="파일을 선택하세요">
                <button id="browse-btn" onclick="browseFile()">찾기</button>
            </div>
        </div>
        <div class="form-group">
            <label>소설 제목</label>
            <input type="text" id="title" placeholder="제목을 입력하세요">
        </div>
        <div class="form-group">
            <label>작가명</label>
            <input type="text" id="author" placeholder="작가명을 입력하세요">
        </div>
        <button id="generate-btn" onclick="generateEpub()">EPUB 파일 생성하기</button>
        <div class="progress-bar" id="progress">
            <div class="progress-bar-fill"></div>
        </div>
        <div class="status" id="status">대기 중...</div>
    </div>

    <script>
        function browseFile() {
            pywebview.api.browse_file().then(fileInfo => {
                if (fileInfo) {
                    document.getElementById('file-path').value = fileInfo.path;
                    document.getElementById('title').value = fileInfo.title;
                }
            });
        }

        function generateEpub() {
            const path = document.getElementById('file-path').value;
            const title = document.getElementById('title').value;
            const author = document.getElementById('author').value;

            if (!path) {
                updateStatus('원고 파일을 먼저 선택해 주세요.', 'error');
                return;
            }

            document.getElementById('generate-btn').disabled = true;
            const progressBar = document.getElementById('progress');
            const progressFill = document.querySelector('.progress-bar-fill');
            progressBar.style.display = 'block';
            progressFill.classList.add('indeterminate');
            progressFill.style.width = '30%';
            updateStatus('파일을 읽는 중...');

            pywebview.api.generate(path, title, author).then(result => {
                document.getElementById('generate-btn').disabled = false;
                progressFill.classList.remove('indeterminate');

                if (result.success) {
                    progressFill.style.width = '100%';
                    updateStatus('성공적으로 생성되었습니다!', 'success');
                    setTimeout(() => {
                        progressBar.style.display = 'none';
                        progressFill.style.width = '0%';
                    }, 2000);
                } else {
                    progressBar.style.display = 'none';
                    progressFill.style.width = '0%';
                    updateStatus(result.error, 'error');
                }
            });
        }

        function updateStatus(msg, className = '') {
            const status = document.getElementById('status');
            status.innerText = msg;
            status.className = 'status ' + className;
        }
    </script>
</body>
</html>
"""

class API:
    def browse_file(self):
        # Use the standard filter string format which is robust across pywebview versions
        # On macOS, this string is parsed to extract extensions
        file_types = ('Document files (*.txt;*.pdf;*.docx;*.hwp;*.hwpx)', 'All files (*.*)')
        
        # Ensure we have a window to attach to
        active_window = window if 'window' in globals() else webview.windows[0]
        
        result = active_window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
        if result:
            path = result[0]
            title = os.path.splitext(os.path.basename(path))[0]
            return {'path': path, 'title': title}
        return None

    def generate(self, input_path, title, author):
        try:
            # Ask location to save
            save_path = window.create_file_dialog(webview.SAVE_DIALOG, directory='', save_filename=f"{title}.epub")
            if not save_path:
                return {'success': False, 'error': '저장이 취소되었습니다.'}

            gen = EpubGenerator(title or "제목 없음", author or "작가 미상")
            content = gen.extract_text(input_path)

            if not content or not content.strip():
                return {'success': False, 'error': '텍스트를 추출하지 못했습니다. 파일이 비어있거나 지원하지 않는 형식입니다.'}

            gen.process_text(content)
            gen.generate(save_path)
            return {'success': True}
        except MissingLibraryError as e:
            return {'success': False, 'error': f'필요한 라이브러리 없음: {str(e)}'}
        except ExtractionError as e:
            return {'success': False, 'error': f'파일 읽기 오류: {str(e)}'}
        except FileNotFoundError:
            return {'success': False, 'error': '파일을 찾을 수 없습니다. 경로를 확인해 주세요.'}
        except PermissionError:
            return {'success': False, 'error': '파일 접근 권한이 없습니다. 파일 권한을 확인해 주세요.'}
        except Exception as e:
            return {'success': False, 'error': f'예상치 못한 오류: {str(e)}'}

def self_authorize():
    """
    Attempt to remove quarantine attribute from the app bundle itself.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled app
        # sys.executable is .../EPUB-Generator.app/Contents/MacOS/EPUB-Generator
        # We need .../EPUB-Generator.app
        try:
            exe_path = sys.executable
            app_bundle_path = None
            if ".app/Contents/MacOS" in exe_path:
                # Deduce .app path
                parts = exe_path.split("/")
                while parts:
                    if parts[-1].endswith(".app"):
                        app_bundle_path = "/".join(parts)
                        break
                    parts.pop()
            
            if app_bundle_path and os.path.exists(app_bundle_path):
                # Check if quarantined (optional, but good to avoid password prompt if not needed)
                # But user asked to "merge" the approval app, implying they want the capability.
                # To avoid annoyance, we can try to check first.
                check_cmd = ['xattr', '-p', 'com.apple.quarantine', app_bundle_path]
                import subprocess
                is_quarantined = False
                try:
                    subprocess.check_call(check_cmd, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                    is_quarantined = True
                except subprocess.CalledProcessError:
                    is_quarantined = False
                
                if is_quarantined:
                    print("Quarantine detected. Requesting authorization...")
                    # Run xattr -d via osascript to get admin privileges
                    script = f'do shell script "xattr -rd com.apple.quarantine {app_bundle_path}" with administrator privileges'
                    subprocess.run(['osascript', '-e', script])
        except Exception as e:
            print(f"Authorization check failed: {e}")

if __name__ == '__main__':
    print("-----------------------------------------")
    print("웹소설 EPUB 생성기를 시작합니다...")
    
    # Self-authorize on startup
    self_authorize()

    print("창이 뜨기까지 몇 초 정도 걸릴 수 있습니다.")
    print("-----------------------------------------")
    
    api = API()
    window = webview.create_window('웹소설 EPUB 생성기', html=HTML_CONTENT, js_api=api, width=500, height=550, resizable=False)
    
    print("GUI 창을 생성했습니다. 지금 화면을 확인해 주세요.")
    webview.start()
