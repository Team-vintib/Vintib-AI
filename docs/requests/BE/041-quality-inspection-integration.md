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

### 1. 동기 REST가 아니라 job 등록 → 폴링입니다

EC2 `ai` 컨테이너에 GPU가 없어서(`mem_limit: 1g`) 실모델 추론은 팀원 노트북이 하고, 워커가
게이트웨이를 아웃바운드로 폴링하는 구조입니다. 그래서 시착(TRYON)과 동일한 패턴입니다.

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

**BE가 저장해야 하는 것**: `findings[].key`와 `statement_required`. 판매자 소명 본문은 AI가
받지 않습니다.

`condition_score`는 가중치·등급 경계가 근거 없는 임의값이라 가격책정 등에 그대로 신뢰해 쓰시면
안 됩니다.

### 3. FE로 전달 시 참고 — FE가 이미 만들어 둔 목업 형태와의 매핑

FE 상품등록 페이지(`ProductRegistrationPage.vue`)에 이미 목업으로 구현돼 있는 형태
(`ProductRegistrationAiPhotoResult`/`ProductRegistrationAiDefectCandidate`,
`productRegistration.types.ts`)와 맞추면 아래처럼 매핑됩니다. **`box` 좌표 변환은 FE가
직접 합니다** — BE는 `findings[].bbox`를 그대로 전달하면 됩니다(AI 원본 포맷 유지, FE가
0~1 정규화 xyxy → 자기 쪽 `{x,y,width,height}` %로 변환).

| FE 필드 | AI/BE에서 채울 값 |
| --- | --- |
| `candidates[].id` | `findings[].key` |
| `candidates[].labelNumber` | `findings[].no` |
| `candidates[].description` | `findings[].description` |
| `candidates[].box` | `findings[].bbox` 그대로(변환은 FE가) |
| `candidates[].isActualDefect` | AI가 주는 값 아님 — 판매자 응답 저장용 BE 로컬 상태(기본 `true`, 판매자가 "아니다" 누르면 `false`) |
| `photoResult.photoId` | 아래 4번의 `image_index` ↔ 사진 매핑으로 결정 |
| `photoResult.status` | job 상태에서 매핑(`queued/processing`→`analyzing`, `failed`→`failed`, `success`+findings 0건→`noFindings`, `success`+findings 있음→`completed`). `regenerating`/`confirmed`는 BE/FE 로컬 상태라 AI가 모릅니다 |

### 4. `image_index` ↔ 프론트/백 매핑 규칙 (신규 요청)

`image_urls`는 **순서가 곧 `image_index`**입니다(0부터). FE의 `photoId`(사진별 로컬 id)로
결과를 되돌려 매핑하려면, **BE가 `image_urls`를 보낼 때 항상 앞면을 0번, 뒷면을 1번으로 고정된
순서로 보내고**, 결과를 받을 때 그 순서 그대로 어느 `photoId`였는지 기억해서 매핑해 주셔야
합니다(AI는 `photoId`라는 개념 자체를 모릅니다).

### 5. 참고 — CH011 sVLM 설명(`include_descriptions`)은 아직 검증 중

`findings[].description`을 생성하는 방식(하자별 개별 크롭 호출 vs 이미지 1장당 배치 호출)을
`AI/validation/QUAL/vlm-description-check/`에서 검증하고 있습니다. **`description` 필드
자체는 이미 확정**이라 지금 연동하셔도 되지만, 값이 자주 `null`일 수 있습니다(옵트인
`include_descriptions=false`가 기본값이고, 검증이 끝나기 전까지는 꺼두시는 걸 권장합니다).

## 관련 자료

- FE 매핑 원본: `FE/src/domains/product/pages/ProductRegistrationPage.vue`,
  `FE/src/domains/product/types/productRegistration.types.ts`
- FE용 렌더링 가이드(bbox 좌표 처리): `docs/requests/FE/036-quality-finding-bbox-rendering.md`
- 설계: `docs/plans/AI/CH020-quality-front-back-cache.md`
- 스키마 원본: `AI/app/quality/schemas.py`, `worker/models/sam3/scoring.py`(`summarize`)
- 시착(TRYON)과 같은 폴링 패턴 참고: `AI/docs/infra-architecture.md`

## 처리 결과

(BE 반영 후 기입)
