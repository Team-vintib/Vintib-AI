# 현재 프로젝트 구조

확인일: 2026-07-24

## 기술 스택

- Vue 3
- TypeScript
- Vite
- Vue Router
- Pinia
- Axios
- SCSS

## 주요 명령

| 명령 | 설명 |
| --- | --- |
| `npm run dev` | Vite 개발 서버 실행 |
| `npm run build` | 타입 체크 후 빌드 |
| `npm run preview` | Vite preview |
| `npm run type-check` | `vue-tsc --build` |
| `npm run lint` | ESLint fix |
| `npm run format` | `src/` Prettier 적용 |

## 현재 폴더

```text
src/
  App.vue
  main.ts
  assets/
    main.scss
  router/
    index.ts

docs/
  notion/
```

## 구현 상태

- 라우터는 생성되어 있으나 등록된 route가 없습니다.
- `App.vue`는 `RouterView`만 렌더링합니다.
- 공통 레이아웃, 페이지, 컴포넌트, API 모듈, 타입, stores 폴더는 아직 없습니다.
- 전역 스타일은 reset과 기본 font-family만 있습니다.
