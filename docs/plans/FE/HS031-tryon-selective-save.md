# HS031 — AI 시착 결과 선택 저장 (맘에 드는 것만, TRYON-005)

- Jira: `S15P11A108-557` [TRYON-005 | FE] (시착 결과 저장·갤러리) / 에픽 `S15P11A108-210` [TRYON]
- 브랜치: `feat/210-tryon-selective-save` (develop-FE 기준)

## 배경/목표

현재 AI 시착 페이지의 `TryOnComposer`는 "입어보기"를 누르면 mock 결과를 생성하자마자
`emit('generated')`로 갤러리(`TryOnResultGallery`)에 **즉시 추가**한다(= 자동 저장).
사용자 요청: **입어보고 미리보기 후 맘에 드는 것만 명시적으로 "저장"** 해야 갤러리에 남게 한다
(무조건 저장 금지).

## 작업 내용

1. `TryOnComposer.vue`
   - `tryOn()`은 결과를 **미리보기(`generatedResult`)에만** 반영하고 `emit('generated')`는 **하지 않는다**.
   - 미리보기 상태(`generatedResult` 있고 생성 중 아님)에서 액션 버튼 노출: **[저장]** / **[다시 입어보기]**.
   - **저장** 클릭 → 이때만 `emit('generated', result)` (갤러리 추가) + 저장 완료 표시(`isSaved`).
   - **다시 입어보기**(취소) 또는 다른 옷으로 재입어보기 → 이전 미리보기 폐기(저장 안 함).
2. `TryOnPage.vue`
   - `handleGenerated`는 그대로 둔다 — 이제 저장 클릭 시점에만 호출되므로 자동 저장이 아니다.
3. 실제 합성·저장 API(`POST /users/{id}/tryons`)는 미구현 → 저장은 로컬 갤러리 추가까지(mock).
   API가 붙으면 "저장" 클릭 핸들러에서 호출한다. (미구현 상태는 HS029에서 이미 문서화, 추가 요청 불필요)

## 구현 파일

- `components/TryOnComposer.vue` — 미리보기 + 저장/취소 버튼, `emit` 시점 변경, `isSaved` 상태
- `pages/TryOnPage.vue` — 변경 없음(핸들러 그대로)

## 검증

- vue-tsc / eslint 통과
- 로컬(mock): 입어보기 → **미리보기만** 뜨고 갤러리엔 안 들어감 → **저장** 눌러야 갤러리 추가 /
  **다시 입어보기**로 취소하면 미추가

## 비고

- 이번 작업은 "저장 트리거" UX만 바꾼다(자동 저장 → 명시 저장). 합성/저장 API 연결은 별도.
- 후속 #3(다중 선택 입어보기)은 같은 시착 영역이라 별도 계획(HS032 예정)으로 이어서 진행.
