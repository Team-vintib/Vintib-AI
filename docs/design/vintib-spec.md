# VinTib 디자인 스펙 (정밀판)

> `VinTib.dc.html`을 픽셀 단위로 재현하기 위한 **권위 있는 기준 문서**. 요약본(프롬프트용 규칙)보다 이 문서가 우선한다.
> 모든 값은 실제 파일에서 그대로 가져온 것. FE 리디자인(`docs/plans/FE/HS030`)은 이 스펙을 기준으로 구현한다.
> 원본은 인라인 스타일/클래스 없음 기준이지만, 우리 앱은 `main.scss` 토큰 + 컴포넌트 scoped 스타일로 옮긴다. 토큰 매핑은 §1 참조.

## 0. 문서 기본 / 폰트

```
Archivo:wght@400;500;600;700
IBM+Plex+Sans+KR:wght@300;400;500;600;700
IBM+Plex+Mono:wght@400;500
```

루트: `background:#0A0A0A; color:#F2F0ED; font-family:'IBM Plex Sans KR'; -webkit-font-smoothing:antialiased`.
전역: `* box-sizing:border-box`, `a{color:#F2F0ED} a:hover{color:#C43D46}`, `img{display:block}`,
`::selection{background:#C43D46;color:#0A0A0A}`, 스크롤바 track `#0A0A0A`/thumb `#2A2827` (8px).
키보드 포커스: `:focus-visible { outline:1px solid #F2F0ED; outline-offset:2px }`.

## 1. 컬러 → 토큰 매핑

| 역할 | 값 | 토큰 |
|---|---|---|
| canvas | `#0A0A0A` | `--color-page` |
| chrome bar | `#050505` | `--color-chrome` |
| hover surface | `#141312` | `--color-surface` |
| soft surface | `#101010` | `--color-surface-secondary` |
| panel(경매) | `#100F0E` | `--color-surface-raised` |
| image bed | `#131211` | `--color-image-frame` |
| line | `#232120` | `--color-border` |
| line faint | `#1B1918` | `--color-border-grid` |
| line input | `#2A2827` | `--color-border-input` |
| line mid | `#3A3735` | `--color-border-strong` |
| line strong | `#4A4644` | `--color-border-underline` |
| text 1 | `#F2F0ED` | `--color-text-primary` / `--color-primary` |
| text 2 | `#E4E1DD` | `--color-text-strong` |
| body | `#B8B3AF` | `--color-text-secondary` |
| meta | `#9A9591` | `--color-text-muted` |
| caption | `#6B6663` | `--color-text-caption` |
| dim(비활성) | `#4F4B49` | `--color-text-disabled` |
| accent | `#C43D46` | `--color-accent` / `--color-live` |
| accent hover | `#D45A62` | `--color-accent-hover` |
| overlay | `rgba(10,10,10,0.78~0.96)` | 인라인 |

**포인트 컬러는 딱 이것만**: LIVE 배지/도트, `ON AIR` 라벨, 경매 라벨/버튼, AI 시착 버튼 보더+글자, 진행 바, 차트 최근 2개 막대, 선택된 체크박스, 도구 바 7px 사각, 링크 호버.

## 2. 타이포 (font shorthand — 그대로 적용)

```
대형 헤드라인   600 74px/0.94 Archivo; -0.04em
페이지 타이틀   600 52px/1 Archivo; -0.04em
상세 타이틀     600 40px/1.08 Archivo; -0.035em
에디토리얼 제목 600 30px/1.15 Archivo; -0.03em
섹션 헤딩       600 26px/1 Archivo; -0.03em
소섹션 헤딩     600 24px/1 Archivo; -0.03em
로고            700 26px/0.9 Archivo; -0.035em; UPPERCASE

카드 제목 L     500 19px/1.3 PlexKR; -0.02em
카드 제목 M     500 18px/1.3 · 500 16px/1.35
상품명          400 14px/1.4 PlexKR; #E4E1DD
본문            300 15px/1.75 PlexKR; #B8B3AF; text-wrap:pretty
히어로 본문     300 15px/1.65 PlexKR; #B8B3AF; max-width:520px
내비 링크       500 13px/1 PlexKR
버튼 L          500 14px/1 · 버튼 M 500 13px/1 · 400/500 12px · 400 11px
유틸 링크       400 11px/1 PlexKR; #6B6663

숫자 특대(경매가) 500 44px/1 Mono; -0.04em
숫자 대(가격)    500 38px/1 Mono; -0.03em
카운트다운       500 30px/1 Mono; -0.02em
지표(라이브 수)  500 26px/1 Mono
실측             500 20px/1 Mono; -0.02em
가격(카드)       500 16px/1 Mono; -0.01em
가격(소형)       500 14px/1 Mono

마이크로 라벨   400 9px/1 Mono; 0.20em; UPPERCASE; #6B6663
배지 라벨       500 9px/1 Mono; 0.16em
메타 모노       400 10px/1 Mono; 0.10~0.20em
섹션 유틸       400 11px/1 Mono; 0.12em; UPPERCASE
```

