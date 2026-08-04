# HS029 — AI 시착 페이지 (입어보기 + 결과 갤러리, TRYON-005)

## 배경
메뉴바 "AI 시착" 링크(`GlobalNavigation`, 로그인 시)는 이미 `/tryon`(requiresAuth)로 연결돼 있으나 **`TryOnPage.vue`는 빈 스텁**이다. 이 페이지를 두 구획으로 채운다.

## 화면 구성
### ① AI 입어보기 (상단)
- **내 전신 사진 1장** 표시 (시착 프로필). 없으면 등록 안내(프로필/온보딩 링크).
- 그 아래 **내가 찜한 옷 캐러셀** — `‹ ›` 화살표로 넘김. 옷 선택 → **입어보기**.
- 입어보기(AI 합성)는 **미구현** → **mock 미리보기**. 합성 API가 붙으면 결과가 ②에 저장되는 구조.

### ② 저장된 시착 결과 (하단)
- **카테고리 탭**(상의/하의/아우터/원피스/신발/가방/액세서리 등 상품 대분류 수준 — 세분화)으로 나눠 보기.
- 결과 **그리드**(합성 이미지 + 등록일). 클릭 → 상세(확대)/삭제. 탭별 빈 상태.

## API 연결 / 데이터
| 요소 | API | 상태 |
|---|---|---|
| 내 전신 사진 | `GET /users/{id}/tryon` (bodyPhotoUrl) | ✅ 실연결(기존 `tryOnProfileApi`) |
| 찜한 옷 | 찜 목록(+상품 카드) | ✅ 실연결 |
| 결과 목록/삭제 | `GET`·`DELETE /users/{id}/tryons` | ✅ 실연결 |
| 결과 응답 | `{ id, productId, imageUrl(presigned), createdAt(오프셋없는 KST) }` | — |
| 입어보기(합성) | `POST /users/{id}/tryons` (AI 합성) | ❌ 미구현 → mock |
| 결과 카테고리(상의/하의…) | 결과 응답에 **없음** | ⚠️ BE 요청 → 지금은 mock에 포함 |

## 부족한 것 → BE/AI 요청 (docs/requests)
1. **결과 응답에 카테고리 추가** (상의/하의 등 대분류) — 탭 필터에 필요. 현재 `{id,productId,imageUrl,createdAt}`만.
2. **시착 생성 `POST /users/{id}/tryons` + AI 합성** — 미구현. 입어보기·결과 저장이 실제로 동작하려면 필요(TRYON-003/004, AI 합성 계약).
   - 두 건 모두 문서 남김(카테고리는 BE, 합성 계약은 AI/BE).

## 구현 파일
- `types/tryOnResult.types.ts` — `TryOnResult { id, productId, imageUrl, createdAt, category?(BE 확인 필요) }`
- `api/tryOnResultApi.ts` — 목록/상세/삭제, `VITE_TRYON_API_ENABLED` 미설정 시 mock(기존 패턴)
- `constants/tryOnResultMockData.ts` — 데모용 결과(카테고리 포함, "Mock 전용")
- `components/TryOnComposer.vue` — ① 입어보기(전신 사진 + 찜 캐러셀 + 입어보기 mock)
- `components/TryOnResultGallery.vue` — ② 결과(카테고리 탭 + 그리드 + 상세/삭제)
- `pages/TryOnPage.vue` — DefaultLayout 안에 ①②

## 진입 연결(수정 아님)
- 메뉴바 링크·라우트 이미 존재 → 페이지 내용만 채움.
- 상품 상세/라이브 시착 패널은 mock 생성 유지. 합성·저장 붙으면 이 갤러리에 반영.

## 브랜치 / Jira
- 브랜치: 시착 에픽 `feat/210-ai-tryon-entry-area` 재활용.
- Jira: TRYON-005 관련 2개 티켓(사용자 확인) — 커밋 키·MR 관련이슈 반영.

## 검증
- vue-tsc / eslint 통과, 로컬(mock)로 입어보기·결과 탭·상세·삭제·빈 상태 확인.
