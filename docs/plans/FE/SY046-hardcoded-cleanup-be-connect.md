# SY046 상품 등록/가격 그래프 하드코딩 정리 — BE/AI 실연동

## 배경/목표

사용자가 "상품 등록 시 품질 검사 / 가격 그래프 등" FE 하드코딩 전반을 정리하고 BE/AI와 연결해달라고 요청. 조사해보니 카테고리·브랜드는 예상과 달리 이미 대부분 실연동 상태였다:

- **카테고리**: `ProductRegistrationPage.vue`가 이미 `getCategories()`(`GET /api/categories`, 실 API)로 채운 `categories.value`를 우선 쓰고, `PRODUCT_REGISTRATION_CATEGORY_OPTIONS`(6개 하드코딩)는 로딩 전/실패 시 폴백으로만 쓰인다. 손댈 것 없음.
- **브랜드**: `ProductCreateRequest.brand`/`ProductUpdateRequest.brand`가 BE 스펙상 `"마스터에서 고르지 않고 자유 텍스트로 받는다"`고 명시돼 있다(Swagger 설명 원문). 즉 지금 FE의 자유입력 `<input>`이 BE 의도와 정확히 일치한다 — `GET /api/brands`가 있다고 select로 바꾸면 오히려 BE 계약과 어긋난다. 손대지 않는다.

실제로 남은, 연결 가능한 작업은 아래 4가지다(4번은 작업 도중 발견 — 배경/목표 아래 "작업 내용 4" 참고).

## 작업 내용

### 1. 검색 필터 카테고리 실연동

`FE/src/domains/search/constants/searchFilterOptions.ts`의 `SEARCH_CATEGORY_FILTER_OPTIONS`(아우터/상의/하의/원피스/신발/액세서리/시계 7개, 이름 문자열 기반, depth 2/3 혼재 — "시계"는 실제로는 액세서리 하위 depth 3)를 제거한다. `ProductRegistrationPage.vue`가 이미 쓰는 패턴(`getCategories()` + `productApi.ts`의 `buildProductCategoryOptions()`)을 `SearchResultsPage.vue`에도 그대로 적용해 실제 대분류(7종: 아우터/상의/하의/신발/가방/액세서리/원피스 및 점프슈트)와 그에 속한 실제 `categoryIds`를 얻는다.

- 필터 체크박스의 `option.id`가 지금은 한글 라벨 문자열인데, 실연동 후에는 `ProductCategoryOption.categoryIds`(number[])를 써야 한다 — `selectedCategoryIds`/쿼리 파라미터 직렬화(`categories=...`) 로직을 숫자 ID 배열 기준으로 조정한다.
- `getFilterOptionLabel` 등 라벨 표시용 헬퍼도 실제 카테고리 옵션 목록을 참조하도록 바꾼다.

### 2. AI 가격 추천 실연동 켜기

등록 화면 "AI 가격 추천" 단계는 이미 실연동 코드가 완성돼 있다(`productAiApi.ts`의 `estimateRegistrationPrice` → `POST /products/price-estimates` → AI 게이트웨이 폴링, BE 쪽도 `SY044`로 반영 완료). 다만 `.env`의 `VITE_PRODUCT_AI_ENABLED=false`라 mock만 타는 중이다.

- `VITE_PRODUCT_AI_ENABLED=true`로 전환.
- 로컬에서 등록 화면 "상태/하자" 이후 가격 추천 단계까지 실제로 진행해 히스토그램·등급별 추천가가 실 데이터로 채워지는지, 실패/로딩 상태 UI가 정상 동작하는지 확인.
- 등급별 대표 `condition_score`(S:95/A:82/B:68/C:50) 잠정치는 이번 범위에서 바꾸지 않는다 — AI가 확정해준 실측값이 82점 하나뿐이라 FE가 임의로 고칠 수 없다(기존 결정 유지).

### 3. 상품 상세 "동일 상품 시세" 신규 기능 (docs/requests/FE/042 반영)

BE에 이미 구현·테스트된 `GET /products/{id}/market-price`를 연결하는 신규 컴포넌트를 상품 상세 화면에 추가한다. 기존 `ProductPriceDistribution.vue`("유사 상품 가격대", 카테고리 기준 추천 — 정책 미확정이라 계속 mock 유지)와는 별개 기능이다.

