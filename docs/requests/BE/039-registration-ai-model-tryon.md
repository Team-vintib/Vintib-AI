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
(`S15P11A108-504`, 시착 job). 고정 인물 사진을 "고객 사진" 자리에, 판매자가 등록
중 올린 상품 사진을 "상품 사진" 자리에 넣기만 하면 그 인물이 상품을 입은 이미지가
생성됩니다. 새 AI 추론 로직은 필요 없습니다.

**페르소나 이미지 호스팅과 job 호출은 AI 쪽에서 전담합니다** — AI 관련 인프라는
AI 팀이 직접 맡기로 한 기존 결정에 따른 것입니다. 그래서 BE는 AI의 job 큐 내부
스키마(`user_image_url`/`mask_type`/`fit_type` 조합, 인증 헤더 등)를 몰라도 되고,
아래 **전용 트리거 엔드포인트 하나만 호출**하면 됩니다. BE에서 해주셔야 할 일은
"① 등록 시 값을 받아 이 엔드포인트를 호출, ② 결과를 폴링해 저장, ③ FE에 노출" 셋
뿐입니다.

## 요청 내용

### 1. AI 착용컷 job 생성 — `POST /ai/tryon/registration-model-cut` 호출

판매자가 상품 등록 시 AI 착용컷을 "사용함"으로 켜고 성별을 고르면, 아래 엔드포인트를
호출해 주세요(내부 Docker 네트워크 `http://ai:8000`). **별도 인증 헤더는 필요 없습니다**
— `X-API-Key`는 워커 전용 엔드포인트(`/ai/workers/*`)에만 요구되고, 이 엔드포인트처럼
BE가 호출하는 쪽은 인증이 없습니다(`AI/docs/infra-architecture.md` §3.2 참고). 기존
`AiClient`/`AiClientConfig`가 이미 이 호스트를 바라보고 있으니 같은 클라이언트를
재사용하시면 됩니다.

**요청**: `POST http://ai:8000/ai/tryon/registration-model-cut`

```json
{
  "product_image_url": "<판매자가 등록 중 올린 상품 사진 URL>",
  "gender": "MALE",
  "mask_type": "upper"
}
```

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `product_image_url` | string | Y | 상품 사진 URL |
| `gender` | `"FEMALE"` \| `"MALE"` | Y | `FEMALE`→도우너, `MALE`→희동이. AI가 내부에서 페르소나 이미지를 알아서 고릅니다 — URL을 직접 넘기지 않습니다 |
| `mask_type` | `"upper"` \| `"lower"` | N (기본 `upper`) | 지금은 AI가 상품 카테고리를 몰라서 값을 그대로 신뢰합니다 — 카테고리별 자동 판별은 별도 요청(`docs/requests/BE/035-tryon-product-category.md`)이 풀리기 전까지는 BE가 카테고리 기준으로 값을 정해 보내주셔야 합니다(하의 카테고리면 `lower`, 그 외엔 `upper`) |

**응답 (200)**: `{"job_id": "..."}` — 접수증입니다. 워커가 꺼져 있어도 200으로
접수됩니다(대기 상태로 남아 있다가 TTL 1시간에 만료).

### 2. 결과 조회 및 저장

기존 게이트웨이 공통 경로 `GET /ai/jobs/{job_id}`로 폴링합니다(다른 AI job과 완전히
같은 형식 — 새 조회 엔드포인트를 따로 만들지 않았습니다). 완료되면 결과 payload에
`image_url`(생성된 착용컷 이미지)이 담깁니다. 이 이미지를 상품의 보조 이미지로
저장해 주세요 — 정확히 어떤 테이블/필드로 둘지는 BE 판단입니다(새 컬럼이든, 기존
상품 이미지 테이블에 "AI 생성" 플래그를 추가하는 것이든).

### 3. FE 노출용 API 명세 (제안)

아래는 저희 쪽 제안입니다 — BE 기존 컨벤션(엔드포인트 네이밍, 응답 envelope)에 맞게
조정하셔도 무방합니다. 핵심은 "① 등록 시 값을 받는 자리, ② 생성 상태/결과를 조회할
자리" 둘입니다.

