# HS022 — TRYON-003 상품 상세 AI 시착 팝업

- Jira: S15P11A108-428 (`[TRYON-003 | FE] AI 시착 상세 팝업 구현`) / 에픽 S15P11A108-210 [TRYON]
- 브랜치: `feat/210-ai-tryon-entry-area` (에픽 210 재사용)

## 배경 / 목표

상품 상세(`ProductDetailView`)에 이미 "AI 시착" 버튼이 있으나, 누르면 `handleTryOn()`이 "상품 AI 시착 화면은 준비 중입니다" 토스트만 띄운다(`ProductDetailView.vue:140`). 이 자리를 **실제 AI 시착 팝업(모달)**으로 채운다. 기능 정의서 4.8 **TRYON-003 상품 가상 시착** = "등록 상품 이미지를 회원의 전신 사진에 합성". 라이브 시착 패널(`LiveTryOnPanel`, TRYON-004)은 이미 구현돼 있으니 **그 시착 흐름을 재사용**하고, 라이브 패널 자체는 수정하지 않는다.

## 현황

- 상품 상세: `ProductPurchaseSummary`의 "AI 시착" 버튼 → `openTryOn` emit → `ProductDetailView.handleTryOn`(준비 중 토스트). **팝업 미구현.**
- 라이브 시착: `LiveTryOnPanel.vue` 완성(mock). prop `product: LiveWatchProduct`, emit `close`, 상태 `EMPTY|READY|GENERATING|RESULT|ERROR`, 사진 등록/생성/결과/저장 흐름 보유.
- BE: 시착 **생성(POST)** 없음, **내 전신 사진 조회** 엔드포인트 없음. 시착 **결과 조회(GET)/삭제(DELETE)**만 존재.

## 작업 내용 (구두)

1. `ProductDetailView`에 시착 팝업(모달) 상태를 두고, `handleTryOn` → 모달 열기로 교체(토스트 제거).
2. 시착 UI/로직 **재사용**: 모달 컨테이너 안에서 `LiveTryOnPanel`을 그대로 사용(**라이브 패널 미수정**). 상품 상세 product를 패널이 받는 `LiveWatchProduct` 형태로 어댑트해 전달. `close` emit으로 모달 닫기.
   - 재사용에 라이브 패널 **수정이 불가피**하면(스타일/프롭 구조 등) 진행 전 사용자에게 공유하고 공용 컴포넌트 분리 여부를 정한다.
3. mock 유지: 전신 사진·시착 생성이 BE에 없어 mock 구동. "실제 저장/생성 API 연결 전" 안내 유지.
4. 없는 API 문서화(늘 하던 대로): `docs/requests/BE`에 (a) 내 전신 사진 조회, (b) 상품 시착 생성(합성) 요청을 007(3.3 생성 / 3.4 프로필)과 연계해 확인·보강.

## 구현 목록

- [x] `ProductDetailView`: 시착 팝업 상태(`isTryOnOpen`/`isTryOnExpanded`) + `handleTryOn` 교체(토스트 제거)
- [x] `LiveTryOnPanel` 재사용(미수정) + product 어댑터 + 팝업 래핑
- [x] 팝업 스타일: **우하단 고정 floating**(스크롤해도 보임, 뒤 페이지 조작 가능) + **확대 토글(전체 화면 모달)** + X 닫기/반응형
- [x] `docs/requests/BE/007`(3.6 상품 시착 생성 / 3.4 전신 사진 조회) gap 문서화
- [x] Vue 화면 확인: 상품 상세 → "AI 시착" → 작은 팝업 ↔ 확대 ↔ X 닫기 (사용자 확인 완료)

## 확인 필요 (미결정)

- 팝업 형태는 **모달**로 본다("상세 팝업"). 라이브는 사이드 패널이라, 모달에 패널 컴포넌트를 넣었을 때 스타일이 어색하면 모달 전용 래퍼로 보정.
- 재사용 시 `LiveTryOnPanel` 수정 필요하면 사전 공유(미수정 원칙).
- 시착 결과 저장(TRYON-005)은 "추가" 우선순위 → 이번 범위 밖(생성/표시까지). BE 저장 API도 미정.
