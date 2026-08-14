# CH002 로컬 워커 중단 안내 배너

## 배경/목표

가상 시착/상품 분류/품질 검수 로컬 워커가 꺼져 있는 동안(발표·시연 대응), 전역 네브 바로 아래에 항상 따라다니는 공지 배너를 띄운다. (`docs/requests/FE/038-local-worker-off-notice-banner.md` 요청을 FE 담당자 본인이 직접 반영)

## 작업 내용

- 새 컴포넌트 `AppWorkerOffNotice.vue`(`shared/components/`)를 만들어 고정 문구를 렌더링한다. 하드코딩된 static 배너로 API 연동 없음.
- `DefaultLayout.vue`에서 `GlobalNavigation`과 새 배너를 공통 `sticky` 래퍼 div로 감싸 둘이 한 덩어리로 스크롤에 따라다니게 한다(`GlobalNavigation` 자체의 `position: sticky` 로직은 손대지 않음).
- 색상은 브랜드 레드 토큰(`--color-accent` / `--color-primary-hover`, `#c43d46`) 배경 + 흰 텍스트로 로고 톤과 맞춘다.
- 다른 레이아웃(`AuthLayout`, `LiveLayout`)에는 적용하지 않는다 — 우선 `DefaultLayout` 적용 화면(일반 페이지)에만 노출.
- 닫기 버튼 없음(항상 노출, 세션 내내 유지).

## 구현 목록

- [ ] `FE/src/shared/components/AppWorkerOffNotice.vue` 신규 작성 (문구 하드코딩, 반응형 줄바꿈)
- [ ] `FE/src/shared/layouts/DefaultLayout.vue` — `GlobalNavigation` + 새 배너를 sticky 래퍼로 감싸기
- [ ] 데스크톱/모바일 폭에서 텍스트 줄바꿈 확인

## 미결정 사항 (기본값으로 진행, 필요시 조정)

- 닫기 가능 여부 → 기본: 닫기 없음
- 적용 레이아웃 범위 → 기본: `DefaultLayout`만
