# SY032 — 디자인 토큰 정리 리팩토링

## 배경/목표

FE는 이미 `src/assets/main.scss`의 `:root`에 색상/spacing/radius/버튼높이/타이포 등 ~65개 CSS 커스텀 프로퍼티를 선언해두었고, 대부분의 컴포넌트가 `<style scoped lang="scss">`에서 `var(--...)`를 참조하는 패턴을 쓰고 있다(색상 토큰화율 약 95%). Tailwind는 v4 CSS-first 방식(`@tailwindcss/vite`, `tailwind.config.*` 없음)이다.

남은 문제: 폰트 사이즈(토큰 3개뿐인데 26종+ px가 694회 하드코딩), transition/duration(토큰 없음, `160ms ease` 138회 등 이미 값은 통일됨), z-index(토큰 없음, 41회 매직넘버), 잔여 hex/rgba(~32건/~72건, 기존 토큰과 중복되거나 완전 신규 색상), box-shadow(1건). 목표는 화면상 픽셀/색상/타이밍이 하나도 달라지지 않는 순수 리팩토링으로 이 잔여 하드코딩을 `main.scss` 토큰 참조로 정리하는 것.

## 작업 내용

- 값을 "가까운 표준값"으로 바꾸지 않는다. 발견된 값과 정확히 같은 값의 변수로 매핑하거나, 없으면 그 값 그대로 `main.scss`에 새 변수를 추가한 뒤 참조로 교체한다.
- "체계적 값"만 토큰화한다: 2회 이상 반복되거나 기존 스케일(4px 배수 spacing 등)에 들어맞는 값만. 컴포넌트 1회성 수치(예: 특정 아바타 38px)는 하드코딩으로 남긴다.
- rgba는 `color-mix()`로 바꾸지 않고 값 그대로 담은 rgba 변수를 추가한다(가장 단순하고 오차 없음).
- 신규 브랜드색은 문맥을 읽어 의미 있는 이름을 붙이되 값은 유지한다.
- auth 도메인의 `text-[13px]` 류 Tailwind arbitrary-value는 `text-[var(--font-size-caption)]`처럼 토큰을 감싸는 형태로 바꾼다. 전체 유틸리티 전환은 하지 않는다(기존 scoped SCSS + var() 패턴 유지).
- `main.scss`에 typography scale, transition/duration, z-index scale, shadow, overlay/scrim 섹션을 신설하고 배치 진행하며 값을 채운다.
- 도메인별 순차 배치로 진행: ① shared ② auth+home ③ live+auction+chat ④ product+my+tryon ⑤ biz+notification+onboard+point+profile+search. `order`/`refund`/`shipping`/`follow`/`recommendation`은 빈 스캐폴드라 대상 없음.
- 배치마다 `npm run type-check` + `npm run build`로 검증, 의심스러운 부분은 `npm run dev`로 목검증.

## 구현 목록

- [x] 계획 문서 작성
- [x] `main.scss` 토큰 뼈대 확장 (typography/transition/z-index/shadow/overlay 섹션 신설, 배치 진행하며 값 채움)
- [x] 배치1 — shared 공통 컴포넌트/레이아웃
- [x] 배치2 — auth, home
- [x] 배치3 — live, auction, chat
- [ ] 배치4 — product, my, tryon
- [ ] 배치5 — biz, notification, onboard, point, profile, search
- [ ] 전체 완료 후 `npm run type-check` + `npm run build` 최종 확인
- [ ] `FE/README.md` 스타일 기준 섹션 갱신 검토(필요 시만)
