# SY026 라이브 생성 썸네일 업로드

## 배경/목표

라이브 생성 화면("방송 정보" 단계, 즉시 라이브/예약 라이브 공용)에 썸네일 사진을 직접 올릴 수 있는 필드가 없다. 현재는 선택한 상품 중 첫 번째 사진을 자동으로 썸네일로 쓴다(`getLiveThumbnailUrl`, `LiveCreatePage.vue`). 방송 제목 필드 위에 사진 업로드 UI를 추가해 사용자가 직접 썸네일을 고를 수 있게 한다.

## 작업 내용

- `liveCreateApi.ts`에 `uploadLiveThumbnail(userId, file)` 추가. 프로필/시착 사진 업로드와 같은 프리사인드 업로드 패턴(업로드 URL 발급 → PUT 업로드) 사용. BE에 아직 없는 엔드포인트라 `docs/requests/BE/021-live-thumbnail-upload.md`로 요청 문서 남김.
- `LiveCreatePage.vue`의 "방송 정보" 단계, 방송 제목 필드 바로 위에 미리보기 + 사진 선택/삭제 UI 추가 (기존 마이페이지 프로필 사진 편집 UI와 동일한 형태로 새로 작성).
- 사진 업로드는 필수 아님 — 업로드하지 않으면 기존처럼 선택 상품 사진 자동 대체 유지.
- 제출 시 업로드한 파일이 있으면 `uploadLiveThumbnail` 호출 결과 URL을, 없으면 기존 `getLiveThumbnailUrl()` 폴백을 `thumbnailUrl`로 사용.

## 구현 목록

- [ ] `docs/requests/BE/021-live-thumbnail-upload.md` 작성
- [ ] `liveCreateApi.ts`: `uploadLiveThumbnail` + 응답 타입 추가
- [ ] `LiveCreatePage.vue`: 썸네일 업로드 필드 + state/handler, `submitLiveCreate` 반영
- [ ] `vue-tsc --noEmit` 통과 확인

## 확인이 필요한 미결정 사항

- BE 엔드포인트 반영 전까지 실제 업로드 호출은 실패할 수 있음(예: 404). 실패 시 에러 메시지를 보여주되, 상품 사진 자동 대체로 계속 제출은 가능하게 둔다.
