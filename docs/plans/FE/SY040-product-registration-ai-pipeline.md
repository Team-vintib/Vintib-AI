# SY040 상품 등록 — 사진 트리거 기반 AI 자동화(카테고리/색상/품질 검증)

## 배경/목표

"AI 품질 검증" 섹션(`condition` 스텝)은 지금까지 front/back 사진을 사용자가 다시 고르고 "확인" 버튼을 눌러야 mock 결과가 뜨는 수동 흐름이었고, 카테고리·색상은 100% 사용자 직접 입력이었다. 이번 작업은 **front/back 사진 2장이 갖춰지는 순간을 트리거**로 (1) 카테고리(대분류/소분류)·색상을 AI가 자동으로 채우고(사용자가 여전히 수정 가능), (2) AI 품질 검증이 백그라운드로 자동 실행돼 `condition` 스텝에서 확인 가능하며, (3) 그 스텝에는 더 이상 사진 선택/추가 선택 UI나 분석을 트리거하는 "확인" 버튼이 없이 결과(사각형 오버레이 + 설명 카드)가 바로 보이도록 바꾼다. 다만 finding 단위 하자 인정/제외와 사진별 결과 저장은 사용자가 직접 해야 하며, 모든 사진이 저장돼야 다음 단계로 넘어갈 수 있다(1차로 완전 읽기 전용으로 만들었다가 사용자 피드백을 받아 이 부분만 복원했다).

BE/AI 쪽에 실제 호출 가능한 엔드포인트가 없어(`docs/APIs.md`에 없음), 이번 작업은 FE 준비(mock 완성) + 교차 팀 요청 문서 작성으로 진행했다.

## 작업 내용

1. **교차 팀 요청 문서**: `docs/requests/BE/042-product-registration-ai-pipeline.md`(상품 생성 전 이미지 URL 확보 방법 — DRAFT 조기 생성 vs 독립 사전 업로드, BE 판단에 위임), `docs/requests/AI/006-registration-category-color-autofill.md`(카테고리 소분류 노출 확장, 색상 자동판별 신규 요청, 품질 검증 bbox 형식 확인).
2. **타입**: `productRegistration.types.ts`에 `ProductRegistrationAiPipelineStatus`(idle/loading/completed/failed) 추가. `ProductRegistrationAiFinding`에 `isActualDefect`(기본 true, 사용자가 하자 인정/제외 토글), `ProductRegistrationAiPhotoResult`에 `confirmed`(사진별 결과 저장 여부)를 둔다. `ProductRegistrationAiCategorySuggestion`/`ProductRegistrationAiColorSuggestion` 신설, `ProductRegistrationDraft`에 `aiQualityStatus`/`aiCategorySuggestion`/`aiColorSuggestion` 추가(`aiCheckPhotoIds`, 죽은 필드였던 `customColor`/`customCategory` 제거).
3. **API/Mock 계층**: `productAiApi.ts` 신설 — `tryOnResultApi.ts`와 동일한 `VITE_PRODUCT_AI_ENABLED` 플래그 패턴(기본 false → mock). 실제 엔드포인트가 없어 플래그를 켜도 `ProductAiAnalysisUnavailableError`를 던지도록 자리만 마련. `productRegistrationAiMockData.ts` 신설(카테고리/색상/품질검증 mock을 한 번에 묶음, "Mock 전용 · BE/AI 확인 필요" 주석 + 관련 요청 문서 경로 명시).
4. **트리거 재배선**: `ProductRegistrationPage.vue`에 front/back 사진 id 기반 `watch`(`aiTriggerPhotoKey`)를 추가해 사진이 갖춰지거나 교체될 때마다 `triggerAiPhotoAnalysis()`를 자동 호출. 기존 "확인" 버튼(`runAiQualityCheck`), 사진 선택/추가 선택 UI 및 관련 상태(`aiCheckPhotoIds`, `isAdditionalAiPhotoPickerOpen`, `toggleAiCheckPhoto` 등)를 모두 제거.
5. **카테고리/색상 자동 채움**: AI 응답이 오면 `categoryMajorId`/`draft.categoryId`/`draft.color`를 자동으로 채우되, 사용자가 이미 해당 필드를 만졌다면(`basicStepTouched`) 덮어쓰지 않는다. 값이 AI 추천과 일치하는 동안만 "AI 추천" 배지를 보여준다(사용자가 바꾸면 자동으로 사라짐).
6. **AI 품질 검증 섹션 개편**: front/back 선택 버튼, "추가 선택" 패널, 트리거용 "확인" 버튼을 제거(분석 자체는 자동). `aiQualityStatus`에 따라 loading(스피너)/failed/idle/completed 4분기로 렌더링. 결과는 캐러셀 + `#c43d46`(`var(--color-error)`) 테두리 사각형 오버레이 + 설명 카드로 표시하되, **finding별 "하자 제외/하자로 표시" 토글**과 **사진별 "결과 저장/수정하기" 버튼**은 되살렸다(1차로 완전 읽기 전용으로 만들었다가 사용자 피드백으로 복원). 제외된 finding은 박스/카드를 무채색 톤다운으로 표시해 "선택 해제"를 시각화한다.
7. **`condition` 스텝 유효성**: `isAiQualityCheckSettled` = `(aiQualityStatus === 'completed' && 모든 사진 confirmed)` 또는 `aiQualityStatus === 'failed'`(AI 실패는 판매자 책임이 아니므로 통과 허용). 스텝 사이드바 완료 표시·리뷰 화면 요약 문구도 함께 갱신. 모두 저장되지 않으면 섹션 하단에 안내 문구를 보여준다.
8. **제출 시 확정 결과 포함**: `productApi.ts`의 `ProductCreateRequest`에 `aiQualityFindings`(사진 역할·설명·box) 필드를 추가하고, `resolveRegistrationAiQualityFindings()`가 `isActualDefect`인 finding만 골라 채운다. BE가 아직 이 필드를 받지 않아 `docs/requests/BE/042`에 저장/노출(상품 상세 `GET /products/{id}` → `docs/requests/BE/019` 형태) 요청 섹션을 추가했다.
9. **"기타" 옵션 제거**: 색상(`PRODUCT_REGISTRATION_COLOR_OPTIONS`), 카테고리 대분류 폴백 목록(`PRODUCT_REGISTRATION_CATEGORY_OPTIONS`)에서 `기타`/`etc` 제거. `ensureEtcCategoryOption`(카테고리 select에 합성 기타 옵션을 끼워 넣던 함수) 삭제. 죽은 필드였던 `customColor`/`customCategory`(템플릿에 입력 UI가 전혀 없었음)도 타입·draft·리셋 코드·`resolveRegistrationColor`에서 함께 제거.

