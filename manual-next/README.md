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
