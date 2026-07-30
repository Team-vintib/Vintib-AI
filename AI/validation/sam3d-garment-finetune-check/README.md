# SAM 3D 의류 단독 파인튜닝 파이프라인 + turntable vs I2V 비교 하네스

**스파이크/스캐폴드입니다. 프로덕션 코드가 아닙니다.** (`AI/CLAUDE.md` — `validation/` 은 PoC 전용)

SAM 3D Objects 를 "의류 단독" 3D 재구성으로 특화 파인튜닝하고, 그 결과물을 **턴테이블 렌더**와
**VideoGen(I2V) 출력**과 같은 지표로 비교해 어느 쪽이 유리한지 판정하기 위한 코드다.

**데이터가 아직 없다.** 그래서 이 리포지토리는

- 데이터가 들어올 자리를 **스키마(컨트랙트)와 config** 로 못박고,
- 더미 픽스처로 **전 단계가 끝까지 도는** 스캐폴드와 단위테스트를 갖추고,
- upstream 에 실제로 공개된 것과 아닌 것을 **`REPORT.md`** 에 조사해 정리했다.

실제 데이터 확보·전처리 실행, 카메라 extrinsic 확보, 아키텍처 개조, 대규모 학습은 범위 밖이다.

## 시작하기

```bash
cd AI/validation/sam3d-garment-finetune-check

python -m venv .venv && .venv/Scripts/activate    # Windows
# source .venv/bin/activate                        # macOS/Linux
pip install -r requirements.txt

make test      # 전 테스트 (외부 데이터·GPU 불필요)
make smoke     # 더미 엔드투엔드 → artifacts/outputs/report/comparison.{md,html}
make audit     # 샘플별로 어떤 감독이 가능한지
```

`uv` 를 쓰면 `uv venv && uv pip install -r requirements.txt`.

### make 없이 실행하기 (Windows 개발 노트북)

이 프로젝트의 Windows 환경에는 `make` 가 없다. Makefile 의 각 타깃은 한 줄 명령이라 그대로
옮겨 쓰면 된다:

```bash
python -m pytest tests -q                                                  # make test
python -m garment3d.cli --config configs/default.yaml --work-dir artifacts/work smoke   # make smoke
python -m garment3d.cli --config configs/default.yaml --work-dir artifacts/work audit   # make audit
```

lint 는 **AI 루트 설정(`AI/pyproject.toml`)을 따른다** — 리포 규칙과 어긋나지 않게:

```bash
cd ../..            # AI/
python -m ruff check validation/sam3d-garment-finetune-check
python -m black --check validation/sam3d-garment-finetune-check
```

## 선결 조사 결과 (요약 — 전문은 `REPORT.md`)

`facebookresearch/sam-3d-objects` (커밋 `f91db41`) 를 직접 클론해 확인했다.

| 필요한 것 | 릴리스 상태 | 이 프로젝트에서 |
| --- | --- | --- |
| mesh → 64³ occupancy | ✅ `inference_utils.py::voxelize_mesh` | `preprocess.voxelizer=sam3d` 로 위임 |
| 64³ → sparse structure latent (stage 1 = 기하) | ✅ `pipeline.models["ss_encoder"]` | `latent_encoder=sam3d_ss` 실호출 |
| SLat 인코더 (stage 2 = 텍스처) | ✅ 가중치까지 있음 (`slat_encoder.ckpt`, 파이프라인만 미연결) | 로드 경로는 TODO |
| **SLat 학습 타깃 생성 코드** | ❌ **없음 — stage 2 의 실제 병목** | **stub + `# TODO`** |
| 학습 **손실** | ✅ `FlowMatching.loss` / `ShortCut.loss` | `Sam3dFlowLoss` 가 그대로 호출 (재구현 안 함) |
| 학습 루프 / 옵티마이저 / DPO | ❌ 없음 | 우리가 새로 씀 (`train/sft.py`, `train/dpo.py`) |
| PEFT(LoRA) | ✅ upstream 의존성에 이미 있음 | `train/lora.py` |
| 턴테이블 렌더 | ✅ `notebook/inference.py::render_video` | `render.backend=sam3d` 로 위임 |

