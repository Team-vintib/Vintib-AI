# 상품 등록 — "AI 착용컷" 생성 연동 요청 (희동이/도우너 모델)

- **요청자 파트**: AI
- **대상 파트**: BE
- **관련 티켓**: `S15P11A108-211` 에픽 하위, `S15P11A108-568`

## 배경

FE 상품 등록 화면(`ProductRegistrationPage.vue`)에 "AI 착용컷 설정" 섹션이 이미
있습니다 — 사용 여부 + 성별(여성/남성) 토글인데, 지금은 **완전히 미완성**입니다.
선택값이 화면 상태에만 잡히고 제출 시 요청 바디에서 빠지며, 호출할 API 자체가
없습니다.

AI 쪽엔 이미 이 용도로 그대로 쓸 수 있는 파이프라인이 프로덕션에 있습니다
(`S15P11A108-504`, `POST /ai/tryon` job). 고정 인물 사진을 "고객 사진" 자리에,
판매자가 등록 중 올린 상품 사진을 "상품 사진" 자리에 넣기만 하면 그 인물이 상품을
입은 이미지가 생성됩니다. 새 AI 추론 로직은 필요 없고, **연동(호출·저장·조회)만
BE에서 만들어주시면 됩니다.**

## 요청 내용

### 1. 고정 인물 사진 호스팅

첨부(`worker/models/catvton/assets/personas/heedongi.png`,
`worker/models/catvton/assets/personas/dooner.png`, 각 ~900KB) 2장을 BE 자체
퍼블릭 버킷(MinIO)에 한 번 업로드해서 안정적인 URL을 만들어 주세요. 여성 선택 →
`dooner.png`, 남성 선택 → `heedongi.png`로 매핑합니다.

### 2. Job 생성

판매자가 상품 등록 시 AI 착용컷을 "사용함"으로 켜고 성별을 고르면, 아래 payload로
`POST /ai/tryon`을 호출해 주세요(AI 게이트웨이 공통 큐, 인증은 `X-API-Key` 헤더 —
`AI/docs/infra-architecture.md` 참고).

```json
{
  "user_image_url": "<위에서 업로드한 페르소나 이미지 URL>",
  "product_image_url": "<판매자가 등록 중 올린 상품 사진 URL>",
  "mask_type": "upper",
  "fit_type": "regular"
}
```

- `mask_type`은 `upper`/`lower` 중 하나입니다. 지금은 AI가 상품 카테고리를 몰라서
  값을 그대로 신뢰합니다 — 카테고리별 자동 판별은 별도 요청(`docs/requests/BE/
  035-tryon-product-category.md`)이 풀리기 전까지는 BE가 카테고리 기준으로 값을
  정해 보내주셔야 합니다(하의 카테고리면 `lower`, 그 외엔 `upper`).
- `fit_type`은 `regular` 고정이면 됩니다 — 판매자가 등록 중에 상세 핏까지 고르게
  하는 건 이번 범위 밖입니다.
- 응답으로 `job_id`를 받습니다.

### 3. 결과 조회 및 저장

기존 게이트웨이 공통 경로 `GET /ai/jobs/{job_id}`로 폴링합니다(시착 워커와 동일
형식). 완료되면 결과 payload에 `image_url`(생성된 착용컷 이미지)이 담깁니다. 이
이미지를 상품의 보조 이미지로 저장해 주세요 — 정확히 어떤 테이블/필드로 둘지는
BE 판단입니다(새 컬럼이든, 기존 상품 이미지 테이블에 "AI 생성" 플래그를 추가하는
것이든).

### 4. FE에 노출

생성 상태(대기/진행중/완료/실패)와 완료 시 이미지 URL을 상품 등록·상세 응답에
포함해 주시면, FE 쪽엔 별도로 안내드리겠습니다.

## 참고

- 페르소나 이미지: `worker/models/catvton/assets/personas/`
- Job 계약: `AI/app/tryon/schemas.py`, `worker/tryon_worker_example.py`
- 설계 문서: `docs/plans/AI/CH021-registration-ai-model-tryon.md`
- 겹치지 않는 별개 요청: `docs/requests/BE/035-tryon-product-category.md`(카테고리
  자동 판별, 이 문서는 그게 없어도 BE가 값을 직접 정해 보내는 방식으로 진행 가능)
