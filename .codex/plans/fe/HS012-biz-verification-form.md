# S15P11A108-397/400 BIZ-001 사업자 정보 제출 계획

## 배경/목표

ONBOARD-004에서 사업자 회원을 선택한 사용자가 사업자 정보를 입력하고 제출할 수 있는
BIZ-001 화면을 구현한다. 화면 구현과 입력 제약을 Jira 작업 단위로 분리하며, 이번
범위에서는 실제 인증 API를 호출하지 않고 더미 제출 성공 후 BIZ-001-2 인증 대기
화면을 거쳐 로그인 상태를 유지한 채 HOME으로 이동한다.

## 확인한 기준

- Jira 작업 우선순위는 `S15P11A108-397` 화면 구현(Medium),
  `S15P11A108-400` 입력 제약(Low) 순서다.
- `S15P11A108-397`은 사업자 인증 화면의 기본 레이아웃과 사업자번호, 상호명,
  대표자명 등의 입력 UI 구현이며 실제 인증 API 호출은 제외한다.
- `S15P11A108-400`은 필수값, 숫자 형식, 제출 가능 여부를 확인할 수 있는 입력 제약과
  더미 상태 구현이다.
- Figma `BIZ-001_사업자 정보 제출` 프레임은 온보딩 진행 단계, 사업자등록번호 입력,
  사업자등록증 이미지 등록, 개인정보 이용 안내와 제출 버튼으로 구성된다.
- 화면 요구 문서는 사업자등록번호와 사업자등록증을 필수로 요구하고, 형식 오류,
  이미지 누락과 업로드 실패 상태를 요구한다.
- 화면 요구 문서와 라우트 문서에 맞춰 BIZ-001 경로는
  `/business/verification`으로 통일한다.
- API 문서에는 `POST /api/business-verifications`가 후보로만 있으며 BE 구현과
  Swagger 계약은 아직 없다.
- 사업자번호 세부 검증 정책과 이미지 형식·용량은 아직 확정되지 않았다.
- BIZ-001 더미 제출 성공 시 BIZ-001-2 인증 대기 화면으로 이동하고, 사용자가
  `메인으로 이동`을 선택하면 `ROUTE_PATHS.HOME`으로 이동한다.

## 작업 1: S15P11A108-397 사업자 인증 입력 화면

- `domains/biz` 안에 BIZ-001 라우트 페이지와 이미지 업로더를 만든다.
- Figma와 기존 디자인 토큰을 기준으로 온보딩 완료 단계, 화면 제목과 설명,
  사업자등록번호, 상호명, 대표자명, 사업자등록증 이미지 등록, 개인정보 이용 안내와
  제출 버튼을 배치한다.
- 파일 선택, 미리보기, 변경과 삭제 상태를 화면에 제공한다.
- 키보드 입력, 파일 입력과 오류 문구를 보조기술이 인식할 수 있도록 label,
  description, status 영역을 연결한다.
- BIZ-001 화면 요구사항 문서를 별도로 만들고 원천 문서와 Figma에서 확인한 요소를
  기록한다.
- 이 작업에서는 서버 제출, 상세 입력 검증과 HOME 이동을 연결하지 않는다.

## 작업 2: S15P11A108-400 사업자 인증 입력 제약

- 사업자등록번호, 상호명, 대표자명과 사업자등록증 필수 검증을 추가한다.
- FE 임시 정책으로 사업자등록번호는 숫자 10자리만 유효하게 처리하고, 체크섬 검증은
  BE 정책 확정 전까지 적용하지 않는다.
- 사업자등록증은 한 개의 파일만 선택하고 `image/*` MIME 여부만 1차 확인한다.
  구체적인 확장자와 최대 용량은 임의로 정하지 않고 BE 확인 항목으로 남긴다.
- 모든 필수 입력이 유효하고 제출 처리 중이 아닐 때만 제출할 수 있도록 한다.
- 일반 오류, 업로드 오류와 중복 제출 방지 상태를 표시한다.
- 실제 API를 호출하지 않는 더미 제출 상태를 거쳐 BIZ-001-2로 이동한다.
- BIZ-001-2에는 인증 대기 상태, 제출 정보와 사업자등록증 확인 UI,
  `메인으로 이동` 버튼을 제공한다.
- `메인으로 이동`을 누르면 로그인 상태를 유지한 채 HOME(`/`)으로 이동한다.
- FE API 후보와 미확정 사항 문서를 갱신하고, BE가 검토할 요청 문서를 작성한다.

## BE 확인용 API 계약 제안

- 이번 작업에서는 API 함수나 요청·응답 타입을 구현하지 않는다.
- `POST /api/business-verifications` multipart 후보와 사업자등록번호, 상호명,
  대표자명, 사업자등록증 필드를 BE 요청 문서에 기록한다.
- endpoint, 필드명, 검증 조건, 이미지 제한과 오류 규격은 BE가 확정한 뒤 별도 연동
  작업에서 구현한다.

## 생성·수정할 파일

### 작업 1

- 새 파일: `FE/src/domains/biz/pages/BusinessVerificationPage.vue`
- 새 파일: `FE/src/domains/biz/components/BusinessCertificateUploader.vue`
- 수정: `FE/src/shared/constants/routes.ts`
- 수정: `FE/src/router/routes.ts`
- 새 파일: `FE/docs/frontend/screens/BIZ-001/requirements.md`
- 수정: `FE/docs/frontend/screens/screen-inventory.md`
- 수정: `FE/docs/frontend/implementation/current-structure.md`
- 수정: `FE/docs/frontend/implementation/status.md`

