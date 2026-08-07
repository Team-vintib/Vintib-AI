# 042 상품 등록 사진 자동분류(카테고리/색상) 연동

- **작성자 파트**: BE/AI / **대상 파트**: FE
- **작성일**: 2026-08-07

## 배경/이유

상품 등록 위저드에서 사진을 올리면 카테고리·색상을 AI가 미리 채워주는 기능의 BE/AI 쪽 연동이
끝났다. 지금은 서버 테스트(엔드투엔드 확인)가 목적이라 모델 정확도 고도화(전처리 크롭 연결,
카테고리 커버리지 확장)는 별도로 미뤄뒀다 — 지금 요청은 **파이프라인 자체가 실제로 도는지
확인할 수 있게 FE 연결만** 부탁하는 것이다. 정확도는 이후 별도 작업으로 개선된다.

## 요청 내용

`ProductRegistrationPage.vue`의 `aiTriggerPhotoKey` watcher(앞/뒤 사진 둘 다 준비되면 발동)
안에서 mock 호출(`analyzeRegistrationPhotos`, `productRegistrationAiMockData.ts`)을 아래 새
BE 엔드포인트로 교체해달라.

1. **`POST /api/products/pre-upload/upload-url`** — `{fileName, contentType}` → 사전업로드용
   presigned URL 발급.
   응답: `{key, uploadUrl, expiresInSeconds}` (`expiresInSeconds=300`)
2. 발급받은 `uploadUrl`로 S3에 실제 업로드(기존 상품 이미지 업로드 흐름과 동일한 방식).
3. **`POST /api/products/pre-upload/classify`** — `{key}` → 분류 job 접수.
   응답: `{jobId}`
4. **`GET /api/products/pre-upload/classify/{jobId}`** — 상태/결과 조회.
   응답: `{status, result, error}`
   - `status`: `PENDING` | `PROCESSING` | `COMPLETED` | `FAILED`
   - `result`(= `status: COMPLETED`일 때만): `{category, colorPrimary, taxonomyVersion}`
     - `category`: `{majorCategoryId, categoryId, action, score}` — `categoryId`가 카테고리
       드롭다운이 실제로 선택할 값. `category` 자체가 `null`일 수 있음(소분류를 categoryId로
       못 옮긴 경우).
     - `colorPrimary`: `{colorId, action, score}` — 보조색상은 없음(항상 `null`이라 필드 자체가
       없음).
     - `action`: `"autofill"` | `"suggest"` | `"none"` — 기존 mock 응답과 같은 어휘라
       `applyAiCategorySuggestion`/`applyAiColorSuggestion` 로직은 그대로 재사용 가능.
   - `error`(= `status: FAILED`일 때만): 에러 메시지 문자열.

폴링은 `pollAiModelCutStatus`(취소 가능한 토큰 루프)를 본떠 만들되, `productId` 대신 `jobId`
하나만으로 동작하게 해달라. **`jobId`는 서버에 저장하지 않으므로 FE가 직접 들고 있다가 상태
조회에 써야 한다**(페이지 이탈 시 폴링 취소만 하면 되고, 재개할 필요는 없음).

`aiGatewayApi.ts`의 `pollAiJob`(AI 게이트웨이 직접 폴링)은 이번엔 쓰지 않는다 — 위 BE
엔드포인트만 거친다. `applyAiCategorySuggestion`/`applyAiColorSuggestion` 자체는 변경 없음.

## 참고

- BE: `ProductPreUploadController`/`ProductPreUploadService`
  (`BE/src/main/java/com/ssafy/backend/product/{controller,service}/`)
- 원 설계: `.claude/plans/fizzy-hopping-gadget.md`
- 지금은 카테고리 인식 가능 소분류가 11종(전체 35종 중 일부)뿐이고, 색상도 주색상만
  나온다 — 서버 테스트 단계에서는 정상이니 이번 연동에서 신경 쓸 필요 없음.
