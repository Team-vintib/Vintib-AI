# 상품 등록 — 카테고리 소분류 노출 + 색상 자동판별 요청

- **요청자 파트**: FE
- **대상 파트**: AI (BE도 함께 확인 필요 — 게이트웨이 경로 관련)

## 배경/이유

상품 등록 화면을 "사진 2장만으로 카테고리(대분류·소분류)·색상을 AI가 자동으로 채우고, 사용자는 필요시 수정만 하는" 흐름으로 바꾸려 합니다. 사용자는 여전히 값을 바꿀 수 있어 `docs/requests/BE/006`에서 확정한 "미분류 상태가 안 생긴다"는 전제와 어긋나지 않습니다.

`docs/requests/BE/033-category-gender-stays-in-form.md`를 보면 분류 파이프라인이 이미 **소분류(35-way)를 1.00 정확도로 먼저 예측한 뒤 `major_of()`로 대분류를 역산**해서 응답하고 있습니다(대분류를 직접 6-way로 물으면 0.35였던 것과 대비). 즉 소분류 id는 이미 모델 내부에서 계산되고 있고, 응답에서 대분류로 접어버릴 뿐이라고 이해했습니다.

## 요청 내용

1. **소분류 id도 함께 응답해 주실 수 있나요?** 지금처럼 (성별 + 판별한 대분류)로 접은 대분류 id뿐 아니라, 내부적으로 이미 예측한 소분류(depth3) id도 같이 내려주시면 등록 폼에서 카테고리 전체를 자동으로 채울 수 있습니다. `033`에서 확정한 "성별은 폼에서 사용자가 먼저 선택, 못 받으면 UNISEX로 응답"은 그대로 유지해 주세요 — 이번 트리거(사진 업로드 즉시)는 사용자가 아직 폼의 다른 값을 채우기 전이라 성별을 못 넘기는 케이스가 기본값이 될 가능성이 높습니다.
2. **색상 자동판별이 가능한가요?** 등록 폼의 색상 선택지는 아래 14개로 고정돼 있습니다(`FE/src/domains/product/constants/productRegistrationOptions.ts`의 `PRODUCT_REGISTRATION_COLOR_OPTIONS` — "기타"는 이후 제거했습니다):
   검정 · 흰색 · 회색 · 빨강 · 주황 · 분홍 · 노랑 · 갈색 · 초록 · 파랑 · 보라 · 베이지 · 네이비 · 혼합
   가능하다면 사진에서 대표 색상을 판별해 이 14개 중 가장 가까운 값으로 매핑해 응답해 주시면 좋겠습니다("기타"가 없으니 애매하면 가장 근접한 색으로). 모델이 색상 판별을 지원하지 않는다면 안 된다고 알려주세요 — 그 경우 색상은 계속 사용자 수동 입력으로 남기겠습니다.
3. **품질 검증 좌표 형식 확인**: `docs/requests/BE/037-quality-inspection-async.md`의 `bbox: [x1,y1,x2,y2]`(정규화 axis-aligned 좌표)를 그대로 쓸 예정입니다 — FE에서 이 bbox의 네 모서리 좌표를 계산해 사진 위에 사각형으로 그립니다. 회전된 사각형이 필요한 상황은 없어서 별도 계약 변경 없이 그대로 재사용하려는데, 이 이해가 맞는지만 확인 부탁드립니다.

엔드포인트/응답 스키마 형태는 기존 카테고리 판별 계약(`docs/requests/AI/004-category-taxonomy-v2.md`)과 비슷한 형태면 됩니다 — 정확한 경로는 `docs/requests/BE/042-product-registration-ai-pipeline.md`(상품 생성 전 이미지 업로드 방식)와 함께 BE가 정리해 주시면 FE가 맞춰 연동하겠습니다.

## 참고 — 이미 구현된 엔드포인트를 확인했습니다

`AI/app/product_classifier/router.py`(`POST /product-classifier/classify`)가 이미 있고, `GET /ai/jobs/{job_id}` 결과의 `ProductClassifyResult`에 `fields.category{value,path,score,action,candidates}`와 `fields.color_primary{value,hex,score,action,candidates}`/`color_secondary`가 이미 존재합니다(`AI/app/product_classifier/schemas.py`). 요청 1·2가 이미 부분적으로 반영돼 있을 수도 있어 보여 여쭤봅니다:

- `fields.category.value`/`.path`가 지금 대분류만 담고 있는지, 아니면 이미 소분류(depth3)까지 포함하는지 확인 부탁드립니다 — `path`라는 이름을 보면 이미 전체 경로일 가능성도 있어 보입니다.
- `fields.color_primary.value`가 어떤 값 집합인지(자유 텍스트인지, 정해진 팔레트인지) 알려주시면 위 14개 옵션과 매핑할 수 있을지 바로 판단할 수 있습니다.

둘 다 이미 원하는 형태라면 요청 1·2는 그대로 닫아도 됩니다 — 그게 아니라면 위 요청대로 확장 부탁드립니다.

## 관련 자료
- `docs/requests/BE/033-category-gender-stays-in-form.md`
- `docs/requests/AI/004-category-taxonomy-v2.md`
- `docs/requests/BE/037-quality-inspection-async.md`
- `docs/requests/BE/042-product-registration-ai-pipeline.md`
- `FE/src/domains/product/constants/productRegistrationOptions.ts` (`PRODUCT_REGISTRATION_COLOR_OPTIONS`)
