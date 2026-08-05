# 의류 실측(cm) 측정 — job 접수/폴링 계약 및 상품 등록 연동 결정 요청

- **요청자 파트**: AI
- **대상 파트**: BE
- **관련 티켓**: `S15P11A108-210` 에픽 하위(구체 이슈 번호 미정)
- **상태**: 요청 (AI 쪽 1단계 배관 구현 완료, 실제 CV/모델 단계는 진행 중)

## 배경

판매자가 상품 등록 시 찍는 옷 사진(기준 물체 + 평평하게 편 옷)에서 어깨너비·소매길이·총장·밑단
너비 등을 cm 단위로 자동 추출하는 기능을 AI에서 만들고 있습니다. 품질검수(`S15P11A108-304`)와
같은 이유로 비동기 큐 방식입니다 — 무거운 처리는 팀원 GPU 노트북 워커가 하고, 노트북은
인바운드 접속이 불가능해서 동기 호출 대상이 될 수 없습니다.

## 요청 내용

### 1. `POST /measurement/scans` — job 접수

품질검수와 완전히 같은 패턴입니다.

```jsonc
// 요청
{
  "product_id": 1042,
  "image_url": "https://.../scan.jpg",  // 기준 물체(A4 용지) + 옷을 위에서 찍은 사진 1장
  "category": "TOP",  // "TOP" | "BOTTOM" (v1 범위)
  "reference_object": "A4_PAPER"  // 현재 유일한 값, 생략 가능(기본값)
}
// 응답 — 결과가 아니라 접수증입니다
{ "job_id": "...", "product_id": 1042 }
```

**기준 물체는 A4 용지입니다(신용카드 아님).** 판매자가 실물 카드를 촬영해 서버로 올리는 흐름은
번호·명의 등 개인정보 노출 위험이 있어 제외했습니다.

### 2. 결과는 `GET /ai/jobs/{job_id}` 로 폴링

시착·품질검수와 동일한 형식입니다.

```jsonc
{
  "job_id": "...",
  "status": "queued" | "processing" | "success" | "failed",
  "result": {
    "measurement_id": "scan_1042_...",
    "product_id": 1042,
    "reference_object_found": true,
    "pixel_to_cm_ratio": 0.2645,
    "landmarks": [ { "type": "SHOULDER_LEFT", "pixel_x": 320.0, "pixel_y": 210.0, "confidence": 0.93 }, ... ],
    "measurements": [
      { "type": "SHOULDER_WIDTH", "value_cm": 52.0, "confidence": 0.9 },
      { "type": "SLEEVE_LENGTH", "value_cm": 62.0, "confidence": 0.87 },
      { "type": "TOTAL_LENGTH", "value_cm": 74.0, "confidence": 0.9 },
      { "type": "HEM_WIDTH", "value_cm": 48.0, "confidence": 0.9 }
    ],
    "overall_confidence": 0.87,
    "needs_retake": false,
    "retake_reason": null,  // "REFERENCE_NOT_FOUND" | "GARMENT_NOT_FOUND" | "GARMENT_NOT_FLAT" | "LOW_LANDMARK_CONFIDENCE"
    "notes": [],
    "latency_ms": 340.5
  }
}
```

**`needs_retake=true`면 `measurements`가 비어 있습니다** — 기준 물체나 원단을 못 찾은 경우입니다.
재촬영 유도 UX는 BE/FE가 정하시면 되고, AI는 이유(`retake_reason`)만 알려드립니다.

가슴단면(pit-to-pit)은 v1 범위 밖입니다 — 겨드랑이 랜드마크가 아직 없습니다.

### 3. 결정해 주셔야 할 것 — `APIs.md`의 `POST /products`(PROD-001)엔 이 흐름을 위한 필드가 없습니다

- 상품 등록 이미지 배열에 "실측용 사진" 역할을 구분하는 플래그를 둘지, 별도 필드로 받을지
- 상품 등록이 실측 완료를 기다릴지, 별도로 진행하고 나중에 붙일지 (품질검수처럼 워커 오프라인
  시 job이 `queued`로 남아 있다가 TTL(1시간)에 만료되는 케이스가 여기도 동일하게 적용됩니다 —
  `GET /ai/workers/status`로 워커 가용 여부를 미리 확인할 수 있습니다)
- cm 값을 어디에 저장할지(Product의 새 필드 vs 별도 테이블)

## 반드시 알아두실 동작

품질검수와 동일 — 워커가 꺼져 있으면 job은 `queued`로 남아 있다가 1시간 뒤 조용히 사라집니다
(그 뒤 조회하면 404). 무한 폴링 대신 타임아웃을 두시는 게 안전합니다.

## 참고

- 스키마 원본: `AI/app/measurement/schemas.py`
- 같은 패턴 선례: `.claude/requests/be/001-quality-inspection-async.md`
- 설계 문서: `.claude/plans/ai/010-garment-measurement-scan.md`