### 작업 2

- 필요 시 새 파일: `FE/src/domains/biz/constants/businessVerification.ts`
- 수정: `FE/src/domains/biz/pages/BusinessVerificationPage.vue`
- 새 파일: `FE/src/domains/biz/pages/BusinessVerificationPendingPage.vue`
- 수정: `FE/src/domains/biz/components/BusinessCertificateUploader.vue`
- 수정: `FE/src/shared/constants/routes.ts`
- 수정: `FE/src/router/routes.ts`
- 수정: `FE/docs/frontend/api/api-index.md`
- 수정: `FE/docs/frontend/decisions/open-questions.md`
- 수정: `FE/docs/frontend/flows/route-map.md`
- 수정: `FE/docs/frontend/screens/BIZ-001/requirements.md`
- 수정: `FE/docs/frontend/implementation/status.md`
- 새 파일: `.codex/requests/be/005-business-verification-api.md`

## 구현 목록

### S15P11A108-397

- [x] `/business/verification` BIZ-001 route 등록
- [x] Figma 기준 사업자 정보 입력 화면 구현
- [x] 사업자등록번호 입력 상태 구현
- [x] 상호명·대표자명 입력 상태 구현
- [x] 사업자등록증 선택·미리보기·변경·삭제 상태 구현
- [x] 개인정보 이용 안내와 제출 버튼 구현
- [x] BIZ-001 요구사항·구조·상태 문서 갱신
- [x] 자동 검증
- [x] 사용자 수동 검증
- [ ] 사용자 확인 후 작업 단위 add/commit/push

### S15P11A108-400

- [ ] 사업자번호 숫자 10자리와 상호명·대표자명 필수 검증
- [ ] 이미지 한 개·이미지 MIME·필수 검증
- [ ] 제출 활성화 조건과 중복 제출 방지
- [ ] 더미 제출 상태와 BIZ-001-2 이동 구현
- [ ] BIZ-001-2 인증 대기·제출 정보 확인 화면 구현
- [ ] BIZ-001-2 메인 이동 버튼과 HOME 이동 구현
- [ ] 일반 오류 표시
- [ ] FE API·미확정 사항 문서 갱신
- [ ] BE API·검증 정책 요청 문서 작성
- [ ] 자동 검증과 사용자 수동 검증
- [ ] 사용자 확인 후 작업 단위 add/commit/push

## 검증 시나리오

1. ONBOARD-004에서 사업자 회원 완료 성공 후 BIZ-001 경로로 이동한다.
2. 사업자등록번호 입력과 사업자등록증 선택 상태가 서로 독립적으로 유지된다.
3. 이미지가 아닌 파일은 거절하고 사용자가 이해할 수 있는 오류를 표시한다.
4. 선택한 이미지는 미리보기·파일명·변경·삭제 동작을 제공한다.
5. 사업자등록번호가 10자리가 아니거나 이미지가 없으면 제출하지 않는다.
6. 모든 필수 입력이 유효하면 제출 버튼을 사용할 수 있다.
7. 요청 중에는 입력 변경과 중복 제출을 막는다.
8. 더미 제출 성공 후 BIZ-001-2 인증 대기 화면으로 이동한다.
9. BIZ-001-2는 제출 정보와 사업자등록증 확인 UI를 표시한다.
10. 메인 이동 버튼을 누르면 로그인 상태를 유지한 채 HOME(`/`)으로 이동한다.
11. ONBOARD-001~004와 기존 인증 route에 회귀가 없다.
12. ESLint, type-check와 build가 통과한다.

## 확인이 필요한 미결정 사항

1. “사업자번호, 상호명, 대표자명 등”에서 기존 문서의 사업자등록증을 제외한 추가 입력
   필드가 있는지 확인이 필요하다.
2. BIZ-001-2 라우트 경로는 `/business/verification/pending`을 FE 경로로 사용할지
   확인이 필요하다.
3. 사업자등록번호 체크섬 검증을 FE에서도 적용할지, BE 응답만 기준으로 할지 확인이
   필요하다.
4. 허용 이미지 확장자와 MIME, 최대 용량, 최소 해상도 정책 확정이 필요하다.
5. multipart endpoint, 필드명, 성공 응답과 오류 필드명은 BE 확인이 필요하다.

## 범위 제외

- BE entity, DB migration, Controller와 Service 직접 구현
- 사업자 인증 심사·승인·반려 상태 관리
- MY-008 사업자 정보·인증 상태 관리
- 확정되지 않은 이미지 용량·해상도 제한
- 실제 사업자 인증 API 호출

## Git 작업 단위

- 브랜치: `feat/205-business-information-submission`
- 첫 번째 커밋:
  `[S15P11A108-397] feat: 사업자 인증 입력 화면 구현`
- 두 번째 커밋:
  `[S15P11A108-400] feat: 사업자 인증 입력 제약 구현`
- 각 작업은 자동 검증과 사용자 수동 검증을 마친 뒤 사용자가 직접 add, commit,
  push한다.
- 두 작업 커밋이 원격 스토리 브랜치에 모두 반영된 뒤 MR을 한 번 생성한다.
- MR 제목: `[BIZ] 사업자 정보 제출`
- MR 대상: `develop-FE`
