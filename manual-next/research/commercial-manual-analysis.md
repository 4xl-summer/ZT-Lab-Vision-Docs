# 상용 비전 매뉴얼 공개 자료 비교 — 정보 구조 벤치마킹

> 기록일: 2026-11-08
> 범위: 공식 웹사이트에 **공개된 문서 분류·탐색 구조**에 대한 조사. 로컬 `W:\Source\Vision-Manuals`의 실제 원문을 읽은 분석이 아님.

## 조사 출처와 사실

| 공급사 | 공식 자료 | 확인한 문서 구성 | ZVision에 반영할 원칙 |
| --- | --- | --- | --- |
| MVTec HALCON | https://www.mvtec.com/products/halcon/documentation | Reference Manual, HALCON Basics, Solution Guide, Programmer's Guide, Technical Notes, Release Notes | 초보용 입문/이론 가이드와 정식 API Reference 분리, 검사 영역별 Solution Guide 마련 |
| Cognex VisionPro | https://support.cognex.com/en/products/visionpro | 소프트웨어 및 하드웨어 설명서, Quick Reference, 튜토리얼, 지원 자료 | 실제 엔지니어 작업 흐름과 제품·하드웨어 통합의 문제 해결 문서 분리 |
| Euresys Open eVision | https://docs-euresys.alliedvision.com/ | Open eVision 라이브러리별 문서 진입, 버전 선택 제공 | 라이브러리/카테고리별 명확한 분류 및 버전 탐색 |
| Matrox Imaging Library (MIL) | https://www.matrox.com/apps/imaging_documentation_files/mil_userguide.pdf | 공개된 MIL User Guide(옛 버전) | 사용 개념과 언어/플랫폼 안내를 API 단순 목록과 분리 |

## 구조 분석에서 도출한 필수 원칙

1. **Start / Concepts / Guides / API / Recipes / Advanced / Reference**를 분리한다.
2. 소주제는 **독립 HTML 파일**로 작성하고 카테고리 페이지는 목록만 안내한다.
3. 문서 한 페이지에서 "무엇/왜 → 실제 API → 매개변수 → 결과·수명 → 예제 → 한계"를 확인하도록 한다.
4. 실제 구현된 기능과 향후 계획·실험을 구분하고 언어별 API 이름을 코드와 대조한다.
5. 생산·실장비 결과가 없는 가이드에서 검출률·속도·정밀도를 수치로 단정하지 않는다.
6. 제품 원문·도표·스크린샷을 복사하지 않고 자체 설명과 합성 이미지·SVG를 작성한다.

## 확인되지 않은 내용

- 사용자 로컬 `W:\Source\Vision-Manuals` 폴더는 이 세션에서 접근 불가.
- 각 제품의 설치형 CHM/PDF 원문 구조, 개별 파라미터 페이지 품질, 페이지당 예제 수 등은 검증하지 못함.
- 이 비교는 **외부 공개 사이트 분류의 기본 벤치마킹**이지, 로컬 자료 전수 분석의 완료 판정은 아님.

## 추후 검증해야 할 자료

로컬 환경에서 실제 파일 목록·버전·라이선스 확인 후 다음을 기록: 분류별 대표 문서의 위치, 각 API 설명 완성도, 예제/이미지/수식 작성 방식, 탐색·검색 실측, 채택할 원칙 및 비채택 이유. 외부 문서 내용의 무단 전재 금지.
