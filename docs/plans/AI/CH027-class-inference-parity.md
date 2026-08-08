# CH027 상품 분류 — 검증 vs 프로덕션 추론 일치 점검

## 배경

`AI/validation/CLASS/product-info-finetune/`(CH014, `CLASSIFIER_FINETUNE_BRIEF.md`)에서
동결 백본(`fashion_clip`) + 선형 헤드 파인튜닝을 진행했고, 실제로 학습·평가에 쓰인 커맨드는
전부 `--variant masked`다(README.md 136~385행 — masked/raw 두 변형을 다 뽑되 최종 체크포인트는
masked로 학습). 지금 `worker/models/product_classifier/`에 실제로 얹혀 있는 체크포인트도
`variant="masked"`로 확인됐다 — **모델 선택 자체는 검증 결과와 일치한다.**

문제는 **서빙 시점 전처리**다. `masked` variant는 학습 때 AI-Hub 정답 polygon으로 배경을
지우고 bbox로 크롭한 이미지를 썼는데(`aihub_preprocess.py:render_variant`), 실서비스
사진에는 그런 정답 polygon이 없다. 그런데 `worker/product_classifier_worker_example.py`는
`download_image()`가 받은 원본을 크롭·마스킹 없이 그대로 분류기에 넣는다(이미 워커
docstring에 명시해 둠, `S15P11A108-597` 커밋). **학습 입력 분포와 서빙 입력 분포가 다르다.**

추가로 확인된 것:
- `CLASSIFIER_FINETUNE_BRIEF.md` §11(수용 기준: 색상 정확도, 폴로 2건, 나머지 17장 불변,
  CPU p50 ≤200ms)의 대조 결과를 `REPORT.md`에 §21로 남기라고 브리핑이 지시했는데, 실제
  `REPORT.md`는 §20에서 끝난다 — **수용 기준 통과 여부가 문서화되어 있지 않다.**
- 브리핑 §10 하드 룰 7번은 "§11 수용 기준을 통과한 뒤에만 `worker/`에 반영"이라고 못 박았는데,
  현재 체크포인트는 이미 `worker/`에 와 있다 — 수용 기준을 실제로 통과했는지, 아니면 게이트를
  건너뛰고 반영됐는지 기록으로는 알 수 없다.
- 체크포인트의 카테고리 `classes`가 11개뿐이다(taxonomy 35종 중 AI-Hub가 직접 커버하는
  9종 + 파생 2~3종 — 브리핑 §5 "합계 9 직접 + 2~3 파생 = 11~12종"과 일치). 이건 버그가
  아니라 브리핑이 처음부터 계획한 범위이지만, 나머지 23~24종은 여전히 zero-shot(백본 그대로)
  의존이라는 걸 명확히 인지하고 있어야 한다.

## 목표

"검증에서 확정된 최적 버전"(masked variant 체크포인트, 동결 백본 + 헤드, 수용 기준)과
"워커 실행 환경"(실제 서빙 코드의 전처리·모델 로딩·출력)이 정말 같은지 점검하고, 다른
부분은 표로 남긴다. 이 계획 자체는 점검 계획이지 재학습/크롭 파이프라인 구현 계획이
아니다 — 점검 결과에 따라 후속 조치(재학습 vs 크롭 연결 vs 현행 유지)는 별도로 결정한다.

## 작업 내용

1. **체크포인트 메타 대조**: `checkpoints/product_classifier/{category,color}/meta.json`의
   `model_id`/`variant`/`unfreeze_layers`/`classes`가 `product-info-finetune/README.md`에
   기록된 최종 커맨드(`vit_last4_category_masked_lr1e-05`,
   `vit_last4_color_masked_lr1e-05_warm` 등)의 하이퍼파라미터와 실제로 일치하는지 확인.
2. **수용 기준 재구성**: `REPORT.md` §21이 없으므로, `aihub_pipeline_final_check.ipynb`·
   `aihub_finetune_summary.py` 산출물(있다면 로컬/원격에 남아있는 실행 기록)에서 §11 수용
   기준 4개 항목의 실제 통과 여부를 복원한다. 기록이 아예 없으면 재평가가 필요하다고
   보고한다(추측으로 채우지 않는다 — 브리핑 자체의 원칙과 동일).
3. **전처리 격차 정량화**: `aihub_evaluate.py`가 masked/raw 두 변형을 다 평가했는지 확인하고,
   있다면 raw variant 정확도를 "크롭 없는 실서비스 입력"의 근사 기대치로 인용한다. 없으면
   실제 상품 사진(크롭 없음) 몇 장으로 직접 추론해 masked-학습 체크포인트가 raw 입력에서
   얼마나 흔들리는지 확인한다.
4. **워커 프로덕션 검증 노트북 작성**: `worker/quality_check_e2e_validation.ipynb`와 같은
   개념으로 `worker/product_classifier_e2e_validation.ipynb`를 만든다 —
   `worker/models/product_classifier/`를 그대로 import해서 카테고리·색상 추론을 단계별로
   실행하고, latency(모델 로드 제외/포함)와 최종 응답 JSON 형태(BE가 받는 것과 동일)를
   확인한다. 크롭 있는 입력/없는 입력을 나란히 돌려 격차를 눈으로 비교하는 셀을 포함한다.
5. **격차 해소 방향 정리(결정은 안 함)**: 위 점검 결과를 바탕으로 후보 3가지
   (SAM3 크롭 재사용 / raw variant로 재학습 / 현행 유지 + 기대 정확도 명시)의 장단점만
   정리해 보고한다. 실제 착수는 별도 계획·승인 이후.

## 구현 목록

- [ ] 체크포인트 meta.json vs README 최종 커맨드 하이퍼파라미터 대조표 작성
- [ ] §11 수용 기준 4개 항목 실제 통과 여부 복원(또는 "기록 없음" 명시)
- [ ] masked vs raw 정확도 격차 수치 확보(기존 평가 결과 재사용 또는 소규모 재확인)
- [ ] `worker/product_classifier_e2e_validation.ipynb` 작성(프로덕션 모듈 직접 import,
      단계별 시각화, latency 측정, 크롭 유/무 비교 셀 포함)
- [ ] 위 4개 결과를 종합한 간단한 격차 리포트(문서 또는 노트북 결론 셀) 작성
- [ ] 격차 해소 후보 3가지 장단점 정리(결정 아님, 보고용)

## 확인이 필요한 미결정 사항

- `aihub_pipeline_final_check.ipynb`(원격 실행 기록)가 로컬에 없다면 §11 수용 기준
  재현을 위해 원격 재실행이 필요할 수 있다 — GPU 필요, 사용자 실행 필요(브리핑 §3-1과 동일
  제약).
- 크롭 격차를 지금 해소할지(SAM3 재사용 등 추가 설계 필요), 아니면 "알려진 한계"로 남기고
  다음 우선순위로 미룰지는 이 점검 결과를 본 뒤 사용자가 결정한다.
