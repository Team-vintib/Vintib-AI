# 022 경매 진입 전 일괄 반영 — 남은 FE 항목

- **작성자 파트**: BE (정윤) / **대상 파트**: FE

## 반영 현황 (2026-08-04 확인)

원 문서의 대부분이 FE 코드에 반영됐다:

- ✅ **§1 시각 9시간 보정 훅 없음** — KST 벽시계 문자열을 그대로 파싱(`LiveWatchPage.vue` 등, `+9h`/`-9h` 보정 코드 없음)
- ✅ **§2.2 `isHost` 사용** — `hostId` 직접 비교 대신 응답 `isHost` 사용 + `GET /api/lives/{liveId}`에 인증 헤더 첨부 (`liveWatchApi.ts`, `LiveWatchPage.vue`, `LiveBroadcastPage.vue`)
- ✅ **§2.3 `/topic/lives/{liveId}/status` 구독** — 종료 시 시청 화면 전환
- ✅ **§3 홈 실데이터 전환**(mock 제거), **§4 통합 검색 실 API**, **§5 예약 라이브 알림 토글**

> ⚠️ **목록 화면 `isHost`(§2.2와 별개)는 아직**입니다 — `028-live-auto-start-isHost-viewercount.md` §2 참고.

## 남은 항목

- **§2.4 개설 요청 `description`(선택) 전송**: 개설 폼이 한 줄 소개(`description`)를 입력받지만(`LiveCreatePage.vue`), `CreateLiveRequest`(`liveCreateApi.ts`)와 `submitLiveCreate`가 이 값을 실어 보내지 않는다. `POST /api/lives`·`POST /api/lives/schedule` 본문에 `description`(선택, 최대 1000자)을 넣을 수 있다. 안 보내면 `null`이고 기존 요청은 그대로 동작한다.

## 시각 계약 (유지 — 배포 시 재확인)

> **모든 datetime 필드는 오프셋 없는 KST 벽시계다.** 뒤에 `Z`를 붙이거나 `.toISOString()` 왕복을 하면 다시 9시간이 틀어진다. 요청으로 보내는 시각(`scheduledAt` 등)도 같은 형식(로컬 벽시계)으로 보낸다.
