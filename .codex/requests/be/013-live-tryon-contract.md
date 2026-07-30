# 라이브 AI 시착 계약 요청

**요청자 파트**: FE  
**대상 파트**: BE

## 배경/이유

`S15P11A108-425`에서 라이브 시청 화면의 AI 시착 패널을 mock 상태로 구현한다. 현재
BE에는 `/api/users/{userId}/tryons` 결과 조회·삭제가 있으나, 라이브 패널이 필요한
현재 전신 사진 조회·변경과 시착 생성 계약은 없다. 기존
`.codex/requests/be/003-onboarding-tryon-profile-api.md`의 `PUT /api/me/tryon`도 FE
선행 계약이며 현재 구현 여부와 최종 경로를 다시 확인해야 한다.

## 요청 내용

아래 항목의 최종 API와 정책을 확정해 달라.

### 1. 현재 회원의 AI 시착 사진 조회

- 인증된 현재 회원 기준으로 등록된 전신 사진 URL 또는 미등록 상태를 조회할 수 있어야 한다.
- presigned URL을 사용한다면 만료 시간과 재조회 기준이 필요하다.
- 본인 사진이므로 path의 임의 `userId` 대신 `/me` 계열 사용 여부를 확인한다.

응답에서 필요한 의미:

- 전신 사진 등록 여부
- 표시 가능한 전신 사진 URL
- 사진 식별자가 필요한 경우 그 값

### 2. 라이브 패널에서 사진 등록·변경

- `multipart/form-data` 이미지 한 장을 등록하거나 기존 사진을 변경할 수 있어야 한다.
- 라이브 패널의 변경이 계정의 대표 전신 사진을 영구 교체하는지, 현재 시착 요청에만
  임시 사용하는지 정책을 확정한다.
- 허용 MIME type, 최대 용량·해상도, 개인정보 보관·삭제 정책과 검증 오류 코드를 제공한다.
- 기존 `PUT /api/me/tryon`을 재사용할지 사진 전용 API로 분리할지 확인한다.

### 3. 시착 가능 여부

- 라이브에 연결된 선택 상품이 AI 시착을 지원하는지 FE가 판별할 수 있어야 한다.
- 상품 또는 라이브 상세 응답에 지원 여부를 포함할지, 생성 요청에서 검증 오류로만
  처리할지 확정한다.
- 라이브에만 임시 소개되고 등록 상품이 아닌 경우의 오류를 구분한다.

### 4. AI 시착 생성

- 인증된 회원과 `productId`를 기준으로 생성 요청을 보낼 수 있어야 한다.
- 등록 사진을 사용할 때와 라이브 패널에서 새로 선택한 사진을 사용할 때의 입력 방식을
  구분한다.
- 동기 응답인지, 오래 걸리는 작업을 위한 비동기 `jobId`·상태 조회 방식인지 확정한다.
- 비동기라면 최소 `QUEUED`, `PROCESSING`, `SUCCEEDED`, `FAILED` 상태와 polling 간격,
  만료·취소 정책이 필요하다.
- 실패 시 재시도 가능한 오류와 재시도하면 안 되는 오류를 구분한다.

### 5. 생성 결과와 결과 저장 분리

기능 정의서는 결과를 자동 저장하지 않고 사용자가 `결과 저장`을 눌렀을 때 저장하도록
정의한다. 생성 직후 `tryon_result`에 영구 저장하는 방식과 충돌하지 않도록 다음을
확정한다.

- 생성 완료 시 임시 결과 URL·만료 시간
- 사용자가 저장할 때 영구 `tryon_result`로 전환하는 API
- 저장하지 않은 임시 결과의 만료·삭제 정책
- 저장 완료 응답의 `resultId`, `productId`, `imageUrl`, 생성 시각

## 현재 FE 처리

- 등록 사진 있음·없음, 생성 중·완료·실패는 mock 상태로 표현한다.
- 파일 선택은 로컬 미리보기만 바꾸며 영구 저장 완료로 표시하지 않는다.
- 실제 생성·polling·결과 저장 API는 호출하지 않는다.
- 선택 상품이 없거나 라이브가 예정·종료 상태이면 AI 시착 진입을 비활성화한다.

## 관련 자료

- Jira `S15P11A108-425`
- `.codex/plans/fe/HS018-ai-tryon-entry-area.md`
- `.codex/requests/be/003-onboarding-tryon-profile-api.md`
- `.codex/requests/be/012-live-watch-detail-contract-gaps.md`
- `.claude/requests/ai/001-tryon-result-contract.md`
- `BE/src/main/java/com/ssafy/backend/tryon/controller/TryOnController.java`
