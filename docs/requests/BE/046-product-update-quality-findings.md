# 046 상품 부분 수정(PATCH)에 하자 검증 확정 결과가 빠져 있음

- 요청자 파트: FE
- 대상 파트: BE
- 우선순위: `SY043` 반영 이후로 실제 데이터 누락 발생 중 — 참고용 아님(2026-08-08 상향)

## 배경

`docs/plans/FE/SY043-product-registration-quality-real.md`로 AI 품질 검증을 실연동하면서, 상품 등록 흐름을 "'상태/하자' 스텝 진입 시 DRAFT 상품+이미지를 미리 만들고(`POST /products`), 최종 제출 때는 나머지 필드만 `PATCH /products/{id}`로 갱신"하는 구조로 바꿨습니다.

그런데 `ProductUpdateRequest`(PATCH)를 보니 `title`/`description`/`categoryId`/`brandId`/`conditionGrade`/`sizeLabel`/`color`/`material`/`measurements`/`defects`만 있고, `POST /products`(`ProductCreateRequest`)에 있는 `aiQualityFindings`(사용자가 "하자로 인정/제외" 확정한 AI 검수 결과)가 PATCH에는 없습니다.

## 영향

- `aiModelEnabled`/`aiModelGender`: 문제 없음 — '기본 정보' 스텝을 벗어날 때 이미 확정되므로 DRAFT 생성 시점의 `POST`에 실려 갑니다. PATCH가 다시 보낼 필요가 없어서 이 필드들은 이번 요청 대상이 아닙니다.
- `aiQualityFindings`: 사용자가 "하자로 인정/제외"를 확정하는 시점 자체가 DRAFT 생성 **이후**(검수 결과가 나온 뒤)라, 최종 제출(PATCH) 시점에만 값이 완성됩니다. 지금 PATCH에 이 필드가 없어서 **DRAFT를 먼저 만드는 상품(카테고리가 검수 지원 대상인 대부분의 상품)은 확정된 하자 판정이 BE로 아예 전달되지 않습니다.**

**2026-08-08 갱신**: `POST /products`는 이제 `aiQualityFindings`를 실제로 저장한다
(`docs/plans/BE/SY043-product-image-role-quality-findings.md` — `photoRole`/`description`/`box`만
저장, AI raw 스키마의 나머지 필드는 저장하지 않는다). 그래서 이 문서가 경고했던 "조용한 데이터
누락"이 지금 실제로 발생 중이다 — **DRAFT를 먼저 만들고 PATCH로 최종 제출하는 상품은 확정된
하자 판정이 저장되지 않는다.** 저장 형식(041 §6)은 정해졌으니 아래 요청만 남았다.

## 요청 내용

`ProductUpdateRequest`에 `aiQualityFindings`(`POST /products`와 같은 타입,
`List<AiQualityFindingRequest>`)를 추가해주세요. 저장 방식은 `POST`가 이미 쓰는 것과 동일하게
(`photoRole`/`description`/`box`만 저장) 반영하면 됩니다.

## 관련 자료

- `docs/plans/BE/SY043-product-image-role-quality-findings.md`(저장 범위 확정 —
  `photoRole`/`description`/`box`)
- `docs/plans/FE/SY043-product-registration-quality-real.md`
- `BE/src/main/java/com/ssafy/backend/product/dto/request/ProductUpdateRequest.java`
- `BE/src/main/java/com/ssafy/backend/product/dto/request/ProductCreateRequest.java`
