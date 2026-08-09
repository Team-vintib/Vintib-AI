# CH001 상품 등록 — AI 가격 추천 실연동 + matchKey 전달

## 배경/목표

`docs/requests/FE/042-pricing-matchkey-forwarding.md`의 1·2번 반영. SY041에서 마련해둔 mock
스캐폴딩(`estimateRegistrationPrice`, `AI_PRICE_GRADE_SCORES`, `aiGatewayApi.ts#pollAiJob`)을
실제 BE 트리거(044, `POST /products/price-estimates`)로 연결하고, 폴링 결과의
`product_match_key`를 등록 제출 시 `PATCH /products/{id}`에 실어 보낸다. 상세 페이지의
"동일 상품 시세" 표시(042의 3번)는 이번 범위 밖.

## 작업 내용

1. **`productAiApi.ts` 실연동**: `ProductAiPriceEstimateInput`을 BE `PriceEstimateRequest`
   계약대로 재정의(`productId?: number`, `categoryId?: number`, `brand?: string`,
   `conditionScore: number`, `conditionGrade: 'S'|'A'|'B'|'C'`). `estimateRegistrationPrice`가
   `VITE_PRODUCT_AI_ENABLED=true`일 때 `POST /products/price-estimates`(BE, `http` 인스턴스)로
   `jobId`를 받고, 기존 `pollAiJob<PricingResult>`(`aiGatewayApi.ts`, AI 게이트웨이 직접 폴링)로
   완료까지 기다린다. AI 응답은 snake_case(`price_range.mid`, `comps_used`,
   `product_match_key` 등) — 기존 `ProductAiPriceEstimate` 형태로 매핑하고, `product_match_key`는
   별도로 함께 반환한다.
2. **`ProductRegistrationPage.vue` 트리거 입력값 채우기**: `triggerAiPriceRecommendation`이
   넘기는 input을 실값으로 — `productId: draft.draftProductId`(pricing 스텝은 condition 스텝
   이후라 이미 생성돼 있음), `categoryId: Number(draft.categoryId)`(이미 BE 카테고리 leaf id
   문자열이라 그대로 변환하면 됨 — `categoryMajorId`는 안 씀), `brand: draft.brand`,
   `conditionScore: AI_PRICE_GRADE_SCORES[grade]`(등급별 대표점수, SY041에서 이미 준비된 표),
   `conditionGrade: grade`. 4개 등급 호출 중 아무 응답에서나 `product_match_key`를 받아
   draft에 저장(등급과 무관하게 동일 값).
3. **draft에 `priceMatchKey: string | null` 필드 추가**(`productRegistration.types.ts`).
4. **`productApi.ts`의 브랜드 필드 정리(선행 버그 수정)**: `ProductCreateRequest`/
   `ProductUpdateRequest`가 아직 `brandId: number | null`(구 FK 방식)을 쓰는데, BE는 이미
   `brand: string`(자유 텍스트, c07ed500)로 바뀐 지 오래라 등록 시 브랜드가 제대로 저장되지
   않고 있었다. `brandId`/`findBrandId` 룩업을 제거하고 `brand: draft.brand.trim() || null`을
   그대로 보내도록 고친다(create/update 둘 다). `ProductUpdateRequest`에 `matchKey: string | null`
   필드를 추가하고, `submitProduct`의 PATCH 바디에 `matchKey: draft.priceMatchKey`를 포함한다.
5. **환경변수**: `VITE_PRODUCT_AI_ENABLED=true`로 켜야 실제 호출이 발생한다(미설정 시 계속
   mock) — 배포 환경 설정은 사용자 몫.

## 구현 목록

- [x] `productAiApi.ts`: `ProductAiPriceEstimateInput` 재정의, `estimateRegistrationPrice` 실연동
      (트리거 POST + `pollAiJob` 폴링 + 응답 매핑), `product_match_key` 반환값 추가
- [x] `ProductRegistrationPage.vue`: 트리거 input 실값 구성, `product_match_key` → draft 저장
- [x] `productRegistration.types.ts`: `priceMatchKey: string | null` 필드 추가
- [x] `productApi.ts`: `ProductCreateRequest`/`ProductUpdateRequest`의 `brandId`→`brand`,
      `findBrandId` 제거, `ProductUpdateRequest`에 `matchKey` 추가, `submitProduct` PATCH에
      `matchKey` 포함
- [ ] `npm run type-check`, `npm run lint` 통과 — **이 환경에 npm/node가 없어 직접 실행 못 함,
      사용자가 로컬에서 확인 필요**
- [x] `docs/requests/FE/042-pricing-matchkey-forwarding.md`에서 반영 완료된 1·2번 제거, 3번(상세
      페이지 표시, 범위 밖)만 남김

## 확인이 필요한 미결정 사항

- `AI_PRICE_GRADE_SCORES`(S95/A82/B68/C50)는 여전히 SY041 시점의 잠정치다 — 실측 없이 그대로
  채택한다.
- 042의 3번(상품 상세 "동일 상품 시세" 표시)은 별도 계획으로 다룬다.
