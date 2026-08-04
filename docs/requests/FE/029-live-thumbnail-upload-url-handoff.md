# 029 라이브 썸네일 업로드 URL 발급 API 반영

- **작성자 파트**: BE (정윤) / **대상 파트**: FE
- **작성일**: 2026-08-04
- **원 요청**: `docs/requests/BE/021-live-thumbnail-upload.md` (요청하신 그대로 반영)

`021`에서 요청하신 프리사인드 업로드 엔드포인트를 구현했습니다.

## `POST /api/users/{userId}/lives/thumbnail/upload-url`

- 요청: `{ "contentType": "image/jpeg" }` (`image/jpeg`/`image/png`/`image/webp`만 허용)
- 응답:

```jsonc
{
  "key": "live-thumbnails/1/3f1c...-abcd.jpg",
  "uploadUrl": "https://s3.../live-thumbnails/1/3f1c...-abcd.jpg?X-Amz-...",
  "url": "https://s3.../vintib-public/live-thumbnails/1/3f1c...-abcd.jpg",
  "expiresInSeconds": 300
}
```

- 요청하신 대로 **확정(confirm) 단계가 없습니다.** `uploadUrl`로 브라우저에서 직접 `PUT`한
  뒤, `url`을 그대로 `POST /api/lives`/`POST /api/lives/schedule`의 `thumbnailUrl`에 실어
  보내면 됩니다.
- 인증된 본인(`userId` == 토큰 주체)만 발급받을 수 있습니다(403). 프로필/커버 이미지와 같은
  패턴입니다.
- 실제 업로드 성공 여부는 서버가 검증하지 않습니다 — 라이브 생성 전이라 확인할 대상이 없고,
  공개 버킷의 비민감 이미지라 프로필 이미지만큼 엄격하게 볼 필요가 없다고 판단했습니다. 업로드를
  하지 않고 `url`만 그대로 보내면 깨진 이미지가 될 뿐이니, 실제 `PUT`을 먼저 완료한 뒤 그 `url`을
  쓰도록 해주세요.

## 참고

- `LiveCreatePage.vue`의 `uploadLiveThumbnail`이 이미 이 계약(프리사인드 발급 → 브라우저 직접
  PUT)을 그대로 기대하고 있어서(`SY026` 계획 문서), 추가 코드 변경 없이 바로 붙을 것으로
  예상합니다. 안 붙으면 알려주세요.
- `docs/requests/BE/021-live-thumbnail-upload.md`는 이번 작업이 `develop-BE` 기준이라 이
  브랜치엔 없습니다(main/develop-FE에만 있음) — 다음 동기화 때 같이 정리해 주세요.
