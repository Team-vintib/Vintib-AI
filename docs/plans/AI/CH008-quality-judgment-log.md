# 품질 검수 — 판단 근거 로컬 로그 저장 — 설계

## 배경 / 목표

지금 품질 검수 판단 근거(score/confidence/threshold/findings/히트맵 URL)는 어디에도 durable
하게 안 남는다 — job result는 Redis `result:{job_id}`에 TTL 3600초만 있다가 사라지고, BE는
finding의 `key`/`statement_required`만 저장하도록 문서화돼 있다(`.claude/requests/be/
001-quality-inspection-async.md`). 히트맵 PNG 파일 자체는 게이트웨이 디스크에 남지만(정리
스크립트가 아직 없어서 우연히 그런 것 — `AI/docs/infra-architecture.md`가 이미 문제로
지적함), 그 파일이 **어떤 판정에서 나왔는지 이어주는 기록**이 없다.

워커가 검수 1건을 처리할 때마다 **결과 전체를 로컬 JSON Lines 파일로 남겨서**, 나중에 팀이
"왜 이렇게 판정했는지"를 재구성할 수 있게 한다.

## 작업 내용

1. **`worker/inspection_logger.py`(신규, 공용 유틸)** — `log_inspection_result(payload, output,
   log_dir=...)` 함수 하나. 순수 로직(파일 append)이라 clipseg/sam3 양쪽 워커가 그대로 재사용.
   - 로그 파일: `{QUALITY_LOG_DIR 환경변수, 기본 "./logs/quality"}/{YYYY-MM-DD}.jsonl`
     (UTC 날짜 — 파일 하나가 무한정 커지지 않게 일별로 나눔).
   - 한 줄 = `{"logged_at": <ISO8601>, "product_id", "image_urls", "category", "base_color"}`
     (요청 컨텍스트) **+ `InspectionResult` 전체 dict**(`run_inference()`가 이미 만드는 그
     dict를 그대로 씀 — 추가 계산 없음).
   - 로깅 실패(디스크 문제 등)는 **검수 응답 자체를 막지 않는다** — try/except로 감싸고
     실패 시 stderr 경고만 출력(로깅은 best-effort, 서비스 가용성이 우선).
2. **`worker/quality_check_worker_example.py`의 `run_inference()` 끝에서 호출** — family
   분기(clipseg/sam3) 아래가 아니라 공통 리턴 직전이라, **한 번만 추가하면 두 백엔드 모두
   자동으로 적용**된다(CH007의 "SAM3만 우선"과 달리 이건 오케스트레이션 레벨이라 범위 제한이
   의미 없음).
3. **`worker/.gitignore`에 `logs/` 추가** — 로컬 산출물, 커밋 대상 아님. 상품 이미지 URL 정도만
   담겨 개인정보 우려는 낮지만 그래도 커밋하지 않는다.
4. **테스트** — `log_inspection_result()`는 순수 로직(dict → JSON 한 줄 append)이라 torch 등
   무거운 의존성이 없다. `AI/test/worker/`에 `test_inspection_logger.py` 추가(임시 디렉터리에
   써서 파일 내용 검증, `AI/test/conftest.py`가 이미 `worker/` 를 sys.path에 넣어 둠).

## 확인이 필요한 미결정 사항

1. **로그 보존 기간/회전 정책** — 이번엔 일별 파일 분리까지만 하고, 오래된 파일 삭제·압축 같은
   보존 정책은 범위 밖으로 둔다(디스크 무한 증가 문제는 인지하되 후속 작업).
2. **중앙 집계 안 함** — 워커가 여러 팀원 노트북에서 개별 실행되면 로그도 각자 로컬에 흩어진다.
   ELK/CloudWatch 같은 중앙 로그 수집은 이 계획 범위 밖(인프라 논의 필요 시 별도 계획).
3. **attention_map 이미지 바이너리는 로그에 안 넣음** — URL만 남긴다(파일은 이미 게이트웨이
   디스크에 있어 중복 저장 방지).

## 구현 목록

- [ ] `worker/inspection_logger.py` 신규 — `log_inspection_result()`
- [ ] `quality_check_worker_example.py`: `run_inference()` 끝에서 호출 배선
- [ ] `worker/.gitignore`: `logs/` 추가
- [ ] `AI/test/worker/test_inspection_logger.py` 신규
- [ ] `ruff`/`black`/`pytest` 로컬 통과 확인 후 커밋 (push는 사용자)
