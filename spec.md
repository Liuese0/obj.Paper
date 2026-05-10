# obj.Paper — 디자인 기획 문서 v1.0
> Claude Design 전달용 | LShift | 2026

> 본 문서는 v1.0 구현의 정본 스펙이다. 코드는 이 문서를 따른다.

---

## 0. 한 줄 요약

**"학술 논문을 블록 단위로 조립하고, 실시간으로 PDF처럼 미리보며, 한 번의 클릭으로 내보내는 데스크톱 에디터"**

GitHub Star를 목표로 하는 오픈소스 프로젝트. PyQt6 기반 Windows 데스크톱 앱(`.exe`).
코드가 아닌 논문 구조에만 집중할 수 있도록 에디터 UX를 최우선으로 설계한다.

---

## 1. 프로젝트 컨텍스트

| 항목 | 내용 |
|------|------|
| 플랫폼 | Windows 11 (`.exe`), macOS 12+ (`.app` / `.dmg`) |
| 프레임워크 | Python 3.11 + PyQt6 |
| 브랜드 | LShift (심볼: `<<`) |
| 타겟 사용자 | 대학원생, 학부 연구자, 논문 작성 입문자 |
| 지원 언어 | 영어(기본), 한국어 |
| 내보내기 | PDF, HTML |
| 저장 형식 | JSON (v2 스펙, v1 하위 호환) |

---

## 2. 디자인 원칙

1. **Academic Calm** — 논문 작성은 집중력이 필요한 작업. 불필요한 시각 노이즈 제거, 눈이 피로하지 않은 크림 계열 배경.
2. **Block-First** — 사용자는 "블록"이라는 단위로 생각한다. 블록의 경계, 타입, 순서가 항상 명확하게 보여야 한다.
3. **What You See Is Close To What You Get** — 우측 미리보기가 실제 PDF 출력과 최대한 근사해야 한다.
4. **Progressive Disclosure** — 자주 쓰는 기능은 즉시 접근, 고급 설정은 필요할 때만 노출.
5. **Keyboard-First** — 마우스 없이도 빠르게 작업할 수 있는 단축키 체계.

---

## 3. 컬러 시스템

### 3.1 기본 팔레트

| 역할 | 이름 | HEX | 사용처 |
|------|------|-----|--------|
| **Background** | Parchment | `#F3F0E9` | 앱 전체 배경, 캔버스 영역 |
| **Accent / Primary** | Terracotta | `#D97757` | 버튼, 선택 상태, 강조, 블록 타입 뱃지 |
| **Surface** | Warm White | `#FDFCF8` | 팔레트 패널, 미리보기 페이지 배경 |
| **Surface 2** | Sand | `#EAE7DE` | 패널 구분선, 비활성 영역, 구분자 |
| **Text Primary** | Ink | `#2C2820` | 본문 텍스트, 블록 내 텍스트 |
| **Text Secondary** | Dust | `#7A7268` | 레이블, 힌트, 플레이스홀더 |
| **Text Tertiary** | Mist | `#B0A99E` | 비활성 UI, 구분선 텍스트 |
| **Border** | Warm Gray | `#D8D3C9` | 패널 테두리, 블록 구분선 |
| **Accent Hover** | Deep Terra | `#C06644` | 버튼 호버 상태 |
| **Accent Light** | Blush | `#F2DED5` | 선택된 블록 배경 하이라이트 |
| **Error** | Red | `#C0392B` | 에러 메시지 |
| **Success** | Forest | `#27AE60` | 저장 완료, 내보내기 성공 |
| **Info** | Steel | `#2980B9` | 정보 툴팁 |

### 3.2 다크모드
v1.0에서는 다크모드 미지원. 향후 확장 고려하여 CSS 변수 방식으로 색상 토큰화.

### 3.3 색상 사용 규칙
- Terracotta(`#D97757`)는 **한 화면에 최대 3개 요소**에만 사용. 남용 금지.
- 배경에 Parchment, 패널에 Warm White → 미묘한 깊이감을 만들어 3분할 구조를 자연스럽게 구분.
- 블록 선택 시: 테두리를 Terracotta 2px, 배경을 Blush로.

