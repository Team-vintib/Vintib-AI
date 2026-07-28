# 상품 이미지 업로드 — presigned 2단계 업로드 연동 요청

**요청자 파트**: BE
**대상 파트**: FE

## 배경/이유

상품 이미지를 S3에 저장하기로 했다(SY008). 상품당 최대 10장까지 업로드할 수 있어, 백엔드가 파일 바이트를 직접 받지 않고 브라우저가 S3에 직접 PUT하는 presigned 방식으로 구현했다. 이 흐름은 기존에 FE가 어디에도 구현해두지 않은 새 계약이라 API 스펙을 공유한다.

## 요청 내용

상품 등록/수정 화면에서 이미지를 올릴 때, 파일 1개당 아래 3단계를 거친다.

1. **업로드 URL 발급** — `POST /api/products/{productId}/images/upload-url`
   - 요청: `{ "fileName": string, "contentType": string }` (`contentType`은 `image/jpeg`, `image/png`, `image/webp` 중 하나만 허용)
   - 응답: `{ "key": string, "uploadUrl": string, "expiresInSeconds": number }` (`expiresInSeconds`는 300, 즉 5분)
2. **S3 직접 업로드** — 1번 응답의 `uploadUrl`로 파일 바이트를 **PUT** (헤더 `Content-Type`을 1번에서 보낸 `contentType`과 동일하게 지정). 백엔드를 거치지 않고 브라우저가 S3(MinIO)에 직접 요청한다.
3. **등록 확인** — `POST /api/products/{productId}/images`
   - 요청: `{ "key": string, "sortOrder": number, "isPrimary": boolean }` (`key`는 1번에서 받은 값을 그대로 사용)
   - 성공(201) 응답: `{ "id": number, "url": string, "sortOrder": number, "isPrimary": boolean }` — `url`이 실제 화면에 보여줄 고정 이미지 URL이다.

이미지 여러 장은 파일마다 1~3단계를 반복한다(병렬 호출 가능). 이미지 삭제는 `DELETE /api/products/{productId}/images/{imageId}`.

상품 상세 조회(`GET /api/products/{id}`) 응답에 이제 `images: [{ id, url, sortOrder, isPrimary }, ...]` 필드가 추가되어 있다.

모든 엔드포인트는 인증 필요(판매자 본인만). 실패 시 공통 `ApiResponse` envelope의 `error.code`로 구분: `P006`(지원하지 않는 이미지 형식), `P007`(2단계 업로드를 하지 않고 3단계를 호출함), `P005`(이미지 10장 초과).

## 관련 자료

- Swagger: `/swagger-ui/index.html` — "상품" 태그 하위 3개 엔드포인트
- `BE/src/main/java/com/ssafy/backend/product/controller/ProductController.java`