**두 가지가 이 프로젝트의 형태를 결정했다:**

1. **stage 2(텍스처) 파인튜닝은 "가중치가 없어서"가 아니라 "입력 만드는 규약을 몰라서" 막혀
   있다.** `slat_encoder.ckpt` 는 릴리스에 있고 `in_channels: 1024`(= DINOv2 ViT-L embed_dim)
   이며 특징 추출기(`dino.Dino`)도 릴리스 안에 있다. 없는 건 **GT 메시를 멀티뷰로 렌더해
   DINOv2 특징을 활성 복셀에 집계하는 단계**이고, 그 규약(뷰 개수·카메라 분포·레이어·집계 방식)이
   문서화되지 않았다. 추측하면 인코더 입력 분포가 학습 시와 어긋나 latent 가 조용히 망가지므로
   `preprocess/latent.py::Sam3dSlatEncoder` 는 `NotImplementedError` 로 뒀다.
   `audit_sample()` 이 이 사실을 샘플 단위로 보고한다.
2. **LoRA 를 아무 Linear 에나 붙이면 런타임에 터진다.** `sp.SparseLinear` 는 `nn.Linear`
   서브클래스인데 forward 가 `SparseTensor` 를 받아서, PEFT 의 `lora_A`(순수 `nn.Linear`)가
   그걸 받고 죽는다. 안전한 타깃은 어텐션의 `to_qkv`/`to_q`/`to_kv`/`to_out` 뿐이고,
   `assert_lora_targets_safe()` 가 부착 **전에** 위험 타깃을 거부한다.

## 데이터 컨트랙트

`garment3d/contracts.py`. 핵심은 `GarmentSample` 과 **`SupervisionAvailability`** 다.

```python
GarmentSample(
    sample_id="...",
    image_path=Path("images/x.png"),        # 필수
    garment_mask_path=Path("masks/x.png"),  # 필수
    mesh_path=Path("meshes/x.obj"),         # 없으면 기하 감독 불가
    camera=Camera(intrinsics=..., extrinsics=...),  # extrinsics 없으면 layout 감독 불가
    texture_path=None,
    category=GarmentCategory.TOP,
    meta={"license": "...", "source": "..."},
)
```

`audit_sample(sample)` 은 이 샘플로 **무엇을 감독할 수 있는지**를 계산한다 —
`geometry` / `layout` / `texture` 3개 플래그 + 왜 안 되는지의 사유. 데이터 확보 단계의
판별 체크리스트를 코드로 옮긴 것이고, `make audit` 이 이걸 표로 찍는다:

```
dummy_000                [GL-] SLat 인코더가 연결되지 않아 texture(stage 2) 는 감독할 수 없습니다
범례: G=geometry L=layout T=texture
```

인덱스는 jsonl 이다 (`GarmentSampleIndex.to_jsonl` / `from_jsonl`). 경로는 상대경로로 담고
`root` 기준으로 해석하므로 데이터셋을 옮겨도 인덱스를 고치지 않는다.

## 데이터 주입 지점 (TODO 위치)

**코드를 고치는 게 아니라 config 를 바꿔서 연결한다.** 실데이터가 들어오면 손댈 곳은 아래뿐이다.

| # | 위치 | 지금 | 실데이터 연결 |
| --- | --- | --- | --- |
| 1 | `configs/*.yaml` → `paths.sample_index` | `null` (더미 생성) | 실인덱스 jsonl 경로 |
| 2 | `configs/*.yaml` → `paths.data_root` | `data` | 실데이터 루트 |
| 3 | `preprocess.voxelizer` | `numpy` (테스트용) | `sam3d` |
| 4 | `preprocess.latent_encoder` | `dummy` | `sam3d_ss` (stage 1) |
| 5 | `render.backend` | `dummy` | `sam3d` |
| 6 | `i2v.backend` + `endpoint` + `VIDEOGEN_API_KEY` | `dummy` | 제공자 확정 후 |
| 7 | `eval.*_backend` | `dummy`/`l2` | `mediapipe`/`opencv_farneback`/`lpips`/`insightface` |

