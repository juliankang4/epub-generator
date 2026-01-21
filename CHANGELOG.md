# 변경 기록 (Changelog)

## v1.2.0 (2026-01-21)

### 개선사항

#### 오류 처리 개선
- 문자열 반환 방식에서 표준 Exception 클래스 방식으로 변경
- `ExtractionError`, `MissingLibraryError` 커스텀 예외 클래스 추가
- 사용자에게 더 명확한 한국어 오류 메시지 제공

#### 챕터 인식 패턴 확장
- **기존**: `# Chapter 1`, `제 1 화`, `제1장`
- **추가 지원**:
  - `1화`, `1장` (숫자로 시작하는 패턴)
  - `EP.1`, `ep 1` (에피소드 약어)
  - `Part 1`
  - `프롤로그`, `에필로그`, `서장`, `종장`, `막간`
  - `제1편`, `제1부`

#### EPUB 생성 개선
- 식별자를 `hash()`에서 `UUID`로 변경하여 충돌 방지
- 폰트 폴백 체인 개선: 다양한 EPUB 리더 호환성 향상
  - 기존: `Noto Sans KR, serif`
  - 변경: `Noto Sans KR, Apple SD Gothic Neo, Malgun Gothic, 맑은 고딕, sans-serif`

#### UI 개선
- 진행률 표시 개선: 애니메이션 → 실제 진행 상태 표시
- 오류 발생 시 더 상세한 메시지 표시

#### 빌드 및 개발 환경
- 빌드 스크립트가 `/Applications` 폴더에 직접 설치하도록 변경
- 데스크톱에 로그 파일 생성하는 코드 제거
- quarantine 속성 자동 제거

### 버그 수정
- HWP 파일 처리 시 빈 파일 검증 추가
- HWPX 파일에서 콘텐츠를 찾을 수 없을 때 명확한 오류 메시지

### 코드 정리
- PyQt 버전에서 디버그 로깅 코드 제거
- 불필요한 `datetime` import 제거

---

## v1.1.0 (이전 버전)

### 기능
- HWP/HWPX 파일 지원 추가
- PDF 텍스트 추출 기능
- 드래그 앤 드롭 지원 (PyQt 버전)
- macOS 권한 자동 처리

---

## v1.0.0 (초기 버전)

### 기능
- TXT, DOCX 파일에서 EPUB 생성
- 자동 챕터 분할
- PyQt6, pywebview, Tkinter 3가지 UI 버전
- macOS 앱 번들링
