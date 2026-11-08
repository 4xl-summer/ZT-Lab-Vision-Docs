# ZVision 신규 HTML 매뉴얼 — 개발 및 검증 현황

> **2026-11-08 기준** · 실제 신규 사이트: [index.html](index.html) · [재구축 지시서](../MANUAL_REBUILD_TASK.md)

이 저장소의 `manual-next/`는 기존 공개 매뉴얼의 루트 경로를 변경하지 않은 채 **소주제별 독립 HTML 페이지**로 구축 중인 차세대 기술 매뉴얼입니다. 개념·가이드·API 상세·합성 검사 예제와 소스 선언 자동 색인을 분리합니다.

## 현재 구성

- **HTML 전체: 292페이지** (GitHub 저장소 트리 기준)
- 분야별 기초/알고리즘 가이드: ROI, 객체 수명, Query, Threshold, Morphology, Canny, Blob, NCC, 차분, 측정, 보정, 3D, 색상, OCR, 추론, 취득 등
- 정식 사용 예시: First Image, ROI Threshold, Blob, NCC 검색, 차분 점 결함의 합성 데이터 예제
- **언어별 선언 색인:** [Rust](reference/rust/index.html), [C#](reference/csharp/index.html), [Python](reference/python/index.html)
- **API 조사 범위:** Rust Facade 20개 모듈 **650개 메서드 선언**, C# Wrapper 10개 파일 **316개 공개 멤버 후보**, Python SDK 10개 파일 **239개 공개 메서드 후보**
- **합계 1,205개**는 *검토한 모듈에서 추출한 후보 수*이며 **전 SDK 공개 API의 분모/공식 커버리지 수치가 아님**
- [API 커버리지·미완료 상태](reference/coverage.html)
- [검증 및 작업 기록](research/progress-2026-11-08.md)

## 자동 품질 검사

- `node manual-next/scripts/validate.cjs`: HTML별 H1, title, 이동 링크, 앵커, 메뉴 정합성 검사
- `.github/workflows/html-manual-qa.yml`: 변경 시 HTML Manual QA 실행
- 별도 GitHub Pages 배포 워크플로 유지
- 현재까지 확인된 HTML Manual QA 실행 성공: [GitHub Actions](https://github.com/4xl-summer/ZT-Lab-Vision-Docs/actions/runs/42478910779)

## **아직 완료되지 않은 것**

1. **상용 매뉴얼 실자료 분석:** 로컬 `W:\Source\Vision-Manuals`의 실제 파일에 이 환경에서 접근할 수 없음
2. **전체 공개 API 100%:** Rust의 re-export·매크로, C#/Python의 다른 수많은 모듈, C ABI 전수 감사가 남음
3. **각 API별 상용 수준 문서:** 모든 항목의 매개변수·오류·소유권·형식·도식·재현 예제를 수동 확인하지 못함
4. **실행 검증:** 새 Rust/C#/Python 빌드와 실제 장비·생산 데이터에 대한 신뢰성/정밀도/성능 인수 미실시
5. **시각적 브라우저 검수:** 모바일/데스크톱의 모든 페이지 렌더링 및 WCAG 전체 검사를 끝내지 못함

**규칙:** 자동 선언 색인은 매뉴얼 작성과 검증을 보조하는 자료다. 선언이 있다고 해서 상용 수준 API 설명·예제 테스트가 완료된 것이 아니다. 확인되지 않은 동작은 추정해 기재하지 않는다.

## 개발 환경과 재현

HTML, CSS, JS는 웹사이트 루트에 필요한 서버 기능이 없는 정적 파일이다. 별도의 빌드 도구 없이 로컬 정적 서버에서 `manual-next/index.html`을 열 수 있다. 최신 Node.js 환경에서 `node manual-next/scripts/validate.cjs`로 링크 검사할 수 있다. Python이나 .NET/Rust 예제는 각각 해당 SDK 설치·네이티브 라이브러리가 있어야 실행된다.

기존 사이트 루트 파일은 마이그레이션 인수 전까지 유지한다. 비공개 코어 구현, 사내 이미지 및 제3자 상용 매뉴얼 원본은 이 공개 저장소에 업로드하지 않는다.