`configs/real_backends.yaml` 이 3~7 을 켠 버전이다. 코드에 남은 `# TODO` 는 두 곳이다:

- `preprocess/latent.py::Sam3dSlatEncoder` — SLat 인코더 가중치 확인 후 채운다.
- `i2v/adapters.py::HttpStubAdapter` — 전송·폴링·디코딩. 제공자 규격 확정 후.

### 아직 CLI 로 안 되는 것

`latent_encoder=sam3d_ss` 는 `pipeline.models["ss_encoder"]` **모듈 주입**이 필요하다(수 GB
파이프라인을 인코더 클래스가 스스로 로드하지 않게 만들었다). CLI 에는 그 배관이 없으므로,
지금은 노트북/스크립트에서 이렇게 쓴다:

```python
from garment3d.preprocess import Sam3dSparseStructureEncoder, preprocess_index
encoder = Sam3dSparseStructureEncoder(pipeline.models["ss_encoder"], device="cuda")
results = preprocess_index(samples, config, encoder=encoder)
```

## 모듈 구조

```
garment3d/
  contracts.py          데이터 컨트랙트 + 감독 가능성 판정
  config.py             yaml/dict config. 모든 백엔드 선택과 경로가 여기 모인다
  data.py               더미 샘플 생성기 + 메시 I/O(trimesh 없이도 OBJ) + 인덱스 실재 검증
  preprocess/
    mesh_utils.py       watertight/manifold 검사, 정규화(upstream 식), subdivide/remesh
    voxelize.py         mesh → 64³ occupancy (numpy 폴백 / sam3d 위임)
    latent.py           occupancy → latent (dummy / sam3d_ss 실호출 / sam3d_slat stub)
    runner.py           샘플 하나를 학습 타깃까지 — 유일한 데이터 의존 지점
  train/
    lora.py             PEFT LoRA 부착 + **위험 타깃 거부**
    sft.py              스텝 스케줄(순수) + torch 학습 루프 + 체크포인트/resume
    dpo.py              best-of-N → 선호쌍 → Diffusion-DPO 손실 + 학습 루프
    dummy_flow.py       upstream 보간식을 따른 최소 flow 모듈 (스모크용)
  render/
    synthetic.py        결함 주입 가능한 합성 시퀀스 (지표 검증의 근거)
    turntable.py        렌더러 인터페이스 (dummy / sam3d)
    video.py            PNG 시퀀스 / GIF / mp4 저장
  i2v/
    base.py             VideoGen 어댑터 인터페이스 + 요청 스키마(start/end 키프레임, depth)
    adapters.py         dummy + HTTP stub
  eval/
    silhouette.py       실루엣 IoU 변동 + 엣지 일관성
    pose_scale.py       2D keypoint 기반 어깨너비·키 스케일 드리프트
    texture.py          flow 보정 잔차 / 지각적 플리커 / 회전 방향·대칭
    identity.py         얼굴 임베딩 코사인 (프레임 간 / 원본 대비)
    harness.py          같은 케이스·같은 지표로 turntable/I2V 둘 다 측정 + 승패
  report/builder.py     markdown/html 표 + 지표별 small multiples 플롯
  pipeline.py           엔드투엔드 스모크
  cli.py                audit / preprocess / smoke / sft / dpo
```

### 설계 원칙 두 개

1. **데이터 의존 로직과 비의존 로직을 갈라 뒀다.** 디스크를 만지는 건
   `preprocess/runner.py`, `data.py`, `render/video.py` 뿐이고, 위생검사·복셀화·지표·리포트는
   전부 순수 함수다. 그래서 데이터 없이도 단위테스트가 성립한다.
2. **무거운 의존성은 전부 선택적이다.** torch/peft/trimesh/opencv/matplotlib/lpips 는
   함수 안에서 lazy import 하고, 없으면 **조용히 폴백하지 않고 무엇이 없어서 무엇을 못 했는지
   남긴다.** 지표 결과에 `flow_backend` 같은 필드가 함께 실리는 이유가 그것이다.

