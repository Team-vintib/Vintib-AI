# 상품 등록 — 사진 2장 시점에 AI 분석을 트리거하려면 상품 생성 전 이미지 URL이 필요합니다

- **요청자 파트**: FE
- **대상 파트**: BE

## 배경/이유

상품 등록 화면(`ProductRegistrationPage.vue`)을 "Front/Back 사진 2장이 갖춰지는 즉시 AI가 카테고리·색상·품질 검증을 자동으로 채워주는" 흐름으로 바꾸려고 합니다. 그런데 지금 구조에서는 이미지가 **상품 생성(`POST /products`) 이후**에만 업로드됩니다(`submitProduct` → `uploadProductImages`, presigned URL 발급 → S3 PUT → `/products/{id}/images` 등록). `categoryId`는 `@NotNull`이라 그 시점엔 이미 카테고리가 채워져 있어야 하는데, 저희가 채우려는 게 바로 그 카테고리 값이라 순서가 꼬입니다 — AI가 분석할 이미지 URL 자체가 상품 생성 전에는 없습니다.

품질 검증(`docs/requests/BE/037`)도 요청 본문에 `product_id`가 필요해 같은 문제를 겪습니다.

## 요청 내용

상품이 완전히 만들어지기 전에, front/back 사진 2장만으로 이미지 URL을 먼저 확보할 방법이 필요합니다. 두 방향을 제안하며 최종 설계는 BE 판단에 맡깁니다.

**방향 A — `DRAFT` 상태 조기 생성**: `ProductSaleStatusDto`에 이미 `'DRAFT'` 값이 보이는데, 혹시 이런 흐름(사진만으로 상품을 `DRAFT`로 먼저 만들고, 이후 카테고리·가격 등 나머지 필드는 별도 update로 채워 최종 등록 상태로 전환)을 염두에 두고 추가해두신 값인가요? 그렇다면 이 방향이 더 자연스러울 것 같습니다. 이 경우 지금 없는 "상품 부분 수정" 엔드포인트(예: `PATCH /products/{id}`)가 함께 필요합니다.

**방향 B — 상품과 무관한 독립 사전 업로드**: 상품 row를 만들지 않고 이미지 파일만 먼저 업로드해 URL(또는 재사용 가능한 S3 key)을 돌려주는 엔드포인트. 이후 실제 `POST /products` 제출 시 이 key를 그대로 넘겨 재업로드 없이 이미지로 등록할 수 있으면 좋겠습니다.

품질 검증(`037`)은 이 사전 업로드로 받은 이미지 URL을 그대로 `POST /quality/inspections`에 넘기는 형태로, 기존 job 등록→폴링 계약을 그대로 재사용하고 싶습니다 — 트리거 시점만 "상품 생성 후"에서 "사전 업로드 직후"로 앞당겨지는 차이입니다.

카테고리/색상 자동판별에 필요한 실제 분류 계약(요청 응답 필드)은 별도로 `docs/requests/AI/006-registration-category-color-autofill.md`에 정리했습니다 — 그쪽 엔드포인트를 BE가 어떤 경로로 노출할지도 이번 결정과 함께 알려주시면 좋겠습니다.

## 3. 등록 시 사용자가 확정한 하자 정보를 저장하고, 상품 상세에서 그대로 보여주세요

AI 품질 검증 섹션에서 사용자가 각 하자 후보를 "하자로 인정/제외"로 확정하고 사진별로 "결과 저장"을 누르면, 그 결과가 최종 확정 목록입니다. 이 정보를 `POST /products` 제출 시 함께 보내려고 합니다 — 요청 바디에 아래 필드를 새로 추가했습니다(FE는 이미 이 필드를 채워서 보내는 중이지만, BE가 아직 받지 않으니 지금은 무시될 뿐입니다).

```jsonc
"aiQualityFindings": [
  {
    "photoRole": "front",           // "front" | "back"
    "description": "소매 끝단 마모 의심",
    "box": { "x": 58, "y": 18, "width": 24, "height": 18 }  // % 좌표(0~100), 사진 프레임 기준
  }
]
```

이걸 저장해두셨다가, 상품 상세 조회(`GET /products/{id}`) 응답에 `docs/requests/BE/019-product-quality-multi-image.md`가 요청한 `aiQualityAnalysis.images[].findings` 형태로 실어 주시면, 상품 상세의 "AI 분석" 탭(`AiQualityAnalysisPanel.vue`)이 등록 시 확정한 하자를 그대로 보여줄 수 있습니다. 019가 원하는 이미지별 `originalImageUrl`/`analyzedImageUrl`/`summary`는 이 등록 흐름만으로는 못 채우는 값이라(원본 이미지 URL 정도는 상품 이미지에서 그대로 가져올 수 있겠지만, `summary`나 주석 이미지는 별도 판단이 필요합니다) 그 부분은 BE/AI 판단에 맡깁니다 — 최소한 `findings`(하자 위치+설명)만큼은 등록 시점 데이터로 채워질 수 있다는 점을 알려드리고 싶었습니다.

## 4. 참고 — AI 쪽 엔드포인트는 이미 구현돼 있습니다

FE에서 직접 확인해보니 `AI/app/product_classifier/router.py`(`POST /product-classifier/classify`)와 `AI/app/quality/router.py`(`POST /quality/inspections`)가 이미 만들어져 있고, 둘 다 `GET /ai/jobs/{job_id}` 폴링으로 결과를 받는 구조까지 동작합니다. 다만 **둘 다 요청 본문에 `product_id`가 필수**라, 정확히 이 문서가 지적한 "상품 생성 전에는 부를 방법이 없다"는 문제 그대로입니다. BE가 이 두 엔드포인트를 호출/프록시하는 코드는 아직 없습니다(컨트롤러 전수 검색 결과 `quality`/`classif`/`/ai/` 매치 0건). 즉 막힌 지점은 AI 구현이 아니라 **이 문서의 방향 A/B 결정과 BE의 프록시·호출 코드**입니다 — 빠른 판단에 참고해주세요.

## 관련 자료
- `FE/src/domains/product/api/productApi.ts` (`submitProduct`, `uploadProductImages`, `resolveRegistrationAiQualityFindings`)
- `docs/requests/BE/037-quality-inspection-async.md` (품질 검수 job 계약)
- `docs/requests/BE/039-registration-ai-model-tryon.md` (등록 중 AI 트리거의 선례 — 다만 이건 "제출 후" 트리거라 이번 요청과는 트리거 시점이 다릅니다)
- `docs/requests/BE/019-product-quality-multi-image.md` (상품 상세 AI 분석 탭이 필요로 하는 응답 형태)
- `docs/requests/AI/006-registration-category-color-autofill.md`
