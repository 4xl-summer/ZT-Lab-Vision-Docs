# ZVision 신규 HTML 매뉴얼 (초기 작성)

기존 공개 사이트를 유지한 채 별도 경로 `manual-next/`에 새 기술 매뉴얼을 구축합니다.

- [진입 페이지](index.html)
- [작업지시서](../MANUAL_REBUILD_TASK.md)
- 형식: 소주제별 독립 정적 HTML, 공통 CSS/JS, 카테고리 목차 및 검색
- API 검토: 공개 Rust Facade, C#, Python 실제 소스 기준 `ce902e85c3405eb63df40c699ddbdf70ee1d03bd`
- 검증 수준: 소스와 기존 테스트 대조 / 신규 SDK 실행·브라우저 실물 QA는 미수행
- 자료 제한: 로컬 `W:\Source\Vision-Manuals`에 직접 접근 불가. 상용 매뉴얼 벤치마킹 미완료
- 보안: 비공개 코어 구현·상용 매뉴얼 원문 반출 금지

완료된 대표 소주제의 품질을 검증한 뒤 점진 확대하고, 기존 루트 사이트의 전환은 별도 검증 후 수행합니다.

## 2026-11-08 문서 확장 (Phase C/D 초기)

- 새 소주제 HTML: 15개 추가 (핵심 개념, 알고리즘, 언어별 공개 API, 합성 검사 예제)
- 메뉴 검색 색인, 카테고리 인덱스 링크 반영
- 신규 HTML은 모두 공통 CSS/JS를 재사용하며 개별 파일 URL로 직접 접근 가능
- 공개 SDK 근거: 코드 저장소 HEAD ce902e85c3405eb63df40c699ddbdf70ee1d03bd
- 현 세션 검증: 공개 시그니처 확인, 기존 Rust 테스트 기대값 대조, HTML 기본 구조/상대 링크 정적 점검
- 현 세션 미검증: 새 Rust/C#/Python 빌드·실행, Windows/WSL 실물 테스트, 브라우저 실제 렌더링/Pages 배포 완료, W:\\Source\\Vision-Manuals의 상용 PDF 분석
- 공개 저장소에 내부 코어 구현·상용 매뉴얼 원문을 업로드하지 않음
