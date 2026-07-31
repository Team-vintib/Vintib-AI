# S15P11A108-403 PROD-008 상품 목록 껍데기 화면 계획

## 배경/목표

회원과 비회원이 상시 판매·경매 상품을 한 화면에서 탐색할 수 있는 PROD-008 상품 목록
껍데기 화면을 구현한다. 이번 작업은 Figma 프로토타입의 레이아웃과 화면 내 표시 상태를
재현하며, 실제 목록 API·필터링·찜·상세 이동 로직은 후속 작업으로 남긴다.

## 확인한 기준

- Jira 스토리 `S15P11A108-403`의 범위는 `[PROD-008] 상품 목록 껍데기 화면 구현`이다.
- 기능 정의서상 PROD-008은 회원이 상품 목록을 조회하는 필수 기능이며, 상시 판매와
  경매 여부에 관계없이 상품을 모두 노출한다.
- 권한 문서상 비회원도 상품 목록과 상세를 조회할 수 있으므로 `/products` route에는
  인증 가드를 적용하지 않는다.
- Figma 배포 프로토타입의 상품 목록은 공통 탐색/검색 영역 아래에 상품 제목,
  카테고리·상태 필터, 판매 방식 탭, 총 개수·정렬, 상품 카드 그리드와 페이지네이션으로
  구성된다.
- 카테고리는 아우터·상의·하의·원피스·신발·액세서리, 상태는 S·A·B·C급을 표시한다.
- 판매 방식 탭은 전체·즉시 구매·경매 예정, 정렬은 최신순·가격 낮은순·가격 높은순을
  표시한다.
- 상품 카드는 4:5 이미지, 상태 등급, 찜 버튼, 브랜드, 상품명, 가격과 상시/경매 배지를
  표시한다.
- 현재 `develop-FE`에는 `/products` 상수만 있고 route와 상품 도메인 구현은 없다.
- 아직 병합되지 않은 HOME 작업 브랜치가 `GlobalNavigation`과 `DefaultLayout` 확장을
  담당하고 있으므로 이번 브랜치에서는 공통 탐색 컴포넌트를 중복 생성·수정하지 않는다.

## 작업 내용

- `domains/product` 안에 `/products`에 연결되는 상품 목록 View를 만든다.
- Figma 상품 목록의 검색 영역을 상품 View 안에 구성하되, 공통 탐색 컴포넌트로
  섣불리 이동하지 않는다.
- 사이드 필터, 판매 방식 탭, 정렬 영역, 상품 카드 그리드와 페이지네이션을 상품 도메인
  컴포넌트로 분리한다.
- 화면 확인용 상품 목록은 실제 API 응답 형태를 고려한 타입과 mock 상수로 분리하며,
  임시 데이터임을 코드와 문서에서 명확히 한다.
- 외부 이미지 URL에 의존하지 않도록 화면 확인용 mock 상품 이미지를 저장소 내부
  자산으로 둔다.
- 컨트롤은 의미에 맞는 `button`, `input`, `select` 요소와 접근 가능한 label을 사용한다.
- 디자인 토큰과 기존 `DefaultLayout`을 사용하고 1440px desktop first로 구현하되,
  1280px에서도 주요 콘텐츠가 깨지지 않도록 카드 열 수와 간격을 조정한다.
- PROD-008 화면 요구사항, 화면 목록, 라우트/구조/구현 상태 문서를 함께 갱신한다.

## 생성·수정할 파일

- 새 파일: `FE/src/domains/product/pages/ProductListView.vue`
- 새 파일: `FE/src/domains/product/components/ProductFilterPanel.vue`
- 새 파일: `FE/src/domains/product/components/ProductCard.vue`
- 새 파일: `FE/src/domains/product/types/productList.types.ts`
- 새 파일: `FE/src/domains/product/constants/productListMockData.ts`
- 새 파일: `FE/src/assets/images/products/mock-*.svg`
- 수정: `FE/src/router/routes.ts`
- 수정: `FE/src/shared/layouts/DefaultLayout.vue`
- 새 파일: `FE/docs/frontend/screens/PROD-008/requirements.md`
- 수정: `FE/docs/frontend/screens/screen-inventory.md`
- 수정: `FE/docs/frontend/flows/route-map.md`
- 수정: `FE/docs/frontend/api/api-index.md`
- 수정: `FE/docs/frontend/decisions/open-questions.md`
- 수정: `FE/docs/frontend/implementation/current-structure.md`
- 수정: `FE/docs/frontend/implementation/status.md`

