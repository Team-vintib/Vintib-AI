# SY017 - 마이페이지 AI 시착 탭

## 배경/목표

현재 AI 시착 프로필은 온보딩 단계에서 전신 사진과 신체 정보를 입력하는 흐름만 있고, 마이페이지에서는 기본 시착 이미지만 일부 관리한다. 마이페이지에 `AI 시착` 탭을 추가해 사용자가 전신 사진, 키, 몸무게, 가슴, 허리, 엉덩이 등 시착 기준 정보를 한 곳에서 조회·수정·삭제할 수 있게 만든다.

이 탭은 이후 상품 상세의 `AI 시착`과 라이브 시청 중 `AI 시착`이 같은 사용자 시착 프로필을 기반으로 동작하도록 하는 FE 기준 관리 화면이다.

## 현재 상태 분석

- `APIs.md`에는 AI 가상 시착 프로필 API 후보가 있다.
  - `GET /users/{userId}/tryon`
  - `PUT /users/{id}/tryon`
  - `DELETE /users/{id}/tryon`
  - `POST /users/{id}/tryons`
  - `GET/DELETE /users/{userId}/tryons`
- `docs/requests/BE/007-live-tryon-contract.md`는 FE 사용처 기준으로 `GET /api/me/tryon`, `PUT /api/me/tryon`을 요청하고 있다.
- 온보딩 `ONBOARD-003` 구현은 전신 사진, 키, 몸무게, 가슴, 허리, 엉덩이를 선택 입력으로 저장하는 선행 UI와 multipart 요청 함수를 갖고 있다.
- 마이페이지 `SY016` 구현은 `/my` 단일 페이지에서 `section` query로 섹션을 전환하며, 프로필 섹션 안에 기본 시착 이미지 관리 UI가 일부 들어가 있다.
- 상품 상세와 라이브 시착 패널은 현재 시착 프로필/생성 API 미연동 상태라 mock 또는 빈 상태로 동작한다.

## 작업 내용

마이페이지에 `section=tryon` 탭을 추가하고, AI 시착 프로필을 별도 관리 영역으로 분리한다. 기존 프로필 섹션에 섞여 있는 기본 시착 이미지 관리는 새 탭으로 이동시키고, 프로필 섹션은 회원 기본 정보와 관심 정보 중심으로 유지한다.

AI 시착 탭은 다음 정보를 관리한다.

- 전신 사진
  - 현재 저장된 사진 미리보기
  - 사진 등록/교체/삭제
  - 전신 사진이 없으면 상품/라이브 AI 시착을 사용할 수 없다는 상태 안내
- 신체 정보
  - 키(cm), 몸무게(kg)
  - 가슴, 허리, 엉덩이 치수
  - 모든 항목은 선택 입력
  - 빈 값은 정상, 값이 있으면 양의 정수 검증
- 시착 사용 상태
  - 사용 가능: 전신 사진이 있음
  - 정보 보강 권장: 전신 사진은 있으나 신체 정보 일부 없음
  - 사용 불가: 전신 사진 없음
- 연결 안내
  - 상품 상세 AI 시착과 라이브 AI 시착이 이 프로필을 기준으로 동작한다는 안내
  - 시착 결과 목록/비교 관리는 TRYON-005 추가 범위이므로 이번 탭에서는 생성 결과 히스토리를 구현하지 않는다.

API adapter는 `domains/tryon` 쪽에 사용자 시착 프로필 타입과 조회/저장/삭제 함수를 두고, `domains/my`는 화면 섹션에서 이를 호출한다. 이렇게 해야 상품 상세와 라이브 시착 패널이 나중에 같은 함수와 타입을 재사용할 수 있다.

BE 계약이 최종 확정되기 전까지는 다음 기준을 사용한다.

- 우선 호출 후보: `GET /api/me/tryon`, `PUT /api/me/tryon`, `DELETE /api/me/tryon`
- 현재 문서의 `/users/{id}/tryon` 계열은 `BE 확인 필요`로 표기한다.
- `VITE_TRYON_API_ENABLED=false` 기본값에서는 mock fallback을 사용한다.
- multipart 필드는 온보딩 선행 계약과 맞춘다: `bodyPhoto`, `heightCm`, `weightKg`, `chest`, `waist`, `hip`

## 구현 목록

- [ ] `domains/tryon/types`에 사용자 시착 프로필 타입을 추가한다.
- [ ] `domains/tryon/api`에 시착 프로필 조회/저장/삭제 adapter를 추가한다.
- [ ] `domains/tryon/constants`에 mock 시착 프로필과 상태 라벨을 둔다.
- [ ] `domains/my`의 섹션 옵션에 `AI 시착` 탭을 추가하고 `section=tryon`을 처리한다.
- [ ] 마이페이지 프로필 섹션에 있던 기본 시착 이미지 관리를 AI 시착 탭으로 이동한다.
- [ ] AI 시착 탭 UI를 구현한다: 상태 요약, 전신 사진 관리, 신체 정보 form, 저장/삭제 상태.
- [ ] 온보딩에서 사용한 전신 사진 업로더/검증 흐름을 재사용하거나, 마이페이지 화면에 맞는 전용 컴포넌트로 분리한다.
- [ ] 선택 숫자 입력 검증을 구현한다: 빈 값 허용, 값이 있으면 0보다 큰 정수만 허용.
- [ ] 저장 중 중복 제출 방지, 성공/실패 메시지, 서버 필드 오류 매핑을 처리한다.
- [ ] 전신 사진 삭제 시 상품/라이브 AI 시착 사용 불가 상태가 명확히 보이도록 한다.
- [ ] `ProductDetailView`와 `LiveTryOnPanel`은 이번 구현에서 생성 API까지 연결하지 않고, 후속 연결 지점만 타입/API 기준으로 맞춘다.
- [ ] `.env.example`에 `VITE_TRYON_API_ENABLED=false`를 추가한다.
- [ ] `FE/docs/frontend/screens/screen-inventory.md`에 마이페이지 AI 시착 탭 상태를 반영한다.
- [ ] `FE/docs/frontend/implementation/current-structure.md`에 `domains/tryon/api`와 사용자 프로필 관리 구조를 반영한다.
- [ ] `FE/docs/frontend/implementation/status.md`가 있으면 TRYON/MY 상태를 갱신한다.
- [ ] `npm run type-check`와 가능한 경우 `npm run build`로 검증한다.

## BE 확인 필요

- 최종 endpoint를 `/api/me/tryon`으로 확정할지, `APIs.md`의 `/users/{id}/tryon` 계열을 유지할지 확인이 필요하다.
- `DELETE /api/me/tryon` 제공 여부와 삭제 범위가 필요하다.
  - 전체 시착 프로필 삭제
  - 전신 사진만 삭제
  - 신체 정보만 초기화
- 저장 응답의 필드명을 확정해야 한다.
  - `tryonProfileId`
  - `bodyPhotoUrl`
  - `heightCm`, `weightKg`, `chest`, `waist`, `hip`
  - `updatedAt`
- 가슴, 허리, 엉덩이의 단위와 허용 범위가 필요하다.
- 상품/라이브 AI 시착 생성 API가 시착 프로필 미등록 상태를 어떤 오류 코드로 내려줄지 필요하다.

## 범위 제외

- 상품 상세 AI 시착 생성 API 실제 연동
- 라이브 AI 시착 생성 API 실제 연동
- 시착 결과 목록, 상세, 삭제, 비교 관리
- 여러 개의 시착 프로필 다중 관리
- 사진 크롭, 배경 제거, AI 전신 판별
- BE/AI 코드 변경
