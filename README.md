# 웹소설 EPUB 생성기 (Source Code)

이 폴더는 '웹소설 EPUB 생성기'의 전체 소스 코드와 빌드 환경을 담고 있습니다.
나중에 버그를 수정하거나 기능을 추가할 때 이 폴더를 사용하세요.

## 📂 폴더 구조
- `epub_gen.py`: **핵심 로직**. 파일에서 텍스트를 추출하고 EPUB을 만드는 기능이 들어있습니다.
- `epub_gui_web.py`: **화면(GUI)**. 사용자가 보는 화면과 버튼 기능을 담당합니다.
- `assets/`: 앱 아이콘 등 이미지 파일이 들어있습니다.
- `requirements.txt`: 이 프로그램에 필요한 파이썬 라이브러리 목록입니다.

## 🛠 수정 및 실행 방법

### 1. 터미널 열기
이 폴더에서 터미널을 열어주세요.

### 2. 가상환경 활성화 (필수)
프로그램을 실행하거나 빌드하기 전에는 항상 가상환경을 켜야 합니다.
```bash
source venv/bin/activate
```
(터미널 프롬프트 앞에 `(venv)`가 뜨면 성공입니다.)

### 3. 소스 코드 실행해보기
앱으로 만들기 전에 코드를 수정하고 바로 테스트해볼 수 있습니다.
```bash
python3 epub_gui_web.py
```

### 4. 앱으로 다시 만들기 (빌드)
수정이 끝난 후, 배포용 `.app` 파일을 다시 만들려면 아래 명령어를 복사해서 실행하세요.
```bash
rm -rf dist build
pyinstaller --noconsole --clean --name "EPUB-Generator" --icon "assets/icon.icns" --add-data "epub_gen.py:." --collect-all hwp5 --add-data "venv/lib/python3.14/site-packages/hwp5/xsl:hwp5/xsl" epub_gui_web.py
```
완료되면 `dist/` 폴더 안에 새로운 `EPUB-Generator.app`이 생깁니다.

### 5. 한글(HWP) 관련 주의사항
`hwp5` 라이브러리를 사용하므로, 빌드 시 `--collect-all hwp5` 옵션이 꼭 필요합니다. 위 명령어를 그대로 쓰시면 됩니다.

## 🚀 문제 해결
- **실행이 안 될 때**: `venv`가 켜져 있는지 확인하세요.
- **앱이 권한 문제로 안 열릴 때**: 앱을 한 번 직접 실행하여 비밀번호 승인을 해주세요.
