# AI 가상 시착(TRYON) — job 계약 정식 전달

- **요청자 파트**: AI
- **대상 파트**: BE
- **관련 티켓**: `S15P11A108-210` 에픽 하위, `S15P11A108-504`

## 배경

FE가 이미 `docs/requests/BE/003-live-tryon-contract.md` 3.3(라이브 AI 시착 생성)·
3.6(상품 상세 AI 시착 생성)에서 "AI 시착 생성 API"를 요청해뒀고, 아직 미해결
상태입니다. `TryOnResultService.saveResult()` 독스트링에도 "실제 AI 호출(합성 생성)은
AI 쪽 계약이 확정되지 않아 이 서비스의 범위 밖"이라고 적혀 있어서, 이번에 그 계약을
정리해서 전달합니다.

AI 쪽 파이프라인(`S15P11A108-504`, VLM 캡션 → FLUX worn-reference → CatVTON 합성)은
이미 프로덕션 워커(`worker/tryon_worker_example.py`)로 존재하고, job 입출력 계약도
코드에 고정돼 있습니다. 아래 계약대로 BE가 (1) job을 생성하고 (2) 폴링해서 (3) 결과를
저장하면, 003 문서가 요청한 두 엔드포인트(`POST /api/lives/{liveId}/products/
{productId}/tryons`, `POST /api/products/{productId}/tryons` 또는 BE가 정한 형태)
내부에서 그대로 쓰실 수 있습니다. **이 문서는 003이 요청한 BE 엔드포인트 모양을 바꾸지
않습니다** — 그 엔드포인트가 내부적으로 호출할 AI 쪽 계약만 채워드리는 것입니다.

## 요청 내용

### 1. Job 생성 — `POST http://ai:8000/ai/tryon`

내부 Docker 네트워크 전용, **별도 인증 헤더 필요 없음**(`X-API-Key`는 워커 전용
엔드포인트에만 요구됩니다 — `AI/docs/infra-architecture.md` §3.2).

**요청 바디**:

```json
{
  "user_image_url": "https://.../person.jpg",
  "product_image_url": "https://.../cloth.jpg",
  "mask_type": "upper",
  "fit_type": "regular",
  "num_inference_steps": 50,
  "guidance_scale": 3.0,
  "body_height_cm": 170.0,
  "body_weight_kg": 65.0,
  "garment_measurements": { "WAIST_WIDTH": 42.0 }
}
```

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `user_image_url` | string | Y | 시착할 회원 전신 사진 URL(라이브면 시청자 본인 사진, 상품 상세면 회원 시착 프로필 사진 — 둘 다 `GET /api/users/{userId}/tryon`으로 이미 조회 가능) |
| `product_image_url` | string | Y | 상품 사진 URL |
| `mask_type` | `"upper"` \| `"lower"` | N (기본 `upper`) | **지금 워커는 이 두 값만 지원합니다.** `AI/app/tryon/schemas.py`의 `MaskType` enum엔 `overall`/`inner`/`outer`도 있지만 아직 워커에 안 붙어 있어서 보내면 에러가 납니다. 상품 카테고리(상의/하의)로 BE가 정해 보내주세요 — 자동 판별은 `docs/requests/BE/035-tryon-product-category.md`가 별도로 다룹니다 |
| `fit_type` | `"regular"` \| `"oversized"` | N (기본 `regular`) | `cropped`는 없습니다(가드레일 정책상 제외) |
| `num_inference_steps` | int | N (기본 50) | CatVTON 디퓨전 스텝 수 |
| `guidance_scale` | float | N (기본 3.0) | CatVTON guidance |
| `body_height_cm` | float | N | `member_body_profile.height_cm`(확정 컬럼) |
| `body_weight_kg` | float | N | `member_body_profile.weight_kg`(확정 컬럼) |
| `garment_measurements` | `{"WAIST_WIDTH": number}` | N | 상품 실측 사이즈표 중 허리 폭. 없으면 핏 계산 없이 `"regular fit"`으로 처리됩니다(`docs/requests/BE/031-garment-measurement-scan.md`가 이 실측값 자체를 다룹니다) |

없는 값은 그냥 필드를 빼고 보내시면 됩니다 — 전부 선택값 폴백이 있습니다(키/몸무게도
없으면 신체 치수 추정 자체를 생략하고 `"regular fit"`으로 진행).