- 응답: `{ productId, matchKey, currentProduct, listings: [{ productId, title, price, priceKind }] }`. `priceKind`: `ASKING`/`SOLD_DIRECT`/`SOLD_AUCTION`.
- `matchKey`가 없거나 `listings`가 비어 있으면(404 아님) "아직 시세 정보 없음"으로 처리.
- 반영 후 `docs/requests/FE/042-pricing-matchkey-forwarding.md` 삭제.

### 4. 상품 등록 "AI 품질 검증" 실폴링 연결 (계획 수립 당시 누락 — 작업 중 발견)

`qualityInspectionHardcodedResult.json`을 죽은 파일로 보고 삭제했다가 빌드가 깨져 확인해보니, SY043 계획 문서의 체크리스트는 "완료"로 표시돼 있었지만 실제 코드는 여전히 가짜였다: `ProductRegistrationPage.vue`의 `beginQualityInspection()`이 draft 상품 생성+이미지 업로드까지는 실제로 하면서도, 검수 결과는 `getProductQualityInspectionStatus`(BE `GET /products/{id}/quality-inspection`) 실폴링 대신 **7초 sleep 후 이 하드코딩 JSON을 그대로 보여주는 방식**이었다. `getProductQualityInspectionStatus`/`mapQualityInspectionResultToPhotoResults`는 이미 `productApi.ts`에 구현돼 있었지만 화면에서 호출되지 않고 있었다.

- `beginQualityInspection()`의 sleep+하드코딩 결과 블록을 실제 폴링(`pollQualityInspectionStatus`, `triggerAiCategoryColorSuggestion`의 `pollProductClassify`와 동일한 토큰 기반 취소/타임아웃 패턴)으로 교체.
- `status === 'NONE'`(SAM3 미지원 카테고리)은 기존 `isQualityCategoryUnsupported` 안내로, `'FAILED'`/타임아웃은 검증 실패로 처리.
- `qualityInspectionHardcodedResult.json`과 그 import는 이제 실제로 죽은 코드가 되어 삭제.

### 5. 상품 상세 "AI 품질 분석" — 조사 결과 정정(이미 실연동돼 있었음)

당초 손대지 않을 항목으로 분류했으나(아래 §AI/005 근거는 stale), 실제 코드를 다시 보니 `ProductDetailView.vue`의 `AiQualityAnalysisPanel`은 이미 `product.aiQualityAnalysis`(BE `ProductDetailResponse.aiQualityAnalysis`, `Product.qualityInspectionStatus`에서 매번 직접 조립 — 별도 영구 저장 테이블 없이 상세 응답 자체에 바로 실려 온다)를 그대로 쓰고 있었다. `aiQualityAnalysisMockData.ts`는 `PRODUCT_API_ENABLED=false`일 때만 쓰이는 오프라인 mock 폴백(`productDetailMockData.ts`)에서만 참조되고, 기본 실행 경로에는 관여하지 않는다. **작업 불필요 — 이미 완료 상태.**

### 6. 상품 등록/상세 "AI 모델컷" 실폴링 연결 (사용자 지적으로 발견)

`ProductRegistrationPage.vue`(등록 완료 시점)와 `ProductDetailView.vue`(상세 진입 시점) 둘 다 `aiModelCutStatus`/`aiModelCutImageUrl`을 실제 생성 결과 대신 하드코딩된 샘플 이미지(`폴로_모델샷.png`)로 채우고 있었다. BE에는 이미 `GET /products/{id}/ai-model-cut` 전용 상태 조회 엔드포인트가 있고, FE `productApi.ts`의 `getProductAiModelCutStatus`도 이미 구현돼 있었지만("완료 화면에서 폴링용으로 쓴다"는 주석까지 있음) 두 화면 다 호출하지 않고 있었다.

- 등록 화면: 최종 제출 성공 직후(`aiModelEnabled`) 하드코딩 대신 `pollAiModelCutStatus`(품질검증과 동일한 토큰 기반 폴링 패턴)를 시작.
- 상세 화면: 상세 응답의 `product.aiModelCut.status`/`.imageUrl`을 그대로 쓰고, `PENDING`/`PROCESSING`이면 같은 방식으로 폴링.
- 이제 완전히 쓰이지 않는 `아이 모델 하드코딩 샘플` import(`aiModelHardcodedShot`)와 이미지 자산(`src/assets/images/ai-model/폴로_모델샷.png`)은 삭제.

### 7. 상품 상세 "유사 상품 추천" 캐러셀 실연동 (사용자 지적으로 발견)

