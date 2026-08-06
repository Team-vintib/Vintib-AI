# 품질 검수 — BE 연동 통합 가이드 (037/038 대체)

- **요청자 파트**: AI
- **대상 파트**: BE
- **관련 티켓**: `S15P11A108-501`(검수 결과 시각화 개선), `-508`(에픽 `-211`)
- **상태**: 요청 (AI 쪽 계약 확정, BE 연동 아직 시작 전으로 확인됨)

## 배경/이유

기존 `037-quality-inspection-async.md`/`038-quality-inspection-per-image-scores.md` 두 문서로
나눠 요청했던 내용을 하나로 합치고, 그 사이 추가된 변경(요약 형식)까지 반영해 **현재 기준
전체 계약**을 정리합니다. BE 쪽 코드를 확인해보니 `quality/inspections`/`ai/jobs` 관련
연동이 아직 없어서(코드 검색 결과) — 처음 시작하실 때 조각난 문서 여러 개보다 이거 하나만
보시면 되게 정리했습니다. 두 문서는 이 문서에 완전히 흡수되어 삭제했습니다.

## 요청 내용

### 0. 언제 호출하는지 — 앞/뒤 사진 업로드 완료 즉시 (신규 명시)

카테고리 선택이나 다른 스텝을 기다리지 않고, **앞/뒤 사진이 둘 다 올라온 시점에 바로**
`POST /quality/inspections`를 호출해 주세요. `AI/README.md`가 그린 원래 그림대로 분류
브랜치와 **병렬로** 먼저 돌려두는 것입니다 — 사용자가 이후 스텝(카테고리 확인, 가격 등)을
진행하는 동안 무거운 검수가 백그라운드에서 끝나 있어서, 검수 결과를 보여줄 페이지에
도달했을 때 FE가 기다리는 시간이 줄어듭니다. 이 호출로 받은 `job_id`는 상품 등록 draft
응답에 실어서 FE에 넘겨주시면 됩니다(FE가 이후 스텝에서 그 `job_id`로 직접 폴링 — 1번 참고).

### 1. 동기 REST가 아니라 job 등록 → 폴링입니다 — 그리고 폴링은 FE가 직접 합니다

EC2 `ai` 컨테이너에 GPU가 없어서(`mem_limit: 1g`) 실모델 추론은 팀원 노트북이 하고, 워커가
게이트웨이를 아웃바운드로 폴링하는 구조입니다. 그래서 시착(TRYON)과 동일한 패턴입니다.

**BE는 AI 게이트웨이를 다시 조회할 필요가 없습니다.** 결과는 FE가 `GET /ai/jobs/{job_id}`를
외부 경로로 직접 폴링해서 실시간으로 이미 들고 있으므로, BE는 **FE가 그 값을 필요한 단계의
요청에 실어 보낼 때 받아서 저장**하면 됩니다. AI 쪽에는 결과를 위한 영구 저장소가 없습니다
(`app/quality/`는 Redis TTL 1시간짜리 큐 어댑터일 뿐입니다) — 하지만 BE가 AI를 다시 찌를
필요는 없고, 아래처럼 FE가 이미 손에 든 값을 그대로 넘겨받으면 됩니다.

