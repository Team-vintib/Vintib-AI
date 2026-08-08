# SY044 AI 가격 추천 경량 트리거 (PROD-011/PROD-012)

## 배경/목표

`docs/requests/BE/044-pricing-estimate-trigger.md`. AI `POST /pricing/estimates`(가격 범위
min/mid/max + 근거 문장, mock 시세로도 지금 연동 가능)가 컨테이너 내부망에만 열려 있어 FE가
직접 못 부른다. 실제 상품 생성 여부와 무관하게 호출 가능한 트리거 엔드포인트 하나만 있으면
등록 화면 "AI 가격 추천" 섹션(히스토그램 + 등급별 추천가)을 지금 당장 채울 수 있다.

`docs/requests/BE/043-registration-price-chart-source.md`(우리 플랫폼 자체 통계 기반 대안)는
같은 화면을 겨냥하지만 실사용 데이터가 사실상 0건이라 당장 불가능 — 문서 자체가 "044만으로
당분간 충분하다"고 명시해 이번 작업으로 함께 해소한다.

## 작업 내용

- **엔드포인트**: `POST /products/price-estimates`. 상품 리소스에 종속되지 않는 트리거라
  `{id}` 없이 컬렉션 경로로 둔다. 로그인 필요(`SecurityConfig` 기본 `anyRequest().authenticated()`
  그대로 적용 — 별도 permitAll 추가 안 함).
- **요청**: `PriceEstimateRequest(productName, categoryId?, brand?, conditionScore, conditionGrade,
  productId?)`. `conditionGrade`는 AI가 받는 `S`/`A`/`B`/`C` 4종만 `@Pattern`으로 허용한다.
  `productId`가 없으면(대부분의 경우) BE가 임시값(`1L`)을 채운다 — AI `PricingRequest.product_id`가
  `ge=1` 제약이라 044가 제안한 `0`은 실제로는 거부된다.
- **카테고리 매핑**: 기존 하자 검수(`ProductImageService`)가 갖고 있던 leaf 카테고리 →
  AI `GarmentCategory`(6종) 매핑을 `GarmentCategoryMapper` 컴포넌트로 추출해 공유한다. 대응값이
  없으면(신발/가방 등) `category=null`로 보낸다 — AI는 카테고리 없이도 동작한다.
- **AI 클라이언트**: `AiClient.createPricingEstimateJob()` 추가, `POST /pricing/estimates` 그대로
  호출하고 `job_id`만 꺼낸다. 응답에 `product_id`(에코) 필드가 더 있어 기존 `AiJobCreatedResponse`에
  `@JsonIgnoreProperties(ignoreUnknown = true)`를 추가해 재사용한다.
- **결과 폴링은 이번 범위가 아니다** — FE가 `GET /ai/jobs/{jobId}`를 외부 경로로 직접 폴링한다
  (044 §4, 품질 검증과 동일 패턴). BE는 job 접수만 책임진다.
- **에러 처리**: AI가 동시 처리 상한(2건)을 넘겨 503을 내면 그대로 전파한다(재시도 없음) — FE가
  등급별로 나눠 호출하는 쪽에서 이미 그 상한을 감안한다(044 §2).

## 구현 목록

- [x] `GarmentCategoryMapper` 추출(`ProductImageService`의 기존 매핑 재사용, 하자 검수 쪽도
      이 컴포넌트로 리팩터)
- [x] `PricingEstimateJobRequest`(AI 클라이언트 DTO), `AiClient.createPricingEstimateJob()`
- [x] `AiJobCreatedResponse`에 `ignoreUnknown = true` 추가(응답의 `product_id` 에코 필드 대응)
- [x] `PriceEstimateRequest`/`PriceEstimateJobResponse`, `PriceEstimateService`
- [x] `ProductController`에 `POST /products/price-estimates` 추가 + Swagger
- [x] 테스트: `GarmentCategoryMapperTest`(매핑/미매핑/null), `PriceEstimateServiceTest`
      (productId 없을 때 placeholder, 있을 때 에코)
- [x] `docs/APIs.md` 반영, `043`/`044` 요청 문서 삭제

## 확인이 필요한 미결정 사항

- `PLACEHOLDER_PRODUCT_ID=1L`은 AI가 에코만 하고 실사용하지 않는 값이라 실제 상품 id=1과
  충돌해도 무해하다는 전제다 — AI 쪽이 이 값을 어딘가에서 실제로 참조하기 시작하면 재검토 필요.
- 043이 요청한 "우리 플랫폼 자체 통계" 기반 히스토그램은 이번 작업으로 대체됐을 뿐 실제로
  만든 것은 아니다 — 나중에 실사용 데이터가 쌓이면 043을 다시 꺼내 별도로 논의한다.
