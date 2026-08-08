# SY043 상품 등록 AI 품질 검증 실연동

## 배경/목표

BE(`S15P11A108-591`)가 하자 검수 파이프라인을 실제로 배포했다 — `POST /products`(DRAFT 상태로 상품 조기 생성 가능), `POST /products/{id}/images`(앞/뒤(sortOrder 0/1) 이미지가 둘 다 등록되는 시점에 카테고리가 SAM3 GarmentCategory 6종에 매핑되면 자동으로 검수 job을 트리거), `GET /products/{id}/quality-inspection`(BE가 AI 게이트웨이를 대신 조회해주는 지연 폴링 — `docs/requests/BE/041`). `docs/requests/FE/036-quality-finding-bbox-rendering.md`가 이 계약을 확정했고, `productApi.ts`에 `getProductQualityInspectionStatus`/`mapQualityInspectionResultToPhotoResults`가 이미 구현돼 있지만 `ProductRegistrationPage.vue`에는 연결돼 있지 않았다 — "AI 품질 검증" 단계는 로컬 파일 기반 목업(`analyzeRegistrationPhotos`)이 채우고 있었다.

목표: 이 목업을 실제 BE job 트리거+폴링으로 교체한다.

## 핵심 설계 결정 (036 §1의 미결 사항)

036이 "FE가 결정할 사안"으로 남긴 것: 실제 job은 상품이 실제로 생성되고(`POST /products`) 이미지가 실제로 등록돼야만(`POST /products/{id}/images`) 트리거되는데, `submitProduct()`는 최종 "완료" 스텝에서만 상품/이미지를 만들었다 — "AI 품질 검증" 리뷰는 그보다 훨씬 앞선 "상태/하자"(`condition`) 스텝에서 보여줘야 해서 시점이 어긋난다.

**결정: 트리거 시점은 "앞/뒤 사진 2장이 갖춰지는 즉시"가 아니라 "'기본 정보' 스텝을 벗어나 '상태/하자' 스텝에 처음 진입할 때"다.**

- 처음엔 "카테고리+사진만 있으면 트리거"(상품명은 placeholder)를 검토했으나, 구현 중 `ProductUpdateRequest.java`(PATCH `/products/{id}`)를 직접 확인한 결과 `aiModelEnabled`/`aiModelGender` 필드가 아예 없다는 걸 발견했다. `POST /products`가 성공한 이후에는 이 값을 바꿀 방법이 PATCH로는 없고, 이미지 등록 시점에 딱 한 번만 도는 `triggerAiModelCutJob`(BE)도 재시도가 없어서, 조기 생성 시점에 `aiModelEnabled`가 아직 확정 안 된 상태(기본값 `false`)로 상품이 만들어지면 **AI 모델컷 기능이 그 상품에서 영구히 비활성화되는 회귀**가 생긴다.
- `canMoveCurrentStepNext`(`'photos'` 스텝)가 이미 `isIntroStepValid`(사진+카테고리+상품명+색상+AI 모델컷 설정+실측 전부)를 요구하므로, **'상태/하자' 스텝에 도달했다는 것 자체가 이 모든 값이 이미 확정됐다는 뜻**이다. 트리거를 이 시점으로 옮기면 상품명 placeholder도, "상품명은 빼고 카테고리만" 같은 예외 처리도 필요 없어진다 — `POST /products`에 필요한 모든 필드(제목 포함)가 이미 자연스럽게 갖춰져 있다.
- 카테고리/색상 자동판별(`docs/requests/AI/006`)은 코드로 재확인한 결과 AI 워커(`worker/models/product_classifier/registry.py`)가 여전히 mock이고 BE(`AiClient.java`)에 트리거 코드 자체가 없다 — 이번 범위에서 실연동하지 않는다. 기존 사진 기반 카테고리/색상 자동 제안(mock)은 유지하되, 이제 품질 검증과는 분리된 별도 함수(`triggerAiCategoryColorSuggestion`)로 갈라졌다.
- 상품 생성 시점이 앞당겨지므로 최종 제출(`submitProduct`)은 분기: `draft.draftProductId`가 있으면 `PATCH /products/{id}`로 나머지 필드(제목/설명/카테고리/브랜드/상태등급/사이즈/색상/소재/실측/하자)만 갱신하고 이미지는 재업로드하지 않는다. 없으면(카테고리가 SAM3 미지원이라 애초에 조기 생성이 트리거 안 된 경우 등) 기존처럼 `POST` 플로우 그대로.
- **새로 발견한 잔여 갭**: `aiQualityFindings`(하자 인정/제외 확정 결과)는 `ProductUpdateRequest`에 필드 자체가 없다 — PATCH 경로로는 절대 못 보낸다. `docs/requests/BE/046`으로 남김(BE가 이 필드를 아직 저장 처리하지 않고 있어 당장 사용자에게 보이는 회귀는 아니지만, 041 §6이 정리되면 조기 생성 경로만 조용히 데이터가 누락될 것).
- **범위 제한(추후 수정됨)**: 처음엔 draft 생성 이후 사진을 교체하는 케이스를 다루지 않았다(이미 등록된 이미지와 어긋나는 문제). 실제로 문제가 되는 걸 확인해 이후 수정 — 사진이 바뀔 때마다(`aiTriggerPhotoKey` watch) `resetAiAnalysis()`가 `draft.draftProductId`까지 초기화하도록 바꿔서, 다음 '상태/하자' 진입 시 새 사진으로 처음부터 다시 검수(=새 draft 상품)하게 됐다. 옛 draft 상품은 BE에 DRAFT 상태로 고아처럼 남지만 목록엔 안 보여서 정리 대상은 아니다. mock 데이터/함수(`analyzeRegistrationPhotos`)는 이후 카테고리/색상도 실연동되며 완전히 제거됨(SY45 계열 작업).

