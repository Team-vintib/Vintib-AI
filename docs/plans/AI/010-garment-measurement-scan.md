# 카메라 가이드라인 기반 의류 실측(cm) 측정 기능

에픽 `S15P11A108-210`. 구체적 이슈 번호는 미정 — 사용자가 JIRA에서 발급 후 전달 예정.

## 배경/목표

현재 핏(fit) 표현은 CatVTON의 `adjust_mask_for_fit`(`worker/models/catvton/model/cloth_masker.py`,
`fit_type: regular/oversized/cropped` 3단계 고정 마스크 팽창/축소)이 전부다. 사이즈 라벨(S/M/L)
차이 몇 단계라는 근사치라 "소매가 정확히 몇 cm 남는지" 같은 정밀한 수치는 알 수 없다. 이 기능은
판매자가 상품 등록 시 찍는 옷 사진(기준 물체 + 평평하게 편 옷, bird's-eye 촬영)에서 실측값(cm)을
자동 추출하는 것을 목표로 한다.

**바로잡은 참조 2가지**: 사용자 초안이 인용한 "기존 로드맵 Phase 3"과 `determine_fit_category`는
실제로는 폐기된 FLUX.2-klein PoC(`AI/validation/AI_tryon/FLUX/verify_cloth_aware_v2.py`)에만
존재한다 — CatVTON 채택 이후 안 쓰는 코드다. 이 기능의 cm 출력값을 실제 핏 연산에 연결하는 건
범위 밖(신체/의류 치수 데이터 출처 확정 후 별도 착수). `AI/test/AI_tryon/catvton/...` 경로도
존재하지 않는다 — 실제 위치는 `worker/models/catvton/`.

**기준 물체는 A4 용지로 결정**(신용카드 아님) — 판매자가 실물 카드를 촬영해 서버로 올리면
번호·명의 등 개인정보 노출 위험이 있어 제외했다. ISO 216, 210x297mm, 비율 1:sqrt(2).

## 작업 내용

`quality_check` 도메인(게이트웨이는 얇게 요청 검증 후 큐 적재만, 실제 처리는 워커)을 그대로
본떠서 만든다. 카드(A4) 검출/원단 분할/랜드마크 검출 3단계가 독립적으로 스왑 가능해야 해서
레지스트리·환경변수가 하나가 아니라 3개다. 전체 파이프라인이 목표지만 한 번에 다 만들지 않고
단계별로 커밋한다.

- **게이트웨이**: `AI/app/measurement/{router,schemas}.py`. `POST /measurement/scans`가
  검증 후 `enqueue_job("garment_measurement", ...)`, `{"job_id","product_id"}`만 반환. 결과는
  기존 `GET /ai/jobs/{job_id}` 재사용.
- **워커**: `worker/garment_measurement_worker_example.py`(오케스트레이션) +
  `worker/models/garment_measurement/`(실제 로직, `contracts.py`/`registry.py`/
  `reference_detector.py`/`segmenter.py`/`landmark_detector.py`/`cm_converter.py`/
  `scenarios.py`/`data/mock_scans.json`).
  **이 폴더는 `clipseg/`와 달리 진짜 서브패키지(`__init__.py` 보유)다** — `clipseg/`처럼
  `contracts.py`/`registry.py`/`scenarios.py`/`segmenter.py`를 flat하게 두면, 같은 pytest
  세션에서 두 폴더가 동시에 sys.path에 들어갈 때 같은 이름의 모듈이 충돌한다(먼저 import된
  쪽이 전역 캐시에 남아 다른 도메인 테스트가 엉뚱한 모듈을 받는 실제 버그를 구현 중 발견).
  그래서 `worker/models`(부모)를 sys.path에 넣고 `from garment_measurement.xxx import ...`
  형태로만 접근한다 — CatVTON이 `model.` 네임스페이스로 같은 문제를 피한 것과 같은 원리.
- **fail-fast 순서**: 기준 물체 검출 실패 → 즉시 반환(원단 분할·랜드마크 단계 건너뜀). 원단
  분할 실패 → 즉시 반환. 이 순서 자체가 "무거운 모델은 스냅샷당 1번만" 목표를 달성한다.
- **cm 환산**(`cm_converter.py`)은 순수 기하 연산이라 무거운 의존성이 없다 — mock/실백엔드
  구분 없이 항상 실제 구현을 그대로 쓴다(레지스트리 스왑 지점 없음).

## 구현 목록

- [x] `AI/app/gateway/schemas.py`의 `FeatureType`에 `"garment_measurement"` 추가
- [x] `AI/app/measurement/{__init__,router,schemas}.py` 신설, `AI/app/main.py`에 라우터 등록
- [x] `worker/models/garment_measurement/` 신설(서브패키지: contracts/registry/scenarios/
      reference_detector/segmenter/landmark_detector/cm_converter, `data/mock_scans.json`)
- [x] `worker/garment_measurement_worker_example.py` 신설(3단계 mock 백엔드로 전체 배관 검증)
- [x] `AI/test/conftest.py`에 `worker/models`를 sys.path에 추가
- [x] `AI/test/measurement/{test_measurement_schemas,test_measurement_router,test_measurement_contract}.py`
- [x] `AI/test/worker/garment_measurement/test_cm_converter.py`(순수 로직, 실제 구현 테스트)
- [x] 검증: `cd AI && ruff check . && black --check . && pytest -q` — 전부 통과(chat-ai conda
      환경, catvton 환경은 ruff만 있고 black 없어서 chat-ai로 통일)
- [x] 워커 오케스트레이션 스모크 테스트(mock 3종 + 재촬영 시나리오 2종) 직접 실행 확인
- [ ] `.claude/requests/be/004-garment-measurement-scan.md`
- [ ] `.claude/requests/fe/002-camera-guide-overlay.md`
- [ ] Phase 2: `reference_detector.py`에 `opencv_contour` 백엔드(OpenCV 컨투어 + A4 종횡비
      `registry.A4_ASPECT_RATIO`). `worker/requirements.txt`에 `opencv-python-headless` 추가
- [ ] Phase 3: `segmenter.py`에 `grabcut` 백엔드. 실측 부족 확인되면
      `AI/validation/garment-measurement-check/`에 YOLO-seg 비교 스파이크
- [ ] Phase 4: `AI/validation/garment-landmark-check/verify_hrnet_landmarks.py` — HRNet
      사전학습(`svip-lab/HRNet-for-Fashion-Landmark-Estimation.PyTorch`) PoC. RTX 4050 6GB
      추론 속도/VRAM 실측, 빈티지 의류 파인튜닝 필요 여부 판단. 통과해야만
      `landmark_detector.py`에 `hrnet_deepfashion2` 백엔드 실구현
- [ ] Phase 6: 세 백엔드를 실제 값으로 교체해 전체 파이프라인 실측 검증

## 미결정 사항

- 카드 없이 촬영했을 때 재촬영 유도 UX — 스키마 훅(`needs_retake`/`retake_reason`)만 마련,
  실제 UX는 FE/BE 몫
- 원단이 안 평평할 때(구겨짐) 오차 허용 범위 — `GARMENT_NOT_FLAT` enum 값은 자리만 있음
- HRNet 사전학습 그대로 vs 빈티지 의류 파인튜닝 필요 여부 — Phase 4 PoC 목적
- GrabCut으로 충분한지 vs YOLO-seg 파인튜닝 필요한지 — Phase 3 판단, 촬영 배경 통제 수준에 달림
- RTX 4050 6GB에서 HRNet 실제 추론 속도/정확도 — Phase 4 PoC의 또 다른 목적
- 구체적 JIRA 이슈 번호

## 관련 자료

- 구조 템플릿: `AI/app/quality/router.py`·`schemas.py`, `worker/quality_check_worker_example.py`,
  `worker/models/clipseg/registry.py`·`contracts.py`, `AI/test/quality/test_quality_contract.py`
- (연동만 참고, 이번 범위 아님) `worker/models/catvton/model/cloth_masker.py`의
  `adjust_mask_for_fit`
