# 라이브 판매자 제어 — 방송 종료 · 현재 상품 전환

- **요청자 파트**: FE
- **대상 파트**: BE
- **관련 이슈**: FE `S15P11A108-437`(상품 전환·종료 버튼), 스토리 `-86`[LIVE-003], 에픽 `-217`[LIVE]
- **관련 기능**: LIVE-003(라이브 상품 연결), LIVE-004(실시간 상품 큐레이션)
- **상태**: 현재 소개 상품 전환 트리거만 남음(방송 종료는 처리 완료 — `docs/requests/FE/013-live-auction-corrections.md` 참고)

## 배경/이유

판매자 방송 화면(`/lives/:liveId/broadcast`)에 **방송 종료**와 **현재 소개 상품 전환** 버튼을
구현했다. 두 동작 모두 판매자(호스트)만 하는 서버 상태 변경인데, 현재 계약에 트리거 엔드포인트가
없어 화면 상태만 바꾸는 mock으로 두었다. 실제 반영과 시청자 전파를 위해 아래가 필요하다.

(경매 시작/입찰/종료 실시간 이벤트는 `009-auction-chat-contract.md`에서 이미 요청 중이므로 중복
요청하지 않는다. 시청자용 현재 상품 토픽 `/topic/lives/{id}/product`는 `docs/requests/FE/001`의
Phase 5로 예고돼 있어, 여기서는 **판매자 트리거 쪽**만 요청한다.)

## 요청 내용

### 2. 현재 소개 상품 전환 (호스트)

- 라이브에 연결된 상품 중 하나를 "현재 소개 상품(NOW)"으로 지정하는 엔드포인트.
  예: `PATCH /api/lives/{liveId}/current-product` body `{ productId }` (또는 BE가 정하는 형태)
- 호스트 본인만 허용, 연결되지 않은 상품이면 에러.
- 라이브 상세(`GET /api/lives/{liveId}`)의 `currentProductId`가 이 값으로 갱신돼야 한다.
  (`currentProductId` 필드 자체는 `007-live-tryon-contract.md` 3.5에서 이미 요청 중)
- 전환 시 **시청자에게 넘어가는 알림**(시스템 채팅 메시지 or 현재 상품 토픽 브로드캐스트)이
  필요하다. 방식이 `/topic/lives/{id}/product`(FE 001 Phase 5)로 정해지면 payload 형태를 알려주면
  FE가 mock을 실제 구독으로 교체한다.

## 확인 부탁

- endpoint/method/body 형태 (FE는 확정 전까지 mock 유지)
- 시청자 전파: 전환을 STOMP로 브로드캐스트하는지, 한다면 토픽/payload