---

## 4. 타이포그래피

### 4.1 UI 폰트 (앱 인터페이스용)
- **Primary**: `Segoe UI` (Windows 기본) / fallback `Inter`
- **Mono**: `Cascadia Code` / fallback `Consolas` (코드 블록 내부)

### 4.2 문서 렌더링 폰트 (미리보기 & PDF 출력용)
사용자가 Document Settings에서 선택 가능:

| 카테고리 | 폰트 | 특성 |
|----------|------|------|
| Serif (기본) | `Times New Roman` | 전통적 논문 스타일 |
| Serif | `Georgia` | 가독성 높은 세리프 |
| Sans | `Arial` | 깔끔한 현대적 스타일 |
| Sans | `Helvetica Neue` | 디자인 논문 |
| Mono | `Courier New` | 레트로 타이프라이터 |

### 4.3 UI 텍스트 크기 스케일

```
Title (앱 윈도우):   13px / Segoe UI / Regular
Panel Header:        12px / Segoe UI / Semibold / Uppercase
Block Label:         11px / Segoe UI / Regular
Body (블록 에디터):  14px / 문서 폰트
Caption / Hint:      11px / Segoe UI / Regular / Color: Dust
```

---

## 5. 레이아웃 구조

### 5.1 전체 윈도우 구성

```
┌─────────────────────────────────────────────────────────────────┐
│  MENU BAR   [File] [Edit] [View] [Format] [Insert] [Help]       │
├─────────────────────────────────────────────────────────────────┤
│  TOOLBAR    [저장] [내보내기▾] [실행취소] [재실행] [포맷]       │
├──────────┬──────────────────────────────────┬───────────────────┤
│          │                                  │                   │
│  BLOCK   │       CANVAS (편집 영역)          │   PREVIEW         │
│  PALETTE │                                  │   (PDF 미리보기)  │
│  (좌측)  │                                  │   (우측)          │
│  240px   │         flex: 1                  │   340px           │
│          │                                  │                   │
├──────────┴──────────────────────────────────┴───────────────────┤
│  STATUS BAR   블록 수: 12개 | 단어 수: 1,423 | 마지막 저장: 2분 전 │
└─────────────────────────────────────────────────────────────────┘
```

**최소 창 크기**: 1280 × 720px
**권장 창 크기**: 1440 × 900px 이상

### 5.2 좌측 — Block Palette (240px 고정)

- 검색 필드 (실시간 필터링)
- STRUCTURE / CONTENT / ACADEMIC / TEMPLATES 그룹
- 드래그 → 캔버스 드롭, 더블클릭으로 현재 커서 위치에 삽입

### 5.3 중앙 — Canvas (편집 영역, flex)

