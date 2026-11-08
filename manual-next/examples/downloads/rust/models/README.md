# 결정론적 합성 모델

이 네 그래프는 매뉴얼 예제를 위해 처음 작성한 결정론적 ONNX 그래프와 그 RTen 변환 결과입니다. 학습된 모델이나 정확도·성능의 증거가 아닙니다. 각 그래프 입력은 F32 NCHW `[1,1,8,8]`이며 픽셀은 0–1입니다.

| 파일 | 출력 shape | 의미 |
|---|---|---|
| demo-classification | `[1,2]` | 전체 평균 m과 1−m으로 만든 logits `[1−m,m]` |
| demo-detection | `[1,1,6]` | `[1,1,6,6,0.9,0]` 고정 검출 행: x0,y0,x1,y1,score,class |
| demo-segmentation | `[1,2,8,8]` | 채널별 `[1−pixel,pixel]` |
| demo-anomaly | `[1,1,8,8]` | 입력을 그대로 반환하는 맵 |

`.onnx`와 `.rten`은 각각 같은 이름의 그래프 원본과 변환 결과입니다. `build_demo_models.py`는 ONNX를 다시 만드는 소스입니다. 실행 시 스크립트가 있는 위치 아래 `models/`에 ONNX를 만듭니다. 재생성에는 ONNX Python 패키지와 호환되는 RTen 변환기가 필요합니다. SDK의 개인 테스트 fixture는 이 묶음에 포함하지 않습니다.
