# 가상 시착 파이프라인 프로덕션 승격 (VLM + FLUX + CatVTON)

## 배경/목표

에픽 `S15P11A108-210`, 이슈 `S15P11A108-504`. `AI/docs/tryon-advancement-strategy.md`
§9~§10에서 검증한 fit-aware worn-reference 기법을 실제 고객 사진 기반 프로덕션 워커로
승격한다.

기존 프로덕션 `worker/tryon_worker_example.py`는 CatVTON만 쓴다 — 실제 고객 사진
(`user_image_url`) + 상품 사진 + 사용자가 고른 `fit_type`(regular/oversized/cropped
드롭다운)을 받아 그대로 합성한다. 검증한 기법은 반대로 고정된 AI 모델 4명에게 실제
사이즈표 기반 핏을 입혀보는 방식이었다 — 실제 고객 개인화는 없었다.

## 확정 사항

- **타겟은 실제 고객 사진이다.** worn-reference를 상품+사이즈당 한 번만 만들어 재사용하는
  캐싱은 폐기 — 고객마다 그 고객 사진을 참조로 다시 생성해야 한다(결과에 고객 본인이
  나와야 하므로).
- 실제 신체 치수(waist_cm 등)는 BE에 없다(`.claude/requests/be/
  004-garment-measurement-scan.md`, 아직 "요청" 상태). 대신 **키/몸무게**(BE
  `member_body_profile.height_cm`/`weight_kg`, 이미 확정 컬럼)로 평균 체형 참조표를 통해
  허리/어깨/종아리 등을 근사한다.
- VLM(Qwen3-VL-4B, 4bit) + FLUX.2-Klein-4B + CatVTON은 **한 워커 프로세스 안에서 순차
  로드/언로드**한다(동시 상주 아님) — `garment_measurement_worker_example.py`가 이미
  전례. 프로덕션엔 GPU 서버가 없고 팀원 노트북(6GB급)이 워커로 붙는 구조라(`AI/docs/
  infra-architecture.md`), 순차라면 피크 VRAM이 가장 큰 단일 스테이지(FLUX, ~5-6GB)
  수준으로 억제된다.
- `worker/models/catvton/model/`을 `AI/validation/TRYON/AI_tryon/CatVTON/model/`과
  재동기화한다(`adaptive_fit.py`의 `scale_px`가 20 vs 60으로 갈라져 있었음 — **프로덕션
  값 20 유지**, 60은 검증 전용 실험값). validation 폴더 전체가 아니라 `model/` 핵심
  라이브러리만 대상. `worker/models/catvton/model/flux/`(예전 미사용 잔재)는 정리한다.
- **`fit_type`에서 `cropped`를 제거한다.** §7.5에서 "기장(길이) 축은 AI 가드레일상 맨살
  노출 우려로 뺐다"고 이미 결정했는데, `cropped`(옷을 짧게 만들어 하체를 더 드러내는
  옵션)는 그 결정과 정확히 충돌한다. 벤더 코드인 `cloth_masker.py`의 `cropped` 분기
  자체는 건드리지 않되(CatVTON 원본 라이브러리 코드), **우리 쪽 스키마(`AI/app/tryon/
  schemas.py`의 `MaskFitType`)와 워커 유효성 검사(`worker/tryon_worker_example.py`)에서
  `cropped`를 허용값에서 제외**해서 그 경로로는 절대 못 들어가게 막는다.
- fit_type 자체도 새 파이프라인에서는 CatVTON 마스크 형태 조절용이 아니라(worn-reference-
  as-person이 마스크를 worn-reference에서 새로 계산하므로), **FLUX 프롬프트의 핏 묘사
  선택**(§10.1의 `fit_descriptor` 결과 대신 쓸 수동 오버라이드) 정도로만 남는다.

**실제로 읽어보니 스키마는 이미 준비돼 있었다** — `AI/app/tryon/schemas.py`의
`TryOnOptions`에 `body_height_cm`/`body_weight_kg`(BE 확정 컬럼)와 `body_chest_cm`/
`body_waist_cm`/`body_hip_cm`(BE 컬럼 미확정, 항상 None 가능) 필드가 이미 있다. 그리고
`.codex/requests/be/003-onboarding-tryon-profile-api.md`(`S15P11A108-254`)가 정확히
가슴/허리/엉덩이 저장 API를 이미 요청해둔 상태다(아직 열려있음) — **새로 안 만들고
이 필드를 그대로 소비하고, chest/waist/hip 컬럼 요청은 003번을 그대로 참조한다.**

**아직 못 푸는 것 (새 BE 요청 필요, 카테고리 하나뿐)**:
- 상품 카테고리(하의/상의/아우터/액세서리)가 AI로 안 넘어온다 — `Product.categoryId`는
  raw `Long` FK뿐, AI의 35종 taxonomy와 연결할 방법이 없다. `mask_type`을 AI가 스스로
  판단 못 함. 이것만 `.claude/requests/be/`에 신규 문서로 남긴다.
- 상품 실측 사이즈표(사이즈별 가슴둘레/기장 등)도 AI로 안 들어온다 — 이건
  `004-garment-measurement-scan.md`가 이미 다루는 영역이라 새로 안 쓰고 참조만 한다.