## 작업 내용

1. `ProductRegistrationDraft`에 `draftProductId: number | null` 필드 추가.
2. `productApi.ts`:
   - `createDraftProduct(draft, options)` 신설(export) — 기존 `submitProduct`의 `POST /products` 호출부를 분리.
   - `uploadProductImages`를 export.
   - `ProductUpdateRequest` 타입 신설(BE `ProductUpdateRequest.java` 그대로 — `aiModelEnabled`/`aiModelGender`/`aiQualityFindings` 없음).
   - `submitProduct`을 수정: `draft.draftProductId`가 있으면 `PATCH`, 없으면 기존 `POST` → `uploadProductImages` 흐름.
3. `ProductRegistrationPage.vue`:
   - `triggerAiPhotoAnalysis` → `triggerAiCategoryColorSuggestion`으로 축소(카테고리/색상 mock 제안만, 품질 검증은 더 이상 안 채움).
   - 신규 `beginQualityInspection()` — `'condition'` 스텝 진입 시(`watch(() => currentStep.value.id, ...)`) 1회 호출. `draftProductId` 없고 사진/카테고리 유효하면 `createDraftProduct` → `uploadProductImages` → `pollQualityInspectionStatus` 순차 실행.
   - 신규 `pollQualityInspectionStatus(productId)` — `pollAiModelCutStatus`와 같은 토큰 기반 취소/타임아웃 패턴. `NONE`이면 `isQualityCategoryUnsupported`를 세우고 종료, `COMPLETED`면 `mapQualityInspectionResultToPhotoResults`로 `draft.aiPhotoResults` 채움, `FAILED`면 실패 처리.
   - 템플릿: `aiQualityStatus === 'failed' && isQualityCategoryUnsupported`일 때 "이 카테고리는 AI 품질 검증을 지원하지 않습니다" 안내 추가.

## 구현 목록

- [x] `productRegistration.types.ts`: `draftProductId` 필드 추가
- [x] `productApi.ts`: `createDraftProduct` 분리(export), `uploadProductImages` export, `ProductUpdateRequest` 타입, `submitProduct` PATCH 분기
- [x] `ProductRegistrationPage.vue`: `triggerAiCategoryColorSuggestion`(카테고리/색상 mock 분리) + `beginQualityInspection`(실 draft 생성/이미지 등록) 배선
- [x] `ProductRegistrationPage.vue`: 실 폴링 연결(`pollQualityInspectionStatus`) + 상태 매핑
- [x] `ProductRegistrationPage.vue`: `mapQualityInspectionResultToPhotoResults`로 결과 매핑 연결
- [x] `NONE`(미지원 카테고리) 안내 상태 UI 추가
- [x] `docs/requests/BE/046-product-update-quality-findings.md` 작성(PATCH에 `aiQualityFindings` 없는 갭 공유)
- [x] `npm run type-check`, `npm run lint` 통과
