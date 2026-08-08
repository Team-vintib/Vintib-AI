# CH027 — 시착 파이프라인: FLUX 멀티이미지 결과를 최종본으로 (CatVTON 제거)

에픽 `S15P11A108-210`.

## 배경/목표

기존 파이프라인(VLM 캡션 → FLUX 워온레퍼런스 → CatVTON 합성)은 4단계 CatVTON이 마스크
영역을 항상 순수 노이즈에서부터 다시 그리는 구조라(`worker/models/catvton/model/pipeline.py`
`masked_image = image * (mask < 0.5)`로 마스크 안쪽을 diffusion 시작 전에 아예 지움),
3단계 FLUX 워온레퍼런스에 잘 나온 디테일(끈, 이너 티, 원단 질감)을 그대로 못 물려받고
오히려 지워버리는 문제가 있었다. 추가로 `fit_type="oversized"`가 마스크 자체를 팽창시켜
몸통이 풍선처럼 부푸는 버그도 발견됨(실측 착용사진과 대조로 확인, 오늘 로컬 반복 테스트).

FLUX.2-klein 파이프라인이 원래 `image: list[PIL.Image]`로 여러 참조 이미지를 받게 설계돼
있음을 확인 — 지금은 사람 사진 한 장만 리스트에 넣고 있었을 뿐, 옷 사진을 두 번째 참조로
같이 넣는 것도 API 레벨에서 가능했다. 사람 사진 + 실제 옷 사진 두 장을 함께 넣고 생성하면
CatVTON 없이도 색상·로고·트림·질감을 상당히 정확하게 반영하면서, 별도 마스크 팽창 로직 없이
자연스러운 드레이프까지 얻어짐을 로컬 반복 테스트(person1+outer/top, person3+shirt 등
여러 조합)로 확인했다. 처리 시간도 CatVTON 로딩+50스텝(~1.5~2분)이 통째로 빠져 단축된다.

## 작업 내용

- `worker/tryon_worker_example.py`의 `run_inference()`에서 4단계(CatVTON 합성)를 제거하고,
  3단계(FLUX 워온레퍼런스)의 출력을 그대로 최종 `image_url`로 사용한다.
- `_generate_worn_reference()`가 `person_image` 한 장 대신 `person_image` + `cloth_image`
  두 장을 FLUX에 `image=[person_image, cloth_image]`로 전달하도록 변경.
- 프롬프트(`worker/models/tryon_flux/prompts.py`)에 오늘 반복 튜닝으로 확정된 내용 반영:
  - "두 번째 참조 이미지의 옷을 정확히(색상/로고/트림/질감) 재현하라"는 명시적 지시
  - 실루엣은 몸에 맞게 슬림하게, 오버핏 느낌은 폭을 넓히는 대신 주름/폴드로 표현하라는 지시
  - 소매/기장/후드 넥라인/끈 늘어짐 등 자연스러운 디테일 지시(제품 특성에 따라 선택적으로
    붙일 수 있게 구조화)
- 기존 CatVTON 기반 4단계 로직은 삭제하지 않고 `worker/tryon_worker_catvton_legacy.py`로
  옮겨 보존한다(향후 롤백/비교용 후보). `worker/models/catvton/`(모델 코드 자체)은 그대로
  둔다 — 다른 워커(예: 등록 AI 착용컷)가 참조할 가능성이 있어 삭제 범위 밖.
- `mask_type`/`fit_type` 파라미터, `body_*`/`garment_measurements` 기반 핏 계산은 더는
  CatVTON 마스크에 쓰이지 않으므로(마스크 자체가 없어짐), 프롬프트 문구 생성에만 관여하도록
  정리한다.

## 구현 목록

- [ ] `worker/models/tryon_flux/generator.py`: `generate(reference_image, prompt)` →
      `generate(person_image, cloth_image, prompt)`로 시그니처 변경, `image=[person_image,
      cloth_image]`로 파이프라인 호출
- [ ] `worker/models/tryon_flux/prompts.py`: 멀티이미지 지시문 + 슬림 실루엣/주름 표현 +
      선택적 소매·기장·후드·끈 클로즈 헬퍼 추가
- [ ] `worker/tryon_worker_example.py`: `run_inference()`에서 CatVTON 단계(4단계) 제거,
      FLUX 결과를 바로 `image_url`로 업로드. `mask_type`/`fit_type` 관련 CatVTON 호출부
      정리
- [ ] 기존 CatVTON 로직을 `worker/tryon_worker_catvton_legacy.py`로 이동(그대로 보존, import
      경로만 정리)
- [ ] `AI/app/tryon/schemas.py`/`AI/app/tryon/router.py`에 CatVTON 전용이던 필드(있다면)
      정리 — 계약 자체(`job_id`/`image_url`/`fit_title`/`fit_description`)는 유지
- [ ] `AI/test/`, `worker` 관련 테스트가 CatVTON 4단계를 전제하고 있으면 갱신
- [ ] `README`/`AI/docs/tryon-advancement-strategy.md`에 파이프라인 변경 반영

## 확인 필요

- 로고 텍스트 정확도는 diffusion 특성상 완벽하지 않음(알려진 한계, 이번 변경으로 해결되는
  범위 아님) — 상품 상세 이미지 대체 용도가 아니라 "착용 느낌 참고용" 임을 UI 카피 등에서
  이미 전제하고 있는지 FE 쪽 확인 필요할 수 있음
- 실제 등록된 다양한 상품 사진(각도/조명/재질)에서도 이번 로컬 테스트만큼 색상·질감 재현이
  잘 되는지는 프로덕션 트래픽으로 추가 검증 필요
