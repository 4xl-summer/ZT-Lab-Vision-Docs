# ZVision 공식 HTML 매뉴얼 품질 재설계 명세

> 문서 ID: ZV-DOC-DESIGN-001  
> 초안/최초 적용: 2026-11-08  
> 상태: **적용 중 — 상용 수준 최종 인수 아님**  
> 문서 대상: https://github.com/4xl-summer/ZT-Lab-Vision-Docs/tree/main/manual-next  
> 제품 코드 근거: 비공개 \`4xl-summer/ZT-Lab-Vision\` main \`ce902e85c3405eb63df40c699ddbdf70ee1d03bd\`  
> 상위 지시: [MANUAL_REBUILD_TASK.md](../../MANUAL_REBUILD_TASK.md)

## 1. 설계 목적과 범위

ZVision 사용자 매뉴얼의 목표는 **함수명과 시그니처를 나열하는 문서가 아니라, 개념을 이해한 후 실제 검사 코드를 구현·검증·문제 해결할 수 있는 산업용 기술 매뉴얼**이다. Rust 공개 Facade에서 객체의 책임을 확인하고, C#·Python·C ABI의 사용 형태와 **차이**를 정확히 설명한다.

기존 \`manual-next/\`의 **소주제별 독립 정적 HTML**은 유지한다. 사이트 전체를 삭제·재생성하거나 기존 루트 홈페이지를 교체하지 않는다. 내용의 깊이와 신뢰도를 우선 개선하며, 개선 과정에서 개별 페이지의 안정적 URL을 보존한다.

실제 사용자가 기대하는 네 가지 질문에 각 페이지가 답해야 한다.

1. **무엇이고 언제 쓰는가?** 원리, 선택 기준, 비적합 조건.
2. **정확히 어떻게 호출하는가?** 공개 객체, 시그니처, 입력 제약·단위·기본값.
3. **무엇이 반환되며 누가 해제하는가?** 값 스냅샷, 이미지/핸들, ROI 좌표, 오류.
4. **결과가 이상하면 무엇을 확인하는가?** 원본/중간/결과 비교, 흔한 실패, 테스트.

## 2. 기준 현황과 부족한 점

2026-11-08 저장소는 약 292개 HTML을 보유하지만 그중 238개가 Rust·C#·Python의 **자동 선언 색인**이다. 선언 개수는 설명의 완성도를 의미하지 않는다. 계측·3D 일부 가이드는 2~3개의 짧은 단락과 이름 표에 불과하고, 객체 모델 페이지에는 실제 구조도·완결된 객체 사용 예제가 없으며, Getting Started에 실제 개발 환경 설치 경로가 없다.

| 차이 | 확인된 증거 | 개선 계약 | 우선 |
| --- | --- | --- | --- |
| API 색인 누락 | Rust \`ZImage\`의 \`pub const fn width/height/layout/origin\`이 자동 색인에서 누락 | \`pub fn\` 외 \`pub const fn\`, re-export, 연관 구현 전체를 공개 객체 기준으로 수집 | P0 |
| 객체 중심 설명 얕음 | \`concepts/object-model.html\`은 역할 표 위주 | 객체 구성/생성/사용/소유/결과/수명 흐름, Rust·C#·Python 차이 | P0 |
| 설치·개발 첫 실행 | \`getting-started/index.html\`은 링크 목차 중심 | OS·환경별 실제 검증된 빌드·네이티브 라이브러리 배치와 첫 예제 연결 | P0 |
| 원리·파라미터 부족 | \`guides/metrology.html\`은 기본 객체명 수준 | 측정 원리, 좌표, 단계별 처리, 실패 진단, 실제 결과 필드 | P1 |
| 이미지·결과 오버레이 부족 | Blob/NCC/계측 가이드의 실측 전후 이미지 부족 | 자체 제작 도식, 재현 입력, 실행 검증된 출력·오버레이와 캡션 | P1 |
| 실행 가능성 | 많은 예제는 \`spec\`/\`image\` 사전 생성 가정 | 각 언어별 독립 실행 예제·패키지/런타임 명시·테스트 연결 | P1 |
| 파라미터 조정·오류 대응 | 초기 가이드의 '주의'는 추상적 | 증상→가능 원인→검증 방법→조정 후보→부작용 표 | P1 |
| 문서 품질 CI | 현재는 링크·제목·목차 검사 위주 | 공개 API diff·스니펫 빌드·이미지 증거·접근성 검증 | P2 |

**중요:** 이 문서의 벤치마크는 상용사의 **공개 공식 문서에서 확인한 작성 방식**에 기반하며 \`W:\Source\Vision-Manuals\`의 로컬 원문을 직접 열람한 증거는 아니다. 로컬 실제 문서 비교는 별도 확인 과제다.

### 2.1 참조한 상용 문서의 좋은 관행

- **HALCON**: 한 연산에 대해 원리, 파라미터, 연산 제약, 예제와 관련 연산을 연결하는 심층 API Reference. 공식 참조 진입: https://www.mvtec.com/products/halcon/documentation
- **Cognex VisionPro**: Tool/Pattern/RunParams/Results의 객체 관계와 개별 결과·예외의 진단. 공식 지원 진입: https://support.cognex.com/en/products/visionpro
- **Euresys Open eVision**: 샘플 이미지 준비 → Gauge/도구 설정 → 결과 확인의 작업 튜토리얼. 공식 문서: https://docs-euresys.alliedvision.com/
- **Matrox MIL**: Blob/계측 기능을 데이터 준비→추출→피처→분석→응용 사례로 나누는 사용자 가이드. 공개된 구 버전 자료와 현재 제품 버전은 구분한다.

저작권이 있는 문장·도식·스크린샷·예제 소스를 가져오지 않는다. 원칙을 참고하여 **ZVision 고유의 설명과 도식**을 제작한다.

## 3. 문서 정보 구조 (IA) 및 페이지 단위

| 구역 | 책임 | 파일 규칙 |
| --- | --- | --- |
| Getting Started | SDK 선택, 설치/빌드/첫 실행 | \`getting-started/<one-topic>.html\` |
| Concepts | 객체, 메모리, ROI, 좌표, Query, Result | \`concepts/<one-concept>.html\` |
| Guides | 알고리즘 원리·파라미터·선택·진단 | \`guides/<one-algorithm>.html\` |
| API | 객체가 소유하는 공개 메서드별 사용 계약 | \`api/<language>/<one-api>.html\` |
| Recipes | 실제 검사 입력부터 판정까지 | \`examples/<one-scenario>.html\` |
| Reference | 에러·형식·호환·릴리스·자동 선언 색인 | \`reference/...html\` |
| Design (편집자용) | 정보 설계·작성 규칙·QA | \`design/*.md\` |

- 소주제 **하나 = 독립된 HTML 파일 하나**. 거대 통합 HTML을 만들지 않는다.
- 기존 292개 페이지의 URL을 함부로 제거하지 않는다.
- 카테고리 홈은 안내 카드와 학습 순서만 제공하고, 실제 설명은 소주제 페이지에 둔다.
- 공통 CSS/JS 사용, 각 페이지는 JavaScript 없이도 본문과 링크를 열람할 수 있어야 한다.
- 링크: 해당 주제의 개념 → 관련 API → 완결 예제 → 실패 해결 방법. Breadcrumb, H1, 제목·본문의 시맨틱 레벨을 유지한다.
- 자동 선언 색인 \`reference/{rust,csharp,python}/\`은 **소스 탐색 보조 자료**다. 검토·실행 검증된 API 페이지와 명확히 구분한다.

## 4. 객체 중심 설명 규칙

### 4.1 단일 객체의 설명 구조

해당 객체의 **책임**, 객체가 가진 **데이터·상태**, 제공하는 **동작**, 요청에 필요한 **Spec/Options**, 반환하는 **이미지/Result**, 가능한 **실패/빈 결과**, **해제·복사·공유 계약**을 순서대로 설명한다.

대표 객체 관계는 다음과 같다.

\`\`\`text
ZImage (픽셀 데이터) ── Threshold/Blur/Roi ──> 새 ZImage
       │
       ├─ query() ─> ImageQuery ─> execute() ─> Execution (output + capture)
       │
       └─ MatchModel.find(image, MatchSpec) ─> MatchResult ─> Match 값들
             ▲
       MatchModel.train_ncc(template)
\`\`\`

- 영상 변환의 결과는 소유 \`ZImage\`인지, 값인지 구분한다.
- \`MatchModel\`은 학습 상태를 소유한다. \`MatchSpec\`은 검색 옵션 값이다. \`MatchResult\`는 독립 값 스냅샷이다.
- Rust \`ImageQuery\` Builder 메서드는 이동형(\`self\`)으로, C#/Python의 관리형 Query Builder는 **가변 객체**로 해석한다.
- ROI/Share는 **별개의 소유 이미지 객체**이지만 같은 픽셀 저장소를 공유한다.
- Rust 소유권 \`Drop\`, C# \`using/Dispose\`, Python \`with/close\`의 사용자 규칙을 분리한다.

### 4.2 공개 API 진실의 원천

\`4xl-summer/ZT-Lab-Vision\`의 **현행 공개 Facade·Wrappers·C ABI**가 기준이다. 내부 알고리즘 구현이 있다고 해서 사용자 공개 API로 기재하지 않는다. 불변 스냅샷과 소유 핸들의 차이를 유지한다.

검증해야 할 공개 항목 종류: \`pub fn\`, \`pub const fn\`, \`pub async fn\`, \`pub use\`, trait 공개 메서드, feature 조건, C# 클래스/partial/오버로드/프로퍼티, Python public 속성·메서드·re-export, C ABI 함수와 handle ownership. 실제 AST·빌드 기반 수집이 가능하면 정규식보다 우선한다.

## 5. 페이지별 품질 기준

### 5.1 개념 페이지 (Concepts)

반드시 들어갈 내용:
1. **짧은 정의**와 어떤 문제를 해결하는지.
2. 시각적 **개념도**. 글자 크기, 범례, 원점/소유 방향 표시; 원본 도식임을 캡션에 명시.
3. 결과가 다른 두 사례 비교 (ROI vs Crop, Share vs Deep Copy 등).
4. Rust/C#/Python 공개 시그니처 또는 정확한 언어별 사용 예.
5. 오류·수명·좌표·픽셀 형식에 대한 명시된 제약.
6. 사용자가 바로 확인할 수 있는 작은 재현 예제와 기대 출력.
7. 관련 알고리즘/API/Recipe 링크.

### 5.2 알고리즘 페이지 (Guides)

원리·수식 → 입력/전제 조건 → 파라미터 타입·단위·유효 범위·기본값 → 처리 단계 → 원본·중간·최종 영상 → 결과 필드 → 실패/파라미터 조정 표 → 비교 알고리즘 → 소유권·복사/실행비용 → 실행 예제. 추정한 성능과 시각화를 실제 실행 결과라고 표기하지 않는다.

### 5.3 정식 API 페이지 (API)

| 필수 필드 | 규칙 |
| --- | --- |
| 객체/메서드/모듈 | 정식 공개 경로와 확인한 SHA 명기 |
| 시그니처 | 언어별 실제 선언 및 오버로드; 생성·팩토리 구분 |
| 인자 | 이름, 타입, 값 범위/기본값/단위, null 가능 여부 |
| 반환 | 타입, 불변값/새 이미지/공유 이미지/소유 핸들 |
| 오류 | 유효성 오류, 알고리즘 오류, 정상 빈 결과 구분 |
| 데이터 제약 | 지원 픽셀 형식, ROI origin, stride, NaN, 경계 |
| 자원 수명 | Rust Drop, .NET Dispose, Python close |
| 예제 | 독립 실행 및 예상 출력, 실제 검증 상태 |
| 연관 자료 | Concept, Guide, Recipe, Result, 버전 |

검증되지 않은 필드는 '미확인', 미적용은 '해당 없음'으로 표시한다. 확인하지 않은 기본값·속도·정밀도를 만들어 넣지 않는다.

### 5.4 실전 레시피 (Recipes)

준비물·코드 환경, 입력 이미지(라이선스·생성 방법), ROI 및 단계별 처리 목적, 전체 컴파일 가능한 코드, 원본/단계/출력의 이미지·수치, 결과 객체에서 합격/불합격 판단하는 방법, 실패/민감도 실험, 실제 활용 시 한계.

소프트웨어 합성 예제를 실장비 생산 검증 결과라고 주장하지 않는다.

## 6. 시각자료와 예제의 정확성

- 각 핵심 개념에 **자체 제작 SVG**를 기본으로 한다. 로컬/글로벌 좌표, 버퍼 소유, 흐름의 화살표 방향을 명시한다.
- 알고리즘별 실습에는 **재현 가능한 원본 및 처리 후 이미지**를 넣는다. 도식은 "개념도", 계산 결과는 "검증된 합성 실행 결과", 생산 이미지는 "실장비 검사 이미지"로 구분한다.
- 원본/중간/최종 결과의 동일한 ROI·스케일·색상 범례·임계값 등 비교 조건을 함께 표시한다.
- 이미지 자체에 로고나 저작권 있는 상용 화면을 그대로 복제하지 않는다.
- 코드 예제의 import/namespace, Native DLL 또는 Python Wheel 버전, 오류 처리 및 소유 객체 해제를 포함한다.
- 실제 빌드·실행하지 않았다면 **코드 검토**라고 표시하고 예상 출력이 기존 테스트 기반인지 수학적 기대값인지 구분한다.

## 7. 검증 게이트 및 출시 상태

### G0 — 출처/경로
공개 SDK 경로와 기준 SHA 확인, 공개 저장소에 비공개 코드·사내 이미지·상용 문서 원문 유출 없음.

### G1 — API 정확성
공개 시그니처, 기본값, 오류, 결과/수명, feature/지원 형식 확인. Rust \`pub const fn\` 누락 등 자동 색인 불완전성을 별도 추적.

### G2 — 문서 구조
페이지 H1 하나, 고유 title, 안정 URL, sidebar/index/search 연결, 모든 내부 링크/앵커 유효. \`node manual-next/scripts/validate.cjs\`가 통과해야 함.

### G3 — 실행 예제
Rust/C#/Python에서 독립 실행·assert 성공, README/설치 안내와 패키지 버전 확인. 실제 실행할 수 없는 경우 G3 미통과.

### G4 — 콘텐츠·디자인
자체 도식과 실제 이미지 구분, 모바일/데스크톱 가독성, 키보드 탐색, 사용자 FAQ/오류 진단. 실제 브라우저 검수 필요.

### G5 — 산업 인수
실장비·반복성·측정 불확도·검출률·처리시간 시험은 별도의 사용자 수락 범위. G2·G3 성공과 혼동 금지.

페이지 상태: \`설계\` → \`초안\` → \`소스 대조\` → \`실행 검증\` → \`시각 QA\` → \`출시\`. 모든 조건을 충족하기 전에는 '상용 수준 완료' 또는 '공식 인수'라고 표시하지 않는다.

## 8. 작업 계획 및 이력

### Phase A — 핵심 객체와 입문 (P0: 이번 첫 적용)

| 페이지 | 주요 변경 |
| --- | --- |
| \`concepts/object-model.html\` | 객체 구성·흐름의 원본 SVG, 책임표, Rust/C#/Python 실제 코드 및 상태·수명 |
| \`concepts/zimage.html\` | 공개 ZImage 속성·행동·형식·처리 흐름을 별도 페이지로 작성 |
| \`concepts/roi.html\` | ROI 중첩, local/global 원점, stride/offset, 원본 해제 후 소유 실험 |
| \`concepts/share.html\` | Share/ROI/Deep Copy의 저장소 토폴로지, 수명 및 실제 예제 |
| \`concepts/lifetime.html\` | Drop/Dispose/close 및 Result 스냅샷의 표준 설명 |
| \`getting-started/index.html\` | 실제 환경 준비 → 첫 이미지 → 관련 API 학습 경로 |
| \`getting-started/sdk-setup.html\` | Rust/C#/Python 개발 환경·Native ABI 준비와 검증되지 않은 설치 단계 분리 |
| \`reference/rust/image-zimage.html\` | \`pub const fn\` 누락 네 메서드 정확한 시그니처·주석 반영 |

### Phase B — 산업 영상 알고리즘 (P1)

- Threshold, Blur, Morphology, Canny, Blob, NCC, AbsDiff 페이지를 각각 예제·결과 이미지·파라미터 영향·실패 진단까지 확대.
- 특히 Blob의 면적·경계·중심·연결성, NCC의 점수·ROI·NMS, 계측의 유효 Probe·Fit 유무를 대상별로 설명.
- 기능 존재 여부를 먼저 확인하고 **미구현 API를 넣지 않는다**.

### Phase C — 실전 검사 레시피 (P1)

- 합성 입력·출력 배열 단위를 넘어, 여러 처리 단계(영상 → ROI → 필터/차분 → 분석 결과 → 오버레이 → 판정)를 검증된 이미지와 코드로 작성.
- C# 검사장비 개발자가 바로 사용할 수 있도록 소유권, WinForms/WPF 표시 어댑터 및 로깅 흐름을 보강하되 제품 코드는 변경하지 않는다.

### Phase D — API 전수 감사/자동화 (P0 병행)

- 실제 공개 Rust 객체별 모든 메서드와 C#/Python 래퍼 공개 API, C ABI의 분모 확정.
- 자동 추출 색인과 수동 검증 API의 누락/차이 보고서 구축.
- \`pub const fn\`을 포함한 모든 공개 선언, 재수출, 속성, feature별 차이를 비교.
- 예제 스니펫 빌드·실행 CI, 이미지 생성 재현, 링크/앵커/접근성 검사 확장.

### Phase E — 전체 QA/버전/배포 (P2)

- 웹·모바일 시각 QA, 문서 버전과 SDK 버전 매핑, 이전/다음 주제, 실제 검색 적합성 검사.
- 기존 공개 매뉴얼의 경로 전환은 별도 검토·회귀 확인 후 한다.

## 9. 이번 단계의 작업 경계 및 보고 형식

이번 적용 범위는 **별도 설계문서 작성 + Phase A 페이지 개정**이다. Phase B~E는 설계에 의한 후속 미완료 상태로 관리한다. 변경한 HTML 파일, Git SHA, 실제 확인한 SDK와 브라우저/CI 검증 결과를 보고하고, 실행하지 않은 사항은 미실행이라고 표시한다.

최종 출시에 앞서 \`W:\Source\Vision-Manuals\`의 실제 상용 매뉴얼 원문 조사와 전체 API/예제/실장비 인수는 여전히 필요하다.