**응답 (200)**: `{"job_id": "..."}` — 접수증입니다. 워커가 꺼져 있어도 200으로
접수됩니다(대기 상태로 남아 있다가 TTL 1시간에 만료 — `GET /ai/workers/status`로
가용 여부를 미리 확인할 수 있습니다).

### 2. 상태/결과 폴링 — `GET http://ai:8000/ai/jobs/{job_id}`

인증 불필요. 다른 모든 AI job(품질검수·실측 등)과 완전히 같은 형식입니다.

**응답 (200)**:

```json
{
  "job_id": "...",
  "status": "success",
  "result": {
    "image_url": "https://.../tryon-results/xxx.png",
    "mask_preview_url": "https://.../tryon-masks/xxx.png",
    "worn_reference_url": "https://.../tryon-worn-references/xxx.png",
    "fit_type": "regular",
    "adaptive_masking_used": true,
    "fit_title": "선택하신 사이즈가 살짝 타이트해요.",
    "fit_description": "허리 부분이 살짝 붙는 느낌으로 예상돼요 (기준보다 약 12% 작아요)."
  },
  "error": null,
  "worker_id": "...",
  "finished_at": "2026-08-06T03:00:00+00:00"
}
```

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `status` | `"queued"` \| `"processing"` \| `"success"` \| `"failed"` | 완료 전엔 `result`가 `null`입니다 |
| `result.image_url` | string | 최종 합성 이미지. `TryOnResultResponse.imageUrl`에 매핑하시면 됩니다 |
| `result.mask_preview_url` | string | 디버깅용 마스크 시각화. FE 노출 불필요 |
| `result.worn_reference_url` | string | 디버깅용 중간 산출물. FE 노출 불필요 |
| `result.fit_type` | string | 요청한 `fit_type`을 그대로 에코 |
| `result.adaptive_masking_used` | boolean | 실측 기반 핏 계산이 실제로 적용됐는지(요청에 `body_*`/`garment_measurements`가 부족하면 `false`) |
| `result.fit_title` \| `result.fit_description` | string \| null | "한 줄 핏 예상" 문구. **둘 다 null일 수 있습니다**(`adaptive_masking_used=false`인 경우) — `docs/requests/BE/038-tryon-fit-summary-fields.md`에서 이미 요청한 필드와 동일합니다, 같이 반영해 주세요 |

`status="failed"`면 `error`에 실패 사유 문자열이 담깁니다. 실제 소요 시간은 참고용으로
VLM 캡션 + FLUX 생성 + CatVTON 합성이 순차로 도는 구조라 대략 1~2분대입니다(워커 성능에
따라 편차 있음).

### 3. 폴링 주도권 — BE 판단

큐가 없어질 때까지 BE가 주기적으로 `GET /ai/jobs/{job_id}`를 호출하는 방식이든, FE가
직접 BE 엔드포인트를 폴링하고 BE가 그때마다 AI를 재조회하는 방식이든 AI 쪽엔 차이가
없습니다 — 003 문서 "6. 협의 필요 사항"에 남아있는 polling vs STOMP push 결정은 BE·FE
간에 정하시면 됩니다.

## 참고

- job 계약 원본(소스 오브 트루스): `worker/tryon_worker_example.py`의
  `TryonWorker.run_inference()` 독스트링 + 반환값
- 스키마 정의(참고용, 검증 로직은 아직 없음): `AI/app/tryon/schemas.py`
- 게이트웨이 공통 규약: `AI/docs/infra-architecture.md` §3.2, §5
- 이미 해결된 FE 쪽 요청: `docs/requests/BE/003-live-tryon-contract.md`(3.3, 3.6이 이
  문서로 채워질 대상), `008-user-tryon-image-contract.md`(회원 전신 사진 조회, 구현
  완료)
- 겹치는 별개 요청: `035-tryon-product-category.md`(`mask_type` 자동 판별),
  `031-garment-measurement-scan.md`(`garment_measurements` 실측값 자체),
  `038-tryon-fit-summary-fields.md`(`fit_title`/`fit_description` 필드, 이미 요청됨 —
  이 문서가 그 필드의 출처인 job 계약 전체를 보여드리는 것뿐입니다)
