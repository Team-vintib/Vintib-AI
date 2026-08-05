# 상품 등록 AI 착용컷 설정 필드 추가 요청

## 요청한 파트 / 대상 파트

- 요청한 파트: FE
- 대상 파트: BE

## 배경/이유

상품 등록 기본 정보 단계에 `AI 착용컷 설정` UI가 추가되었습니다. FE draft에는 `aiModelEnabled`, `aiModelGender` 상태가 있지만 현재 BE `POST /api/products`의 `ProductCreateRequest`에는 해당 필드가 없어 등록 시 설정값을 저장할 수 없습니다.

## 요청 내용

- `POST /api/products`에서 AI 착용컷 설정값 저장 가능 여부를 검토해 주세요.
- 제안 필드:
  - `aiModelEnabled: boolean`
  - `aiModelGender: "FEMALE" | "MALE" | null`
- `aiModelEnabled=false`인 경우 `aiModelGender`는 null 허용이면 됩니다.
- `aiModelEnabled=true`인 경우 FE에서는 성별 선택을 필수 검증하고 있습니다.
- 상품 상세 조회 응답에서도 설정값을 확인할 수 있어야 하면 `GET /api/products/{id}` 응답 필드 추가도 함께 검토해 주세요.

## 참고

- FE 파일: `FE/src/domains/product/pages/ProductRegistrationPage.vue`
- FE draft 타입: `FE/src/domains/product/types/productRegistration.types.ts`
- 현재 BE 생성 DTO: `BE/src/main/java/com/ssafy/backend/product/dto/request/ProductCreateRequest.java`