## 구현 목록

- [x] `/products` 공개 route 등록
- [x] PROD-008 검색, 페이지 제목과 기본 레이아웃 구현
- [x] 카테고리·상품 상태 사이드 필터 껍데기 구현
- [x] 전체·즉시 구매·경매 예정 탭과 정렬 UI 구현
- [x] 타입 기반 mock 상품 카드 그리드 구현
- [x] 상품 카드의 4:5 이미지, 등급·판매 방식·찜 표시 구현
- [x] 페이지네이션 껍데기 구현
- [x] 키보드 focus, label, aria-label과 이미지 alt 적용
- [x] 기존 DefaultLayout의 중앙 콘텐츠 폭과 반응형 바깥 여백 보완
- [x] 1440px·1280px·1024px 화면 레이아웃 검증
- [x] PROD-008 요구사항·구조·상태 문서 갱신
- [x] ESLint, type-check와 build 검증
- [x] 사용자 수동 검증

## 검증 시나리오

1. 비로그인 상태에서도 `/products`에 직접 접근할 수 있다.
2. Figma 기준 필터, 판매 방식 탭, 정렬, 카드 그리드와 페이지네이션이 표시된다.
3. 상시 판매와 경매 예정 상품이 같은 목록에 함께 노출되고 표시 방식이 구분된다.
4. 상품 이미지 비율, 찜 버튼 위치와 카드 정보 순서가 디자인 규칙을 따른다.
5. checkbox, 탭, select와 pagination을 키보드로 탐색할 수 있고 focus가 보인다.
6. 1440px과 1280px에서 가로 스크롤이나 카드 겹침이 발생하지 않는다.
7. 기존 인증·온보딩·사업자 route에 회귀가 없다.
8. ESLint, type-check와 build가 통과한다.

## 확인이 필요한 미결정 사항

1. 실제 상품 목록 endpoint, pagination envelope, 필터·정렬 query 규격은 미확정이다.
2. PROD-008 상품 카드 선택 시 이동할 PROD-006 상세 화면은 아직 미구현이다.
3. 찜 API와 비회원 찜 버튼 동작 정책은 미확정이다.
4. HOME 작업의 공통 탐색 컴포넌트 병합 시점에 따라 최종 통합 화면 검증이 필요하다.

## 범위 제외

- 실제 상품 목록 API 호출과 Loading·Empty·Error 상태
- 필터·정렬·페이지네이션의 데이터 처리 및 URL query 동기화
- 찜 등록·해제와 로그인 유도
- 상품 상세 화면 구현 및 카드 선택 이동
- 공통 `GlobalNavigation` 신규 구현 또는 HOME 작업 코드 수정
- BE·AI 코드와 API 계약 변경

## Git 작업 단위

- 브랜치: `feat/211-product-list`
- 커밋: `[S15P11A108-403] feat: 상품 목록 껍데기 화면 구현`
- 자동 검증과 사용자 수동 검증 후 로컬 커밋까지만 진행하며 push는 사용자가 직접 한다.
- MR 제목: `[PROD] 상품 목록 껍데기 화면 구현`
- MR 대상: `develop-FE`

## 후속 개선: 실사 이미지와 가격 필터

### 배경/목표

기존 MR에서 구현한 PROD-008 상품 목록의 일러스트형 mock SVG를 실제 쇼핑몰 상품 사진처럼
보이는 로컬 이미지 자산으로 교체한다. 요구 문서에 명시된 최소·최대 가격 입력을 추가하고,
입력한 가격 범위에 맞는 mock 상품만 실제로 표시되도록 개선한다.

