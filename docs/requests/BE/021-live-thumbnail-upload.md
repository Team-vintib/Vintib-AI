# 021 라이브 썸네일 업로드 API 요청

## 요청자 파트 / 대상 파트

- 요청자 파트: FE
- 대상 파트: BE

## 배경/이유

라이브 생성 화면(`즉시 라이브`/`예약 라이브` 공용 "방송 정보" 단계)에 썸네일 사진 업로드 필드를 추가한다. 라이브 생성(`POST /api/lives`, `POST /api/lives/schedule`)은 `thumbnailUrl` 문자열을 바로 받는 단일 요청 계약이라(`docs/requests/FE/006-live-contract-corrections.md` 참고), 상품 사진처럼 "엔티티 생성 후 업로드"가 아니라 프로필/시착 사진처럼 "업로드해서 URL을 먼저 받고, 그 URL을 생성 요청에 실어 보내는" 방식이 필요하다. 그런데 라이브 쪽엔 이런 프리사인드 업로드 엔드포인트가 아직 없다(상품/프로필/시착 사진엔 있음).

## 요청 내용

`POST /api/users/{userId}/lives/thumbnail/upload-url` 같은, 기존 프로필 이미지(`POST /api/users/{userId}/profile-image/upload-url`)·시착 사진(`POST /api/users/{userId}/tryon/upload-url`)과 동일한 패턴의 프리사인드 업로드 엔드포인트를 만들어 주세요.

- 요청 바디: `{ contentType: string }`
- 응답: `{ key: string, uploadUrl: string, url: string, expiresInSeconds: number }`

프로필 이미지는 업로드 후 `PUT /users/{userId}/profile-image { key }`로 confirm해서 최종 URL을 받지만, 라이브는 생성 전이라 confirm할 대상(`liveId`)이 없습니다. 그래서 **upload-url 응답 자체에 최종 공개 URL(`url`)까지 포함**해 주시면, FE가 별도 confirm 없이 이 URL을 그대로 라이브 생성 요청의 `thumbnailUrl`에 실어 보낼 수 있습니다.

## 관련 자료

- 기존 패턴: `POST /api/users/{userId}/profile-image/upload-url`, `POST /api/users/{userId}/tryon/upload-url`
- 라이브 생성 계약: `docs/requests/FE/006-live-contract-corrections.md`
