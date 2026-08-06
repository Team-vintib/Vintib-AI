# 가상 시착 결과 — "한 줄 핏 예상" 필드(fit_title/fit_description) 추가 요청

- **요청자 파트**: AI
- **대상 파트**: BE
- **관련 티켓**: `S15P11A108-210` 에픽 하위, `S15P11A108-567`

## 배경

FE가 이미 시착 결과 화면에 "한 줄 핏 예상" UI 자리를 만들어뒀습니다
(`FE/src/domains/tryon/constants/liveTryOnMockData.ts`, 지금은 하드코딩된 목업:
`fitTitle: 'M 사이즈가 적합합니다.'` / `fitDescription: '어깨와 가슴 부분에 약간 여유
있는 핏이 예상됩니다.'`). AI 쪽엔 이 값을 실제로 계산하는 로직을 이미 구현·검증했습니다
(`worker/models/catvton/model/fit_summary.py`, 신체 실측 대비 의류 실측 비율로 5단계
한국어 문구를 생성 — 예: `"선택하신 사이즈가 살짝 타이트해요."` / `"허리 부분이 몸에
붙는 타이트한 핏으로 예상돼요 (기준보다 약 27% 작아요)."`).

`TryOnResultService.saveResult()`의 독스트링에 이미 "실제 AI 호출은 AI 쪽 계약이
확정되지 않아 범위 밖"이라고 명시돼 있어서, 이번에 그 계약의 일부(핏 예상 필드)를
확정해서 전달합니다.

## 요청 내용

시착 job 결과를 실제로 수신·저장하는 로직을 구현하실 때(AI 게이트웨이 job 결과,
`GET /ai/jobs/{job_id}`), 결과 payload에 아래 두 필드가 새로 포함될 예정이니
`TryOnResult` 엔티티와 `TryOnResultResponse`에 같이 반영해 주시면 됩니다.

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `fit_title` | string \| null | 한 줄 요약(예: `"선택하신 사이즈가 살짝 타이트해요."`) |
| `fit_description` | string \| null | 근거를 덧붙인 한 문장(예: `"허리 부분이 몸에 붙는 타이트한 핏으로 예상돼요 (기준보다 약 27% 작아요)."`) |

**둘 다 `null`일 수 있습니다** — 회원 신체 실측(키/몸무게 등)이나 상품 실측 사이즈가
없으면 AI가 비율 자체를 계산 못 해서 값을 안 보냅니다(추측성 문구를 보여주지 않고
침묵하는 쪽을 택했습니다). `TryOnResultResponse`에서도 이 null을 그대로 흘려보내
주시면, FE 쪽에서 "예상 정보 없음" 처리를 하게 됩니다(별도로 `docs/requests/FE/`에
안내).

## 참고

- 계산 로직: `worker/models/catvton/model/fit_summary.py`
- 설계 문서: `docs/plans/AI/CH020-tryon-fit-summary-text.md`
- 이 필드는 회원 신체 실측(허리/가슴 등)과 상품 실측 사이즈가 둘 다 있어야 값이 채워집니다
  — 그 실측값 자체를 BE가 어떻게 넘겨줄지는 별개 논의입니다(`docs/requests/BE/
  031-garment-measurement-scan.md`가 상품 실측 쪽은 이미 다루고 있습니다. 회원 신체
  허리/가슴/엉덩이 컬럼은 아직 확정 문서를 못 찾았는데, 이미 처리돼서 지워진 것일 수도
  있으니 확인 부탁드립니다). 이 문서는 그 실측값이 있다는 전제하에 만드는 **파생
  텍스트**만 다룹니다.