`getSimilarProducts`가 실제 `GET /products/{id}/similar`(CH034, `SimilarProductQueryService`) 대신 상품 ID 5개(41/42/17/43/1)를 하드코딩해 `GET /products`(페이지네이션 전체 목록)에서 그 5개만 골라 쓰고 있었다. 이 우회는 "실제 API가 같은 상품만 반복 반환한다"는 코멘트와 함께 도입됐는데, 코드로 다시 확인해보니 `GET /products/{id}/similar`의 실제 응답(`SimilarProductsResponse`)은 페이지네이션이 아니라 `{ productId, items }` 단일 목록이다 — 예전 호출부가 페이지네이션 응답을 기대하는 파서로 이 응답을 읽었다면 필드가 어긋나 그렇게 보였을 수 있다. BE 서비스 코드 자체는 캐시 후보/SQL 폴백 모두 대상 상품과 품절 상품을 제외하도록 정상 구현돼 있다. 실제 엔드포인트를 올바른 응답 타입으로 파싱하도록 되돌렸다.

### 8. 상품 상세 "유사 상품 가격대" 그래프의 상품 187 특례 제거 (사용자 지적으로 발견)

`normalizeSimilarProducts`가 상품 id=187에 한해 하드코딩된 93개 목록(`HARDCODED_SIMILAR_PRODUCTS_FOR_187`)을 대신 반환하고 있었다. 이 특례를 제거하고 모든 상품에 대해 BE 상세 응답의 `similarProducts`(카테고리 기준, `SimilarProductResponse`)를 그대로 쓰도록 통일했다. 상품 187은 BE 데모 시드 데이터가 같은 제목으로 여러 건 중복 등록돼 있어 실제로는 같은 제목이 반복 노출될 수 있는데, 이건 FE가 고칠 수 있는 범위가 아니라 BE 시드 데이터 품질 문제다 — 필요하면 별도로 BE에 시드 다양화를 요청해야 한다.

## 이번 범위에서 손대지 않는 것

(모든 항목을 실연동 또는 근거 확인 후 결정. 남은 의도적 mock 없음 — AI 가격 추천 등급별 잠정 점수만 AI 확정 전까지 유지, 위 §2 참고.)

## 구현 목록

- [x] `searchFilterOptions.ts`에서 `SEARCH_CATEGORY_FILTER_OPTIONS` 제거, `SearchResultsPage.vue`를 `getCategories()`+`buildProductCategoryOptions()` 기반으로 전환(선택 상태·쿼리 파라미터를 categoryIds 배열 기준으로 조정)
- [x] `.env`/`.env.example`의 `VITE_PRODUCT_AI_ENABLED`를 `true`로 변경
- [x] 상품 상세 "동일 상품 시세" 컴포넌트(`ProductMarketPrice.vue`) 및 `productApi.ts`의 `getProductMarketPrice(productId)` 추가, 화면 배치
- [x] `docs/requests/FE/042-pricing-matchkey-forwarding.md` 삭제
- [x] `ProductRegistrationPage.vue`의 `beginQualityInspection()`을 실폴링(`pollQualityInspectionStatus`)으로 교체, `qualityInspectionHardcodedResult.json` 삭제
- [x] 상품 상세 "AI 품질 분석" 실연동 여부 재확인(이미 완료 — 추가 작업 없음)
- [x] 등록/상세 화면의 AI 모델컷 하드코딩을 `getProductAiModelCutStatus` 실폴링으로 교체, `aiModelHardcodedShot` import·자산 삭제
- [x] `getSimilarProducts`를 `GET /products/{id}/similar`(`SimilarProductsResponse` 정확한 타입)로 되돌림, `HARDCODED_SIMILAR_PRODUCT_IDS` 제거
- [x] `normalizeSimilarProducts`의 상품 187 특례(`HARDCODED_SIMILAR_PRODUCTS_FOR_187`, 93건) 제거
- [x] `npm run type-check`, `npm run lint` 통과
- [ ] 로컬에서 AI 가격 추천/검색 필터/상품 상세 시세/등록 품질 검증/AI 모델컷/유사 상품 추천/유사 상품 가격대 7곳 직접 확인(개발 서버 미기동 — 사용자 확인 필요)
- [ ] "유사 상품" 하드코딩 — 사용자 요청 문구가 잘려서 범위 미확정(HARDCODED_SIMILAR_PRODUCT_IDS인지 id=187 목록인지 확인 필요)
