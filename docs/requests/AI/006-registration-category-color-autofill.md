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

## 참고 — 코드까지 직접 확인했고, 요청 1·2는 사실상 해소됐습니다

`AI/app/product_classifier/`와 `worker/models/product_classifier/`를 직접 읽어봤습니다.

- **요청 1(소분류) 해소**: `worker/models/product_classifier/contracts.py`의 `CategoryPrediction.to_dict()`가 `"value": self.subcategory.value`(예: `"CARDIGAN"`, 소분류 코드 그대로), `"path": self.path`(예: `["아우터", "가디건"]`, 대분류→소분류 한글 표시 배열)로 채우고 있어 **이미 소분류까지 응답에 있습니다.** 다만 **성별 조합 depth2 `categoryId`(4~23)는 응답에 없습니다** — FE/BE가 성별과 이 `value`/`path`를 조합해 `categoryId`를 계산해야 합니다. 이 계산 방법(테이블/함수)을 알려주시면 좋겠습니다.
- **요청 2(색상) 해소**: `worker/models/product_classifier/color.py`의 `PALETTE`가 13색(`BLACK/WHITE/GRAY/RED/ORANGE/PINK/YELLOW/BROWN/GREEN/BLUE/PURPLE/BEIGE/NAVY`) + `MIXED`로 확정돼 있고, 이 14개가 FE 옵션 14개와 정확히 1:1 매핑됩니다(대소문자만 다름). FE는 `mapAiColorKeyToOptionId()`로 이미 매핑 코드를 만들어뒀습니다.
- 요청 3(bbox 좌표)은 `037`이 아니라 지금은 `docs/requests/BE/041-quality-inspection-integration.md`(037/038 통합본)로 대체됐습니다 — 내용은 동일(정규화 `[x1,y1,x2,y2]`)하니 그대로 확인 부탁드립니다.

## 새로 발견한 것 — 확인 부탁드립니다

1. **`taxonomy_version` 기본값 불일치(버그로 보임)**: `AI/app/product_classifier/schemas.py`의 `ProductClassifyRequest.taxonomy_version` 기본값이 `"v1"`인데, 실제 워커가 쓰는 값은 `worker/models/product_classifier/taxonomy.py`의 `TAXONOMY_VERSION = "v2-be-seed-2026-08-03"`입니다. `worker/product_classifier_worker_example.py`가 결과를 조립할 때 `payload.get("taxonomy_version", TAXONOMY_VERSION)`으로 요청값(`"v1"`)을 그대로 쓰기 때문에, 실제로는 v2 taxonomy로 분류해놓고 응답의 `taxonomy_version`은 `"v1"`이라고 잘못 표시됩니다. BE가 버전 불일치 시 프리필을 거부하는 로직을 넣으면 항상 거부될 수 있어 미리 알려드립니다.
2. **트리거 시점 확인**: `041-quality-inspection-integration.md`가 "품질 검수는 BE가 앞/뒤 사진 업로드 완료 직후 트리거하고, 분류(카테고리·색상) 이벤트는 그와 별개"라고 명시했습니다. 분류도 041과 같은 패턴(BE가 사진 업로드 시점에 `POST /product-classifier/classify`를 트리거하고, job_id를 등록 draft 응답에 실어 보내면 FE가 `GET /ai/jobs/{job_id}`로 직접 폴링)을 따르는 게 맞는지 확인 부탁드립니다 — 맞다면 041의 폴링 코드를 그대로 재사용할 수 있어 FE 작업이 단순해집니다.
3. **워커가 아직 mock 스텁**: `worker/models/product_classifier/registry.py`의 `ACTIVE_CATEGORY_BACKEND`/`ACTIVE_COLOR_BACKEND`가 둘 다 `"mock"`이라, 지금 연동해도 카테고리는 항상 `JACKET`(score 0), 색상은 항상 `BLACK`(score 0)로 고정 응답됩니다. 실백엔드(CLIP 등) 전환 일정이 있다면 참고차 알려주시면 좋겠습니다 — FE는 그 전까지는 이 기능을 mock 그대로 두고 실사용자에게 노출하지 않을 계획입니다.

## 관련 자료
- `docs/requests/BE/033-category-gender-stays-in-form.md`
- `docs/requests/AI/004-category-taxonomy-v2.md`
- `docs/requests/BE/041-quality-inspection-integration.md`(037/038 대체)
- `docs/requests/BE/042-product-registration-ai-pipeline.md`
- `FE/src/domains/product/constants/productRegistrationOptions.ts` (`PRODUCT_REGISTRATION_COLOR_OPTIONS`)
- `FE/src/domains/product/constants/aiColorPalette.ts`(`mapAiColorKeyToOptionId`)
