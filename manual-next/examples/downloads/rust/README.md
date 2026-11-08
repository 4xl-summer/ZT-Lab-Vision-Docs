# ZVision 합성 실행 예제

SDK 소스 기준 revision: `ce902e85c3405eb63df40c699ddbdf70ee1d03bd`. 예제는 합성 데이터를 사용하며 실장비 인수, 모델 정확도 또는 생산 성능을 나타내지 않습니다. 기록된 기대값은 `records.json`을 참조하세요. 검증 영수증은 매뉴얼의 검증 기록을 확인하세요.

기준 실행 환경: WSL, Python 3.14, .NET SDK 10.0.403, Rust 1.85.1. 같은 revision의 SDK 소스 체크아웃을 준비하고 아래 명령의 `SOURCE_ROOT`를 실제 절대 경로로 바꾸세요. SDK 바이너리와 래퍼는 같은 빌드에서 사용하세요.

## Rust 실행 (WSL)

이 디렉터리에서 다음을 실행합니다. Cargo 자체는 환경 변수를 의존성 경로에서 확장하지 않으므로 `setup.py`가 로컬 `Cargo.toml`을 생성합니다. 프로그램은 `models`의 제공된 RTen 파일을 컴파일 시 읽습니다.

```sh
export SOURCE_ROOT="/absolute/path/to/sdk/source"
python3.14 setup.py
cargo run --locked --manifest-path Cargo.toml
```

각 성공 사례는 한 줄의 JSON으로 출력됩니다. `records.json`은 사례 ID별 기대값입니다. 임시 TIFF와 모델 파일을 생성한 뒤 제거합니다. SDK의 `zvision-ops`는 현재 facade에서 재수출하지 않은 옵션 열거형을 사용하기 위한 의존성입니다.
