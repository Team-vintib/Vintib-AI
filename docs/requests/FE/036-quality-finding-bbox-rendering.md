# 품질 검수 하자 bbox — JSON 형태와 렌더링 방식 안내

- **요청자 파트**: AI
- **대상 파트**: FE
- **관련 자료**: `docs/requests/BE/019-product-quality-multi-image.md`(FE가 먼저 낸 요청,
  이 문서는 그 후속), `AI/app/quality/schemas.py`

## 배경/이유

`019`에서 FE가 "주석 이미지(`analyzedImageUrl`)가 없으면 좌표만 받아서 직접 오버레이해도
된다"고 이미 제안해주셨는데, 저희 쪽에서 검증해보니 **좌표 기반이 맞고, 사실 그쪽으로 가야만
하는 이유**가 있어 정리해서 안내합니다.

판매자가 특정 하자를 "아니다"라고 답하면 그 박스가 빨강 → 초록으로 바뀌는 인터랙션을
계획 중이신 것으로 알고 있습니다. **이건 서버가 미리 그려서 주는 정적 PNG(`AnnotatedImage`,
`analyzedImageUrl`)로는 할 수 없습니다** — 이미지가 고정돼 있어서 상태가 바뀔 때마다 박스
색을 다시 그려서 새 이미지를 받아와야 하는데, 그러면 매번 서버 렌더링·재요청이 필요해 느립니다.
좌표(`bbox`)를 받아서 FE가 캔버스/오버레이 엘리먼트로 직접 그리면 상태 변경 시 즉시 색만
바꿀 수 있습니다.

## job은 언제 시작되고, 언제/어떻게 폴링하는지

- **트리거는 BE가 하고, 시점은 앞/뒤 사진 업로드 완료 직후입니다.** 상품 분류(색상·카테고리)
  칸을 띄우는 이벤트와는 별개입니다 — 검수 job은 그보다 먼저, 사진 두 장이 채워지는 즉시
  백그라운드로 시작됩니다(분류 브랜치와 병렬). FE가 직접 job을 트리거할 필요는 없습니다.
- BE는 이 시점에 만든 `job_id`를 사진 업로드/임시저장 응답에 실어서 내려줄 예정입니다 — 이
  값을 등록 폼 상태에 들고 있다가, 검수 결과를 보여줄 페이지(현재 목업상 'condition' 스텝)에
  진입했을 때 그 `job_id`로 **FE가 AI 게이트웨이를 직접 폴링**합니다: `GET
  https://i15a108.p.ssafy.io/ai/jobs/{job_id}` (BE를 거치지 않는 외부 경로입니다). BE는
  AI를 따로 조회하지 않습니다 — 대신 FE가 상태 확정/최종 제출 등 각 단계에서 **이미 받아둔
  `condition_score`/`condition_grade`/`findings[].key`별 응답을 그 단계의 요청 payload에
  실어서** BE로 넘겨주셔야 합니다(자세한 필드는 `docs/requests/BE/041` 참고).
- 사용자가 카테고리 선택 등 앞 스텝에서 시간을 쓰는 동안 검수가 이미 끝나 있을 가능성이 높지만,
  **`status`가 `queued`/`processing`으로 올 수 있다는 걸 감안해서 로딩(`analyzing`) 상태와
  재폴링 로직은 그대로 유지해 주세요** — 워커가 바쁘거나 꺼져 있으면 시간이 걸릴 수 있습니다.
  `status: "failed"`나 1시간 뒤 만료(404)도 처리해 주세요.

## 지금 실제로 오는 JSON (이미 확정된 계약)

`GET /ai/jobs/{job_id}` 결과 중 `status: "success"`일 때 `result.findings[]` 배열, 항목 1건:

```jsonc
{
  "key": "stain_0_5_1",           // 이 하자의 고정 식별자 — 사용자가 "아니다"라고
                                   // 답한 걸 BE에 저장할 때 이 키로 매핑합니다
  "defect_type": "STAIN",         // STAIN | DIRT_MARK | HOLE_TEAR | DISCOLORATION | PILLING | FRAY
  "label": "오염",                // defect_type의 한글 태그
  "status": "DETECTED",           // DETECTED | SUSPECTED (AI 확신도)
  "image_index": 0,               // 이 하자가 속한 이미지(앞/뒤 등 여러 장 중 몇 번째)
  "no": 1,                        // 같은 image_index 안에서 1부터. analyzedImageUrl의 숫자와 동일
  "bbox": [0.42, 0.35, 0.55, 0.47], // 정규화 좌표 (x1, y1, x2, y2), 0~1
  "confidence": 0.81,
  "severity": "MODERATE",         // MINOR | MODERATE | MAJOR
  "statement_required": true,     // 판매자 소명 입력 대상인지
  "needs_seller_review": false,   // AI 확신도가 낮아 확인이 특히 필요한지
  "description": "옅은 갈색 얼룩이 소매 끝부분에 있습니다."  // 한 줄 설명, 없으면 null
}
```

