# HS021 — LIVE-005 시청자 화면 API 연결

- Jira: S15P11A108-430 (`[LIVE-005 | FE] 시청자 화면 API 연결 구현`) / 에픽 S15P11A108-217 [LIVE]
- 브랜치: `feat/217-viewer-screen-api`

## 배경/목표

라이브 시청자 화면(`LiveWatchPage`)을 실 BE API에 연결한다. 조사 결과 **핵심 연결은 이미 되어 있다**:
`.env.local`의 `VITE_LIVE_WATCH_API_ENABLED=true`로 `GET /lives/{liveId}`(라이브 상세)와 STOMP(chat/reactions/viewers) 실연동 경로가 동작한다.
따라서 이 작업의 실제 범위는 **① 배포 서버 대상 실연결 검증 → ② BE가 아직 주지 않는 필드(gap) 처리·요청 → ③ 연결 가능한 나머지 배선**이다.

## 현재 연결 상태 (조사 결과)

- ✅ 라이브 상세: `liveWatchApi.requestLiveWatch()` → `GET /lives/{liveId}` (비회원 `skipAuth`). `LiveDetailResponse` 매핑됨.
- ✅ 실시간: `LiveChatOverlay` + `liveRealtimeClient`가 `/ws` 접속, `/topic/lives/{id}/chat|reactions|viewers` 구독. 시청자 수 → `updateViewerCount`.
- ⚠️ 상품 카드 상세 필드는 `mapLiveProductDto`에서 전부 `null` 하드코딩 (`liveWatchApi.ts:44-52`) — BE `LiveProductResponse`가 `productId/productTitle/sortOrder`만 줌.
- ⚠️ `currentProductId` 항상 `null` (`liveWatchApi.ts:69`) — BE가 "현재 판매 상품" 미제공 → 초기 선택은 첫 상품 fallback.
- ⚠️ `hostProfileImageUrl`, `description` `null` — BE `LiveDetailResponse` 미제공.
- ⚠️ 팔로우 버튼(`isFollowing`), 찜(`wishedProductIds`)은 현재 **로컬 상태**만. (팔로우 API 미구현, 찜 API는 존재)

## 작업 내용

1. **실서버 검증**: 배포 서버(`https://i15a108.p.ssafy.io/api`) 대상으로 라이브 시청 진입 → 상세 렌더/로딩·에러·not-found 상태, STOMP 채팅·반응·시청자수 수신 확인. (앱 실행 검증, 코드 변경 최소)
2. **BE gap 문서화**: BE가 안 주는 필드/엔드포인트를 `docs/requests/BE/`에 요청 문서로 정리. FE는 임의 확정 없이 `null` 유지 + `BE 확인 필요` 표시.
3. **연결 가능한 배선**: BE가 이미 주는데 FE가 아직 안 쓰는 값이 있으면 매핑 보강. (현재로선 추가 필드 없음 — 검증으로 확인)
4. 찜(위시) API가 시청 화면 상품 카드에 연결 가능한지 검토 후 스코프 결정.

## 구현 목록

- [x] `.env.example`에 `VITE_LIVE_WATCH_API_ENABLED=true` 추가 (실 API 연결 기본값 문서화)
- [x] `docs/requests/BE/007`(3.5)에 라이브 상품 카드 상세 필드 확장 요청 (brand/price/thumbnail/saleType/condition 등)
- [x] `docs/requests/BE/007`(3.5)에 `currentProductId`·host 프로필·description 요청
- [x] `liveWatchApi.ts`의 null gap 필드에 `BE 확인 필요` 주석 + 요청 문서 위치 표기
- [x] 팔로우 API는 BE 미구현(`008-social-notification`에 기재) → 시청 팔로우 버튼은 API 확정 후 연결, 이번 스코프 밖 명시
- [ ] (사용자) 로컬 `npm run dev` + 멀티탭으로 라이브 상세·채팅·반응·시청자 수 실연결 최종 확인

## 확인 필요 (미결정)

- 팔로우/찜은 별도 에픽(follow/product) 소관 — 시청 화면에서 어디까지 LIVE-005 범위로 볼지 확정 필요.
- 영상 스트리밍(OpenVidu 등) 토큰 발급은 별도 작업(-449 언급)으로 이 작업 범위 밖으로 본다.
- **FE 배포(HS020) 시 주의**: 현재 FE는 미배포. 배포할 때 프로덕션 빌드 env에 `VITE_LIVE_WATCH_API_ENABLED=true`를 포함해야 배포본도 실 API로 붙는다. (`.env.example`은 Vite가 빌드 시 읽지 않으므로 문서용)
