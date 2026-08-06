# 상품 등록 — AI 가격 추천을 지금 당장 붙일 수 있는 경량 트리거 엔드포인트 요청

- **요청자 파트**: FE
- **대상 파트**: BE

## 배경/이유

`docs/requests/BE/028-pricing-async.md`(AI→BE)가 `POST /pricing/estimates`(가격 범위 min/mid/max + 근거 문장, `GET /ai/jobs/{job_id}` 폴링) 계약을 이미 확정했고, mock 시세로도 지금 당장 연동해도 된다고 명시합니다. 이 호출에 필요한 값은 `product_id`(에코만 됨)·`product_name`·`brand`·`category`·`condition_score`·`condition_grade`뿐이라 **이미지도, 실제로 생성된 상품도 필요 없습니다** — `docs/requests/BE/042-product-registration-ai-pipeline.md`가 막고 있는 "상품 생성 전 이미지 URL 문제"에서 완전히 자유롭습니다.

다만 `POST /pricing/estimates`는 Caddy가 외부로 노출하지 않아(컨테이너 내부망 `http://ai:8000/pricing/estimates`만 가능) FE가 직접 부를 수 없고, 지금 BE에는 이걸 대신 호출해줄 엔드포인트가 없습니다.

FE는 상품 등록 화면의 "AI 가격 추천" 섹션(가격대별 등록 상품 수 히스토그램 + 등급별 추천가 4개, 기존 UI 그대로 유지)을 이 계약으로 채우려 합니다 — `docs/requests/BE/034`/`043`이 요청한 우리 플랫폼 자체 통계(실데이터 0건이라 당장 불가능)와는 다른 데이터 소스입니다.

## 요청 내용

1. **경량 트리거 엔드포인트 하나**: 로그인 사용자가 (실제 상품 생성 여부와 무관하게) `productName`/`category`/`brand`(선택)/`conditionScore`/`conditionGrade`를 보내면, BE가 `POST /pricing/estimates`를 그대로 프록시 호출하고 `job_id`를 돌려주는 엔드포인트가 필요합니다. `product_id`는 AI가 에코만 하므로 실제 상품 id가 없으면 임시값(0 등)을 채워 보내주시면 됩니다.
2. FE는 등급(S/A/B/C) 4개 각각에 대해 이 엔드포인트를 호출해 등급별 추천가를 만들 계획입니다. `POST /pricing/estimates` 동시 처리 상한이 2건이라(028 §"반드시 알아두실 동작") FE가 2개씩 나눠 호출합니다.
3. **등급→대표 `condition_score` 매핑값 확인 요청**: 028 예시(82점 → A등급)만 확인됐고 나머지 등급의 정확한 대표 점수는 근거가 없습니다. FE는 잠정적으로 S=95, A=82, B=68, C=50을 코드에 표시해뒀습니다 — 실제 등급 경계·대표값이 있다면 알려주세요.
4. 결과 폴링(`GET /ai/jobs/{job_id}`)은 FE가 직접 외부 경로로 하므로(품질 검증과 동일한 방식, `docs/requests/FE/036` 참고) BE가 추가로 할 일은 없습니다.

## 관련 자료
- `docs/requests/BE/028-pricing-async.md`(AI↔BE 가격 추정 계약, 이미 확정)
- `docs/requests/BE/034-pricing-internal-comps-source.md`, `docs/requests/BE/043-registration-price-chart-source.md`(우리 플랫폼 통계 기반 대안 — 실데이터 부족으로 보류 중, 이 요청으로 대체 가능할 수 있음)
- `FE/src/domains/product/api/productAiApi.ts`(`estimateRegistrationPrice`, `AI_PRICE_GRADE_SCORES`)
- `FE/src/domains/product/pages/ProductRegistrationPage.vue`(`triggerAiPriceRecommendation`)
