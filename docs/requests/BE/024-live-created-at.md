# 024 라이브 상세 응답에 생성 시각(createdAt) 추가 요청

- **요청자 파트**: FE (김현수)
- **대상 파트**: BE
- **관련 이슈**: FE `S15P11A108-563` [LIVE-005] 본인 생성 라이브 재입장 및 생성 시각 기준
- **작성일**: 2026-08-04

## 배경 / 이유

라이브 "시간"을 **생성 시각(createdAt) 기준**으로 다루려는 요구가 있다(경과시간 표시 등).
그런데 현재 라이브 상세(`GET /api/lives/{liveId}`) 응답에는 `scheduledAt`·`startedAt`·`endedAt`만
있고 **`createdAt`이 없다**(`LiveDetailDto`). 그래서 FE가 생성 시각 기준 계산을 할 수 없다.

> 참고: "생성 시각 기준"의 정확한 의미(경과시간 계산 기준인지, 표시/정렬 기준인지)는 팀 내에서 한 번 더
> 확정이 필요하다. 다만 어느 쪽이든 **상세 응답에 `createdAt`이 있어야** FE가 처리 가능하다.

## 요청 내용

- 라이브 상세(`GET /api/lives/{liveId}`) 응답에 **`createdAt`(생성 시각) 필드 추가**.
  - datetime 포맷은 기존 `scheduledAt`/`startedAt`과 동일(오프셋 없는 KST 벽시계) 권장.
- (가능하면) 목록(`GET /api/lives`) 응답에도 동일하게 추가하면 목록 표시/정렬에도 쓸 수 있음.

## 관련 자료

- FE 타입: `LiveDetailDto` / `LiveWatchViewData` (`FE/src/domains/live/types/liveWatch.types.ts`) — 현재 createdAt 없음
- 경과시간 계산: `LiveBroadcastPage.vue` / `LiveWatchPage.vue`의 `elapsedSeconds`(현재 `startedAt` 기준)
