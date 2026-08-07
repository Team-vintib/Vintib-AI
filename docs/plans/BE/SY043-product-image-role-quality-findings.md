# SY043 상품 이미지 role 구분 + AI 품질 검수 결과 저장 (PROD-001/PROD-006)

## 배경/목표

상품 등록 필드 전수 점검(사용자 확인) 중 확인된 구멍 두 개를 채운다.

1. **이미지 role**: `ProductImage`가 `sortOrder`/`isPrimary`뿐이라 "이게 앞면/뒷면(하자 검증용)인지
   추가샷인지"를 서버가 모른다. `002-product-contract.md`가 이미 "이미지 role 정책 필요 시
   `images[].role: FRONT | BACK | ADDITIONAL` — 아직 미반영"으로 남겨둔 항목이고, AI 품질 검수
   (`041-quality-inspection-integration.md`)도 `image_urls`를 앞면=0/뒷면=1 고정 순서로 요구해서
   role 없이는 그 순서를 보장할 방법이 없다.
2. **AI 품질 검수 결과 저장**: `042-product-registration-ai-pipeline.md` §3에 따라 FE가 이미
   `POST /products` 요청에 `aiQualityFindings`(사용자가 인정/확정한 하자 목록)를 실어 보내고
   있는데 BE가 안 받아서 무시된다. 상품 상세 "AI 분석" 탭(`019-product-quality-multi-image.md`)도
   채울 데이터가 없어 mock으로 남아 있다.

## 1. 이미지 role

### 작업 내용

- `ProductImageRole` enum 신설: `FRONT` / `BACK` / `ADDITIONAL`.
- `ProductImage`에 `role` 컬럼 추가.
- `ProductImageRegisterRequest`에 `role` 필드 추가(필수).
- 검증: 상품당 `FRONT` 1장·`BACK` 1장만 허용(중복 등록 시 에러). `ADDITIONAL` 개수는 기존
  `MAX_IMAGES_PER_PRODUCT=10` 상한을 그대로 쓴다(앞뒤 2 + 추가 최대 8 = 10, 우연히 요청 스펙과
  맞아떨어진다 — 별도 분리 상한을 새로 두지 않는다).
- `ProductImageResponse`에 `role` 노출.

### 범위 밖

**"상품 생성 전에 이미지를 먼저 올리는" 문제(042)는 포함하지 않는다.** 042는 아직 방향(B안:
독립 사전 업로드)만 확정됐고 계획을 안 썼다 — role은 지금 있는 흐름
(`POST /products/{id}/images`, 상품이 이미 생성된 뒤 업로드)에 그대로 얹는다. 042가 나중에
구현되면 그 흐름의 등록 요청에도 `role`만 똑같이 실어 보내면 되므로 이번 작업이 헛수고가 되지
않는다.

## 2. AI 품질 검수 결과 저장

### 작업 내용

- `ProductQualityFinding` 엔티티 신설 — `ProductDefect`와 같은 패턴(상품당 여러 행, 등록 시
  한 번에 저장):
  - `photoRole`(`FRONT`/`BACK`, 위 enum 재사용)
  - `description`(TEXT)
  - `box`(JSONB, `{"x":.., "y":.., "width":.., "height":..}` — `Product.measurements`와 같은
    JSON 컬럼 패턴)
  - `sortOrder`
- `Product`에 `conditionScore: Double`(nullable) 컬럼 추가 — 041이 요청한 값. **가중치·등급
  경계가 근거 없는 임의값이라 가격책정 등 다른 로직이 그대로 신뢰해 쓰면 안 된다**(041 본문
  경고)는 점을 엔티티 주석에도 남긴다 — 저장만 하고 다른 도메인 로직이 참조하지 않는다.
- `ProductCreateRequest`에 `conditionScore`(선택)·`aiQualityFindings: List<AiQualityFindingRequest>`
  (선택, 각 `photoRole`/`description`/`box`) 추가.
- `ProductService.createProduct`에서 findings 저장(`saveDefects`와 같은 패턴).
- `GET /products/{id}` 응답에 `aiQualityAnalysis` 객체 추가(019가 요청한 형태를 최소 범위로
  채운다):
  - `status`: findings 요청 자체가 없었으면 `NOT_REQUESTED`, 요청은 있었는데 0건이면
    `NO_FINDINGS`, 1건 이상이면 `COMPLETED`. **`ANALYZING`/`FAILED`는 BE가 만들 수 없다** —
    FE가 AI job을 직접 폴링해서 이미 끝난 결과만 `POST /products` 시점에 BE로 넘어오기
    때문이다(041 §1의 설계 그대로).
  - `images[]`: `FRONT`/`BACK` 각각 — `label`("앞면"/"뒷면"), `originalImageUrl`(같은 상품의
    role 일치하는 `ProductImage`에서 조회 — 그래서 1번 작업이 선행돼야 한다),
    `analyzedImageUrl`(주석 이미지가 없으므로 `originalImageUrl`과 동일하게 — 019가 허용한
    대안), `summary`(null — AI가 이 흐름으로는 안 주는 값, 019도 "BE/AI 판단"이라며 이미 유보를
    인정한 부분), `findings`(저장된 값 중 photoRole 일치하는 것만).
  - `disclaimer`: 고정 문구.
- `PATCH /products/{id}`(수정)는 이번 범위에 포함하지 않는다 — "등록 시점에 확정한 데이터"라는
  게 042/019의 전제다. 수정 시점에도 갱신이 필요해지면 별도 요청으로 다룬다.

## 구현 목록

- [ ] `ProductImageRole` enum 추가
- [ ] `ProductImage.role` 컬럼 추가 + `ProductImageRegisterRequest`/`ProductImageResponse` 반영
- [ ] 상품당 FRONT/BACK 중복 등록 방지 검증
- [ ] `ProductQualityFinding` 엔티티/리포지토리 추가
- [ ] `Product.conditionScore` 컬럼 추가
- [ ] `ProductCreateRequest`에 `conditionScore`/`aiQualityFindings` 추가, 등록 시 저장
- [ ] `GET /products/{id}` 응답에 `aiQualityAnalysis` 추가(상태 파생 로직 포함)
- [ ] 테스트: FRONT/BACK 중복 등록 거부, findings 저장, `aiQualityAnalysis` 상태 파생
      (NOT_REQUESTED/NO_FINDINGS/COMPLETED) 3케이스
- [ ] Swagger 갱신

## 확인이 필요한 미결정 사항

- 기존에 이미 등록된 이미지들의 `role`을 어떻게 채울지(마이그레이션 없이 `role IS NULL` 허용 +
  기존 데이터는 전부 `ADDITIONAL` 취급 정도가 무난해 보임 — 확정 필요).
- FRONT/BACK 중복 등록을 막을 에러 코드 — 기존 `PRODUCT_IMAGE_*`(P004~P007)에 이어 새 코드
  (`P008` 등) 신설 예정.
- `conditionScore` 타입 — AI 원본이 `condition_score: 78.0`(실수)라 `Double`로 잡음, 이견 없으면
  그대로 진행.