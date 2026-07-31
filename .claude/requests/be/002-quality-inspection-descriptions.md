# 품질 검수 — 하자 한 줄 설명 옵트인 필드 추가

- **요청자 파트**: AI
- **대상 파트**: BE
- **관련 티켓**: `S15P11A108-309` (에픽 `-211`)
- **상태**: 요청 (AI 쪽 구현 완료, BE 반영 시점은 협의)

## 배경

`finding.description`(sVLM이 생성하는 하자 한 줄 설명, 상품 상세 불릿 리스트용)이 스키마에
CH007부터 있었지만 항상 `None`이었습니다. 이번에 실제로 채우도록 연결했는데, **생성에
finding당 수 초가 걸려서**(이미지 1장에 findings가 6~16건 나올 수 있음) 항상 켜두면 검수
응답이 이미지당 수십 초~수 분까지 늘어날 수 있습니다. 그래서 `include_attention_maps`와
같은 방식의 **옵트인 플래그**로 뒀습니다.

## 요청 내용

### 1. `POST /quality/inspections` 요청 본문에 필드 1개 추가

기존 필드(`product_id`/`image_urls`/`category`/`base_color`/`include_attention_maps`)는
그대로입니다. 추가된 것:

```jsonc
{
  // ...기존 필드...
  "include_descriptions": false  // 선택, 기본 false
}
```

`true`로 보내면 `result.findings[].description`이 채워집니다(아래 2번). 안 보내면 지금과
동일하게 계속 `None`입니다 — **기존 호출부는 아무것도 안 바꿔도 그대로 동작합니다.**

### 2. `result.findings[].description`이 채워지는 조건

- `include_descriptions: true`로 요청했고
- 그 finding의 `status`가 `"DETECTED"`일 때만 채워집니다(`"SUSPECTED"`는 계속 `None`).
- 설명 생성이 개별적으로 실패해도 검수 자체는 실패하지 않습니다 — 그 finding만
  `description: null`로 남고 나머지 응답은 그대로 나갑니다.

```jsonc
{
  "key": "stain_0_5_1",
  "defect_type": "STAIN",
  "status": "DETECTED",
  // ...기존 필드...
  "description": "허리 중앙 부분 — 작은 흰색 얼룩이 부드럽게 퍼진 모양으로 있습니다."
}
```

### 3. 지금 당장 켤 필요는 없습니다

상품 상세 화면에 불릿 리스트를 아직 안 붙이신다면 `include_descriptions`를 안 보내도
됩니다(생략 시 기본 false, 지연시간 영향 없음). 화면에 붙일 준비가 되면 그때 켜시면 됩니다.

## 관련 자료

- 설계 문서: `.claude/plans/ai/CH009-quality-defect-vlm.md`,
  `.claude/plans/ai/CH011-quality-vlm-production-wiring.md`
- 스키마 원본: `AI/app/quality/schemas.py`(`InspectionRequest.include_descriptions`,
  `Finding.description`)
- 선례: `include_attention_maps` — 같은 옵트인 패턴
