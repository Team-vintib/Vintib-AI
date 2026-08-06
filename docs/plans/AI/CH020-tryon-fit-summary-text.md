# 시착 결과 "한 줄 핏 예상" 텍스트 생성 (S15P11A108-567)

에픽 `S15P11A108-210` 소속. FE가 이미 UI 자리를 만들어둔 `fitTitle`/`fitDescription`
(`FE/src/domains/tryon/constants/liveTryOnMockData.ts` — 지금은 100% 하드코딩된 목업:
`'M 사이즈가 적합합니다.'` / `'어깨와 가슴 부분에 약간 여유 있는 핏이 예상됩니다.'`)을
실제 계산값으로 채운다.

## 배경

이미 검증된 로직이 있다 — `worker/models/catvton/model/adaptive_fit.py`의
`compute_width_adjustment(body_circumference_cm, garment_flat_width_cm)`가 "옷이 몸통
둘레 대비 얼마나 여유/타이트한지"를 비율(ratio)로 계산하고, `AI/validation/TRYON/
AI_tryon/CatVTON/generate_worn_reference_{jeans,top,outer}_fitaware.py`의
`fit_descriptor(ratio)`가 이 비율을 FLUX 프롬프트용 영어 문구(7단계)로 바꿔서 실제
시착 이미지 생성에 이미 쓰고 있다. 이번엔 같은 비율 계산을 **고객이 보는 화면용
한국어 한 줄**로 바꾸기만 하면 된다 — 이미지 생성용 문구(‘second-skin, 단추가 터질
듯한’ 같은 과장된 시각 묘사)와는 톤이 달라야 한다(고객 안내 문구는 담백하게).

## 접근 방식

1. **`worker/models/catvton/model/fit_summary.py`(신규)**: `fit_summary_ko(ratio:
   float | None, part: Literal["waist","chest"]) -> dict | None`. `ratio`가 `None`이면
   `None`(측정값 없음 → 폴백, 기존 `adaptive_fit.py`의 "입력 없으면 결과도 None" 원칙과
   동일). 5단계로 나눈다(레귤러 / 살짝 타이트-루즈 / 확실히 타이트-루즈) — 이미 검증된
   `fit_descriptor()`의 임계값(0.95~1.05 레귤러, 0.85·1.15·1.30 경계)을 그대로 재사용,
   문구만 고객용 평이한 한국어로 새로 쓴다. 반환값은 FE 계약과 동일한 `{title,
   description}` 형태.
2. **검증**: 이번 세션에서 만든 시착 결과 평가 설문(아티팩트)에 쓴 7장 예시 이미지 각각의
   실측 비율(이미 계산 완료 — 예: 둘리 청바지 M ratio=0.727, 희동이 상의 XXL
   ratio=1.380 등)을 넣어서 문구가 자연스러운지 확인한다. 별도 검증 스크립트로 돌린다.
3. **설문 반영**: 설문 페이지의 "유도된 핏" 배지 문구를 이 함수 출력으로 교체한다(지금은
   제가 손으로 쓴 문구).
4. **워커 연결**: `worker/tryon_worker_example.py`의 `run_inference()` 반환값에
   `fit_title`/`fit_description` 필드를 추가한다 — `estimate_body_measurements()` +
   `compute_width_adjustment()`가 이미 계산 중인 ratio를 그대로 재사용(신규 계산 없음).
   측정값이 없으면(대부분의 실제 요청이 아직 그럴 것) `None`으로 빠진다 — 프로덕션
   동작을 바꾸지 않는 안전한 추가.

## 범위 밖

- FE가 mock 대신 이 값을 실제로 렌더링하도록 바꾸는 작업 — FE 소유 코드라 직접 안 건드림,
  필요하면 `docs/requests/FE/`에 별도 안내만 남긴다.
- 상의 어깨/소매 축, 기장 축 등 폭 외 다른 축의 한 줄 요약 — 지금은 가장 값이 갖춰진 폭
  (허리/가슴) 축 하나만.

## 커밋 계획

`feat/210-tryon-evaluation-survey` 브랜치, 커밋 키 `[S15P11A108-567]`:
1. `feat:` `fit_summary.py` 추가
2. `test:` 7장 예시 비율로 검증 스크립트 실행 및 결과 확인
3. `feat:` 설문 페이지에 반영
4. `feat:` `tryon_worker_example.py`에 필드 추가
