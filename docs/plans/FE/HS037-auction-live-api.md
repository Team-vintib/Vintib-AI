# HS037 — 라이브 경매·방송 결과 API 연동

- Jira: `S15P11A108-432`, `S15P11A108-436`, `S15P11A108-438`,
  `S15P11A108-440`, `S15P11A108-441` / 에픽 `S15P11A108-209` `[AUCT]`
- 브랜치: `feat/209-auction-live-flow`

## 배경/목표

라이브 시청·판매자 방송 화면에 남은 경매 mock을 실제 REST·STOMP 계약으로 교체한다.
시청자는 서버가 내려준 다음 입찰가를 밀어서 입찰하고, 판매자는 경매 시작부터 방송 종료
요약·유찰 상품까지 실제 결과를 확인한다.

## 기준 자료

- `FE/docs/notion/기능 정의서.md` AUCT-001~014
- `FE/docs/notion/화면 기반 개발 요구 문서.md` LIVE-005/AUCT
- `FE/docs/frontend/screens/AUCT-003-006/requirements.md`
- `FE/docs/frontend/screens/LIVE-005/requirements.md`
- `docs/requests/FE/024-auction-snapshot-start-contract.md`
- `docs/requests/FE/025-auction-bid-contract.md`
- `docs/requests/FE/030-auction-close-contract.md`
- `docs/requests/FE/031-broadcast-summary-unsold-contract.md`
- 실제 BE `auction` Controller·DTO·STOMP 계약

## 작업 내용

- 경매 공용 타입과 API adapter를 추가해 현재 경매 조회, 설정, 시작, 입찰, 결과 조회,
  방송 요약과 유찰 목록을 실제 응답 구조로 통일한다.
- 라이브의 기존 STOMP 연결 하나에 경매 토픽을 추가하고 snapshot 전체를 교체하여
  시작·입찰·자동 연장·종료를 반영한다.
- 시청자 입찰 CTA는 클릭 버튼이 아닌 밀어서 완료하는 방식으로 구현한다. 처리 중·비회원·
  최고 입찰자·포인트 부족·종료 상태를 구분하고 서버 오류 시 최신 snapshot을 다시 조회한다.
- 판매자 패널은 조건 저장 후 반환된 경매 ID로 실제 시작 API를 호출하며, 실시간 snapshot으로
  현재가·최고 입찰자·입찰 수·연장 횟수·종료 결과를 표시한다.
- 방송 종료 시 summary와 유찰 목록을 조회해 대시보드와 남은 상품 관리 화면을 채우고,
  해당 경로의 mock 결과 생성과 query 시나리오를 제거한다.

## 구현 목록

- [x] 경매 REST API·DTO·오류 메시지 adapter 추가
- [x] 경매 STOMP 이벤트 타입과 snapshot 검증·공유 상태 연결
- [x] 시청자 현재 경매 조회와 밀어서 입찰 UI 구현
- [x] 판매자 경매 설정·시작·진행·종료 실 API 연결
- [x] 낙찰 오버레이를 `AUCTION_CLOSED` 실제 결과로 연결
- [x] 방송 종료 summary·유찰 목록 API 연결
- [x] 실제 연결로 대체된 경매·종료 mock 제거
- [x] 구현 상태 문서 갱신
- [x] ESLint·TypeScript·프로덕션 빌드 검증
- [ ] 배포 BE 환경에서 판매자·시청자 동시 접속 E2E 검증

## 확인 사항

- 남은 시간은 `endsAt - serverNow`로 맞추고, 0초가 되어도 서버의 `AUCTION_CLOSED` 전에는
  임의로 낙찰·유찰 처리하지 않는다.
- 입찰 금액은 FE에서 계산하지 않고 snapshot의 `nextBidPrice`를 그대로 보낸다.
- 방송 종료 시에는 경매 종료 이벤트가 별도로 오지 않으므로 summary API를 결과 기준으로 쓴다.
- AI 시착 등 이번 경매 흐름과 무관한 mock은 유지한다.

## 구현 결과

- 변경 파일 대상 ESLint, `vue-tsc --build`, Vite 프로덕션 빌드 통과
- 실제 BE 경매·방송 종료 Controller/DTO와 FE 요청 계약이 일치해 별도 BE 요청 문서는 추가하지 않음
- 실시간 판매자·시청자 동시 경매, 포인트 hold/release, 자동 종료 결과는 배포 BE 환경에서 최종 확인 필요
