# CH002 — 하자 검수: "하자 아님" key만 저장 + 상세 응답을 원본 JSON에서 직접 조립

## 배경/목표

`docs/requests/FE/043-quality-finding-confirm-status-and-detail-cards.md`에 FE가 역제안한
방식을 반영한다. 원래 요청(043)은 등록 제출 payload에 finding마다 `no`/`section`/`confirmed`를
추가해서 보내는 방식이었는데, FE가 더 단순한 방식을 제안했고 실제로 더 낫다 — 이미
`Product.qualityInspectionResult`(jsonb)에 AI 원본 결과(`condition_score`/`findings`/
`image_summaries` 등) **전체**가 영구 저장돼 있기 때문이다(품질검수 job 완료 시
`completeQualityInspectionJob()`이 캐시, Redis TTL 1시간 만료 대비).

**SY043 §2의 결정을 뒤집는다.** SY043은 "AI raw 스키마는 저장하지 않고 photoRole/description/
box만 저장"하기로 정했었다(041 §6 결정) — 그때는 "등록 화면에서 이미 인정/제외를 확정한 결과만
필요하다"는 전제였다. 지금은 상품 상세에도 등록 화면과 **동일한 번호·부위**로 보여줘야 한다는
새 요구가 생겨서 그 전제가 깨졌다. 원본을 이미 통째로 갖고 있으니, 축소 저장한 사본
(`ProductQualityFinding`)을 유지하는 게 오히려 낭비이자 불일치 위험이다.

## 작업 내용

### 1. 저장 — "하자 아님" key 목록만

- `Product`에 `excludedQualityFindingKeys`(jsonb, `List<String>`, 기본 빈 리스트) 컬럼 추가 —
  `qualityInspectionResult`와 같은 `@JdbcTypeCode(SqlTypes.JSON)` 패턴.
- `ProductUpdateRequest.aiQualityFindings: List<AiQualityFindingRequest>` →
  `excludedQualityFindingKeys: List<String>`로 교체. 기존 null=미반영/값 있으면 전체 교체
  규칙 그대로 유지(`defects`와 같은 패턴).
- `ProductCreateRequest`에는 추가하지 않는다 — SY043이 이미 정한 대로 이 값은 검수 job이 끝난
  **이후**(DRAFT 생성 이후)에만 존재할 수 있어 PATCH 전용이다.
- `POST /products` 쪽 finding 저장 로직(`saveDefects`류)은 제거 — 저장할 대상 자체가 없어진다.

### 2. 삭제 — `ProductQualityFinding`

엔티티/리포지토리/`AiQualityFindingRequest`를 삭제한다. 다른 어디서도 참조 안 됨(확인 완료 —
`ProductService` 하나뿐). `ddl-auto: update`라 마이그레이션은 없고, `product_quality_finding`
테이블은 빈 채로 남는다(운영 데이터 없는 pre-launch 단계라 문제 없음, 나중에 수동 정리 가능).

### 3. `GET /products/{id}` 응답 — 원본 JSON에서 직접 조립

`ProductService.buildAiQualityAnalysis()`를 `ProductQualityFindingRepository` 대신
`product.getQualityInspectionResult()`(raw `Map<String,Object>`)를 파싱하도록 재작성한다.

- **status 파생**: 기존엔 finding row 유무로만 `NOT_REQUESTED`/`NO_FINDINGS`를 구분 못 했는데
  (`AiQualityAnalysisResponse`의 "구분 안 함" 주석), 이제 `Product.qualityInspectionStatus`
  (`NONE`/`PENDING`/`PROCESSING`/`COMPLETED`/`FAILED`)를 그대로 매핑하면 정확히 구분된다:
  `NONE→NOT_REQUESTED`, `PENDING`/`PROCESSING→ANALYZING`, `FAILED→FAILED`,
  `COMPLETED`+findings 0건`→NO_FINDINGS`, `COMPLETED`+findings 있음`→COMPLETED`.