데이터가 없으면 안전한 기본값으로 폴백한다(카테고리 모르면 요청의 `mask_type` 값을
그대로 신뢰, 키/몸무게 없으면 "regular fit" 고정 묘사) — `body_estimate.py`도 height/
weight가 `None`이면 호출 자체를 건너뛰는 방어적 설계로 간다.

**로컬 워커 셋업 문서화**: `worker/README.md`가 기능별로 `FEATURE_BACKEND=mock|실제`
환경변수 스왑 컨벤션을 이미 확립해뒀다(`QUALITY_BACKEND`, `STT_BACKEND` 등 — GPU 없이도
mock으로 전 경로 검증 가능). 새 VLM/FLUX 단계도 같은 컨벤션(`TRYON_VLM_BACKEND`,
`TRYON_FLUX_BACKEND`)을 따르고, README에 CatVTON 워커 섹션을 갱신해 이 문서 하나로
로컬 세팅이 끝나게 한다.

## 작업 내용

1. **`worker/models/catvton/` 재동기화**: validation의 `model/`(pipeline.py,
   cloth_masker.py, adaptive_fit.py, attn_processor.py, utils.py)로 덮어쓰되
   `adaptive_fit.py`의 `scale_px`는 20(프로덕션값) 유지. 안 쓰는 `model/flux/`,
   `app_flux.py` 등 잔재 삭제.
2. **`fit_type`에서 `cropped` 제거**: `AI/app/tryon/schemas.py`의 `MaskFitType`,
   `worker/tryon_worker_example.py`의 검증 로직 둘 다.
3. **신체 치수 근사 모듈**: `worker/models/catvton/body_estimate.py`(가칭) —
   `estimate_body_measurements(height_cm, weight_kg) -> dict`. 공개 인체측정 평균 기반
   근사(스캔 아님, 코드/문서에 명시).
4. **워커 오케스트레이션 재작성**: `worker/tryon_worker_example.py`를 VLM 캡션 →
   (신체 치수 근사 + 사이즈표 있으면) 핏 계산 → FLUX worn-reference 생성(`image=`고객
   사진 참조 편집) → CatVTON 합성(worn-reference-as-person, `image=`worn-reference,
   `condition_image=`실제 상품 사진)으로 확장. 스테이지 끝날 때마다 `del`+
   `torch.cuda.empty_cache()`. 어텐션 부스팅(§8)은 이번엔 안 가져옴(worn-reference-as-
   person이 마스크를 worn-reference에서 새로 계산해 길이 문제가 원천적으로 안 생길 걸로
   기대 — 재현되면 그때 되살림).
5. **BE 요청 문서 1건**: 카테고리 노출만 신규 작성. chest/waist/hip은
   `.codex/requests/be/003-onboarding-tryon-profile-api.md` 참조, 사이즈표는
   `.claude/requests/be/004-garment-measurement-scan.md` 참조(중복 작성 안 함).
6. **`worker/README.md` 갱신**: CatVTON 워커 섹션에 `TRYON_VLM_BACKEND`/
   `TRYON_FLUX_BACKEND`(mock 기본값) 환경변수, 모델 다운로드/체크포인트 안내, job
   payload에 새로 추가된 필드 반영.
7. **문서 갱신**: `AI/docs/tryon-advancement-strategy.md`에 프로덕션 반영 현황 절 추가.

## 구현 목록

- [ ] `worker/models/catvton/model/` validation과 재동기화 확인(scale_px=20 유지, 이미
      대부분 동일함을 확인함), 미사용 flux 잔재 삭제 완료
- [ ] `AI/app/tryon/schemas.py` `MaskFitType`에서 `cropped` 제거 (height/weight/chest/
      waist/hip 필드는 이미 존재, 새로 안 만듦)
- [ ] `worker/tryon_worker_example.py` fit_type 검증에서 `cropped` 제거
- [ ] `worker/models/catvton/body_estimate.py` 신체 치수 근사 모듈 + 간단 단위 테스트
- [ ] `worker/tryon_worker_example.py` 오케스트레이션 재작성(VLM→FLUX→CatVTON 순차
      체이닝, worn-reference-as-person, mock/real 백엔드 스왑 컨벤션 적용)
- [ ] `.claude/requests/be/` 카테고리 노출 요청 문서 1건 작성
- [ ] `worker/README.md` CatVTON 섹션 갱신
- [ ] `AI/docs/tryon-advancement-strategy.md` 프로덕션 반영 현황 갱신
- [ ] 엔드투엔드 수동 스모크 테스트 (실제/샘플 고객 사진 1장 + 알파테스트 상품)
- [ ] `S15P11A108-504`로 커밋

## 범위 밖

- 카테고리 자동 판별 로직 구현 — BE 데이터 없이 불가, 요청 문서만.
- 실제 신체 스캔 기반 정밀 치수 — `004-garment-measurement-scan.md` 영역, 키/몸무게
  근사로 대체.
- 어텐션 부스팅 재도입, 워커 다중 프로세스/큐 분리 — 이번엔 시도 안 함.

## 확인이 필요한 미결정 사항

- 신체 치수 근사 공식/룩업 테이블의 출처 데이터 — 공개 인체측정 평균 데이터 기반으로
  일단 합리적인 근사치를 넣고, 오차가 크면 추후 조정.