자간 규칙: **Archivo 헤딩 = 음수 자간(−0.03~−0.04em)**, **모노 라벨 = 양수 자간(0.10~0.30em)**. 큰 라벨일수록 좁게, 작은 라벨일수록 넓게.

## 3. 레이아웃 상수

```
좌우 여백 40px (라이브 시청 24px / 패널 28px) · 섹션 상단 64px · 페이지 마지막 96px
섹션 헤더 border-bottom:1px #232120; padding-bottom:14px · 헤더 아래 margin-top:24px(격자는 1px)
필터 레일 232px, 콘텐츠 gap 40px
상품 상세 우측 460px(좌 1fr) gap 40px sticky top 200px · 썸네일 열 84px, 본 이미지 gap 12px
라이브 시청 19%/1fr/260px 높이 720px · 하단 패널 19%/1fr/380px
스티키: 도구 바 top:0 h44 z90 · 사이트 헤더 top:44 z80
```

**헤어라인 격자**: `display:grid; gap:1px; background:#1B1918`, 셀 `background:#0A0A0A`. 스펙 테이블도 동일(셀 padding 24px 0).
**느슨한 그리드**: `gap:24px` + 카드 `border:1px #232120; padding:18~24px`.
**탭 바**: `display:flex; gap:1px; background:#232120`, 각 탭 `flex:1; padding:15px 0; center`. 활성만 `background:#F2F0ED; color:#0A0A0A; 500`.

## 4~20. 컴포넌트 요약 (원본 §4~20)

