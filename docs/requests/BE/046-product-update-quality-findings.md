# 046 상품 부분 수정(PATCH)에 하자 검증 확정 결과가 빠져 있음

- 요청자 파트: FE
- 대상 파트: BE
- 우선순위: 참고용(현재 FE에서 회피 가능, 블로킹 아님)

## 배경

`docs/plans/FE/SY043-product-registration-quality-real.md`로 AI 품질 검증을 실연동하면서, 상품 등록 흐름을 "'상태/하자' 스텝 진입 시 DRAFT 상품+이미지를 미리 만들고(`POST /products`), 최종 제출 때는 나머지 필드만 `PATCH /products/{id}`로 갱신"하는 구조로 바꿨습니다.

그런데 `ProductUpdateRequest`(PATCH)를 보니 `title`/`description`/`categoryId`/`brandId`/`conditionGrade`/`sizeLabel`/`color`/`material`/`measurements`/`defects`만 있고, `POST /products`(`ProductCreateRequest`)에 있는 `aiQualityFindings`(사용자가 "하자로 인정/제외" 확정한 AI 검수 결과)가 PATCH에는 없습니다.

## 영향

- `aiModelEnabled`/`aiModelGender`: 문제 없음 — '기본 정보' 스텝을 벗어날 때 이미 확정되므로 DRAFT 생성 시점의 `POST`에 실려 갑니다. PATCH가 다시 보낼 필요가 없어서 이 필드들은 이번 요청 대상이 아닙니다.
- `aiQualityFindings`: 사용자가 "하자로 인정/제외"를 확정하는 시점 자체가 DRAFT 생성 **이후**(검수 결과가 나온 뒤)라, 최종 제출(PATCH) 시점에만 값이 완성됩니다. 지금 PATCH에 이 필드가 없어서 **DRAFT를 먼저 만드는 상품(카테고리가 검수 지원 대상인 대부분의 상품)은 확정된 하자 판정이 BE로 아예 전달되지 않습니다.**

참고로 `aiQualityFindings`는 BE 코드 전체에서 아직 어디서도 저장 처리가 안 되고 있어서(POST로 보내도 무시됨, 041 §6 교차 확인 미해결) 지금 당장 사용자에게 보이는 회귀는 아닙니다 — 다만 나중에 041 §6이 정리돼 BE가 이 필드를 실제로 저장하기 시작하면, DRAFT 우선 생성 경로의 상품만 조용히 이 데이터가 누락되는 문제가 생깁니다.

## 요청 내용

`ProductUpdateRequest`에 `aiQualityFindings`(POST와 같은 타입)를 추가해주시면 좋겠습니다. 저장 방식은 041 §6(원본 전체 vs `key` 목록)이 정해지는 대로 POST/PATCH 동일하게 반영하면 될 것 같습니다.

## 관련 자료

- `docs/requests/BE/041-quality-inspection-integration.md` §6(저장 범위 미확정)
- `docs/plans/FE/SY043-product-registration-quality-real.md`
- `BE/src/main/java/com/ssafy/backend/product/dto/request/ProductUpdateRequest.java`
- `BE/src/main/java/com/ssafy/backend/product/dto/request/ProductCreateRequest.java`
