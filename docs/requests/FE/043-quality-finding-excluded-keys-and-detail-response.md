# 043 하자 검수 — 제외 key 목록 전송 + 상세 응답 필드 (최종 반영됨)

- **요청자 파트**: BE / **대상 파트**: FE
- **관련 자료**: `docs/requests/FE/036-quality-finding-bbox-rendering.md`(§3이 이걸로 해소됨)

## 배경/이유

042/041 방식(등록 시 인정된 finding만 photoRole/description/box로 전송) 대신, FE 제안대로
**"하자 아님" key 목록만 전송 + BE가 원본 JSON에서 상세 응답을 조립**하는 방식으로
전환했다(CH002, BE 구현 완료). 아래는 FE가 맞춰야 하는 최종 계약이다.

## 요청 내용

### 1. 등록 제출 payload

`ProductUpdateRequest`(PATCH `/products/{id}`)의 `aiQualityFindings` 필드가
**`excludedQualityFindingKeys: string[]`**로 바뀌었다 — "하자 아님"으로 표시한 finding의
`key`만 배열로 보낸다. null=미반영, 빈 배열=제외 전부 해제. `POST /products`(생성) 쪽엔
이 필드가 없다(검수 job이 생성 이후에 끝나므로 PATCH 전용, 기존과 동일).

### 2. 상품 상세 응답

`GET /products/{id}`의 `aiQualityAnalysis`:
- `status`에 `ANALYZING`/`FAILED`가 추가됐다(기존 3종 + 2종 = 5종, BE가 job 상태를 그대로 반영).
- `images[].summary`가 이제 실제로 채워진다(AI 원본 `image_summaries` 그대로).
- `images[].findings[]` 필드 교체: `key`/`type`(원본 한글 label)/`location`(원본 부위 코드
  그대로, 번역 안 함 — `aiSectionLabels.ts`로 FE가 매핑)/`description`(null 가능)/`no`/
  `box`(`{x,y,width,height}`, 0~100 소수, 반올림 없음)/`isExcluded`.
- **`isExcluded=true`인 finding도 응답에 포함된다** — 번호(`no`)가 등록 화면과 어긋나지
  않게 하기 위해서다. 카드에 보여줄지는 FE 재량.
