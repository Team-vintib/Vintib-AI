# 디자인 토큰 초안

출처: `docs/notion/프론트엔드 디자인 구현 규칙.md`

## Color

```scss
:root {
  --color-page: #F7F6F2;
  --color-surface: #FFFFFF;
  --color-surface-secondary: #F0F0EB;
  --color-text-primary: #171815;
  --color-text-secondary: #686A64;
  --color-text-muted: #92948E;
  --color-text-inverse: #FFFFFF;
  --color-border: #E1E0DA;
  --color-border-strong: #C9C8C1;
  --color-primary: #294335;
  --color-primary-hover: #1F352A;
  --color-primary-soft: #E7EEE9;
  --color-live: #C43D46;
  --color-auction: #A92F38;
  --color-auction-soft: #F7E8EA;
  --color-timer: #CF7A36;
  --color-ai: #6F5BD3;
  --color-ai-soft: #F0EDFC;
  --color-live-background: #0E1110;
  --color-live-surface: #171B19;
  --color-live-surface-raised: #202522;
  --color-live-border: #343A36;
  --color-live-text-primary: #F7F7F4;
  --color-live-text-secondary: #A9ADA7;
}
```

## Typography

- 기본 폰트: `Pretendard, "Noto Sans KR", Inter, sans-serif`
- Display: 48px / 60px / 700
- 페이지 제목: 36px / 48px / 700
- 섹션 제목: 26px / 36px / 700
- 카드 제목: 17px / 24px / 600
- 본문: 15px / 24px / 400
- 버튼: 15px / 20px / 600
- 캡션: 13px / 18px / 400

## Layout

- 1440px desktop first
- 중앙 콘텐츠 최대 너비: 1320px
- 기본 간격 단위: 8px
- 모바일/태블릿 breakpoint는 미확정

## Radius

- control: 8px
- card: 12px
- media: 16px
- modal: 16px
- badge: 4px
- chip: 999px