## 평가 지표

`eval/harness.py::METRIC_DIRECTIONS` 가 각 지표의 방향(클수록 좋음/작을수록 좋음/진단용)의
**단일 출처**다. 리포트도 승패 판정도 여기만 읽는다.

| 축 | 지표 | 방향 |
| --- | --- | --- |
| 형태·핏 일관성 | `silhouette_iou_mean` / `_std` / `_min`, `silhouette_area_cv`, `edge_density_cv`, `edge_iou_mean` | 혼합 |
| 체형 스케일 드리프트 | `scale_height_cv`, `scale_height_drift`, `scale_shoulder_ratio_cv` | 작을수록 |
| 텍스처 안정성 | `texture_flow_residual_mean` / `_std`, `texture_perceptual_mean`, `texture_perceptual_flicker`, `texture_direction_flip_ratio`, `texture_symmetry_error` | 작을수록 |
| identity | `identity_cosine_mean` / `_min`, `identity_vs_reference_mean` / `_last` | 클수록 |
| 진단(판정 제외) | `foreground_ratio_mean`, `scale_missing_ratio`, `identity_detect_ratio` | — |

### 숫자를 읽기 전에 알아야 할 것

- **어깨너비는 회전에 따라 실제로 변한다.** 그래서 분산 그대로가 아니라 **키로 정규화한 비율**의
  변동을 본다. 세로 스케일(키)은 회전 불변량이라 그쪽이 흔들리면 그게 드리프트다.
- **`flow_backend=dummy` 면 `flow_residual` 은 raw 프레임 차분이다.** 회전에 의한 정상적 변화가
  제거되지 않았다는 뜻이고, 하네스가 경고로 남긴다.
- **밝기 임계치로 실루엣을 뽑는다.** 임계치가 시퀀스에 안 맞으면 실루엣·스케일 지표 전체가
  무의미해진다. `foreground_ratio_mean` 이 0/1 에 붙으면 `eval.background_threshold` 를 고쳐야
  한다. 특히 밝기 잡음이 심한 I2V 출력은 배경이 전경으로 새어 들어와 **면적이 오히려 안정돼
  보이는 역전**이 생긴다.
- **`texture_symmetry_error` 의 성립 조건은 좁다** — 닫힌 360° 시퀀스 + 좌우 대칭에 가까운
  피사체. 절대 판정이 아니라 turntable vs I2V 상대 비교로만 읽는다.
- **`direction_flip_ratio` 는 정답 방향을 모르는 상태의 일관성 지표다.** 한 방향으로 꾸준히
  도는지만 본다(중간에 뒤집히는 게 I2V 의 전형적 실패다). ZeroFlow 로는 0.0 이 나오는데
  그건 "뒤집힘 없음"이 아니라 "판정 불가"다.
- **의류 단독 크롭에는 얼굴이 없다.** 그때는 `eval.measure_identity=false` 로 끈다. 임베딩을
  못 얻으면 지표는 `None` 이고 0 으로 채우지 않는다 — 0 은 "정체성이 완전히 무너졌다"로 읽힌다.
- 더미 `pose`/`face` 백엔드는 마스크 기하·상단 패치 기반 **프록시**다. 프레임 간 변동을 보는
  데는 유효하지만 실측 비교에는 `mediapipe`/`insightface` 로 바꿔야 한다.

## DPO 정식화

flow/diffusion 모델에는 토큰 로그확률이 없으므로 Diffusion-DPO 계열의 암묵적 보상을 쓴다:

```
z = -β · [ (L_policy(chosen) - L_ref(chosen)) - (L_policy(rejected) - L_ref(rejected)) ]
loss = -log σ(z)
```

`L` 은 **손실**이라 작을수록 좋다. 부호를 두 군데 적으면 반드시 어긋나므로
`dpo_logits()` 한 함수에 모아 두고 numpy/torch 양쪽이 같은 함수를 쓴다
(`test_dpo_logits_sign_convention_rewards_lower_chosen_loss` 가 이 부호를 지킨다).

