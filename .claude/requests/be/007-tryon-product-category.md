# 가상 시착 — 상품 카테고리를 AI가 판별 가능한 형태로 노출 요청

- **요청자 파트**: AI
- **대상 파트**: BE
- **관련 티켓**: `S15P11A108-210` 에픽 하위, `S15P11A108-504`
- **상태**: 요청

## 배경

가상 시착 워커가 마스킹할 의류 부위(`mask_type`: `upper`/`lower`)를 결정하려면 그 상품이
상의인지 하의인지 알아야 합니다. 지금은 이 값을 시착 요청자가 직접 골라서 넘겨야 하는데,
상품 자체에 이미 카테고리가 등록돼 있으니 AI가 그걸로 자동 판별하는 게 더 자연스럽습니다.

`BE/src/main/java/com/ssafy/backend/product/entity/Product.java`를 확인해보니
`categoryId`가 raw `Long` FK뿐이고, 카테고리 코드(문자열)를 돌려주는 API나 enum이 따로
없습니다. AI 쪽엔 이미 35종 소분류 taxonomy(`AI/validation/CLASS/product-info-check/
taxonomy.py`, BE 시드 데이터 기준으로 만들어둔 것)가 있지만, 이게 BE의 실제 `categoryId`
값과 연결할 방법이 없어서 지금은 그림의 떡입니다.

## 요청 내용

아래 둘 중 편하신 쪽으로 결정해 주시면 됩니다.

**옵션 A — `categoryId` -> 카테고리 코드 매핑을 조회 가능하게**: `GET /categories`(또는
비슷한) 엔드포인트가 `id`, `name`, `depth`, 가능하면 대분류 코드(OUTER/TOP/BOTTOM/SHOES/
BAG/ACCESSORY/DRESS_JUMPSUIT — AI taxonomy의 `MAJOR_CATEGORIES`와 동일한 집합) 정도를
내려주면, AI가 시작할 때 한 번 캐싱해서 `categoryId` -> 대분류를 자체적으로 매핑할 수
있습니다.

**옵션 B — 시착 요청 payload에 대분류를 직접 실어서 전달**: BE가 이미 `categoryId`로
대분류를 알고 있으니, AI 게이트웨이로 시착 job을 만들 때 `garment_type`(예:
`"OUTER"`/`"TOP"`/`"BOTTOM"` 등 소문자/대문자는 협의) 필드 하나를 같이 넘겨주는 방식도
가능합니다. 이쪽이 더 간단하면 이걸로 해주셔도 됩니다.

어느 쪽이든, AI가 원하는 최종 값은 "이 상품이 상의/하의/아우터/신발/가방/액세서리/원피스
중 뭔지"뿐입니다 — 소분류(35종) 세부까지는 지금 당장 필요 없습니다.

## 참고

- AI taxonomy 정본: `AI/validation/CLASS/product-info-check/taxonomy.py`
  (`MAJOR_CATEGORIES`)
- 시착 job payload 스키마: `AI/app/tryon/schemas.py`, `worker/tryon_worker_example.py`
- 겹치지 않는 별개 요청: `.claude/requests/be/004-garment-measurement-scan.md`(상품
  실측 사이즈), `.codex/requests/be/003-onboarding-tryon-profile-api.md`(고객 신체
  치수) — 이 문서는 카테고리 노출만 다룹니다.
