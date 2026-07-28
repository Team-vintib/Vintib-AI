# 품질 검수 API 비동기 전환 — 계약 변경 요청

- **요청자 파트**: AI
- **대상 파트**: BE
- **관련 티켓**: `S15P11A108-304` [PROD-009 | AI] 품질 검수 서비스 구현 (에픽 `-211`)
- **상태**: 요청 (AI 쪽 구현 진행 중, BE 반영 시점은 협의)

## 배경

품질 검수를 동기 REST로 만들었는데 **실제 배포 환경에서 동작할 수 없다는 게 확인됐습니다.**

- EC2 `ai` 컨테이너에 **GPU가 없고 torch도 설치돼 있지 않습니다**(`mem_limit: 1g`). 실제 모델
  (CLIPSeg)을 그 안에서 돌릴 수 없습니다.
- 추론은 **팀원 노트북 GPU**가 담당합니다. 노트북은 공유기 뒤라 인바운드 접속이 불가능해,
  워커가 게이트웨이를 아웃바운드로 폴링하는 구조입니다(`AI/docs/infra-architecture.md` §2).
- **인바운드가 불가능한 자원은 동기 호출 대상이 될 수 없습니다.** 시착(CatVTON)이 이미 같은
  이유로 비동기 큐를 씁니다.

그래서 품질 검수도 시착과 동일한 **job 등록 → 폴링** 방식으로 바꿉니다.

## 요청 내용

### 1. `POST /quality/inspections` 의 응답이 바뀝니다

| | 변경 전 | 변경 후 |
| --- | --- | --- |
| 응답 | 검수 결과 전체(JSON) | `{"job_id": "<uuid>"}` |
| 소요 | 즉시(목업) / 실모델은 불가 | 즉시 반환, 결과는 폴링 |

**요청 본문은 그대로입니다.** `product_id` · `image_urls[]` · `category` · `base_color` ·
`include_attention_maps`(선택, 기본 false). 검증 실패는 지금처럼 422입니다.

### 2. 결과는 `GET /ai/jobs/{job_id}` 로 폴링합니다

시착과 완전히 동일한 엔드포인트·형식입니다. 이미 쓰고 계신 방식 그대로입니다.

```jsonc
{
  "job_id": "...",
  "status": "queued" | "processing" | "success" | "failed",
  "result": { /* status가 success일 때만 채워집니다 — 아래 3번 */ },
  "error": "...",      // failed일 때
  "worker_id": "..."
}
```

### 3. `result` 스키마

필드 정의 원본은 `AI/app/quality/schemas.py`입니다. 형태만 옮기면:

```jsonc
{
  "inspection_id": "insp_1042_7f3c",
  "product_id": 1042,
  "condition_score": 78.0,          // 0~100
  "condition_grade": "A",           // S | A | B | C
  "summary": "오염 2건, 얼룩 1건이 확인되었습니다.",
  "findings": [
    {
      "key": "stain_0_5_1",         // 안정 키 — 판매자 소명을 이 키에 매답니다
      "defect_type": "STAIN",       // STAIN|DIRT_MARK|HOLE_TEAR|DISCOLORATION|PILLING|FRAY
      "status": "DETECTED",         // DETECTED | SUSPECTED
      "image_index": 0,
      "section_no": 5,              // 3×3 부위 넘버링
      "section": "CHEST_CENTER",
      "confidence": 0.893,
      "area_ratio": 0.0113,
      "bbox": [0.42, 0.35, 0.55, 0.47],   // 정규화 좌표
      "severity": "MODERATE",       // MINOR | MODERATE | MAJOR
      "statement_required": true,   // 판매자 소명 입력 대상
      "needs_seller_review": false  // 모델 신뢰도가 낮아 확인 필수
    }
  ],
  "section_scores": [ { "section_no": 1, "section": "SHOULDER_LEFT", "score": 0.04 } ],
  "attention_maps": [ { "image_index": 0, "defect_type": "STAIN", "url": "https://.../results/..." } ],
  "notes": ["일부 항목은 모델 신뢰도가 낮아 판매자 확인이 필요합니다."]
}
```

**BE가 저장해야 하는 것**: finding의 `key`와 `statement_required`. 판매자 소명 본문은 AI가
받지 않습니다 — AI는 판정만 하고 저장은 BE가 합니다(라이브 댓글 관리와 같은 경계).

`condition_score`는 가격책정 입력이 될 값인데, **가중치·등급 경계가 아직 근거 없는 임의값**
입니다. 라벨링된 검증셋 확보 전까지 그대로 신뢰해 쓰시면 안 됩니다.

### 4. 호출 경로 주의 — Caddy는 `/quality/*`를 AI로 보내지 않습니다

`infra/caddy/Caddyfile`이 `/ai/*`와 `/results/*`만 `ai:8000`으로 라우팅하고 **나머지는 전부
`backend:8080`** 으로 갑니다.

- BE → AI 검수 요청: **컨테이너 내부 네트워크로** `http://ai:8000/quality/inspections`
- 결과 폴링: 내부로 `http://ai:8000/ai/jobs/{id}` 또는, FE가 직접 폴링해야 하면
  외부 경로 `https://i15a108.p.ssafy.io/ai/jobs/{id}`가 그대로 열려 있습니다

## 반드시 알아두실 동작 — 워커가 꺼져 있으면 `queued`로 머뭅니다

추론 워커가 **팀원 노트북**이라 항상 떠 있지 않습니다. 워커가 없으면 job은 `queued` 상태로
남아 있다가 **1시간(TTL) 뒤 조용히 사라집니다**(그 뒤 조회하면 404).

- 무한 폴링하지 마시고 타임아웃을 두시는 게 안전합니다.
- 워커 가용성을 미리 확인할 수 있도록 `GET /ai/workers/status`를 이번에 함께 추가합니다
  (기능별 최근 폴링 시각). 상품 등록 화면에서 "지금 검수 가능/불가"를 판단하는 데 쓰실 수 있습니다.

### 알려진 한계 (이번 범위 밖)

워커가 job을 가져간 직후 죽으면 그 job은 `processing`인 채로 TTL까지 남습니다 — 재시도 대상이
되지 않습니다. 가시성 타임아웃 도입은 별도 작업으로 잡아뒀습니다. 폴링 타임아웃을 두시면
BE 쪽에서는 `failed`와 동일하게 처리하시면 됩니다.

## 관련 자료

- 구조 근거: `AI/docs/infra-architecture.md` §2(워커는 Redis 직접 접속 금지) /
  §3.2(게이트웨이는 추론하지 않음) / §6(기능별 동기·비동기 분류)
- 설계 문서: `.claude/plans/ai/005-quality-inspection-prototype.md`
- 스키마 원본: `AI/app/quality/schemas.py`
- 같은 패턴 선례: 시착 — `worker/README.md`의 "전체 흐름 테스트" 절