#### ① 상품 등록 요청 — 기존 `POST /products`에 필드 추가

요청 바디에 아래 2개 필드를 추가해 주세요.

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `aiModelEnabled` | boolean | N (기본 `false`) | AI 착용컷 생성 여부 |
| `aiModelGender` | `"FEMALE"` \| `"MALE"` \| `null` | `aiModelEnabled=true`면 필수 | 여성 선택 → 도우너, 남성 선택 → 희동이 |

`aiModelEnabled=true`인데 `aiModelGender`가 없으면 400(`INVALID_REQUEST` 계열)으로
막아주시면 됩니다. `aiModelEnabled=true`면 BE는 상품 사진 업로드가 끝난 뒤 위 1번
엔드포인트를 호출해 `job_id`를 받아두시면 됩니다.

등록 응답(`ProductResponse` 등 기존 상품 응답 DTO)에는 아래처럼 하위 객체를 하나
추가하는 걸 제안합니다 — ②번 조회 API 응답과 필드를 동일하게 맞췄습니다.

```json
{
  "success": true,
  "data": {
    "id": 123,
    "...": "기존 상품 필드",
    "aiModelCut": {
      "status": "PENDING",
      "imageUrl": null
    }
  },
  "error": null
}
```

`aiModelEnabled=false`로 등록한 상품은 `aiModelCut.status`를 `"NONE"`으로 주시면
FE가 이 영역 자체를 안 그리면 됩니다.

#### ② 생성 상태/결과 조회 — 신규 `GET /products/{productId}/ai-model-cut`

즉시 완료되지 않는 작업(2~3분대)이라 FE가 폴링할 별도 엔드포인트가 필요합니다.
BE는 이 엔드포인트 안에서 저장해둔 `job_id`로 AI의 `GET /ai/jobs/{job_id}`를
대신 조회해(또는 이미 완료돼 저장된 결과가 있으면 그대로) 아래 형태로 내려주시면
됩니다.

**요청**: `GET /products/{productId}/ai-model-cut` (인증: 기존 상품 조회와 동일 정책)

**응답 (200)**:

```json
{
  "success": true,
  "data": {
    "status": "PROCESSING",
    "imageUrl": null
  },
  "error": null
}
```

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `status` | `"NONE"` \| `"PENDING"` \| `"PROCESSING"` \| `"COMPLETED"` \| `"FAILED"` | `NONE`=애초에 미사용, `PENDING`=AI 큐 대기, `PROCESSING`=AI 작업 중(대기/처리 구분이 번거로우면 `PENDING`으로 합쳐도 무방), `COMPLETED`=완료, `FAILED`=실패(등록 자체는 정상 진행된 상태) |
| `imageUrl` | string \| null | `status="COMPLETED"`일 때만 값 존재 |

**상품이 없을 때 (404)**:

```json
{
  "success": false,
  "data": null,
  "error": { "code": "PRODUCT_NOT_FOUND", "message": "상품을 찾을 수 없습니다.", "errors": [] }
}
```

폴링 주기는 FE 재량이지만, 참고로 5초 간격·최대 1~2분 정도면 대부분 결과가 나올
것으로 예상됩니다(VLM 캡션 → FLUX → CatVTON 순차 처리, 워커 가용 상황에 따라 편차
있음).

## 참고

- 트리거 엔드포인트 구현: `AI/app/tryon/router.py`, `AI/app/tryon/schemas.py`
  (`RegistrationModelCutRequest`/`RegistrationModelCutEnqueued`)
- 페르소나 이미지 호스팅: `AI/app/static/personas/`(AI가 자체 서빙, BE 업로드 불필요)
- 설계 문서: `docs/plans/AI/CH021-registration-ai-model-tryon.md`
- 겹치지 않는 별개 요청: `docs/requests/BE/035-tryon-product-category.md`(카테고리
  자동 판별, 이 문서는 그게 없어도 BE가 값을 직접 정해 보내는 방식으로 진행 가능)
