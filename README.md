# ZVision 개발자 매뉴얼

[업데이트된 매뉴얼](https://4xl-summer.github.io/ZT-Lab-Vision-Docs/manual-next/) · [API 색인](https://4xl-summer.github.io/ZT-Lab-Vision-Docs/manual-next/reference/) · [실행 검증](https://4xl-summer.github.io/ZT-Lab-Vision-Docs/manual-next/reference/verification.html)

문서 기준 SDK: `ce902e85c3405eb63df40c699ddbdf70ee1d03bd`. 원리·설정·입출력·좌표·수명·오류와 실행 프로젝트를 연결합니다. 기존 루트 매뉴얼과 해시 링크는 유지하고 신판 진입 링크를 제공합니다.

소주제 HTML, 원본 페이지 레코드(`manual-next/content/pages.json`), 실제 SDK에서 추출한 API 메타데이터, 검색·공통 스타일, 실행 예제 다운로드로 구성합니다. SDK 코어 구현, 생산 데이터, 제3자 상용 매뉴얼 원본은 포함하지 않습니다.

설명 소주제 526개와 SDK 고유 메서드·생성자·연관 함수 3,250개를 독립 파일로 연결하고 시각 해설과 실제 사진 사례를 보강한 총 6,152페이지입니다. 필드와 열거값은 소유 타입에서 함께 설명합니다. 장 페이지는 개요와 하위 페이지 목록을 제공하며, 이전 `페이지#소주제` 주소는 대응하는 파일로 연결됩니다.

## 수정과 재생성

본문은 `manual-next/content/pages.json`에서 수정한 뒤 `python manual-next/scripts/build_manual.py --docs . --build`로 생성합니다. SDK가 바뀌면 해당 SDK를 빌드·import·문서화해서 API 메타데이터도 다시 대조해야 합니다. 기존 메타데이터를 새 SDK의 검증 결과로 재사용하지 않습니다.

```sh
node manual-next/scripts/validate.cjs
python manual-next/scripts/check_content.py
python manual-next/scripts/check_topics.py
python manual-next/scripts/check_visuals.py
python -m http.server 8766 --bind 127.0.0.1
```

로컬 서버에서 `manual-next/`를 열어 검색·목차·테마·모바일 화면을 확인합니다. 검색 API 색인은 필요할 때 불러오므로 서버를 통한 열람이 필요합니다. GitHub Pages와 HTML QA는 별도 워크플로로 실행합니다.

하위 문서는 `parent`, `topic_anchor`, `topic_order`, `nav_label`로 구성합니다. `content/topic-redirects.json`은 이전 주소 연결, `content/topic-mapping.json`은 원래 설명 주제와 코드 해시의 대응을 기록합니다. 본문에 새 코드 예제를 추가했다면 실행 기록도 갱신해야 합니다.

독립 소주제의 화면 검증은 `content/topic-layout-verification.json`에 기록합니다. 1280×900에서 제목·탐색·자동 관련 API·검증 부록을 제외한 본문 높이가 700px 이상인지 확인합니다. 본문 해시와 줄바꿈을 정규화한 스타일 해시가 바뀌면 `check_topics.py`가 오래된 측정 기록을 거부하므로 브라우저 재측정이 필요합니다. 화면 높이는 문서 분량의 기준이며 API 동작 검증과는 별개입니다.

## 실행 범위

Linux x64 / Ubuntu 24.04 WSL, Rust 1.85.1, .NET SDK 10.0.403, CPython 3.14에서 통합 예제와 문서의 전체 코드 블록을 실행했습니다. 생성 wheel·NuGet의 별도 설치 소비자와 다운로드 ZIP을 푼 프로젝트도 확인했습니다. 입력·기대값·코드 해시는 `manual-next/content/verification.json`에 있습니다.

이번 분리에서 추가한 호출 단편 8개는 별도의 합성 입력으로 실행했습니다. SDK Python 패키지와 네이티브 라이브러리가 준비된 환경에서, 문서 저장소 루트의 `python manual-next/examples/verify-topic-calls.py`로 재현할 수 있습니다. 스크립트는 문서의 실제 단편을 읽어 실행하고 현재 폴더에 `topic-call-results.json`을 만듭니다. 해당 기록과 검증된 스크립트 해시는 `manual-next/content/topic-call-verification.json`에 있습니다.

선언·설명 대조, 코드 실행, 브라우저 검증은 각각 다른 증거입니다. 실측·실장비·GPU·생산 정확도·전체 경계 입력의 인수는 포함하지 않습니다. 상세 범위는 매뉴얼의 API 범위와 검증 페이지를 확인하세요.

## 시각 자료와 실제 사진 측정

[시각 해설](https://4xl-summer.github.io/ZT-Lab-Vision-Docs/manual-next/labs/visual-guide.html)은 실제 AntV Infographic 0.2.20으로 렌더한 SVG 24개와 draw.io 32.6.10으로 내보낸 구조도 14개입니다. 편집용 `.drawio`와 AntV 구문을 함께 보관하며, 관련 본문 57곳과 각 그림의 독립 해설 페이지에서 읽을 수 있습니다. 정적 SVG는 외부 글꼴 서버 없이 표시됩니다.

[측정 화면](https://4xl-summer.github.io/ZT-Lab-Vision-Docs/manual-next/labs/measurement.html)은 공개 사진 4종으로 SDK를 실행한 7개 사례를 읽습니다. 입력·처리 이미지·검출 표시·픽셀·확대·수치·프로파일 그래프와 실제 파라미터를 확인합니다. 브라우저는 저장된 SDK 실행 결과를 보여주며 네이티브 SDK를 실행하지 않습니다. 원/프로파일은 각각 잔차 재계산과 표본 비교의 검증 범위를 명시합니다. 표시 영역과 실제 처리 범위는 별도로 표시합니다.

사진 원본·출처와 사용 조건은 `assets/measurement/sources.json`, 계산값은 `measurements.json`, 도식 정보는 `assets/visuals/manifest.json`, 실행 및 산출물 해시는 `content/visual-verification.json`에 있습니다. 기준 치수 없는 사진은 px·px²로 해석하며 실제 생산 정확도를 주장하지 않습니다.

재현은 SDK Python 래퍼와 네이티브 라이브러리가 준비된 Python 3.14 / Linux 환경에서 다음 순서로 실행합니다. `ZVISION_NATIVE_LIBRARY`와 `PYTHONPATH`는 자신의 SDK 설치 위치를 사용합니다.

```sh
python -m pip install -r manual-next/examples/requirements-measurements.txt
python manual-next/examples/generate-measurements.py --output manual-next/assets/measurement
npm ci --prefix manual-next/tools/visuals
node manual-next/scripts/render_infographics.cjs
drawio -x -f svg --embed-diagram -b 24 -o manual-next/assets/visuals/drawio manual-next/assets/visuals/drawio/*.drawio
python manual-next/scripts/normalize_drawio.py
```

다시 생성한 그림과 측정 결과는 화면·수치 검증 후 실행 기록과 해시를 갱신합니다. `check_visuals.py`는 기록과 달라진 자산을 거부합니다. 전체 모니터나 사용자의 다른 창을 촬영한 이미지 대신 agent-desktop으로 전용 측정 창만 캡처합니다.
