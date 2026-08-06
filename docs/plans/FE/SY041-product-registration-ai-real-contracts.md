# SY041 상품 등록 AI 3종 — 재조사 기반 실연동 준비

## 배경/목표

SY040 이후 BE/AI/FE 문서·코드를 다시 조사한 결과, 세 AI 기능(카테고리/색상 자동판별, AI 품질 검증, AI 가격 추천)의 실제 성숙도가 크게 다르다는 게 드러났다.

- **AI 품질 검증**: `docs/requests/BE/041-quality-inspection-integration.md`(037/038 통합)와 `docs/requests/FE/036-quality-finding-bbox-rendering.md`가 필드 단위까지 확정된 계약이다. FE가 BE를 거치지 않고 `GET https://i15a108.p.ssafy.io/ai/jobs/{job_id}`를 직접 폴링하는 구조까지 못박혀 있고, 기존 FE mock 구조가 거의 그대로 맞는다고 AI가 확인해줬다.
- **AI 가격 추천**: `docs/requests/BE/028-pricing-async.md`가 `POST /pricing/estimates`(가격 범위 min/mid/max + 근거) 계약을 확정했고, 이미지·실제 상품 없이도 지금(mock 시세로) 연동 가능하다.
- **카테고리/색상 자동판별**: AI 코드는 있지만 BE 연동 가이드가 없고, 워커가 mock 스텁(항상 JACKET/BLACK, score 0)이라 지금 연동해도 의미 있는 값이 안 나온다.

공통 블로커는 여전히 `docs/requests/BE/042-product-registration-ai-pipeline.md`(상품 생성 전 이미지 URL 확보 문제)이지만, **가격 추천만은 이미지가 전혀 필요 없어 이 블로커에서 자유롭다** — 새 경량 BE 엔드포인트 하나만 있으면 지금 실동작 가능. 사용자 결정으로 가격 섹션 UI(히스토그램+등급별 추천가 4개)는 그대로 유지하고, 데이터만 이 실제 계약(028)으로 "믹스"해서 채운다.

## 작업 내용

1. **공용 AI 게이트웨이 폴링 클라이언트**: `aiGatewayApi.ts` 신설 — BE를 거치지 않는 별도 axios 인스턴스(`VITE_AI_GATEWAY_BASE_URL`, 기본 `https://i15a108.p.ssafy.io`)와 `pollAiJob()`(`GET /ai/jobs/{job_id}`, success/failed까지 반복, 404는 실패로 취급).
2. **AI 가격 추천 실연동 준비**: `productAiApi.ts`에 `estimateRegistrationPrice(grade, input)` 추가(등급 1건당 1 job, mock 우선). `ProductRegistrationPage.vue`에서 pricing 스텝 진입 시 등급 S/A/B/C 4개를 2개씩 배치 호출(028의 동시 2건 제한 준수) → `price_range.mid`로 등급별 추천가, 실제 확정 등급의 `comps_used` 가격을 `buildPriceRecommendationBuckets()`로 버킷팅해 히스토그램을 채운다. 트리거 자체는 아직 실제 BE 엔드포인트가 없어(`044` 미해결) mock 유지, 로딩/실패/idle 상태 UI 추가.
3. **AI 품질 검증 필드 재정렬**: `ProductRegistrationAiFinding`을 041/036이 확정한 실제 필드(`key`,`defectType`,`label`,`status`,`imageIndex`,`no`,`bbox`[x1,y1,x2,y2] 0~1,`confidence`,`severity`,`statementRequired`,`needsSellerReview`,`description`)로 재정렬. 렌더링용 `{x,y,width,height}%`는 `qualityFindingBox.ts#toPercentBox()`로 bbox에서 파생시킨다. `isActualDefect`는 계속 FE 로컬 상태. 제출 필드(`aiQualityFindings`)도 이 실제 필드명으로 다시 맞추고, 인정/제외 여부와 무관하게 전체를 보낸다(041이 "아니다로 처리된 것도 알아야 한다"고 명시).
4. **카테고리/색상 — 최소 정리만**: AI 색상 팔레트(13색+MIXED)가 FE 14개 옵션과 1:1 매핑됨을 확인하고 `aiColorPalette.ts`(`mapAiColorKeyToOptionId`)로 반영. 트리거/실연동은 여전히 미룬다(워커가 mock 스텁이라 의미 없음).
5. **교차 팀 요청 문서**: 신규 `docs/requests/BE/044-pricing-estimate-trigger.md`(경량 가격 추천 트리거 엔드포인트 요청). `043`에 044로 대체 가능하다는 메모 추가. `041`에 019와의 저장 범위(findings 원본 vs key만) 교차 확인 섹션 추가. `AI/006`에 taxonomy_version 기본값 불일치 버그, 041과 같은 트리거 패턴을 따르는지 확인 질문, 이미 코드로 확인된 소분류/색상 답변 반영.

## 구현 목록

- [x] `aiGatewayApi.ts` 신설(`pollAiJob`), `.env.example`에 `VITE_AI_GATEWAY_BASE_URL` 추가
- [x] `ProductRegistrationAiFinding` 타입을 041/036 필드로 재정렬, `qualityFindingBox.ts#toPercentBox()` 신설
- [x] mock 데이터(`productRegistrationAiMockData.ts`)를 새 필드 형태로 갱신
- [x] `ProductRegistrationPage.vue`의 finding 렌더링/토글을 새 필드(`key`/`no`/`bbox`)로 갱신
- [x] `productApi.ts`의 `aiQualityFindings` 제출 필드를 041 필드명으로 재정렬(필터 없이 전체 전송)
- [x] `aiColorPalette.ts`(색상 팔레트 매핑) 신설, mock에 반영
- [x] `productAiApi.ts`에 가격 추천 함수(`estimateRegistrationPrice`, `AI_PRICE_GRADE_SCORES`) + mock(`buildMockPriceEstimates`) 추가
- [x] `priceBuckets.ts`(`buildPriceRecommendationBuckets`) 신설
- [x] `ProductRegistrationPage.vue`: 가격 추천 상태 관리(refs화) + 트리거(2+2 배치) + 로딩/실패/idle UI
- [x] `docs/requests/BE/044-pricing-estimate-trigger.md` 신설
- [x] `docs/requests/BE/043`, `041`, `docs/requests/AI/006` 갱신
- [x] `npm run type-check`, `npm run lint` 통과

## 확인이 필요한 미결정 사항

- **가격 추천 트리거 엔드포인트**: `044` 회신 전까지는 mock만 동작한다 — 회신 오면 `estimateRegistrationPrice`의 real 분기만 채우면 된다.
- **등급→대표 점수 매핑**: S=95/A=82/B=68/C=50은 FE 임시값이다(082점=A등급 예시 하나만 확인됨) — `044` 회신으로 확정 필요.
- **품질검증 제출 필드 저장 범위**: `041`에 교차 확인을 남겼다 — BE가 findings 원본을 저장할지 key만 저장할지에 따라 `019`(상품 상세 노출) 반영 여부가 갈린다.
- **카테고리/색상 트리거 시점**: `AI/006`에 041과 같은 패턴을 따르는지 물어뒀다 — 회신 전까지 트리거 코드는 만들지 않는다.
- **상품 생성 전 이미지 URL 문제(`042`)**: 여전히 미해결 — 품질검증/카테고리분류의 실제 트리거는 이게 풀려야 가능하다.
