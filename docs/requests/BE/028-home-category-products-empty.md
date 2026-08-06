# 028 홈 카테고리별 상품 섹션이 항상 0건으로 내려옴

> **2026-08-05 갱신**: FE는 이제 이 필드를 쓰지 않고 상품 목록 페이지와 같은 방식
> (`GET /categories` + `GET /api/products?categoryIds=...`)으로 홈 카테고리별 상품 탭을 직접
> 구성하도록 바꿔서, 더 이상 FE가 이 필드에 막혀 있지는 않습니다. 다만 `/home` 응답의
> `categoryProductSections`는 히어로 배너 콜라주 이미지 후보로도 쓰이고 있어(`HomeHeroCarousel.vue`),
> 항상 빈 배열이면 그 콜라주 이미지 다양성이 줄어듭니다. 급하지 않지만 아래 버그 자체는 유효하니
> 여유 있을 때 반영해 주세요.

- 요청자 파트: FE
- 대상 파트: BE

## 배경/이유

홈 화면 "카테고리별 상품" 탭 섹션에 상품이 하나도 뜨지 않는다는 사용자 리포트를 조사했다.
`HomeService.categoryProductSections()`(`BE/src/main/java/com/ssafy/backend/home/service/HomeService.java`)
코드를 보면 원인이 두 가지 겹쳐 있다.

1. **"루트" 정의가 의도와 다르다.** 코드는 `parentId == null`인 카테고리를 루트로 삼는데,
   시드 데이터 기준 이건 성별 카테고리(남성/여성/공용, depth=1) 3개뿐이다. 반면
   `CategoryProductSectionResponse`의 Javadoc은 "탭 구성은 카테고리 마스터의 최상위
   카테고리를 따른다 — 아우터·상의·하의·신발·가방·액세서리 6개"라고 명시하고 있다. 즉 의도한
   "최상위"는 depth=2(성별 아래의 옷 종류)인데, 코드는 depth=1(성별)을 쓰고 있다.
2. **카테고리 id 수집이 한 단계만 내려간다.** `categoryIdsByRoot`를 채우는 루프가
   `category.getParentId()`가 루트 id와 "직접" 일치하는 카테고리만 추가한다. 루트가
   depth=1(성별)이라면 이 루프는 depth=2(아우터 등)까지만 모으고, 실제 상품이 걸려 있는
   depth=3(자켓/티셔츠 등 소분류)는 전혀 포함되지 않는다. 그 결과
   `findByCategoryIdInAndSaleStatusOrderByCreatedAtDesc` 조회의 `categoryIds`에 상품이 실제로
   속한 카테고리 id가 하나도 없어서, ON_SALE 상품이 아무리 많아도 이 섹션은 항상 빈 배열이
   된다.

## 요청 내용

- Javadoc이 말하는 의도(депth=2 카테고리 6개를 탭으로 사용)에 맞게 루트 선정 기준을 고쳐
  주세요.
- 각 루트에 속하는 카테고리 id를 모을 때, 직계 자식뿐 아니라 그 아래 소분류(depth=3)까지
  재귀적으로 포함하도록 고쳐 주세요(실제 상품은 소분류에 걸린다).
- 위 두 가지를 고치면 FE(`FE/src/domains/home/api/homeViewApi.ts`)의 소분류→중분류 매핑
  로직은 그대로 맞아떨어질 것으로 예상되어 FE 쪽 추가 변경은 필요 없을 것으로 보인다(응답의
  `categoryName`이 중분류 6개 중 하나로 오는지만 확인 부탁).

## 관련 자료

- `BE/src/main/java/com/ssafy/backend/home/service/HomeService.java` `categoryProductSections()`,
  `toSection()`
- `BE/src/main/java/com/ssafy/backend/home/dto/response/CategoryProductSectionResponse.java`
  (Javadoc에 의도한 탭 목록 명시)
- `BE/src/main/resources/db/seed.sql` (카테고리 depth 구조: 1=성별, 2=옷 종류, 3=소분류)
- `docs/plans/FE/SY034-home-product-card-revamp.md` (이번 홈 개선 작업의 일부로 발견)
