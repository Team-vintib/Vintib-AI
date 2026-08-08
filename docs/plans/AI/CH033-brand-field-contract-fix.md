# CH033 브랜드 필드 계약 수정 — brandId(FK) → brand(텍스트) 반영 + 경고 로그

## 배경/목표

BE가 2026-08-08 `c07ed500`(`S15P11A108-327`)에서 상품 브랜드를 FK(`brandId: Long`)에서
자유 텍스트(`brand: String`)로 바꿨는데, `AI/app/shared/be_client.py`는 여전히
`body.get("brandId")`로 읽고 있어 항상 `None`을 반환하고 있었다(2026-08-09 발견).

`product_match.resolve_brand_id()`가 원래 "brand_id가 거의 항상 비어 있다"는 전제로 제목
텍스트 검색 폴백을 이미 갖고 있어서 완전히 실패하진 않았지만(제목에 브랜드명이 있으면
찾아짐), 판매자가 브랜드 칸에만 입력하고 제목엔 안 쓴 경우는 브랜드를 못 찾아 매칭
정확도가 떨어진다. FE가 이제 브랜드를 텍스트로 제대로 저장하니(CH001 FE 세션에서 수정),
이 필드를 실제로 읽어서 쓰는 게 이득이다.

추가로, 같은 종류의 BE 계약 변경이 재발했을 때 바로 알아챌 수 있도록 `brand` 키 자체가
없을 때(값이 null인 것과 다르다) 경고 로그를 남긴다.

## 작업 내용

1. **`be_client.py`**: `BeProduct.brand_id: int | None` → `brand: str | None`로 필드명·타입
   교체, `body.get("brandId")` → `body.get("brand")`. `_warn_if_brand_field_missing()` 추가 —
   응답에 `"brand"` 키 자체가 없으면(값 null이 아니라 키 부재) `logging.warning`. 값이
   null인 건 판매자가 브랜드를 안 적은 정상 케이스라 경고하지 않는다.
2. **`product_match.resolve_brand_id()`**: 파라미터를 `brand_id: int | None` →
   `brand_name: str | None`로 교체. `brand_name`(BE 필드, 신뢰도 높음) → `product_name`(제목,
   기존 폴백) 순서로 별칭 사전과 부분일치 검사한다. 둘 다 실패하면 `None`.
3. **`attribute_extraction.py`**: `AttributeExtractor.extract()`(양쪽 구현체)의 `brand_id`
   파라미터를 `brand_name`으로 교체. `LlmAttributeExtractor`는 BE `brand_name` → 제목 →
   LLM 자체 브랜드 추측 순으로 우선순위를 유지한다(BE 필드가 LLM 추측보다 신뢰도 높음).
4. **`comps.py`/`product_corpus.py`**: 호출부를 `brand_name=product.brand`/`item.brand`로
   갱신. `product_corpus.py`의 코퍼스 캐시 컬럼(`ProductCorpusItem.brand_id`)은 BE 원본이
   아니라 **추출기가 해석한 결과**(`extracted.brand_id`)를 저장하도록 `_upsert()` 시그니처에
   `brand_id` 파라미터를 추가한다 — 이 컬럼은 조회용이 아니라 디버깅용이라 실제로 매칭 키
   계산에 쓰인 값이어야 의미가 있다.
5. **테스트**: `test_be_client.py`(brand 필드 파싱 + 경고 로그 2건), 나머지 pricing/
   recommend 테스트의 `BeProduct(brand_id=...)` 생성자·`resolve_brand_id`/`extract()` 호출을
   새 시그니처로 갱신.

## 구현 목록

- [x] `be_client.py`: `BeProduct.brand`, `_warn_if_brand_field_missing()`, 두 fetch 함수 갱신
- [x] `product_match.resolve_brand_id()`: `brand_name` 파라미터, 2단계(brand_name→title) 검색
- [x] `attribute_extraction.py`: 양쪽 추출기 `extract()` 파라미터 갱신, LLM 우선순위 유지
- [x] `comps.py`/`product_corpus.py` 호출부 갱신, `_upsert()`가 해석된 brand_id 저장
- [x] 영향받는 테스트 전부 새 시그니처로 갱신 + 경고 로그 테스트 2건 추가
- [x] `ruff check .`, `black --check .`, `pytest -q` 전부 통과 확인

## 확인이 필요한 미결정 사항

- 코퍼스는 이미 예전(브랜드 항상 unknown 취급) 데이터로 채워져 있다 — 배포 후 재실행 필요
  (사용자가 이후 배포 시점에 직접 확인하기로 함, 이 계획 범위 밖).