참조모델은 **LoRA 어댑터를 끈 같은 베이스**를 전제하며, 그 스위칭은 호출자가 `ref_loss_fn` 으로
주입한다(peft 버전별 API 차이를 학습 루프에 묶지 않기 위해). `DpoTrainer` 는 참조 손실을 한 번 더
detach 한다 — 참조모델까지 학습되는 게 가장 비싼 실수다.

## 비용·안전 규율

`AI/CLAUDE.md` 의 하드 룰을 따른다.

- **모든 기본값이 무과금·무의존이다.** `i2v.backend=dummy`, `render.backend=dummy`,
  `preprocess.voxelizer=numpy`. `test_defaults_are_all_free_backends` 가 이걸 지킨다.
- `HttpStubAdapter` 는 **전송 코드가 없다.** `endpoint` 가 비어 있으면 시도조차 하지 않고,
  API 키는 환경변수(`VIDEOGEN_API_KEY`)에서만 읽는다. 제공자 규격을 추측해 구현하지 않았다.
- `configs/real_backends.yaml` 은 과금 경로를 포함하므로 **사용자가 직접** 켠다.

## 테스트

```
222 passed                    # torch + peft + matplotlib + opencv 있는 환경
205 passed, 17 skipped        # CI 환경 (AI/requirements-dev.txt 만 설치, torch 없음)
```

CI(`ai-test`)는 `AI/requirements-dev.txt` 만 설치하고 `AI/**` 전체에 `ruff`/`black`/`pytest` 를
돌린다. 그래서 **torch/peft/matplotlib 을 쓰는 테스트는 전부 `pytest.importorskip` 으로 감싸
있다** — 이 규약을 깨면 CI 가 빨개진다. 순수 로직(컨트랙트·config·메시 위생·복셀화·지표·리포트)은
CI 에서 그대로 실행된다.

테스트가 지키는 것 중 특히 중요한 것들:

- `test_sam3dft_lora.py` — SparseLinear 타깃을 **부착 전에** 거부하는가 (가짜 모듈로, torch 없이)
- `test_sam3dft_dpo.py` — DPO 손실 부호 규약, 참조모델이 학습되지 않는가
- `test_sam3dft_sft.py` — `max_steps` 가 업데이트 횟수인가, 마지막 스텝이 저장되는가, resume
- `test_sam3dft_eval.py` — 지표가 **결함 주입에 실제로 반응하는가**(항상 같은 값을 뱉으면 실패)
- `test_sam3dft_e2e.py` — 더미 엔드투엔드 + CLI

파일명은 `test_sam3dft_*.py` 로 통일했다 — pytest 가 basename 으로 모듈을 식별해서
**리포 전체에서 유일해야** 한다(`AI/CLAUDE.md` 테스트 배치 규칙).

## 다음 단계

1. **SLat 특징 집계 규약을 정한다** — 뷰 개수·카메라 분포·DINOv2 레이어·복셀당 집계 방식.
   가중치(`slat_encoder.ckpt`)와 특징 추출기(`dino.Dino`)는 이미 있으니 이 규약만 확정되면
   stage 2 경로를 채울 수 있다. 확정 못 하면 stage 1(기하)만 LoRA 학습하는 것으로 범위를 닫는다.
   그리고 다운로드가 끝난 뒤 **`ss_encoder.safetensors` 가 0 바이트가 아닌지** 확인한다.
2. 데이터를 확보하면 `make audit` 으로 **(이미지, 메시) 페어링과 카메라 extrinsic 보유율**을
   먼저 측정한다. 페어링이 없으면 visually-grounded SFT 가 아니라 합성 렌더 pretraining 보강에
   가까워지므로, 그 수치가 파인튜닝 방식 자체를 결정한다.
3. VideoGen 제공자를 정하고 `HttpStubAdapter` 를 채운 뒤, 실제 케이스로
   turntable vs I2V 를 돌려 `METRIC_DIRECTIONS` 기준으로 판정한다.