### 작업 내용

- 외부 URL 만료나 CORS에 영향을 받지 않도록 로컬 포토리얼 상품 이미지를 사용한다.
- 데님 재킷, 니트, 트렌치코트, 시계, 가죽 가방, 스니커즈의 실사형 이미지를 상품 카드의
  4:5 영역에 맞춰 제공한다.
- 상품 필터에 선택 입력인 최소 가격과 최대 가격을 추가한다.
- 최소 가격과 최대 가격은 0 이상의 숫자만 허용한다.
- 두 값이 모두 입력됐을 때 최소 가격이 최대 가격보다 크면 오류 문구를 표시하고 기존
  적용 조건을 유지한다.
- 유효한 가격 조건을 적용하면 경계값을 포함해 mock 상품 목록을 필터링하고 결과 개수를
  갱신한다.
- 가격 범위에 해당하는 상품이 없으면 필터 결과 없음 상태와 초기화 동작을 제공한다.
- 기존 카테고리·상태 필터, 검색, 페이지네이션의 서버 조회나 URL query 연동은 이번
  범위에 포함하지 않는다.

### 수정할 파일

- 수정: `FE/src/domains/product/pages/ProductListView.vue`
- 수정: `FE/src/domains/product/components/ProductFilterPanel.vue`
- 수정: `FE/src/domains/product/constants/productListMockData.ts`
- 교체: `FE/src/assets/images/products/mock-*.svg`
- 추가: `FE/src/assets/images/products/product-*.webp`
- 수정: `FE/docs/frontend/screens/PROD-008/requirements.md`
- 수정: `FE/docs/frontend/implementation/current-structure.md`
- 수정: `FE/docs/frontend/implementation/status.md`

### 구현 목록

- [x] 상품 여섯 개의 일러스트형 SVG를 실사형 로컬 이미지로 교체
- [x] 최소·최대 가격 입력과 단위 표시 구현
- [x] 가격 범위 유효성 검사와 접근 가능한 오류 안내 구현
- [x] 적용된 가격 범위에 따른 상품 목록·결과 개수 갱신
- [x] 가격 필터 결과 없음과 초기화 상태 구현
- [x] PROD-008 요구사항·구조·구현 상태 문서 갱신
- [x] Prettier, ESLint, type-check, build 검증
- [x] `/products`에서 가격 필터와 반응형 화면 수동 검증

### 검증 시나리오

1. 가격을 입력하지 않고 적용하면 상품 여섯 개가 모두 표시된다.
2. 최소 가격만 입력하면 해당 금액 이상의 상품만 표시된다.
3. 최대 가격만 입력하면 해당 금액 이하의 상품만 표시된다.
4. 최소·최대 가격을 함께 입력하면 경계값을 포함한 범위의 상품만 표시된다.
5. 최소 가격이 최대 가격보다 크면 오류가 표시되고 목록 조건은 바뀌지 않는다.
6. 결과가 없으면 빈 상태가 표시되고 초기화하면 전체 목록으로 돌아온다.
7. 모든 상품 카드에 실사형 로컬 이미지가 표시되며 이미지 비율이 깨지지 않는다.
8. 1440px·1280px·1024px에서 가격 입력과 상품 목록이 겹치지 않는다.

### Git 및 MR 작업 단위

- 브랜치: `feat/211-product-list`
- 커밋 1: `[S15P11A108-403] fix: 상품 목록 이미지를 실사 자산으로 교체`
- 커밋 2: `[S15P11A108-403] feat: 상품 목록 가격 필터 기능 추가`
- Codex는 add·commit·push를 수행하지 않고 사용자가 직접 진행한다.
- MR 제목: `[PROD] 상품 목록 이미지 및 가격 검색 개선`
- MR 대상: `develop-FE`
- MR은 리뷰어 2명 이상 승인 후 Merge 방식으로 병합하고 원격 작업 브랜치를 삭제한다.
- Jira 상태 변경은 진행하지 않는다.
