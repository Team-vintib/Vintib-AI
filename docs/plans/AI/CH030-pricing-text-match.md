# CH030 시세 조회 — 이미지 임베딩 없는 "동일 상품" 텍스트 매칭

## 배경 / 목표

시세 조회(`AI/app/pricing/`)의 주 경로가 외부 GMS LLM 웹검색(`llm_web_search`, 호출마다
과금)이라 내부 조회로 바꾸려 한다. CH024가 이미 만든 `internal` 백엔드는 **이미지 임베딩**
(CLIP)으로 후보를 찾는데, 이번엔 **상품명·브랜드·카테고리 텍스트만으로 "동일 상품"을
판정**하는 세 번째 접근을 만든다 — 후보 검색만 새로 짜고, CH024가 만든 하단 파이프라인
(hedge 필터·BE 조회·CompItem 조립)은 재사용한다.

추가로, 상품 등록 마지막 단계(가격 책정)에서 AI가 계산한 "동일 상품 판정 키"를 상품 저장
시 DB에 같이 넣어서, **구매자 화면은 RAG/AI 호출 없이 순수 DB 조회**로 동일 상품 시세를
보여주는 것도 목표다. 이는 `docs/requests/BE/025-product-same-price-chart.md`(FE→BE,
미답변)와 같은 요구라, 이번 계획의 산출물로 025를 대체한다.

## 조사로 확인된 것

- `GET /api/brands`(21개 브랜드 name/nameEn)·`GET /api/products`(categoryIds 등 필터,
  페이지네이션, DRAFT 제외)가 이미 공개 API로 있다 — 새 BE 검색 API 없이 이 둘로 AI가 자체
  코퍼스를 만들 수 있다.
- `brand_id`가 실데이터 903건 중 0건, `title`은 자유텍스트뿐(모델 전용 필드 없음) — 브랜드는
  `brand_id` 있으면 그걸, 없으면 title에서 브랜드 별칭 사전으로 파싱해야 한다.
- 완료거래가(`orders.order_price`/`auction.final_price`)를 노출하는 API가 없다 — `GET
  /api/products`의 `price`는 호가일 뿐이다. AI가 자체 해결 불가, BE 확장 필요.
- `product` 테이블 변경은 nullable 컬럼 하나(`match_key`)만 추가하면 된다 — 완료거래가
  자체는 `orders`/`auction` 테이블에 이미 있다.
- 완료거래 실데이터가 사실상 0건(직접판매 72건은 테스트 픽스처)이라, 호가(ON_SALE)+완료거래
  둘 다 태그로 구분해 포함한다(완료거래만 쓰면 항상 "데이터 없음").

## 작업 내용

1. **매칭 알고리즘** (`app/pricing/product_match.py`, 신규, 순수 함수): 제목 정규화, 브랜드
   별칭 사전(`GET /api/brands` 캐시)으로 브랜드 귀속, `brand_id + 정규화 토큰`으로 1차
   match_key, 표본 부족 시 `brand_id + category`로 완화한 2차 키.
2. **후보 코퍼스** (`app/pricing/product_corpus.py`, 신규): `GET /api/products?categoryIds=...`를
   카테고리별로 pull해 AI 자체 코퍼스로 캐시(`internal_corpus.py`와 같은 패턴이나 임베딩 없이
   텍스트/정형필드만). LLM 재랭킹은 opt-in으로 분리(GMS 호출이라 `AI/CLAUDE.md` 하드 룰 대상,
   커밋 기본값은 항상 off).
3. **`comps.py` 신규 백엔드**: `key="internal_text"` 추가, 후보 검색만 새로 짜고
   `InternalCompsSource`가 쓰는 hedge 필터·BE 조회·CompItem 조립은 재사용.
4. **`hedge.py` 조정**: `filter_by_sale_type`을 "DIRECT_SALE만 허용"에서 "호가·완료거래 모두
   허용 + 태그 유지"로 변경.
5. **`schemas.py`**: `PricingResult`에 `product_match_key: str | None` 추가 — BE가 상품 저장
   시 그대로 반영할 값.
6. **`registry.py`**: 새 백엔드 키 등록, 커밋 기본값은 여전히 `mock`.
7. **BE 요청 문서** (`docs/requests/BE/`, 025 대체): `GET /api/products` 응답에
   `finalPrice`/`priceKind` 추가, `product.match_key` 컬럼 추가, `POST /pricing/estimates`의
   `product_match_key`를 상품 저장 시 반영, 구매자 화면은 `match_key` 기준 DB 쿼리로 구현.

## 구현 목록

- [ ] `app/pricing/product_match.py` + `test/pricing/test_product_match.py`
- [ ] `app/pricing/product_corpus.py` (BE 목록 API bulk pull 캐시)
- [ ] `comps.py`에 `internal_text` 백엔드 배선
- [ ] `hedge.py` sale_type 필터 → 호가/완료거래 태그 구분으로 조정
- [ ] `schemas.py`에 `product_match_key` 필드 추가
- [ ] `registry.py`에 백엔드 등록(기본값 `mock` 유지)
- [ ] `docs/requests/BE/` 신규 문서 작성(025 대체 — 025는 BE 반영 확인 후 삭제)

## 확인이 필요한 미결정 사항

- LLM 재랭킹 사용 여부 — 순수 텍스트 매칭만으로 1차 구현은 가능하다. 켜려면 GMS 호출이라
  하드 룰 대상, 사용자만 켤 수 있다.
- 기존 상품 903건의 `match_key` 소급 계산(백필)은 이번 범위 밖.
- 1차 키(정확 매칭) 판정 임계치(완전 일치 vs 토큰 overlap 비율)는 실측 전 임의값 — 다른
  pricing 계수들과 같은 성격의 부채로 남긴다.