- **헤더 3단**: 1단 유틸(찜/장바구니/알림 11px #6B6663, hover #F2F0ED) / 2단 로고+내비(활성 #F2F0ED, 나머지 #9A9591)+POINTS/아바타 26px 박스 / 3단 검색줄 border-top #1B1918 h46. 헤더 bg `rgba(10,10,10,0.94)`+blur14, 하단 1px #232120.
- **히어로**: h640 br5 border-bottom #232120 bg #131211. 이미지 filter `saturate(.82) contrast(1.05) brightness(.9)`. 좌우+하단 3중 스크림. 순서: 상태줄(UPCOMING 배지+브랜드라벨, mb26) → h1 74px → 본문 mt22 mw520 → 지표3 mt34 gap34 → 버튼3 mt38 gap8 → 인디케이터 우하단(활성 26×3 #F2F0ED, 나머지 10×3 #3A3735).
- **상품 카드 4:5**: 이미지 br5 bg #131211 filter(.88/1.04/.95). 좌상단 판매방식 배지 top0 left0 `rgba(10,10,10,0.84)` 9px모노 0.12em. 우상단 ♡ top10 right12 14px모노. 하단 스크림 라벨. 본문 padding 16/16/24: 브랜드(9px모노 0.20em #6B6663 UPPER) → mt9 상품명(14px/1.4 #E4E1DD) → mt14 가격(16px모노) ↔ 사이즈캡션(10px #6B6663).
- **라이브 카드 4:3**: padding20 격자 안. LIVE 배지(flex gap5 padding6/9 bg accent, 4×4 흰사각 vtPulse + LIVE 9px모노 500 0.16em). 우상단 시청자수. 하단 상태 스크림. 이미지 아래 브랜드→제목(19px min-height50 2줄)→헤어라인(border-top #1B1918) 아바타20+판매자 ↔ LOTS 08(11px모노 #6B6663).
- **예정 라이브(가로형)**: flex gap18 border #232120 padding18, hover border #4A4644 bg #101010. 이미지 132px 3:4.
- **필터 레일**: aside border-top 1px **#F2F0ED** pt18, FILTER(10px모노 0.20em #F2F0ED). 그룹 mt30 pb26 border-bottom #1B1918. 체크박스 12×12 사각(1px #3A3735, 선택 시 border+bg #F2F0ED). 사이즈 3열 사각칩. AI시착 = #C43D46 채운 사각. 하단 [초기화](1px #2A2827)/[적용](#F2F0ED 채움) padding13/0.
- **상품 상세**: 브레드크럼 11px모노 0.10em #6B6663(현재만 #E4E1DD). 우측 460 sticky top200: 배지→브랜드(10px모노 **0.24em**)→h1 40px→가격(38px모노+원 14px #9A9591 · 우측 VIEWS/LIKES 11px모노)→판매자박스→버튼3(찜/장바구니 1px #2A2827, **AI시착 1px #C43D46 글자 #C43D46**)→구매(bg #F2F0ED 14px 500 #0A0A0A). 스펙 3열 헤어라인(라벨 9px모노 0.20em+값 17px). 실측 4열 헤어라인(라벨 11px한글+값 20px모노). 하자 `6×6 #C43D46`+DEFECTS.
- **라이브 시청**: 상단바 padding16/24 border-bottom #232120. 본문 19%/1fr/260 h720. 좌레일 로트리스트(border-left 3px, 선택 #C43D46+bg #141312). 중앙 영상+채팅 오버레이(w360 `rgba(8,8,8,0.68)` blur12, 발신자색: 일반 #9A9591/판매자 #F2F0ED/AI oklch(.75 .13 88)/system #C43D46). 우레일 AI FITTING 3:5.
- **경매 패널 380**: padding26/28 bg #100F0E. LIVE AUCTION(10px모노 0.20em #C43D46)↔타이머. 진행바 h3 bg #232120, 내부 bg #C43D46 transition width 950ms. 현재가 44px모노 -0.04em+P. 차트 flex 막대(gap3 h46, 각 flex1 transform-origin bottom br1 animation vtBar 620ms delay i*45ms, 색: 마지막2 #C43D46/나머지 #3A3735). 입찰버튼 padding18 bg #C43D46 15px모노 500 #FFF, hover #D45A62.
- **섹션 헤더**: flex 하단정렬 border-bottom #232120 pb14. h2 600 26px Archivo -0.03em. 우측 `View all →`(11px모노 0.12em #6B6663 UPPER, hover #F2F0ED). 지표 동반형은 제목 옆 `ON AIR 12`(10px모노 0.18em **#C43D46**). 콘텐츠 헤더는 border-top **#F2F0ED** pt18.
- **페이지 타이틀 블록**: padding44/0, 영문 eyebrow(10px모노 0.16em #6B6663 UPPER) 위 + 한글 h1 52px Archivo -0.04em 아래. 지표는 우측 flex-end(라벨 9px모노+값 26px모노 gap34, 첫 지표 #C43D46).
- **푸터**: border-top #232120 padding48/40, flex 하단정렬. 좌 VINTIB(22px Archivo 700 -0.035em UPPER)+서브(10px모노 0.20em #4F4B49). 우 링크3 gap32 11px #6B6663 hover #F2F0ED.

## 13. 상태 표 (핵심)

전역: `button,a { transition: color/bg/border 160ms ease-out }`. 카드: `transition: transform 220ms cubic-bezier(.22,1,.36,1), bg/border 220ms`. 카드 img: `transform 620ms cubic-bezier(.22,1,.36,1)`.

| 요소 | 기본 | 호버 | 활성 | 비활성 |
|---|---|---|---|---|
| 카드(격자) | bg #0A0A0A | bg #141312 +translateY(-3px)+img scale(1.045) | — | — |
| 카드(보더) | border #232120 | border #4A4644 bg #101010 +리프트+확대 | — | — |
| 유틸 링크 | 11px #6B6663 | #F2F0ED | — | — |
| 내비 링크 | 13px 500 #9A9591 | #F2F0ED | #F2F0ED | — |
| View all → | 11px모노 0.12em #6B6663 | #F2F0ED | — | — |
| 1차 버튼 | bg #F2F0ED #0A0A0A | bg #C43D46 #FFF | — | bg #1B1918 #4F4B49 |
| 2차 버튼 | 1px #2A2827 #9A9591 | border #F2F0ED #F2F0ED | — | border #1B1918 #4F4B49 |
| 히어로 2차 | 1px #4A4644 #F2F0ED | border #F2F0ED bg rgba(242,240,237,0.06) | — | — |
| AI 시착 | 1px #C43D46 #C43D46 | bg #C43D46 #FFF | — | — |
| 입찰 | bg #C43D46 #FFF | bg #D45A62 | — | bg #2A2827 #6B6663 |
| 팔로우 | 1px #3A3735 #F2F0ED | border #F2F0ED | 팔로잉 border #2A2827 #9A9591 | — |
| 테마 칩(분할) | bg #0A0A0A #9A9591 | bg #F2F0ED #0A0A0A | — | — |
| 필터 칩(사각) | 1px #2A2827 #9A9591 | border/글자 #F2F0ED | bg #F2F0ED #0A0A0A 500 | — |
| 사이즈 칩 | 1px #2A2827 #9A9591 | border/글자 #F2F0ED | bg #F2F0ED #0A0A0A | #4F4B49 border #1B1918 |
| 체크박스 12×12 사각 | 1px #3A3735 투명 | border #F2F0ED | border+bg #F2F0ED | border #1B1918 |
| 체크박스 포인트형 | — | — | bg #C43D46 (AI시착 필터) | — |
| 라디오 | 12×12 사각(원형 금지) | — | — | — |
| 입력 필드 | 1px #2A2827 투명 #F2F0ED | border #3A3735 | 포커스 border #F2F0ED, outline 없음 | border #1B1918 #4F4B49 |
| 페이지 번호 | 1px #232120 #9A9591 38×38 | border/글자 #F2F0ED | bg #F2F0ED #0A0A0A 500 | #4F4B49 |
| 리스트 항목(로트) | border-left 3px 투명 | bg #141312 | border-left #C43D46 bg #141312 | opacity .5 |
| 갤러리 썸네일 | 1px #232120 | border #4A4644 | border #F2F0ED | — |
| 찜 하트 | ♡ #F2F0ED | ♥ #C43D46 | ♥ #C43D46 | — |
| 히어로 인디케이터 | 10×3 #3A3735 | #6B6663 | 26×3 #F2F0ED | — |

## 15. 탭·세그먼트 3종

- **A. 풀폭 세그먼트**(페이지 최상위 분류): `flex gap1 bg #232120`, 각 `flex:1 padding15/0 center`. 활성 흰 블록(500), 나머지 `bg #0A0A0A #9A9591` hover #F2F0ED. 개수 배지 금지.
- **B. 칩 필터**(2차 좁히기): `flex gap8`, 활성 `bg #F2F0ED #0A0A0A 500`, 나머지 `1px #2A2827 #9A9591`. 줄 전체 하단 `border-bottom 1px #F2F0ED`.
- **C. 테마 스트립**(카테고리): A와 형태 같으나 **기본 활성 없음** — 호버 시에만 흰 블록 반전.
- **D. 언더라인 탭**: 2px #C43D46 밑줄 — 도구 바 전용, 제품 화면 금지.

## 17. 배지 (예외 없이 이미지 모서리 top0/left0/right0, 떠있는/pill 금지. 찜 하트만 top10 right12)

LIVE(bg #C43D46 9px모노 500 0.16em #FFF +4×4 흰사각 vtPulse) · UPCOMING(도트5×5) · SOON/일정(`rgba(10,10,10,0.82)` #F2F0ED) · ENDED(#6B6663) · 시청자수(`rgba(10,10,10,0.78)`) · 판매방식(`rgba(10,10,10,0.84)` 0.12em) · 상태스크림(하단 `linear-gradient(0deg, rgba(10,10,10,0.94), transparent)`) · HD·1080P(`rgba(8,8,8,0.7)` border rgba(242,240,237,0.12)) · 확대 ⤢(`rgba(10,10,10,0.8)` 0.14em).

## 10. 모션

키프레임 `vtReveal`(opacity0+translateY18+blur6 → 정상), `vtPulse`(1.7s: scale1↔0.7 opacity1↔0.35), `vtBar`(scaleY .04→1). → `main.scss`에 전역 등록됨.
스크롤 리빌: IntersectionObserver 1회 생성, threshold .12, 그리드 자식 55ms 스태거(상한 8, 모바일 35ms), 1회. **콘텐츠 미리 숨기지 않음**(both fill, 1500ms 안전장치). 카운트다운 `Date.now()` 기준(누적 금지). transform/opacity/blur만.

## 12. 이미지 필터

히어로 `saturate(.82) contrast(1.05) brightness(.9)` / 에디토리얼 `.82/1.06/.9` / 라이브스틸 `.86~.88/1.04~1.05/.93~.94` / 상품 `.88/1.04/.95` / 전신·AI시착 `.86/1.04` / 아바타 `.85/1.03`. 컨테이너 항상 `position:relative; overflow:hidden; border-radius:5px; background:#131211`.

## 데이터 톤 샘플

브랜드 `Levi's/Carhartt/Nike/Adidas/Polo/Alpha/Lee/Wrangler/Big Mac/Schott` · 판매자 `seoul.vintage/workwear.archive/oldschool.kr/surplus.seoul` · 상태 `상시 판매/경매 예정/경매 진행 중/AI 시착 가능/현재 경매 중/다시보기` · 지표 `VIEWERS 1,245/LOTS 08/FOLLOWERS 1,245 · ITEMS 86/ON AIR 12` · 금액 `45,000원 · 시작가 20,000P · 72,000P`.

## 반응형 (확장 시)

1440+ 기준(40px, 상품 3~4열). 1280 → 32px. 1024 → 필터 드로어, 라이브 2열. 768 → 24px, 상품 2열, 라이브 1열, 내비 햄버거, 라이브시청 3분할 해제. 480 → 16px, 상품 2열 유지(1열 금지), 히어로 74→40, 타이틀 52→32. 터치 타깃 ≥44px.
