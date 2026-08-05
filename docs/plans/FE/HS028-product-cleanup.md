# HS028 — 상품 파트 정리 (목록 PROD-008 / 상세·검수 SALE-001)

## 배경/목표
님 파트인 상품 **목록·상세·검수** 최종 점검. mock·하드코딩 제거, 실 API(010) 필드 매핑, 계약값 정정. **등록(ProductRegistrationPage)은 KimSeoyeon 파트라 제외.**

## A. 목록 (PROD-008 · `feat/211-product-list` 🆕 에픽211)
- saleType 탭값 `DIRECT` → **`DIRECT_SALE`** (010 계약)
- 카테고리 필터 문자열코드(`outer`…) → **`categoryIds(number)`**, 카테고리 v2 반영
- 페이지네이션 이전/다음 버튼 배선(`hasNext`/`page`)
- 무의미 `filteredProducts` computed 정리, mock 코드값(`productListMockData`) 정리
- (N+1 이미지: `primaryImageUrl` 없을 때 상세 재호출 — 여력되면 개선)

## B. 상세·검수 (SALE-001 · `feat/212-fixed-price-purchase-ui` ♻️ 에픽212)
**실 API 매핑(하드코딩 제거)** — `ProductDetailDto`에 필드 추가 + `toProductDetailViewData` 매핑:
- `sellerFollowerCount` → `seller.followerCount` (현 `0`)
- `sellerProductCount` → `seller.productCount` (현 `0`)
- `linkedLive` (BE `{liveId,title,status,scheduledAt,startedAt,thumbnailUrl}` → FE `{id,title,startsAt,status,thumbnailUrl}` 변환) (현 `null`)
- `defects`(string[]) → `sellerDisclosedDefects`({title,description}) 변환 (현 `[]`)
- `measurements`(object) → 뷰데이터에 추가 + `ProductDetailInformation`의 하드코딩 실측 교체
- `sellerNickname` → 판매자명 (현 "Vintage Hunter" 하드코딩)

**제거(API 미제공 → 빈값/삭제)**:
- 생산시기·생산국가·사이즈 "(105)" placeholder
- `PRIVATE` 죽은 분기(003): `productDetail.types.ts`·`productApi.ts`·`ProductPurchaseSummary.vue`
- 죽은 mock: `ProductDetailMockScenario`/`getMockScenario`/mock 시나리오, `productDetailApi` scenario 무시 로직

**검수 이미지 캐러셀(task#6)**: 세로 스택 → 스와이프(넘겨보기). 필수 2개(앞·뒤). *단 images[].role(앞/뒤)은 BE 미제공(010) → 역할 구분은 BE 대기, 지금은 전체 이미지 캐러셀.*

**BE 대기(비워둠)**: `similarProducts`(→ 시세 그래프, `docs/requests/BE/016` 요청함, 수요일 데이터 시 자동 부활), `aiQualityAnalysis`.

## 구현 목록
- [ ] 목록: saleType/categoryIds/페이지네이션/mock값
- [ ] 상세 DTO+매핑: follower/product/linkedLive/defects/measurements/판매자명
- [ ] 상세 measurements → ProductDetailInformation 연결, 생산정보/사이즈 placeholder 제거
- [ ] 상세 PRIVATE 제거(003)
- [ ] 상세 죽은 mock 정리
- [ ] 상세 검수 이미지 캐러셀
- [ ] 로컬(5173) 확인

## 브랜치 / Jira
- 목록 → `feat/211-product-list` 🆕 · Jira **PROD-008 538**(부모 235)
- 상세·검수 → `feat/212-fixed-price-purchase-ui` ♻️ · Jira **SALE-001 539**(부모 117)
- BE 요청: `docs/requests/BE/016` (유사상품 가격분포)
