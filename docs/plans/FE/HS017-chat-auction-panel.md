# AUCT-003~006 채팅·경매 패널 UI

## 배경/목표

`S15P11A108-423`에서 `LIVE-005` 시청 화면에 Figma 기준 채팅 overlay와 실시간 경매
패널 UI를 연결한다. 더미 데이터와 로컬 UI 상태까지만 구현하고 실제 채팅·입찰 API,
WebSocket/STOMP와 서버 경매 판정은 연결하지 않는다.

## 기준 자료

- Figma 배포 프로토타입 라이브 시청 화면
- `FE/docs/notion/화면 기반 개발 요구 문서.md`
- `FE/docs/notion/기능 정의서.md`
- `FE/docs/notion/프론트엔드 디자인 구현 규칙.md`
- `FE/docs/frontend/screens/LIVE-005/requirements.md`
- `.codex/requests/be/012-live-watch-detail-contract-gaps.md`
- `S15P11A108-419`에서 구현한 라이브 시청 화면 컴포넌트

`012`에 채팅, 경매 snapshot·입찰·event와 반응 이모지 계약이 이미 정리돼 있으므로
현재 확인 범위에서는 새 BE 요청 문서를 만들지 않는다. 구현 중 `012`에 없는 계약이 실제로
발견될 때만 다음 번호 요청 문서를 추가한다.

## 작업 내용

### 채팅 overlay

- 영상 왼쪽 중앙에 하트·불·박수·놀람 반응 버튼을 세로로 배치한다.
- 영상 왼쪽 하단에 Figma 더미 메시지 목록과 채팅 입력창·전송 버튼을 배치한다.
- 판매자 메시지는 일반 시청자 메시지와 색상으로 구분한다.
- 긴 메시지, 목록 overflow와 스크롤, 빈 입력, 방송 종료 상태를 표현한다.
- 전송은 네트워크 요청 없이 로컬 mock 메시지만 추가하고, 이모지는 로컬 누름 효과만 제공한다.

### 경매 패널

- Figma 기준 380px 패널에 현재 입찰가, 다음 입찰가, 남은 시간, 최고 입찰자와 사용 가능
  포인트를 표시한다.
- 다음 입찰가를 포함한 Auction Red 입찰 CTA를 제공한다.
- 더미 상태로 기본 입찰 가능, 처리 중, 최근 입찰자 연속 입찰 제한, 포인트 부족,
  예정·종료·상품 없음 상태를 구분한다.
- 로컬 mock 입찰은 중복 클릭을 막고 화면 상태만 전환한다. 서버 선착순 판정, 포인트 보류,
  자동 연장과 낙찰 처리는 구현하지 않는다.

### 컴포넌트 경계

- `domains/chat`에 라이브 채팅 overlay의 컴포넌트·타입·mock 상수를 둔다.
- `domains/auction`에 시청자 경매 패널의 컴포넌트·타입·mock 상수를 둔다.
- `LiveVideoStage`에는 채팅 UI를 직접 구현하지 않고 overlay slot을 제공한다.
- `LiveWatchPage`가 LIVE 화면에서 CHAT과 AUCT 컴포넌트를 조립한다.
- 기존 `LiveWatchSidePanel`은 삭제하지 않고 후속 정리 전까지 보존한다.

### 문서

- `FE/docs/frontend/screens/LIVE-005/requirements.md`에 423 UI 범위와 mock/API 경계를 추가한다.
- `FE/docs/frontend/screens/AUCT-003-006/requirements.md`를 작성한다.
- `FE/docs/frontend/implementation/current-structure.md`와 `status.md`를 갱신한다.
- route는 바뀌지 않으므로 `route-map.md`는 구현 상태 설명만 필요한 경우에 한해 갱신한다.

## 제외 범위

- 실제 WebSocket/STOMP 연결, 과거 채팅 조회와 재접속
- 실제 채팅 전송·moderation·AI 답변
- 실제 경매 snapshot·입찰·입찰 내역·실시간 event
- 서버 기준 중복 클릭·선착순·연속 입찰 제한 판정
- 포인트 보류·해제, 낙찰·유찰과 주문 생성
- 변경된 AI 입어보기 상태와 상세 팝업

## 구현 목록

- [x] 채팅·경매 화면 요구사항 문서 작성
- [x] 채팅 메시지·반응 mock 타입과 데이터 정의
- [x] Figma 채팅 overlay와 입력 UI 구현
- [x] 경매 snapshot·입찰 상태 mock 타입과 데이터 정의
- [x] Figma 실시간 경매 패널과 상태별 CTA 구현
- [x] 라이브 영상 overlay slot과 페이지 조립
- [x] 1280px Figma 비율과 좁은 화면 반응형 확인
- [x] 빈 입력·중복 클릭·포인트 부족·종료 상태 확인
- [x] 구현 구조와 상태 문서 갱신
- [x] 변경 파일 ESLint·type-check·build 검증
- [x] 실제 Vue 화면에서 채팅·경매 UI 수동 확인

## Git 및 MR 작업 단위

- 브랜치: `feat/209-chat-auction-panel`
- 스토리: `S15P11A108-423`
- 커밋은 실제 작업 단위별로 한글 내용으로 나눈다.
- MR 제목: `[AUCT] 채팅·경매 패널 UI 구현`
- MR 대상: `develop-FE`
- push는 사용자가 직접 수행한다.
