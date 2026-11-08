# ZVision 합성 실행 예제

SDK 소스 기준 revision: `ce902e85c3405eb63df40c699ddbdf70ee1d03bd`. 예제는 합성 데이터를 사용하며 실장비 인수, 모델 정확도 또는 생산 성능을 나타내지 않습니다. 기록된 기대값은 `records.json`을 참조하세요. 검증 영수증은 매뉴얼의 검증 기록을 확인하세요.

기준 실행 환경: WSL, Python 3.14, .NET SDK 10.0.403, Rust 1.85.1. 같은 revision의 SDK 소스 체크아웃을 준비하고 아래 명령의 `SOURCE_ROOT`를 실제 절대 경로로 바꾸세요. SDK 바이너리와 래퍼는 같은 빌드에서 사용하세요.

## 네이티브 라이브러리 (WSL)

해당 SDK 소스에서 생성한 네이티브 공유 라이브러리가 필요합니다. 예를 들어 다음은 같은 체크아웃에서 release 라이브러리를 빌드합니다.

```sh
export SOURCE_ROOT="/absolute/path/to/sdk/source"
cd "$SOURCE_ROOT"
cargo build -p zvision-ffi --release --locked
export ZVISION_NATIVE_LIBRARY="$SOURCE_ROOT/target/release/libzvision_ffi.so"
```

별도 target이나 출력 디렉터리를 지정했다면 실제 파일의 절대 경로로 바꾸세요. `ZVISION_NATIVE_LIBRARY`는 절대 파일 경로여야 합니다. 이제 압축을 푼 예제의 언어별 디렉터리로 이동합니다. 네이티브 로딩에 실패하면 경로와 아키텍처, 종속 라이브러리를 확인하세요.

## C# 실행 (WSL)

예제의 `csharp` 디렉터리에서 실행합니다. 프로젝트는 `SOURCE_ROOT`의 SDK C# 프로젝트를 참조합니다.

```sh
export ZVISION_MANUAL_MODELS="$(cd ../models && pwd)"
dotnet run --project ManagedExamples.csproj -p:SOURCE_ROOT="$SOURCE_ROOT"
```

정상 실행 시 검증된 값으로 구성한 JSON 객체가 출력됩니다. 모델 환경 변수를 설정하지 않으면 AI 사례가 생략되므로 전체 실행에는 위 설정이 필요합니다.