- **`AiQualityFindingResponse` 필드 교체** — 엔티티가 아니라 raw map에서 채운다:
  - `key` ← `finding.key` 그대로
  - `type` ← `finding.label`(한글 원본 라벨)
  - `location` ← `finding.section` **원본 그대로**(예: `"HEM_RIGHT"`, 번역 안 함 — FE가
    `aiSectionLabels.ts`로 변환)
  - `description` ← `finding.description` 그대로(`null` 허용)
  - `box` ← `finding.bbox`([x1,y1,x2,y2] 0~1 정규화)를 `{x,y,width,height}`(0~100, **반올림
    없는 소수**)로 변환. 계산: `x=x1*100, y=y1*100, width=(x2-x1)*100, height=(y2-y1)*100`.
    FE `qualityFindingBox.ts::toPercentBox()`와 같은 공식 — 등록 화면과 완전히 같은 렌더링
    결과를 보장하려고 일부러 그 로직을 그대로 옮긴다.
  - `isExcluded` ← `product.getExcludedQualityFindingKeys().contains(finding.key)`
  - **모든 finding을 담는다** — `isExcluded=true`인 것도 응답에 포함한다(FE가 카드에서
    숨길지/다르게 표시할지 정함, 043 참고). 번호(`no`)는 원본 `finding.no`를 그대로 실어서
    FE가 정렬·표시에 쓸 수 있게 한다(FE 요청 필드엔 없었지만 원본에 이미 있는 값이라 굳이
    빼지 않는다 — 있어야 등록 화면과 순서가 100% 일치함을 보장하기 쉽다).
- **`AiQualityAnalysisImageResponse.summary`** ← `image_summaries[]`에서 `image_index` 일치하는
  항목의 `summary`(더 이상 하드코딩 `null` 아님).
- `originalImageUrl`/`analyzedImageUrl`은 기존과 동일하게 `ProductImage`(role 기준) 조회로
  채운다(변경 없음 — AI가 이미지 URL을 따로 안 줌).

### 4. 삭제 대상 정리

- `ProductQualityFinding.java`, `ProductQualityFindingRepository.java`,
  `AiQualityFindingRequest.java` 삭제
- `AiQualityFindingResponse.java`는 삭제하지 않고 필드만 교체(위 스키마)

## 구현 목록

- [x] `Product`: `excludedQualityFindingKeys`(jsonb `List<String>`) 컬럼 + getter/변경 메서드 추가
- [x] `ProductUpdateRequest`: `aiQualityFindings` → `excludedQualityFindingKeys: List<String>` 교체
- [x] `ProductService`: PATCH 처리부에서 findings 저장 로직 제거, excluded keys 저장으로 교체
- [x] `ProductService.buildAiQualityAnalysis()`: raw `qualityInspectionResult` 파싱으로 재작성
      (status 매핑 — `ANALYZING`/`FAILED` 추가, finding 필드 매핑, bbox 변환, summary 매핑)
- [x] `AiQualityFindingResponse`: `key`/`type`/`location`/`description`/`box`/`isExcluded`/`no`로 필드 교체
- [x] `ProductQualityFinding`/`ProductQualityFindingRepository`/`AiQualityFindingRequest` 삭제
- [x] 테스트: status 5분기(NOT_REQUESTED/ANALYZING/NO_FINDINGS/COMPLETED/FAILED) 갱신,
      `isExcluded` 매핑, bbox 변환, summary 노출, PATCH의 excluded keys 저장(null=미반영) 반영
- [ ] Swagger 갱신(수동 확인 — `@Schema` 주석은 코드에 반영됨, 실제 swagger-ui 렌더는 미확인)
- [x] `docs/requests/FE/043-*.md`를 최종 계약으로 다시 작성(교체), `036` §3 정리 완료

## 리스크 / 확인 필요

- bbox 변환 공식이 FE `qualityFindingBox.ts`와 정확히 같은지 실제 코드 대조 필요(수치가
  1px이라도 어긋나면 "등록 화면과 동일" 요구를 못 지킴).
- `excludedQualityFindingKeys`에 없는 `key`가 온 채로 저장 요청이 오면(오래된 key, 오타 등)
  — 조용히 무시할지 400을 낼지 결정 필요. **제안: 조용히 무시**(존재 검증하려면 원본 JSON을
  다시 파싱해야 하는데, 그 비용 대비 실익이 적고 틀린 key는 어차피 매칭될 finding이 없어
  효과가 없을 뿐 부작용도 없음).
