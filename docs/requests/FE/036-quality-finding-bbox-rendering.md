# 036 품질 검수 하자 bbox — 남은 FE 항목

- **요청자 파트**: AI / **대상 파트**: FE
- **관련 자료**: `docs/requests/BE/041`(제출 payload 필드), `AI/app/quality/schemas.py`

> bbox 좌표 기반 오버레이 렌더링·"하자 아님" 빨강→초록 토글·`findings[].key`를 제출 payload에 싣는 것은
> 반영 완료되어 덜어냈다(`ProductRegistrationPage.vue` 오버레이, `qualityFindingBox.ts`,
> `productApi.ts`의 `aiQualityFindings`). 목업 구조도 계약과 일치한다. 아래 실연동/미확정만 남는다.

## 남은 항목

### 1. 실폴링 미연결 (2026-08-07 갱신 — BE 쪽은 준비됨, FE 화면 연결만 남음)

**BE/041이 방식을 바꿔서 반영됐다** — FE가 AI 게이트웨이를 직접 폴링하는 게 아니라, BE의
`GET /products/{id}/quality-inspection`을 폴링한다(자세한 내용은 041 §"처리 결과" 참고).
`aiGatewayApi.ts`의 `pollAiJob`(`GET /ai/jobs/{job_id}` 직접 폴링)은 이 기능에는 쓰지 않는다
(다른 기능 — 가격 추천 — 은 여전히 그 방식을 쓰므로 파일 자체는 유지).

`productApi.ts`에 이미 추가된 것:
- `getProductQualityInspectionStatus(productId)` — 위 BE 엔드포인트 호출
- `mapQualityInspectionResultToPhotoResults(result, photoIdByImageIndex)` — AI 원본(snake_case)을
  `ProductRegistrationAiPhotoResult[]`(camelCase, 화면 렌더링용)로 변환하는 매퍼(아래 매핑표 그대로 구현)

**아직 안 된 것**: 위 두 함수를 `ProductRegistrationPage.vue`에 실제로 연결하는 일. 지금 그 화면의
`aiQualityStatus`/`aiPhotoResults`는 **상품 등록 전, 로컬 파일 단계**에서 도는 목업
(`productAiApi.ts`의 `analyzeRegistrationPhotos`)이 채운다 — 반면 검수 job은 이미지가 실제로
**등록된 뒤**(BE가 트리거)에야 존재한다. 즉 "언제 트리거되는 job"과 "언제 보여주는 화면"의 시점이
서로 다르다. 두 가지 중 하나를 정해야 한다:
  (a) 사진 선택 즉시 상품 draft+이미지를 실제로 만들어 그 시점부터 진짜 job을 트리거하고, 지금의
      목업 미리보기 자리를 실제 폴링으로 교체한다, 또는
  (b) 모델컷처럼 최종 제출 이후의 별도 화면(완료 화면 등)에서 실제 검수 결과를 보여준다.
이건 화면 흐름 설계라 AI가 대신 정하지 않았다 — FE가 결정할 사안.

### 2. `condition_score`/`condition_grade` 미수집·미전달

지금 제출되는 `conditionGrade`는 판매자가 수동 선택한 S/A/B/C이고, AI가 준 `condition_score`/`condition_grade`를
받아 두었다가 각 단계 제출 payload에 싣는 흐름이 없다(현재는 `findings[].key` + 필드만 전달). `docs/requests/BE/041` 참고.

## 계약 참고 (실연동 시)

`GET /ai/jobs/{job_id}` `status: "success"` → `result.findings[]` 항목:

- `key` (고정 식별자, "아니다" 저장 앵커) · `defect_type`(`STAIN|DIRT_MARK|HOLE_TEAR|DISCOLORATION|PILLING|FRAY`) · `label`(한글)
- `status`(`DETECTED|SUSPECTED`) · `image_index`(앞=0, 뒤=1 고정) · `no`(image_index 내 1부터)
- `bbox`(정규화 `[x1,y1,x2,y2]` 0~1) · `confidence` · `severity`(`MINOR|MODERATE|MAJOR`)
- `statement_required` · `needs_seller_review` · `description`(한 줄 설명 — VLM 검증 중이라 `null` 가능)
