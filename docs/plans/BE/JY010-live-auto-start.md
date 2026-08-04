# JY010 예약 라이브 자동 시작

## 배경/목표

예약 라이브(`SCHEDULED`)는 예정 시각이 지나도 자동으로 `LIVE`가 되지 않는다 — 상태 전이는
`PATCH /api/lives/{liveId}/status`를 호스트가 직접 호출해야만 일어난다(`LiveReminderScheduler`는
알림만 보내고 상태는 건드리지 않는다). 그 결과 호스트가 깜빡하면 방송이 영원히 "예정"에 머물고,
홈 화면 `liveNow`/`scheduledLives`(시간 지난 예약은 제외)에서도 조용히 사라진다. 예정 시각이 되면
서버가 알아서 `LIVE`로 넘겨야 한다.

## 작업 내용

- `LiveReminderScheduler`와 같은 패턴의 새 `@Scheduled` 스케줄러를 만들어, 예정 시각이 지난
  `SCHEDULED` 라이브를 주기적으로 찾아 `LIVE`로 전이시킨다.
- 전이 로직은 새로 만들지 않고 기존 `LiveService.transitionStatus(hostId, liveId, request)`를
  그대로 재사용한다 — 호스트 ID를 그 라이브의 실제 호스트로 채워 호출하면 `isHostedBy` 검증도
  자연히 통과하고, room 배정·`LIVE_STARTED` 팔로워 알림까지 수동 시작과 동일한 경로를 탄다.
- 상태 전이 브로드캐스트(`/topic/lives/{liveId}/status`)는 현재 컨트롤러에만 있다. 스케줄러는
  컨트롤러를 거치지 않으므로, 전이에 성공한 라이브마다 스케줄러가 직접
  `SimpMessagingTemplate`로 같은 payload(`LiveStatusResponse`)를 쏜다.
- 한 라이브의 전이 실패(예: room 배정 예외)가 나머지를 막지 않도록 라이브 단위로 예외를
  잡는다 — 배치 전체가 한 번의 실패로 멈추면 안 된다.
- 폭주 방지로 한 번에 처리하는 상한을 둔다(다른 배치 상한들과 같은 이유) — 남는 건 다음 주기에
  마저 처리된다.
- 주기는 30초(`fixedDelay`)로 잡는다 — 알림(`LiveReminderScheduler`, 60초)보다 짧게 잡아
  "예정 시각에 방송이 켜진다"는 체감을 확보한다.

## 구현 목록

- [ ] `LiveRepository`에 `findByStatusAndScheduledAtLessThanEqual(status, now, pageable)` 추가
- [ ] `LiveService.autoStartDueLives()`: 대상 조회 → 라이브별 `transitionStatus` 호출(예외는
      개별적으로 잡고 로그만 남김) → 성공한 것들의 `LiveResponse` 목록 반환
- [ ] `LiveAutoStartScheduler`(`@Scheduled(fixedDelay = 30_000)`): `autoStartDueLives()` 호출 후
      결과마다 `/topic/lives/{liveId}/status` 브로드캐스트
- [ ] 테스트: 서비스 단위(예정 시각 지난 것만 전이되는지, 실패한 라이브가 있어도 나머지는
      전이되는지), 필요하면 스케줄러 통합 테스트
