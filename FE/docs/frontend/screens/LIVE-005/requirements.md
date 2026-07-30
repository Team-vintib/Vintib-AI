# LIVE-005 라이브 시청 화면 요구사항

## 화면 목표

라이브 방송의 영상, 상품 큐와 방송 정보를 한 화면에서 확인한다. `S15P11A108-419`는
후속 채팅·경매·AI 시착 UI가 연결될 전체 배치와 영상 영역을 구현한다.

## 기준 자료

- Figma 배포 프로토타입 라이브 시청 화면
- `docs/notion/화면 기반 개발 요구 문서.md`
- `docs/notion/기능 정의서.md`
- `docs/notion/프론트엔드 디자인 구현 규칙.md`
- 2026-07-30 로컬 Swagger `VinTib API v0.1`
- `origin/develop-BE@dd6a0b6`의 최종 `009-live-list-api-contract.md`와
  `LiveDetailResponse`

## 화면 구조

- 상단: 뒤로가기, LIVE 상태, 방송 제목, 시청자 수, 경과 시간, 팔로우
- 왼쪽: 현재 소개 상품을 포함한 상품 큐
- 중앙: 라이브 영상 영역과 후속 채팅 overlay 영역
- 중앙 하단: 선택 상품의 이미지와 기본 정보, 상세 이동 action
- 영상 우측 하단: Figma와 같은 AI 시착 진입 버튼(상세 팝업·상태 로직 제외)
- 하단 오른쪽: 후속 실시간 경매 패널 영역

## S15P11A108-419 동작

- `/lives/:liveId` route로 진입한다.
- 상품 큐 항목을 선택하면 선택 상태와 하단 상품 정보가 함께 변경된다.
- 라이브 목록과 상품 상세의 기존 route에서 전달된 `liveId`를 사용한다.
- 실제 스트리밍 전에는 Figma prototype과 같은 mock poster를 표시한다.
- 화면별 mock query로 loading, error, not-found, empty-products, scheduled, ended를 확인한다.

## API와 mock 경계

`GET /api/lives/{liveId}`에서 확인된 필드만 실제 DTO 후보로 사용한다.

- 방송 ID, 호스트 ID·닉네임, 제목, 썸네일, 상태
- 예정·시작·종료 시각, 최고 시청자 수
- 편성 상품 ID·제목·정렬 순서
- 편성 상품에서 유도한 복수 카테고리 ID·이름

현재 계약에 없는 아래 값은 mock 전용 view model이다.

- 현재 동시 시청자 수
- 현재 소개 상품
- 상품 이미지, 브랜드, 가격, 소재, 상태, 실측과 하자 요약
- 영상 접속 토큰과 playback 정보

`peakViewerCount`는 현재 동시 시청자 수로 표시하지 않는다.
`009` 확정에 따라 현재 시청자 수는 `S15P11A108-450` 전까지 표시를 생략하며, 영상 접속
토큰은 `S15P11A108-449`에서 별도 연동한다.

## 상태

- loading: 전체 layout skeleton
- error: 재시도와 라이브 목록 이동
- not-found: 존재하지 않는 방송 안내
- empty-products: 영상은 유지하고 상품 큐와 선택 상품 빈 상태 표시
- scheduled: 예정 방송 상태와 예정 시각 표시
- ended: 종료 상태와 최고 시청자 정보 표시

## 제외 범위

- 실제 영상 송출·재생 SDK
- 채팅 메시지·입력·WebSocket
- 현재가·최고 입찰자·입찰 CTA와 경매 event
- AI 시착 진입 상태와 변경된 상세 팝업
- 팔로우·찜 실제 API

## 접근성

- 상품 큐는 현재 선택과 현재 소개 상태를 텍스트와 `aria` 상태로 함께 제공한다.
- 이미지에 방송·상품을 설명하는 대체 텍스트를 제공한다.
- 상태 안내는 적절한 `status` 또는 `alert` 역할을 사용한다.
- 모든 버튼은 키보드 focus가 보이도록 한다.