## 렌더링 방식 제안

1. **박스는 `bbox`(정규화 좌표)로 FE가 직접 그립니다.** `analyzedImageUrl`이 오면 그건
   미리보기 참고용으로만 쓰고, 실제 인터랙션(클릭·상태 전환)은 좌표 기반 오버레이로
   구현해 주시면 됩니다 — 019에서 제안하신 방식 그대로입니다.
2. **박스 안 숫자는 `no`를 그대로 씁니다.** `analyzedImageUrl`이 있다면 그 이미지 위 숫자와
   `no`가 1:1로 일치합니다.
3. **하자 유형·설명 텍스트**는 이미지 위가 아니라 리스트/툴팁 등 FE UI에서 보여주시면
   됩니다 — `defect_type`/`label`은 항상 있고, `description`은 없을 수 있습니다(현재
   검증 중인 기능이라 아래 참고).
4. **박스 색상 초기값**: `status`가 `SUSPECTED`거나 `needs_seller_review`가 `true`면
   "AI가 의심하는 부분 — 확인해 주세요" 톤으로 구분해서 보여주시는 걸 권장합니다(색을
   다르게 하든 아이콘을 붙이든 FE 판단).

## 참고 — 상품등록 페이지의 목업 구현과 이미 정확히 맞습니다

`ProductRegistrationPage.vue`/`productRegistration.types.ts`의
`ProductRegistrationAiPhotoResult`/`ProductRegistrationAiDefectCandidate` 목업 형태를 봤는데,
저희 계약과 그대로 맞아떨어집니다 — 새로 구조를 바꾸실 필요 없습니다.

| FE 필드 | 매핑 |
| --- | --- |
| `candidates[].id` | `findings[].key` |
| `candidates[].labelNumber` | `findings[].no` |
| `candidates[].description` | `findings[].description` |
| `candidates[].box` | `findings[].bbox`를 FE가 `{x,y,width,height}`(%)로 변환(위 렌더링 방식 그대로) |
| `candidates[].isActualDefect` | AI가 주는 값이 아니라 FE 로컬 상태(기본 `true`, 판매자가 "아니다" 누르면 `false`) — 최종 제출 시 BE로 전달 |
| `photoResult.photoId` | `image_index` → `photoId`, FE가 직접 매핑 |

BE는 `image_urls`를 AI에 보낼 때 항상 앞면=0, 뒷면=1 순서로 고정해서 보냅니다. FE는 애초에
어느 사진을 앞면/뒷면으로 업로드했는지 알고 있으므로, 이 고정 순서만 알면 `image_index`를
자기 `photoId`로 바로 매핑할 수 있습니다 — BE가 매핑 정보를 따로 내려줄 필요가 없습니다.

## 확인이 필요한 것 (BE와 같이 정해야 함)

- 판매자가 "아니다"라고 답한 걸 저장하는 엔드포인트/필드는 아직 저희 쪽에서 확정한 게
  없습니다 — `key`를 앵커로 쓰는 것까지는 정해져 있지만, 그 상태를 어떻게 저장·조회하는지는
  BE와 별도로 맞춰야 합니다. FE에서 필요한 형태(예: PATCH 요청에 `key` 배열)가 있으면
  `docs/requests/BE/`에 알려주세요.

## 참고 — `description` 필드는 아직 검증 중

`description`(VLM이 생성하는 한 줄 설명)은 지금 `AI/validation/QUAL/vlm-description-check/`에서
방식을 검증 중입니다(이미지 1장당 1회 호출로 여러 하자를 한꺼번에 설명받는 방식 테스트).
`key`/`defect_type`/`label`/`bbox`/`no`는 이미 프로덕션에 있는 확정 필드라 지금 바로 연동
가능하고, `description`은 검증이 끝나고 프로덕션에 반영되면 별도로 알려드리겠습니다 — 지금은
`null`이 올 수 있다는 점만 감안해 주세요.
