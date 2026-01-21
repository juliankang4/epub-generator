# 웹소설 EPUB 생성기

다양한 형식의 원고 파일(TXT, PDF, DOCX, HWP, HWPX)을 EPUB 전자책으로 변환하는 macOS 앱입니다.

## 주요 기능

- **다양한 파일 형식 지원**: TXT, PDF, DOCX, HWP, HWPX
- **자동 챕터 분할**: 다양한 패턴 인식 (제1화, Chapter 1, 프롤로그 등)
- **한국어 최적화**: 한글 폰트 및 인코딩 자동 처리
- **드래그 앤 드롭**: 파일을 끌어다 놓기만 하면 변환 시작
- **깔끔한 UI**: macOS 스타일 인터페이스

## 설치 및 실행

### 앱으로 사용하기
`/Applications/EPUB-Generator.app`을 더블클릭하세요.

### 소스에서 실행하기
```bash
# 가상환경 활성화
source venv/bin/activate

# PyQt 버전 실행 (추천)
python3 epub_gui_qt.py

# 웹 버전 실행
python3 epub_gui_web.py
```

## 빌드 방법

```bash
# 자동 빌드 (권장)
./build_mac.sh

# 결과: /Applications/EPUB-Generator.app
```

## 프로젝트 구조

```
├── epub_gen.py          # EPUB 생성 핵심 로직
├── text_extractor.py    # 다양한 파일 형식에서 텍스트 추출
├── epub_gui_qt.py       # PyQt6 GUI (현재 사용)
├── epub_gui_web.py      # pywebview GUI (대체 버전)
├── epub_gui.py          # Tkinter GUI (레거시)
├── build_mac.sh         # macOS 빌드 스크립트
├── requirements.txt     # Python 의존성
└── assets/              # 앱 아이콘
```

## 지원하는 챕터 패턴

- `# 제목` (마크다운 헤더)
- `제1화`, `제 1 화`, `제1장`, `제 1 장`
- `1화`, `1장`
- `Chapter 1`, `CHAPTER 1`
- `Episode 1`, `EP.1`, `ep 1`
- `Part 1`
- `프롤로그`, `에필로그`, `서장`, `종장`, `막간`

## 문제 해결

| 문제 | 해결 방법 |
|------|----------|
| 앱이 실행되지 않음 | 시스템 환경설정 > 개인정보 및 보안 > "확인 없이 열기" |
| HWP 파일 읽기 실패 | 복잡한 서식의 HWP는 지원이 제한될 수 있음 |
| PDF 텍스트 추출 안됨 | 이미지 기반 PDF는 지원하지 않음 |

---

## 업데이트 기록

자세한 변경 내역은 [CHANGELOG.md](CHANGELOG.md)를 참고하세요.
