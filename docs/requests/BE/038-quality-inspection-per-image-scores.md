# 품질 검수 결과 — section_scores/이미지별 요약 계약 변경

- **요청자 파트**: AI
- **대상 파트**: BE
- **관련 티켓**: `S15P11A108-508`([PROD-009 | AI] 품질 검수 앞/뒤 시멘틱 캐싱, 에픽 `-211`)
- **상태**: 요청 (AI 쪽 구현 완료, BE 반영 시점은 협의)

## 배경/이유

`037-quality-inspection-async.md`가 문서화한 `section_scores`는 이미지 여러 장이 와도 **항상
9개**였습니다(이미지 간 확률을 `max()`로 합쳐서 냈습니다). 앞/뒤 2장을 캐러셀로 보여주는
FE 요구(`019-product-quality-multi-image.md`)를 확인하는 과정에서, 이 합산 방식 때문에
앞면과 뒷면의 같은 섹션 번호 확률이 서로 덮어써지는 문제를 발견해 고쳤습니다.

## 요청 내용

### 1. `section_scores`에 `image_index`가 추가되고, 개수가 `9 × 이미지 수`로 바뀝니다

이전에는 항상 9개(이미지 전체 합산)였지만, 이제 이미지 1장당 9개씩 독립적으로 나옵니다.
2장이면 18개, `image_index`로 어느 이미지 것인지 구분합니다.

```jsonc
"section_scores": [
  { "image_index": 0, "section_no": 5, "section": "CHEST_CENTER", "score": 0.81 },
  { "image_index": 1, "section_no": 5, "section": "CHEST_CENTER", "score": 0.02 }
  // ...
]
```

### 2. `image_summaries` 필드가 새로 추가됩니다(기존 `summary`는 그대로 유지)

`summary`(전체 합산 한 줄 요약)는 그대로 두고, 이미지별 요약이 필요하면 이 필드를 씁니다.
하자가 없는 이미지도 빠짐없이 포함됩니다("확인된 하자가 없습니다").

```jsonc
"image_summaries": [
  { "image_index": 0, "summary": "오염 1건이 확인되었습니다." },
  { "image_index": 1, "summary": "확인된 하자가 없습니다." }
]
```

## 관련 자료

- 설계: `docs/plans/AI/CH020-quality-front-back-cache.md`
- 기존 계약: `docs/requests/BE/037-quality-inspection-async.md`, `docs/requests/BE/019-product-quality-multi-image.md`
- 스키마 원본: `AI/app/quality/schemas.py`(`SectionScore`, `ImageSummary`, `InspectionResult`)

## 처리 결과

(BE 반영 후 기입)
