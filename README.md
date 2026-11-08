# ZVision 개발자 매뉴얼

[업데이트된 매뉴얼](https://4xl-summer.github.io/ZT-Lab-Vision-Docs/manual-next/) · [API 색인](https://4xl-summer.github.io/ZT-Lab-Vision-Docs/manual-next/reference/) · [실행 검증](https://4xl-summer.github.io/ZT-Lab-Vision-Docs/manual-next/reference/verification.html)

문서 기준 SDK: `ce902e85c3405eb63df40c699ddbdf70ee1d03bd`. 원리·설정·입출력·좌표·수명·오류와 실행 프로젝트를 연결합니다. 기존 루트 매뉴얼과 해시 링크는 유지하고 신판 진입 링크를 제공합니다.

소주제 HTML, 원본 페이지 레코드(`manual-next/content/pages.json`), 실제 SDK에서 추출한 API 메타데이터, 검색·공통 스타일, 실행 예제 다운로드로 구성합니다. SDK 코어 구현, 생산 데이터, 제3자 상용 매뉴얼 원본은 포함하지 않습니다.

## 수정과 재생성

본문은 `manual-next/content/pages.json`에서 수정한 뒤 `python manual-next/scripts/build_manual.py --docs . --build`로 생성합니다. SDK가 바뀌면 해당 SDK를 빌드·import·문서화해서 API 메타데이터도 다시 대조해야 합니다. 기존 메타데이터를 새 SDK의 검증 결과로 재사용하지 않습니다.

```sh
node manual-next/scripts/validate.cjs
python manual-next/scripts/check_content.py
python -m http.server 8766 --bind 127.0.0.1
```

로컬 서버에서 `manual-next/`를 열어 검색·목차·테마·모바일 화면을 확인합니다. 검색 API 색인은 필요할 때 불러오므로 서버를 통한 열람이 필요합니다. GitHub Pages와 HTML QA는 별도 워크플로로 실행합니다.

## 실행 범위

Linux x64 / Ubuntu 24.04 WSL, Rust 1.85.1, .NET SDK 10.0.403, CPython 3.14에서 통합 예제와 문서의 전체 코드 블록을 실행했습니다. 생성 wheel·NuGet의 별도 설치 소비자와 다운로드 ZIP을 푼 프로젝트도 확인했습니다. 입력·기대값·코드 해시는 `manual-next/content/verification.json`에 있습니다.

선언·설명 대조, 코드 실행, 브라우저 검증은 각각 다른 증거입니다. 실측·실장비·GPU·생산 정확도·전체 경계 입력의 인수는 포함하지 않습니다. 상세 범위는 매뉴얼의 API 범위와 검증 페이지를 확인하세요.