- **상태(condition) 확정 단계**: FE가 `condition_score`/`condition_grade`를 그 단계의 확정
  요청 payload에 실어 보내주세요. 이후 가격책정(`app/pricing/`)이 이 값을 **요청 payload로**
  받는 것으로 이미 설계돼 있습니다(`AI/app/pricing/schemas.py` 주석: "상품 등록 흐름에서 BE가
  검수 결과를 들고 있으므로 그대로 실어 보낸다") — BE가 그 값을 갖고 있으려면 FE가 넘겨주는
  경로가 있어야 합니다.
- **최종 제출 단계**: FE가 findings의 `key`별 판매자 응답(어느 게 "아니다"로 처리됐는지 등,
  2번 하단)을 실어 보내주세요.

이러면 BE가 별도 폴링 인프라를 둘 필요가 없고, TTL(1시간) 만료 리스크도 자연히 없어집니다 —
FE가 애초에 실시간으로 받아둔 값을 넘기는 것뿐이라 AI 쪽 TTL과 무관합니다.

**참고(당장 처리할 필요는 없음)**: 이 구조는 FE가 넘긴 값을 BE가 그대로 신뢰하는 구조입니다.
나중에 어뷰징(예: 클라이언트에서 `condition_score` 조작)이 문제되면, BE가 저장 시점에
`job_id`로 AI를 한 번 더 조회해 검증하는 절차를 추가할 수 있습니다.

```jsonc
// 1) 요청 — POST /quality/inspections (컨테이너 내부망: http://ai:8000/quality/inspections)
{
  "product_id": 1042,
  "image_urls": ["https://.../front.jpg", "https://.../back.jpg"],  // 순서가 곧 image_index — 아래 4번 참고
  "category": "TOP_KNIT",
  "base_color": "LIGHT",              // 기본값 LIGHT, 선택
  "include_attention_maps": false,     // 기본값 false, 선택
  "include_descriptions": false        // 기본값 false, 선택 — 아래 6번 참고
}
```

```jsonc
// 2) 응답 — 결과가 아니라 접수증
{ "job_id": "3f2a-...", "product_id": 1042 }
```

```jsonc
// 3) 결과 폴링 — GET /ai/jobs/{job_id} (시착과 동일 엔드포인트/형식)
{
  "job_id": "3f2a-...",
  "status": "queued" | "processing" | "success" | "failed",
  "result": { /* status가 success일 때만. 아래 3절 참고 */ },
  "error": "...",
  "worker_id": "..."
}
```

**워커가 꺼져 있으면 `queued`로 머물다 1시간(TTL) 뒤 사라집니다**(그 뒤 조회 시 404). 무한
폴링하지 말고 타임아웃을 두세요. `GET /ai/workers/status`로 워커 가용 여부를 미리 확인할 수
있습니다.

호출 경로 주의 — Caddy는 `/quality/*`를 AI로 안 보냅니다. `/ai/*`·`/results/*`만 `ai:8000`으로
갑니다. BE→AI 요청은 컨테이너 내부망으로, FE가 직접 폴링해야 하면 외부 경로
(`https://i15a108.p.ssafy.io/ai/jobs/{id}`)가 열려 있습니다.

### 2. `result` 스키마 (현재 기준 전체)

```jsonc
{
  "inspection_id": "insp_1042_7f3c",
  "product_id": 1042,
  "condition_score": 78.0,
  "condition_grade": "A",
  "summary": "[이미지 1]\n1. 오른쪽 가슴 오염 — 옅은 갈색 얼룩이 확인됩니다.\n\n[이미지 2]\n확인된 하자가 없습니다.",
  "image_summaries": [
    { "image_index": 0, "summary": "1. 오른쪽 가슴 오염 — 옅은 갈색 얼룩이 확인됩니다." },
    { "image_index": 1, "summary": "확인된 하자가 없습니다." }
  ],
  "findings": [
    {
      "key": "stain_0_5_1",
      "defect_type": "STAIN",
      "label": "오염",
      "status": "DETECTED",
      "image_index": 0,
      "section_no": 5,
      "section": "CHEST_CENTER",
      "no": 1,
      "confidence": 0.893,
      "area_ratio": 0.0113,
      "bbox": [0.42, 0.35, 0.55, 0.47],
      "severity": "MODERATE",
      "statement_required": true,
      "needs_seller_review": false,
      "description": "옅은 갈색 얼룩이 확인됩니다."
    }
  ],
  "section_scores": [
    { "image_index": 0, "section_no": 5, "section": "CHEST_CENTER", "score": 0.81 }
    // 이미지 1장당 9개, 이미지 수만큼 곱해집니다(2장이면 18개) — 이미지 간 확률을 합치지 않습니다
  ],
  "attention_maps": [{ "image_index": 0, "defect_type": "STAIN", "url": "https://.../results/..." }],
  "annotated_images": [{ "image_index": 0, "url": "https://.../results/..." }],
  "notes": ["일부 항목은 모델 신뢰도가 낮아 판매자 확인이 필요합니다."],
  "latency_ms": 42.1
}
```

**주의**: `summary`는 더 이상 "오염 2건이 확인되었습니다" 같은 한 줄 집계가 아니라 **이미지별
넘버링 리스트**(여러 줄 문자열)입니다. 이미지가 2장 이상이면 `[이미지 N]` 헤더로 나뉩니다.
한 줄로 보여줄 곳이 있다면 `image_summaries[i].summary`를 이미지별로 쓰시는 게 낫습니다.

**BE가 저장해야 하는 것**: 위 1번대로 FE가 각 단계에서 넘겨주는 값 — 상태 확정 단계의
`condition_score`/`condition_grade`, 최종 제출 단계의 `findings[].key`별 판매자 응답
(어느 `key`가 "아니다"로 처리됐는지, `statement_required`인 항목의 소명 텍스트 등). `key`를
앵커로 매칭하시면 됩니다. 판매자 소명 본문 자체는 AI가 생성하지 않고 받지도 않습니다.

`condition_score`는 가중치·등급 경계가 근거 없는 임의값이라 가격책정 등에 그대로 신뢰해 쓰시면
안 됩니다.

### 3. (참고용) FE가 실제로 매핑하는 형태 — BE가 이 매핑 자체를 만들 필요는 없습니다

아래 매핑은 FE가 자기 UI 필드로 변환할 때 직접 수행합니다(자세한 내용은
`docs/requests/FE/036-quality-finding-bbox-rendering.md` 참고). BE는 위 1·2번대로 FE가
넘겨주는 `key`/`condition_score`/`condition_grade` 등만 저장하면 되고, 이 표처럼 FE 전용
필드 형태로 가공할 필요는 없습니다 — "FE 쪽에서 최종 제출로 뭐가 넘어올지" 감을 잡는 참고
자료로만 보시면 됩니다.

| FE 필드 | AI에서 채울 값 |
| --- | --- |
| `candidates[].id` | `findings[].key` |
| `candidates[].labelNumber` | `findings[].no` |
| `candidates[].description` | `findings[].description` |
| `candidates[].box` | `findings[].bbox`(FE가 0~1 정규화 xyxy → 자기 쪽 `{x,y,width,height}` %로 변환) |
| `candidates[].isActualDefect` | AI가 주는 값 아님 — 판매자 응답, FE 로컬 상태(기본 `true`, 판매자가 "아니다" 누르면 `false`) → 최종 제출 시 BE로 전달 |
| `photoResult.photoId` | 아래 4번의 `image_index` ↔ 사진 매핑으로 FE가 결정 |
| `photoResult.status` | FE가 job 상태에서 매핑(`queued/processing`→`analyzing`, `failed`→`failed`, `success`+findings 0건→`noFindings`, `success`+findings 있음→`completed`) |

### 4. `image_index` ↔ 프론트/백 매핑 규칙 (신규 요청)

`image_urls`는 **순서가 곧 `image_index`**입니다(0부터). BE는 `POST /quality/inspections`에
`image_urls`를 보낼 때 **항상 앞면을 0번, 뒷면을 1번으로 고정된 순서**로만 보내주시면 됩니다.
그 뒤 FE가 `image_index`를 자기 `photoId`로 매핑하는 건 FE 몫입니다(FE는 애초에 자기가 앞면을
0번째로 업로드했다는 걸 알고 있으므로, 별도로 순서를 넘겨받을 필요가 없습니다). AI는
`photoId`라는 개념 자체를 모릅니다.

### 5. 참고 — CH011 sVLM 설명(`include_descriptions`)은 아직 검증 중

`findings[].description`을 생성하는 방식(하자별 개별 크롭 호출 vs 이미지 1장당 배치 호출)을
`AI/validation/QUAL/vlm-description-check/`에서 검증하고 있습니다. **`description` 필드
자체는 이미 확정**이라 지금 연동하셔도 되지만, 값이 자주 `null`일 수 있습니다(옵트인
`include_descriptions=false`가 기본값이고, 검증이 끝나기 전까지는 꺼두시는 걸 권장합니다).

## 6. 참고 — `019`(상품 상세 AI 분석 탭)와 저장 범위가 다를 수 있습니다

이 문서 §1은 "BE가 findings의 `key`별 판매자 응답만 저장하면 된다"고 돼 있는데, `docs/requests/BE/019-product-quality-multi-image.md`(상품 상세 "AI 분석" 탭)는 그 화면을 채우려면 각 finding의 원본 데이터(`box`, `description`, `defect_type` 등)도 필요합니다. FE는 최종 제출 시 findings 원본 전체(인정/제외 여부 포함)를 `POST /products` 요청의 `aiQualityFindings` 필드로 보내도록 만들어뒀습니다(BE 미수신 상태) — `key` 목록만 저장할지, 원본 전체를 저장해 019도 함께 채울지 확인 부탁드립니다.

## 관련 자료

- FE 매핑 원본: `FE/src/domains/product/pages/ProductRegistrationPage.vue`,
  `FE/src/domains/product/types/productRegistration.types.ts`
- FE용 렌더링 가이드(bbox 좌표 처리): `docs/requests/FE/036-quality-finding-bbox-rendering.md`
- 설계: `docs/plans/AI/CH020-quality-front-back-cache.md`
- 스키마 원본: `AI/app/quality/schemas.py`, `worker/models/sam3/scoring.py`(`summarize`)
- 시착(TRYON)과 같은 폴링 패턴 참고: `AI/docs/infra-architecture.md`

## 처리 결과

(BE 반영 후 기입)
