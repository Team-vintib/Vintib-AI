# 026 라이브 목록 최신순(LATEST) 정렬을 생성 시각(createdAt) 기준으로

- **요청자 파트**: FE (김현수)
- **대상 파트**: BE
- **관련 이슈**: FE `S15P11A108-563` [LIVE-005] 라이브 생성 시각 기준
- **작성일**: 2026-08-04

## 배경 / 이유

라이브 목록을 "최근순"으로 볼 때 기준을 **생성 시각(createdAt)** 으로 하려 한다.

- **즉시 시작** 라이브는 시작 시각 ≈ 생성 시각이지만, **예약 시작** 라이브는 시작 시각(scheduledAt) ≠ 생성 시각이다.
- 그래서 "최근에 만든 순"으로 정렬하려면 startedAt/scheduledAt이 아니라 **createdAt** 기준이어야 한다.

FE는 이미 목록을 서버 사이드 정렬로 요청한다(`GET /api/lives?sort=LATEST`) — 정렬 기준은 BE가 정한다. 즉 FE 코드 변경 없이 **BE의 `LATEST` 정렬 기준만 createdAt으로** 하면 된다.

## 요청 내용

- `GET /api/lives`의 **`sort=LATEST`를 `createdAt` 내림차순(최신 생성 먼저)** 으로 정렬해 주세요.
  - (현재 startedAt/scheduledAt 기준이면 예약 라이브가 생성 순서와 다르게 섞입니다.)
- 가능하면 목록 응답에도 `createdAt`을 포함해 주세요(관련: `docs/requests/BE/024-live-created-at.md` — 상세 응답 createdAt 요청과 함께).

## 관련 자료

- FE: `LiveListView.vue`(기본 `sort='LATEST'`), `liveListApi.ts`(sort 파라미터 서버 전달)
- 함께 볼 것: `024-live-created-at.md`(라이브 상세 createdAt 요청)