**블록 상태 표시**:
- **기본**: 얇은 Warm Gray 테두리 (0.5px)
- **호버**: 테두리 D97757 (1px), 오른쪽 상단에 [↑][↓][⋮] 컨트롤 표시
- **선택(포커스)**: 테두리 D97757 (2px), 배경 Blush(#F2DED5)
- **드래그 중**: 반투명(70%), 드롭 위치에 Terracotta 수평선 표시

### 5.4 우측 — Preview Panel (340px 기본, 240–480px 리사이즈)

- 실시간 업데이트 (편집 후 500ms debounce)
- 페이지 번호 네비게이션
- "외부 PDF 열기" → 참고 PDF를 이 패널에서 표시 가능

---

## 6. 블록 타입 상세 정의 (12종)

`title`, `authors`, `abstract`, `heading`, `paragraph`, `equation`, `figure`, `table`, `list`, `code`, `references`, `pagebreak`

각 블록 공통 속성:

```json
{
  "id": "uuid",
  "type": "block_type",
  "data": { ... },
  "settings": {
    "alignment": "left|center|right|justify",
    "spacing_before": 12,
    "spacing_after": 12
  }
}
```

세부 정의는 원본 디자인 문서 §6.2 참조.

---

## 7. 인라인 포맷팅 툴바

블록 내 텍스트 선택 시 플로팅 툴바 표시: B/I/U/S/∑/🔗/색상/지우기.

| 버튼 | 기능 | 단축키 |
|------|------|--------|
| **B** | 굵게 | Ctrl+B |
| *I* | 기울임 | Ctrl+I |
| U | 밑줄 | Ctrl+U |
| S | 취소선 | - |
| ∑ | 인라인 수식 감싸기 | Ctrl+M |
| 🔗 | 하이퍼링크 | Ctrl+K |
| 색상 | 텍스트 색상 | - |
| 지우기 | 포맷 제거 | Ctrl+\ |

---

## 8. Document Settings (문서 전체 설정)

캔버스 상단 `[Document Settings ⚙]` 버튼 클릭 시 우측에서 슬라이드인하는 설정 패널.
TYPOGRAPHY / LAYOUT / NUMBERING / TEMPLATE 4섹션.

---

## 9. 논문 포맷 템플릿

| 템플릿 ID | 이름 | 용지 | 컬럼 | 여백 | 폰트 |
|-----------|------|------|------|------|------|
| `ieee` | IEEE Conference | Letter | 2단 | 좁음 | Times NR 10pt |
| `acm` | ACM SIGPLAN | Letter | 2단 | 표준 | Linux Libertine 10pt |
| `nature` | Nature Journals | A4 | 1단 | 넓음 | Arial 10pt |
| `lncs` | Springer LNCS | A4 | 1단 | 표준 | Times NR 10pt |
| `apa` | APA Style | Letter | 1단 | 넓음 | Times NR 12pt |
| `general` | General (기본) | A4 | 1단 | 표준 | Times NR 12pt |

---

## 10. 내보내기 (Export)

- PDF: QPrinter로 인쇄 출력
- HTML: 단일 `.html` 파일 (CSS 인라인, 수식 base64 PNG)

---

## 11. 파일 관리 (저장/로드)

`.pw` 또는 `.json` (JSON v2 스펙). 30초 자동 저장.

---

## 12. 단축키 목록

macOS는 `Ctrl` 대신 `Cmd(⌘)` 사용.

| 기능 | Windows | macOS |
|------|---------|-------|
| 저장 | Ctrl+S | ⌘S |
| 다른 이름으로 저장 | Ctrl+Shift+S | ⌘⇧S |
| PDF 내보내기 | Ctrl+E | ⌘E |
| 실행 취소 / 재실행 | Ctrl+Z / Ctrl+Y | ⌘Z / ⌘⇧Z |
| 새 문서 | Ctrl+N | ⌘N |
| 열기 | Ctrl+O | ⌘O |
| 블록 위/아래로 이동 | Alt+↑/↓ | ⌥↑/↓ |
| 블록 복제 | Ctrl+D | ⌘D |
| 블록 삭제 | Delete | Backspace |
| 현재 블록 아래에 새 단락 추가 | Ctrl+Enter | ⌘Return |
| 블록 타입 변경 팝오버 | Ctrl+/ | ⌘/ |
| 포맷 템플릿 선택 | Ctrl+Shift+P | ⌘⇧P |
| 집중 모드 | F11 | ⌘Ctrl+F |
| 언어 전환 (영/한) | Ctrl+Shift+L | ⌘⇧L |

---

## 13. 다국어 지원

영어(`en`) / 한국어(`ko`). View → Language로 즉시 전환.

---

## 14. 상태 표시줄 (Status Bar)

`블록: 14개  |  단어: 2,847  |  페이지: 8  |  마지막 저장: 3분 전  |  영어 ▾`

---

## 15. 집중 모드 (F11)

좌·우 패널 숨김, 캔버스 중앙 정렬, 상단 툴바 최소화.

---

## 16. 외부 PDF 참조 기능

우측 미리보기 패널에서 외부 PDF를 표시 가능.

---

## 17. 접근성 / 확장성

- 키보드만으로 모든 기능 접근 가능
- `@register_block` 데코레이터로 새 블록 타입 추가 가능

---

*문서 끝 — obj.Paper Design Spec v1.0 | LShift 2026*
