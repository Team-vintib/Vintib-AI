# 가격 책정 API 신설 — 연동 요청

- **요청자 파트**: AI
- **대상 파트**: BE
- **관련 티켓**: `S15P11A108-338` [PROD-010 | AI] 가격 책정 서비스 구현 (에픽 `-211`)
- **상태**: 요청 (AI 쪽 프로토타입 구현 완료, mock 백엔드 기준. BE 반영 시점은 협의)

## 배경

상품 등록 흐름에서 **품질 검수 다음 단계**로, 중고 시세를 검색해 권장 판매 가격대를
제안하는 API를 추가했습니다.

**폴링 계약은 품질 검수(`001`)와 완전히 동일합니다.** 접수 시 `job_id`를 받고
`GET /ai/jobs/{job_id}`로 결과를 조회하는 방식이라, 이미 쓰고 계신 폴링 코드를 그대로
재사용하시면 됩니다.

비동기인 이유는 품질 검수와 **다릅니다.** 품질 검수는 노트북 GPU에 인바운드가 안 돼서였고,
가격 책정은 GPU가 필요 없습니다 — 단지 **느립니다.** 외부 LLM으로 웹검색을 돌려 시세를
모으는데 실측 최소 7.7초가 걸립니다. 상품 등록 화면을 그만큼 세울 수 없어 비동기로 했습니다.

→ **가격 책정에는 노트북 워커가 없습니다.** `ai` 컨테이너가 직접 처리하므로 누가 노트북을
켜 두지 않아도 동작합니다.

## 요청 내용

### 1. `POST /pricing/estimates` 로 접수합니다

Caddy가 `/pricing/*`를 외부로 노출하지 않으므로, 품질 검수와 마찬가지로 **컨테이너 내부
주소**로 호출하시면 됩니다 — `http://ai:8000/pricing/estimates`.

```jsonc
{
  "product_id": 1042,            // 필수. AI는 에코만 합니다
  "product_name": "리바이스 501 빅E 데님",  // 필수. 검색 쿼리의 뼈대
  "brand": "리바이스",            // 선택. 상품명에 이미 있으면 생략해도 됩니다
  "category": "BOTTOM_PANTS",    // 선택. 품질 검수와 같은 enum
  "condition_score": 82.0,       // 필수. 품질 검수 결과를 그대로
  "condition_grade": "A",        // 필수. 품질 검수 결과를 그대로
  "retail_price": 129000         // 선택. 있으면 근거 문장에 할인율을 덧붙입니다
}
```

응답은 접수증뿐입니다.

```jsonc
{ "job_id": "<uuid>", "product_id": 1042 }
```

검증 실패는 422입니다(상품명 누락, `condition_score` 범위 밖, 미등록 등급 등).

### 2. ⚠️ `condition_score` · `condition_grade` 를 BE가 실어 주셔야 합니다

**AI에는 품질 검수 결과를 조회할 저장소가 없습니다.** 검수 결과는 Redis `result:{job_id}`에
TTL 1시간으로만 남고, 그 뒤에는 사라집니다. 가격 책정이 나중에 그걸 되찾을 방법이 없습니다.

상품 등록 흐름에서 BE가 검수 결과를 이미 들고 계시니, 그 두 값을 요청에 그대로 넣어 주시면
됩니다.

확인해 보니 현재 BE 스키마에는 `condition_grade`(VARCHAR)만 있고 **`condition_score` 컬럼이
없습니다.** 점수까지 저장·전달해 주시면 더 세밀한 보정이 가능합니다. 등급만 가능한 상황이면
알려 주세요 — 등급만으로도 동작하도록 폴백이 들어 있습니다.

> 참고로 `001`에서도 말씀드렸듯 **`condition_score`의 가중치·등급 경계는 아직 근거 없는
> 임의값입니다.** 가격 책정도 그 값을 그대로 쓰므로, 산출 가격을 "정확하다"고 사용자에게
> 표현하지 마시고 참고용으로 노출해 주세요.

### 3. 결과는 `GET /ai/jobs/{job_id}` 로 폴링합니다

`001`과 동일한 엔드포인트·형식입니다. `result` 안에 아래가 담깁니다.

