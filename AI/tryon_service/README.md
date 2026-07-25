# 가상 시착 서비스 (TRYON-003)

`S15P11A108-181`(비동기 처리 아키텍처), `S15P11A108-182`(이미지 생성 범위 정책),
`S15P11A108-189`(FastAPI 모듈 구조 스캐폴딩)에서 정해진 설계를 바탕으로 작성한
가상 시착 추론 API + Celery 워커 구현.

## 구조

```
tryon_service/
├── main.py                    # FastAPI 앱 엔트리포인트
├── api/routes/tryon.py        # POST /tryon, GET /tryon/{request_id}
├── schemas/tryon.py            # 요청/응답 Pydantic 모델
├── services/
│   ├── tryon_service.py        # 업로드 검증/저장 + 큐 적재
│   └── status_store.py         # Redis 기반 요청 상태 저장소
├── worker/
│   ├── celery_app.py           # Celery 앱 설정 (Redis 브로커/백엔드)
│   └── tasks.py                 # 실제 CatVTON 추론 실행 태스크
└── ml/catvton/                 # (이관 필요) 모델 코드 — 아래 "선행 작업" 참고
```

## ⚠️ 선행 작업 필요 — 모델 코드 이관

이 구현은 `AI/test/AI_tryon/catvton/`에서 검증 완료된 CatVTON 파이프라인
코드를 전제로 작성됨. 실행 전 아래를 먼저 진행해야 함:

1. `AI/test/AI_tryon/catvton/model/pipeline.py`,
   `AI/test/AI_tryon/catvton/model/cloth_masker.py`,
   `AI/test/AI_tryon/catvton/utils.py` 등을 `tryon_service/ml/catvton/`로 복사
2. `app/worker/tasks.py`의 import 경로(`app.ml.catvton.*`)가 실제 이관된
   위치와 일치하는지 확인
3. 스파이크 코드에 있던 검증/실험용 분기(`fit_type` 실험 코드 등)를 정리하고,
   프로덕션에 필요한 부분만 남기는 리팩터링 권장

> **참고**: JIRA 티켓 설명에는 이관 대상이 `AI/test/model_selection`으로
> 적혀 있으나, 실제 가상 시착 스파이크 코드는 `AI/test/AI_tryon/catvton`에
> 있음. 티켓 설명 오기로 추정되어 후자를 기준으로 작성함 — 확인 필요.

## 미구현/TODO

- [ ] 웹훅 방식 결과 알림 (현재 폴링 방식만 구현)
- [ ] `estimated_wait_seconds` 산정 로직 정교화 (현재 고정값)
- [ ] S3 등 오브젝트 스토리지 연동 (현재 로컬 디스크 저장)
- [ ] dead-letter 큐 모니터링/알림 연동
- [ ] 모델 코드 실제 이관 (위 선행 작업 항목)
- [ ] 통합 테스트 작성

## 실행 방법 (모델 이관 완료 후)

```bash
# FastAPI 서버
uvicorn app.main:app --reload --port 8000

# Celery 워커 (별도 터미널, GPU 1개당 워커 1개 권장)
celery -A app.worker.celery_app worker --loglevel=info --queues=tryon

# Redis (로컬 개발용)
docker run -d -p 6379:6379 redis:7-alpine --appendonly yes
```

## API 사용 예

```bash
# 요청 접수
curl -X POST http://localhost:8000/tryon \
  -F "person_image=@person.jpg" \
  -F "cloth_image=@cloth.jpg" \
  -F "fit_type=oversized"

# 응답: {"request_id": "...", "status": "pending", ...}

# 결과 폴링
curl http://localhost:8000/tryon/{request_id}
```
