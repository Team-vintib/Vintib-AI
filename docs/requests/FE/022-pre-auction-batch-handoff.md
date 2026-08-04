# 022 경매 진입 전 일괄 반영 — 남은 FE 항목

- **작성자 파트**: BE (정윤) / **대상 파트**: FE

> 대부분(§1 시각 보정 없음, §2.2 상세 `isHost`, §2.3 status 구독, §3 홈 실데이터, §4 통합 검색, §5 예약 알림 토글)은 반영 완료되어 덜어냈다. §2.4 1건 + 시각 계약만 남긴다.

## 남은 항목

- **§2.4 개설 요청 `description`(선택) 전송**: 개설 폼이 한 줄 소개(`description`)를 입력받지만(`LiveCreatePage.vue`), `CreateLiveRequest`(`liveCreateApi.ts`)와 `submitLiveCreate`가 이 값을 실어 보내지 않는다. `POST /api/lives`·`POST /api/lives/schedule` 본문에 `description`(선택, 최대 1000자)을 넣을 수 있다. 안 보내면 `null`이고 기존 요청은 그대로 동작한다.

## 시각 계약 (유지 — 배포 시 재확인)

> **모든 datetime 필드는 오프셋 없는 KST 벽시계다.** 뒤에 `Z`를 붙이거나 `.toISOString()` 왕복을 하면 다시 9시간이 틀어진다. 요청으로 보내는 시각(`scheduledAt` 등)도 같은 형식(로컬 벽시계)으로 보낸다.