## 구현 목록

- [x] `docs/requests/BE/042-product-registration-ai-pipeline.md` 작성
- [x] `docs/requests/AI/006-registration-category-color-autofill.md` 작성
- [x] `productRegistration.types.ts` 타입 확장/정리
- [x] `productAiApi.ts`, `productRegistrationAiMockData.ts` 신설
- [x] `ProductRegistrationPage.vue`: 트리거 재배선, 카테고리/색상 자동 채움 + AI 추천 배지
- [x] `ProductRegistrationPage.vue`: AI 품질 검증 섹션 템플릿/스타일 전면 개편(읽기 전용)
- [x] `condition` 스텝 유효성/완료 판정 로직 교체
- [x] finding 하자 인정/제외 토글 + 사진별 결과 저장/수정 복원, 전체 confirm 게이트 복원
- [x] 제출 요청에 `aiQualityFindings` 포함, `docs/requests/BE/042`에 저장/노출 요청 섹션 추가
- [x] 색상/카테고리 "기타" 옵션 및 죽은 `customColor`/`customCategory` 필드 제거
- [x] `npm run type-check`, `npm run lint` 통과

## 확인이 필요한 미결정 사항

- **꼭짓점 4개 해석**: 기존 axis-aligned bbox(037)의 네 모서리로 그리는 것으로 해석해 구현했다 — 회전 가능한 자유 사각형을 의미한 것이라면 SVG polygon 렌더링으로 재설계해야 한다.
- **카테고리 자동 채움 범위**: 기존 확정 설계(대분류만 AI)를 넘어 소분류까지 자동 채움을 시도하는 것으로 mock을 구성했다 — AI가 실제로 소분류 id를 노출해줄 수 있는지는 `AI/006` 요청 회신 대기.
- **상품 생성 전 이미지 업로드 방식**: `BE/042` 요청에서 BE가 어떤 방식(DRAFT 조기 생성 vs 독립 사전 업로드)을 택하느냐에 따라 `productAiApi.ts`의 실 연동 코드가 달라진다 — 지금은 mock만 완성해뒀고, 회신 후 별도 작업으로 실 연동한다.
- **색상 자동판별 가능 여부**: AI 모델이 실제로 색상 판별을 지원하는지 미확인 — 안 된다는 회신이 오면 색상은 계속 수동 입력으로 남긴다.
- **상품 상세 탭 연동 범위**: 이번엔 등록 쪽에서 확정 데이터를 만들어 제출하는 데까지만 했다 — 상세 페이지의 `AiQualityAnalysisPanel.vue`/`aiQualityAnalysisMockData.ts`는 건드리지 않았다(이미 `019` 요청이 나가 있고 실 데이터가 오기 전까지는 mock 유지가 맞다고 판단). `BE/042`·`019`가 반영되면 상세 페이지 mock 제거는 별도 작업이 필요하다.
