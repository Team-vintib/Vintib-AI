# NOTI 알림 센터와 공통 팝업

## 배경/목표

상위 작업 `S15P11A108-420`, `S15P11A108-421`의 알림 관련 FE 화면을 구현한다.
현재 placeholder인 `/notifications`를 실제 알림 센터로 교체하고, 공통 헤더에서 사용할
알림 팝업과 안 읽은 알림 배지를 연동한다.

## Jira별 구현 범위

### S15P11A108-420 — 알림 목록·필터 UI 구현

- 알림 도메인 전용 DTO, 화면 모델, API adapter를 정의한다.
- `/notifications` route의 placeholder를 실제 알림 센터 View로 교체한다.
- 전체, 라이브, 경매, 거래, 배송, 포인트 탭을 구현한다.
- 알림 카드에 타입별 아이콘/배지, 제목, 본문, 생성 시각, 읽음/안읽음 상태를 표시한다.
- 목록 loading, empty, error, filter-empty 상태와 retry 동작을 제공한다.
- 모두 읽음 버튼을 제공하고 성공 후 현재 목록과 안 읽은 개수를 갱신한다.
- 알림 카드 선택 시 단건 읽음 처리 후 연결 리소스로 이동한다.
- 연결 라우트가 아직 없거나 `refType/refId`가 부족한 알림은 이동 실패 안내로 처리한다.

### S15P11A108-421 — 공통 알림 팝업 구현

- `GlobalNavigation`의 알림 액션에 팝업을 연결한다.
- 팝업에는 최근 알림 일부, 안 읽은 상태, 모두 읽음, 알림센터 이동을 제공한다.
- 팝업과 알림 센터가 같은 API/composable 또는 store 상태를 공유하도록 구성한다.
- 팝업에서 읽음 처리한 결과가 헤더 배지와 알림 센터 목록에 반영되게 한다.
- 모바일 폭에서는 팝업이 화면 밖으로 넘치지 않도록 반응형 배치를 적용한다.

## BE API 확인 결과

- 실제 구현 API는 `APIs.md` 후보의 `/api/notifications`가 아니라
  `/api/users/{userId}/alerts` 계열이다.
- 목록 조회: `GET /api/users/{userId}/alerts?unreadOnly=false&page=0&size=20`
- 단건 읽음 처리: `PATCH /api/users/{userId}/alerts/{id}`
- 전체 읽음 처리: `PATCH /api/users/{userId}/alerts/read-all`
- 목록 응답은 BE 공통 `PageResponse` 구조인
  `content`, `page`, `size`, `totalElements`, `totalPages`, `hasNext`를 사용한다.
- 알림 아이템 필드는 `id`, `type`, `title`, `body`, `refType`, `refId`, `isRead`, `createdAt`이다.
- BE 정렬은 안 읽은 알림 우선, 최신순으로 고정되며 클라이언트 `sort`는 무시된다.
- 서버 카테고리 필터는 없으므로 탭 필터는 FE에서 `type` 또는 `refType` 기준으로 처리한다.

## 예상 파일 구조

```text
FE/src/domains/notification/
  api/
    notificationApi.ts
  components/
    NotificationCard.vue
    NotificationCenterState.vue
    NotificationPopup.vue
  constants/
    notificationOptions.ts
  pages/
    NotificationCenterPage.vue
  stores/
    notificationStore.ts
  types/
    notification.types.ts
```

## 구현 목록

- [x] NOTI 타입, 탭 옵션, refType 라우팅 매핑 정의
- [x] BE `PageResponse`를 FE 목록 모델로 변환하는 notification API adapter 구현
- [x] 알림 목록/읽음 처리/전체 읽음 상태를 관리하는 store 또는 composable 구현
- [x] 알림 카드 컴포넌트 구현
- [x] 알림 센터 탭, 목록, 모두 읽음, 상태 화면 구현
- [x] BE 페이지네이션 `hasNext` 기준 전체 탭 더보기 구현
- [x] `/notifications` placeholder를 알림 센터 View로 교체
- [x] 알림 팝업 컴포넌트 구현
- [x] `GlobalNavigation` 알림 버튼, unread badge, 팝업 연동
- [x] 알림 클릭 시 단건 읽음 처리와 연결 route 이동 구현
- [x] 수동 화면 확인용 `mock=default|empty|error|loading` query 지원
- [x] `api-index.md`, `route-map.md`, `screen-inventory.md`, `current-structure.md`, `status.md` 갱신
- [x] `npm run type-check` 검증

## 확인이 필요한 미결정 사항

- `type` 값 전체 목록과 각 값의 탭 분류 기준이 BE에서 고정되어 있는지 확인이 필요하다.
- 안 읽은 알림 개수 전용 API가 없어 팝업/헤더 배지 계산 방식은 FE 조회 결과 기준으로 시작한다.
- `refType`별 최종 이동 route가 아직 모두 구현되지 않았다. 우선 존재하는 `LIVE`, `PRODUCT`,
  `POINT`, `MY` 중심으로 연결하고 주문/배송/경매 상세 route는 준비 상태 안내 또는 추후 매핑으로 둔다.
- 서버 페이지네이션과 FE 탭 필터를 함께 사용할 때 전체 탭별 개수가 정확하지 않을 수 있다.
  MVP에서는 첫 페이지 기반 필터로 시작하고, 정확한 탭별 count가 필요하면 BE에 필터/count API를 요청한다.

## Git 및 MR 작업 단위

- 기준: 최신 `develop-FE`
- 브랜치 후보: `feat/420-421-notification`
- 커밋 1: `[S15P11A108-420] feat: 알림 목록 및 필터 UI 구현`
- 커밋 2: `[S15P11A108-421] feat: 공통 알림 팝업 구현`
- push는 사용자가 직접 수행한다.