```jsonc
{
  "job_id": "...",
  "status": "queued" | "processing" | "success" | "failed",
  "worker_id": "ai-inprocess",   // 노트북이 아니라 컨테이너가 처리했다는 표시
  "result": {
    "estimate_id": "price_1042_e689",
    "product_id": 1042,
    "priced": true,              // ★ false일 수 있습니다 — 아래 4번 참고
    "reason_code": "PRICED",     // PRICED | INSUFFICIENT_COMPS | NO_SEARCH_PERFORMED | PARSE_FAILED
    "price_range": {             // priced=false면 null
      "min": 47000,
      "mid": 57000,              // 이 값을 기본 제안가로 쓰시면 됩니다
      "max": 67000
    },
    "currency": "KRW",
    "confidence": 0.749,
    "confidence_level": "HIGH",  // LOW | MEDIUM | HIGH
    "rationale": [               // 판매자에게 그대로 보여줄 수 있는 한국어 근거
      "비교 매물 3건의 중앙값은 51,841원입니다.",
      "컨디션 A(82점)을 반영해 계수 1.10을 적용했습니다."
    ],
    "comps_used": [ /* 근거로 쓴 매물 목록 (title/price/url/listed_at/is_used) */ ],
    "comps_stats": { "count": 3, "median": 51841, "p25": 49248, "p75": 58061, "used_ratio": 1.0 },
    "condition": { "score": 82.0, "grade": "A", "coefficient": 1.096 },
    "model": { "comps_source": "mock", "comps_model_id": null, "pricer": "rule_baseline" },
    "notes": [ /* 한계·주의 문구 */ ],
    "latency_ms": 12.3
  }
}
```

### 4. ★ `priced: false` 를 실패로 다루지 말아 주세요

**가장 중요한 부분입니다.** 시세 근거를 못 찾은 것은 오류가 아니라 정상적인 결과입니다.
그 경우에도 `status`는 `success`이고 `priced`만 `false`입니다.

실측상 LLM 웹검색으로 모이는 비교 매물이 **쿼리당 평균 1.7건**입니다. 니치한 상품일수록
0건이 흔합니다. 이걸 실패로 보고 재시도하시면 **재시도할 때마다 외부 API 비용이 발생하는데
결과는 같습니다.**

→ `priced: false`면 "AI 제안 없음 — 직접 입력" UI로 보내 주세요. `reason_code`로 사유를
구분하실 수 있습니다.

`status: "failed"`는 인프라 오류(키 누락, 외부 API 장애, 타임아웃)일 때만 납니다. 이때만
재시도 대상입니다.

## 반드시 알아두실 동작

- **`GET /ai/workers/status`로 가격 책정 가용성을 판단하지 마세요.** 그 엔드포인트는 노트북
  워커 목록만 보여주는데 가격 책정에는 워커가 없어서 아예 나오지 않습니다. 컨테이너가 떠
  있으면 항상 가능합니다.
- **`POST /ai/pricing`으로 넣지 마세요.** 범용 게이트웨이 경로는 큐에 적재하는데, 가격 책정은
  그 큐를 읽는 주체가 없어서 job이 영원히 처리되지 않습니다. 반드시 `POST /pricing/estimates`를
  쓰셔야 합니다.
- **동시 처리 상한이 2건입니다.** 초과하면 접수 단계에서 **503**이 납니다(job이 만들어지지
  않습니다). 잠시 후 재시도하시면 됩니다. 상한을 둔 이유는 가격 job이 컨테이너 스레드를
  다 쓰면 다른 API의 결과 폴링까지 느려지기 때문입니다.
- **결과 TTL은 1시간**입니다. `001`과 동일합니다. 보관이 필요하면 BE DB에 저장해 주세요.
- 컨테이너가 재시작되면 처리 중이던 job은 `processing`인 채 TTL까지 남습니다. 폴링 타임아웃
  (60초 권장)을 두시고, 넘으면 `failed`와 동일하게 처리해 주세요.

## 현재 상태 — 기본은 목업입니다

AI 쪽 기본 설정은 **mock 백엔드**라 지금 붙이시면 상품명 기반의 가짜 매물로 가격이 나옵니다
(`model.comps_source: "mock"`, `notes`에 목업이라고 표시됩니다). API 계약을 먼저 맞추기 위한
것이고, 실검색 전환은 AI 쪽에서 별도로 진행합니다.

**연동 개발은 지금 시작하셔도 됩니다** — 실검색으로 바꿔도 요청·응답 형태는 그대로입니다.

## 관련 자료

- 설계 문서: `.claude/plans/ai/CH003-pricing-service-prototype.md`
- 검증 근거(왜 비동기인지, 왜 comps가 적은지): 노션 `웹검색 테스트`(LAB-47)
- 스키마 원본: `AI/app/pricing/schemas.py`
- 구조: `AI/docs/infra-architecture.md` §6 (기능별 동기·비동기 분류)
- 선행 요청: `.claude/requests/be/001-quality-inspection-async.md`
