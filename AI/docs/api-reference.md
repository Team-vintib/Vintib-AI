# AI 게이트웨이 API 레퍼런스

S15P11A108-371(EC2 인프라 배관 E2E 검증)에서 실제로 curl로 검증한 내용 기준. BE가
`AiClient.java`를 구현할 때 참고한다.

루트 `APIs.md`와는 다른 계약이다. `APIs.md`는 **FE↔BE 공개 API**(예:
`POST /users/{id}/tryons`)이고, 이 문서는 **BE↔AI 내부 API**다. FE는 이 API를 직접 호출하지
않는다 — BE가 자신의 공개 엔드포인트를 처리하면서 내부적으로 이 API를 호출하는 구조다.

```
FE → BE  POST /users/{id}/tryons        (APIs.md, BE가 구현)
       ↓ BE가 내부적으로
BE → AI  POST /ai/tryon                 (이 문서)
       ↓ AI가 큐에 적재, 워커가 폴링해 추론
BE ← AI  GET /ai/jobs/{job_id} 폴링
FE ← BE  GET /users/{id}/tryons/{id}    (APIs.md, BE가 구현)
```

구조 배경은 `infra-architecture.md`(게이트웨이·워커·Redis 큐 전체 그림)를 먼저 읽으면 이해가
빠르다.

## 왜 폴링 방식인가

시착·품질검수 같은 작업은 GPU 추론이 필요해서 수 초~수십 초가 걸린다. 요청을 동기로
막아두면 안 되므로, 접수만 즉시 응답하고(`job_id` 반환) 별도로 상태를 조회하는 방식이다.
BE는 `job_id`를 받으면 그걸로 `GET /ai/jobs/{job_id}`를 반복 호출(폴링)해서 `status`가
`success`/`failed`로 바뀔 때까지 기다린다.

## 엔드포인트

| 이름 | Method | Endpoint | 인증 | 호출 주체 |
|---|---|---|---|---|
| 헬스체크 | GET | `/ai/health` | 없음 | 누구나 |
| job 접수 | POST | `/ai/{feature}` | 없음 | BE |
| job 상태 조회 | GET | `/ai/jobs/{job_id}` | 없음 | BE |
| 워커 poll | GET | `/ai/workers/poll?feature={feature}` | `X-API-Key` | 워커(로컬 노트북) |
| 워커 결과 제출 | POST | `/ai/workers/result` | `X-API-Key` | 워커 |
| 워커 이미지 업로드 | POST | `/ai/workers/upload-image?prefix={prefix}` | `X-API-Key` | 워커 |
| 워커 JSON 업로드 | POST | `/ai/workers/upload-json?prefix={prefix}&name={name}` | `X-API-Key` | 워커 |
| 결과 파일 서빙 | GET | `/results/{prefix}/{filename}` | **없음(공개)** | 누구나 — 접근 제어 검토 중, [`results-access-control.md`](./results-access-control.md) 참고 |

`X-API-Key`는 `WORKER_API_KEY` 환경변수 값과 정확히 일치해야 한다(EC2 `.env`와 워커 로컬
환경변수 양쪽에 동일하게 설정). 워커 전용 엔드포인트는 BE가 호출할 일이 없다.

## job 접수: `POST /ai/{feature}`

`feature`는 `tryon` / `quality_check` / `chat_rag` / `recommend_offline` 중 하나
(`app/gateway/schemas.py`의 `FeatureType`). **`tryon`만 워커까지 실제로 연결되어 있고,
나머지 셋은 타입만 정의되어 있을 뿐 아직 처리하는 워커가 없다** — 지금 이 셋으로 job을
넣으면 큐에는 쌓이지만 아무도 꺼내가지 않는다.

body는 feature별로 자유 형식 dict다(게이트웨이 레벨에서는 검증하지 않는다 — 워커가
필요한 키를 직접 읽는다).

### `tryon` payload (실제 구현, `worker/tryon_worker_example.py` 기준)

```json
{
  "user_image_url": "https://.../person.jpg",
  "product_image_url": "https://.../cloth.jpg",
  "fit_type": "regular"
}
```

| 필드 | 필수 | 설명 |
|---|---|---|
| `user_image_url` | 필수 | 인증 없이 HTTP(S) GET으로 받아올 수 있는 URL이어야 한다. 로컬 경로는 안 된다(`storage_utils.download_image`는 HTTP(S)만 지원). |
| `product_image_url` | 필수 | 위와 동일 |
| `fit_type` | 선택(기본 `regular`) | `regular` \| `oversized` \| `cropped` |

- 응답(성공 시 `GET /ai/jobs/{job_id}`의 `result`):
  ```json
  {
    "image_url": "https://i15a108.p.ssafy.io/results/tryon-results/xxx.png",
    "mask_preview_url": "https://i15a108.p.ssafy.io/results/tryon-masks/xxx.png",
    "fit_type": "regular"
  }
  ```
- `app/tryon/schemas.py`에 `MaskType`·`num_inference_steps`(10~50, 기본 30)·
  `guidance_scale`(1.0~10.0, 기본 2.5) 같은 더 상세한 파라미터 계약이 정의되어 있지만,
  **현재 워커 구현은 이 값들을 payload에서 읽지 않는다** — `num_inference_steps=20`,
  `guidance_scale=2.5`가 코드에 고정되어 있다. 비동기 전환/고도화 시 이 스키마가 실제로
  쓰일 예정이다(`AI/docs/tryon-advancement-strategy.md` 참고).

### `quality_check` / `chat_rag` / `recommend_offline`

아직 워커가 없다(`worker/quality_check_worker_example.py`의 `run_inference()`는
`NotImplementedError` 스텁). payload 계약은 미정.

## job 상태 조회: `GET /ai/jobs/{job_id}`

```json
{
  "job_id": "0e83aede-253b-4081-8054-a67f605e7884",
  "status": "queued",
  "result": null,
  "error": null,
  "worker_id": null,
  "finished_at": null
}
```

`status`는 `queued` → `processing` → `success`/`failed` 순으로 바뀐다. job은 Redis에
**TTL 1시간**으로만 보관되므로, 그 안에 폴링을 끝내야 한다. 만료된 job을 조회하면
`404 {"detail": "job not found or expired"}`.

`failed`가 3회 재시도(`MAX_RETRY=3`)를 넘기면 dead-letter 큐로 이동하고 최종
`status: "failed"`로 고정된다.

## 참고 — 자체 API 문서(Swagger)는 지금 외부에 안 열려 있음

FastAPI가 자동 생성하는 `/docs`(Swagger UI)·`/openapi.json`은 항상 앱 최상위 경로에
생기는데, Caddy는 `/ai/*`·`/results/*`만 AI 컨테이너로 보내고 나머지는 backend로 보낸다.
그래서 외부에서 `/ai/docs`로 접속하면 실제로는 `/ai/{feature}` 라우트가 `feature="docs"`로
매칭되어 `405 Method Not Allowed`가 뜬다 — Swagger가 아니다. 지금 규모(엔드포인트 7개)에서는
이 문서가 그 역할을 대신하고, 필요성이 커지면 그때 Caddy 라우팅 추가를 검토한다.
