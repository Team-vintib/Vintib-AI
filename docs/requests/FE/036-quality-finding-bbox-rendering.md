# 036 품질 검수 하자 bbox — 남은 FE 항목

- **요청자 파트**: AI / **대상 파트**: FE
- **관련 자료**: `docs/requests/BE/041`(제출 payload 필드), `AI/app/quality/schemas.py`

> bbox 좌표 기반 오버레이 렌더링·"하자 아님" 빨강→초록 토글·`findings[].key`를 제출 payload에 싣는 것은
> 반영 완료되어 덜어냈다(`ProductRegistrationPage.vue` 오버레이, `qualityFindingBox.ts`,
> `productApi.ts`의 `aiQualityFindings`). 목업 구조도 계약과 일치한다. 아래 실연동/미확정만 남는다.

## 남은 항목

### 1. AI 게이트웨이 실폴링 미연결 (BE 선행 필요)

현재 findings는 목업(`productAiApi.ts`의 `analyzeRegistrationPhotos` — real 모드는 throw)에서 오고,
`aiGatewayApi.ts`의 `pollAiJob`(`GET /ai/jobs/{job_id}`)은 정의만 돼 있고 호출되지 않는다. 실연동하려면:

- BE가 사진 업로드/임시저장 응답에 `job_id`를 실어 줘야 한다(`docs/requests/BE/041`). 지금 등록 폼 상태에 `job_id`를 들고 있지 않다.
- condition 스텝 진입 시 그 `job_id`로 **BE를 거치지 않고** `GET https://i15a108.p.ssafy.io/ai/jobs/{job_id}`를 직접 폴링.
- `status`: `queued`/`processing` → 로딩(`analyzing`) 유지·재폴링, `success` → findings 렌더, `failed`·1시간 만료(404) 처리.
  (현재 `analyzing` UI는 목업 analyze 결과의 `aiQualityStatus`에만 연결돼 있어 실제 job status와 무관하다.)

### 2. `condition_score`/`condition_grade` 미수집·미전달

지금 제출되는 `conditionGrade`는 판매자가 수동 선택한 S/A/B/C이고, AI가 준 `condition_score`/`condition_grade`를
받아 두었다가 각 단계 제출 payload에 싣는 흐름이 없다(현재는 `findings[].key` + 필드만 전달). `docs/requests/BE/041` 참고.

### 3. "하자 아님" 저장 엔드포인트 미확정 (BE와 협의 필요)

판매자가 "아니다"로 답한 상태(`isActualDefect=false`)를 저장/조회하는 엔드포인트·필드가 아직 확정 안 됨.
`key`를 앵커로 쓰는 것까지만 정해졌다. FE에서 필요한 형태(예: PATCH에 `key` 배열)가 있으면 `docs/requests/BE/`에 요청.

## 계약 참고 (실연동 시)

`GET /ai/jobs/{job_id}` `status: "success"` → `result.findings[]` 항목:

- `key` (고정 식별자, "아니다" 저장 앵커) · `defect_type`(`STAIN|DIRT_MARK|HOLE_TEAR|DISCOLORATION|PILLING|FRAY`) · `label`(한글)
- `status`(`DETECTED|SUSPECTED`) · `image_index`(앞=0, 뒤=1 고정) · `no`(image_index 내 1부터)
- `bbox`(정규화 `[x1,y1,x2,y2]` 0~1) · `confidence` · `severity`(`MINOR|MODERATE|MAJOR`)
- `statement_required` · `needs_seller_review` · `description`(한 줄 설명 — VLM 검증 중이라 `null` 가능)
