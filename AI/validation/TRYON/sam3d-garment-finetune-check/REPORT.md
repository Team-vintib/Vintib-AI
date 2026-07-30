# 선결 조사 — `facebookresearch/sam-3d-objects` 에 무엇이 공개돼 있는가

조사 대상 커밋: `f91db41` ("SA-3DAO Release - README Update (#190)"), 로컬 클론
`~/workspace/sam-3d-objects`. 아래 표의 "위치"는 그 클론 기준 경로다.

체크포인트는 **1차 조사 시점에는 없었고**(빈 디렉터리) 조사 도중 사용자가 받기 시작해서
`S15P11A108/checkpoints/hf/` 에서 파일 목록과 yaml 을 직접 확인했다(2026-07-29 17:12 시점).
그 결과 §5 의 미확정 항목이 해소됐다 — **SLat 인코더 가중치는 릴리스에 포함된다.**

> ⚠️ 관측 당시 다운로드가 **진행 중**이었고 직후 디렉터리가 비어 있는 상태로 바뀌었다
> (`hf download` 의 `-download` 폴더 → `mv` 과정으로 보인다). 아래 파일 목록·크기는 그
> 시점의 관측이며, **최종 경로는 다운로드가 끝난 뒤 다시 확인해야 한다.**

## 요약 표

| # | 항목 | 공개 여부 | 위치 |
| --- | --- | --- | --- |
| 1 | 추론 파이프라인 | ✅ | `sam3d_objects/pipeline/inference_pipeline.py`, `inference_pipeline_pointmap.py`, `notebook/inference.py::Inference` |
| 2 | 로드된 모델 접근 경로 | ✅ | `pipeline.models` (`torch.nn.ModuleDict`) |
| 3 | mesh → 64³ occupancy | ✅ | `sam3d_objects/pipeline/inference_utils.py::voxelize_mesh` |
| 4 | 64³ → sparse structure latent 인코더 | ✅ 코드 + 파이프라인 연결 | `models["ss_encoder"]` = `SparseStructureEncoder` |
| 5 | SLat(structured latent) **인코더** | ✅ 가중치까지 있음 (파이프라인만 미연결) | 클래스 `structured_latent_vae/encoder.py::SLatEncoder`, 가중치 `checkpoints/hf/slat_encoder.ckpt` |
| 6 | SLat 학습 타깃 구성(멀티뷰 렌더 + 특징 집계) | ❌ 없음 — **stage 2 의 실제 병목** | 특징 추출기 `dit/embedder/dino.py::Dino` 는 있다 |
| 7 | 학습 **손실** | ✅ | `flow_matching/model.py::FlowMatching.loss`, `shortcut/model.py::ShortCut.loss` |
| 8 | 학습 루프 / 옵티마이저 / 스케줄러 | ❌ 없음 | — |
| 9 | DPO / 선호학습 | ❌ 없음 | — |
| 10 | PEFT(LoRA) | ✅ 의존성에 이미 있음 | `requirements.txt` 의 `peft==0.10.0` |
| 11 | turntable 렌더 | ✅ | `notebook/inference.py::render_video`, `kaolin.visualize.IpyTurntableVisualizer` |
| 12 | 메시(glb) 출력 | ✅ 단 기본 off | `postprocess_slat_output(..., with_mesh_postprocess=True)` |

## 세부

### 1·2. 파이프라인과 모델 접근 경로

`notebook/inference.py::Inference.__call__` 은 `InferencePipelinePointMap.run()` 을 호출하고,
`run()` 은 `**ss_return_dict`(레이아웃: `coords` / `rotation` / `translation` / `scale`) +
디코딩 출력 + `pointmap` 을 합친 dict 를 돌려준다.

디코딩 출력 키는 `inference_pipeline.py::decode_slat` 에서 정해진다 — `"mesh"`, `"gaussian"`,
`"gaussian_4"`. 데모가 쓰는 `output["gs"]` 는 `postprocess_slat_output` 이
`outputs["gs"] = outputs["gaussian"][0]` 로 만들어 주는 별칭이다(`inference_pipeline.py:564`).

모델은 `pipeline.models` 한 곳에 모여 있다(`inference_pipeline.py:189`):

```python
self.models = torch.nn.ModuleDict(
    {
        "ss_generator": ss_generator,          # stage 1: sparse structure(기하) flow
        "slat_generator": slat_generator,      # stage 2: structured latent(텍스처/디테일) flow
        "ss_encoder": ss_encoder,
        "ss_decoder": ss_decoder,
        "slat_decoder_gs": slat_decoder_gs,
        "slat_decoder_gs_4": slat_decoder_gs_4,
        "slat_decoder_mesh": slat_decoder_mesh,
    }
)
```

**`slat_encoder` 키는 없다.** 항목 5 참고.

generator 는 flow matching 래퍼이고 실제 트랜스포머는 한 겹 더 안에 있다 —
`pipeline.models["ss_generator"].reverse_fn.backbone` (`inference_pipeline.py:620`,
`is_mm_dit()` 가 이 경로로 `latent_mapping` 속성을 확인한다). LoRA 는 이 `backbone` 에 붙인다.

### 3. mesh → 64³ occupancy — 있다

`inference_utils.py::voxelize_mesh(mesh, resolution=64)`:

- z-up → y-up 회전(`[[1,0,0],[0,0,-1],[0,1,0]]`)을 **먼저** 적용한다.
- 이미 `[-0.5, 0.5]` 로 정규화된 메시면 정규화를 건너뛰고, 아니면
  `normalize_mesh_verts` 로 최대 변 길이 기준 정규화한다.
- `open3d` 의 `VoxelGrid.create_from_triangle_mesh_within_bounds(voxel_size=1/64)` 를 쓴다 —
  **표면 복셀화(surface voxelization)이고 내부를 채우는 solid occupancy 가 아니다.**
- 반환: `(ss[1,64,64,64] long, scale, center)`. `scale`/`center` 는 이미 정규화된 입력이면 `None`.

우리 코드는 이걸 그대로 부르고(백엔드 `sam3d`), open3d 없이도 단위테스트가 돌게 순수 numpy
표면 복셀화 폴백(백엔드 `numpy`)을 따로 둔다. 폴백은 **동일 결과를 보장하지 않는다** — 학습
데이터 생성에는 `sam3d` 백엔드만 쓴다.

### 4·5·6. 인코더 — stage 1 은 바로 되고, stage 2 는 "타깃 생성 코드"만 없다

- **stage 1 (기하)**: `voxelize_mesh` → `models["ss_encoder"]` 로 SFT 타깃(sparse structure
  latent)을 **공개 코드만으로 만들 수 있다.**
- **stage 2 (SLat)**: `SLatEncoder` 클래스는 있지만 `InferencePipeline` 이 instantiate 하지
  않는다(`models` ModuleDict 에 `slat_encoder` 키가 없다). 다만 **가중치는 릴리스에 있다** —
  `checkpoints/hf/slat_encoder.ckpt` (173 MB) + `slat_encoder.yaml`:

  ```yaml
  _target_: ...structured_latent_vae.encoder.SLatEncoderTdfyWrapper
  resolution: 64
  model_channels: 768
  latent_channels: 8
  in_channels: 1024      # ← 입력이 occupancy 가 아니라 1024차 특징이다
  num_blocks: 12
  num_heads: 12
  ```

  `in_channels: 1024` 이 결정적이다. SLat 인코더의 입력은 **활성 복셀별 1024차 시각 특징**이고,
  1024 는 DINOv2 ViT-L 의 embed_dim 이다. 실제로 릴리스의 조건 임베더가 그 모델을 쓴다
  (`ss_generator.yaml` → `dit.embedder.dino.Dino(dino_model="dinov2_vitl14_reg", input_size=518)`),
  그리고 `dino.py::Dino` 는 `torch.hub.load("facebookresearch/dinov2", …)` 범용 래퍼라
  **특징 추출기도 릴리스 안에 있다.**

  → 그래서 stage 2 에 실제로 없는 것은 **하나**다: GT 메시를 멀티뷰로 렌더해 DINOv2 특징을
  뽑고 **활성 복셀에 집계**하는 단계(TRELLIS 계열 데이터 엔진). `data/dataset/tdfy/` 는 추론용
  이미지·마스크 전처리와 pose target 뿐이고, (이미지, 메시) 쌍 Dataset 도 SLat 타깃 생성기도 없다.
  **그 규약(뷰 개수·카메라 분포·DINO 레이어·집계 방식)이 문서화되지 않았으므로 추측하지 않는다.**

→ **그래서 `garment3d/preprocess/latent.py` 는 stage 1 실호출 + stage 2 stub 이다.**
`Sam3dSlatEncoder` 는 `NotImplementedError` 이고, 채워야 할 것이 "가중치 확보"가 아니라
"특징 집계 규약 확정"이라는 사실이 TODO 에 적혀 있다.

### 7. 학습 손실 — 있다 (중요). 단 generator 클래스마다 다르다

`FlowMatching.loss(x1, *args_conditionals, **kwargs_conditionals)` 가 공개돼 있고
`(total_loss, detail_losses)` 를 돌려준다. 내부적으로 `_generate_t` → `_generate_x0` →
`_generate_xt` → `_generate_target` → `reverse_fn(x_t, t*time_scale, cond)` 를 수행한다.

**주의**: 실제 `ss_generator` 는 순수 `FlowMatching` 이 아니다. `ss_generator.yaml` 을 보면
`generator.shortcut.model.ShortCut` 이고, `ShortCut(FlowMatching)` 은 `loss()` 를
**오버라이드**해서 flow matching 항과 self-consistency 항을 섞는다(`d` 를 reverse_fn 에 추가로
넘긴다). 시그니처는 같으므로 우리 어댑터는 그대로 동작하지만, **"우리가 계산하는 손실이
정확히 무엇인가"는 로드된 generator 클래스가 결정한다.**

같은 yaml 에서 읽히는 다른 사실:

- `reverse_fn` 이 `ClassifierFreeGuidanceWithExternalUnconditionalProbability` 로 한 겹 더
  감싸져 있고 그 안이 `mot_sparse_structure_flow.SparseStructureFlowTdfyWrapper` 다.
  → `resolve_backbone()` 이 `reverse_fn` → `backbone` 을 반복해서 따라가는 이유가 이것이다.
- `loss_weights` 가 `{shape: 0, translation: 1.0, scale: 0.1, 6drotation_normalized: 0.1}` 다.
  **`shape` 가중치가 0** 이므로 이 체크포인트의 ss_generator 손실은 레이아웃 항이 지배한다 —
  의류 형태를 학습시키려면 이 가중치를 조정해야 하고, 그건 config 판단이지 코드 판단이 아니다.

즉 **손실을 우리가 다시 구현할 필요가 없다.** `garment3d/train/sft.py` 는 `loss()` 를 호출하는
얇은 어댑터(`Sam3dFlowLoss`)를 쓰고, 학습 루프(옵티마이저·누적·체크포인트·resume)만 우리가 갖는다.

### 8·9. 학습 루프와 DPO — 없다

`grep -rln "optimizer\|\.backward()\|AdamW" sam3d_objects/` 는 3개 파일만 잡는데 전부 학습이
아니다 — `dit/embedder/dino.py`, `utils/postprocessing_utils.py`,
`pipeline/layout_post_optimization_utils.py`(테스트타임 레이아웃 최적화). **옵티마이저를 돌리는
학습 스크립트는 릴리스에 없다.** DPO 도 없다. 둘 다 우리가 새로 쓴다.

### 10. LoRA 부착 지점 — 안전한 타깃과 깨지는 타깃이 나뉜다 ⚠️

`sp.SparseLinear` 는 `nn.Linear` **서브클래스**인데 forward 가 `SparseTensor` 를 받는다
(`modules/sparse/linear.py`):

```python
class SparseLinear(nn.Linear):
    def forward(self, input: SparseTensor) -> SparseTensor:
        return input.replace(super().forward(input.feats))
```

PEFT 의 `lora.Linear` 는 `isinstance(module, nn.Linear)` 로 잡아 놓고
`base_layer(x) + lora_B(lora_A(dropout(x)))` 를 계산한다. `x` 가 `SparseTensor` 면
`lora_A` (순수 `nn.Linear`) 가 그걸 그대로 받아 **터진다.**

반면 어텐션의 `to_qkv`/`to_q`/`to_kv`/`to_out` 은 순수 `nn.Linear` 이고,
`SparseMultiHeadAttention._linear()` 가 `x.replace(module(x.feats))` 로 **dense 텐서만
통과시킨다** → PEFT LoRA 가 정상 동작한다.

| 모듈 이름 | 타입 | 입력 | LoRA |
| --- | --- | --- | --- |
| `to_qkv` (self-attn) | `nn.Linear` | dense (`.feats`) | ✅ 안전 |
| `to_q`, `to_kv` (cross-attn) | `nn.Linear` | dense (`.feats`) | ✅ 안전 |
| `to_out` | `nn.Linear` | dense (`.feats`) | ✅ 안전 |
| `input_layer`, `out_layer` (SLat 계열) | `SparseLinear` | `SparseTensor` | ❌ 깨진다 |
| `mlp.0`, `mlp.2` (`SparseFeedForwardNet`) | `SparseLinear` | `SparseTensor` | ❌ 깨진다 |

→ `configs/garment_lora.yaml` 의 `target_modules` 기본값은 `[to_qkv, to_q, to_kv, to_out]`
이고, `garment3d/train/lora.py::assert_lora_targets_safe()` 가 `SparseLinear` 타깃을
**부착 전에** 거부한다. 위험 목록을 주석으로만 남기면 언젠가 누가 `mlp` 를 넣는다.

`sparse_structure_flow.py` 쪽(stage 1)은 dense `nn.Linear` 기반이라 `input_layer`/`out_layer`
도 안전하지만, 두 stage 를 같은 config 로 다루므로 기본값은 보수적으로 둔다.

### 11·12. 렌더링과 메시 출력

`notebook/inference.py` 가 `render_video(scene, r, fov, pitch_deg, yaw_start_deg, resolution)`
→ `["color"]` 프레임 리스트를 준다. **다만 이건 `kaolin` + `gsplat` + `pytorch3d` 가 깔린
환경에서만 임포트된다**(`notebook/inference.py` 최상단이 `import gradio`, `from kaolin...`,
`from pytorch3d.transforms ...` 를 무조건 수행하고, `os.environ["CUDA_HOME"] = os.environ["CONDA_PREFIX"]`
때문에 conda 환경 밖에서는 `KeyError` 로 죽는다).

→ 우리 `garment3d/render/turntable.py` 는 `TurntableRenderer` 인터페이스 + 백엔드 2개다:
`sam3d`(위 `render_video` 위임, lazy import) / `dummy`(순수 numpy 합성 프레임, 테스트용).

메시는 `with_mesh_postprocess=True` 로 `postprocess_slat_output` 을 부르면 `outputs["glb"]`
가 생긴다. `Inference.__call__` 이 이 값을 `False` 로 하드코딩해 두었으므로, glb 가 필요하면
`Inference` 를 우회해 파이프라인을 직접 불러야 한다.

## 관측한 체크포인트 파일 (2026-07-29 17:12, `S15P11A108/checkpoints/hf/`)

| 파일 | 크기 |
| --- | --- |
| `ss_generator.ckpt` | 6.69 GB |
| `slat_generator.ckpt` | 4.91 GB |
| `slat_decoder_mesh.ckpt` / `.pt` | 363 MB 각 |
| `slat_encoder.ckpt` | 173 MB |
| `slat_decoder_gs.ckpt` | 171 MB |
| `slat_decoder_gs_4.ckpt` | 170 MB |
| `ss_decoder.ckpt` | 148 MB |
| `ss_encoder.ckpt` | 119 MB |
| `ss_encoder.safetensors` | **0 바이트** ⚠️ |

⚠️ **`ss_encoder.safetensors` 가 0 바이트다.** `SLatEncoderTdfyWrapper`/`SparseStructure…Wrapper`
는 `pretrained_ckpt_path` 의 확장자가 `.safetensors` 면 `load_file()` 로 읽는다
(`encoder.py:86`) — 이 빈 파일을 가리키면 로드가 실패한다. 다운로드가 진행 중이던 시점의 관측일
수 있으니 **완료 후 크기를 다시 확인**하고, 실패하면 `.ckpt` 쪽을 쓰도록 경로를 지정해야 한다.

> 리포 루트에 12 GB 가 놓이므로 루트 `.gitignore` 에 `/checkpoints/` 를 추가해 뒀다.
> `git add .` 한 번으로 리포가 폭발하는 걸 막기 위한 것이다.

## 아직 확정하지 못한 것

1. **SLat 특징 집계 규약** (항목 6) — 뷰 개수, 카메라 분포, DINOv2 어느 레이어의 출력,
   복셀당 집계 방식(평균? 가시성 가중?). 릴리스에 코드가 없어 추측하지 않았다. stage 2
   파인튜닝을 하려면 이걸 먼저 정해야 한다.
2. 기하/텍스처 트랜스포머의 **정확한 파라미터 수** — 과제 설명의 1.2B / 600M 은 검증하지
   않았다. `.ckpt` 파일 크기(6.69 GB / 4.91 GB)는 옵티마이저·EMA 상태가 섞여 있을 수 있어
   파라미터 수로 환산할 수 없다. `state_dict` 를 열어서 세야 확정된다.
3. 다운로드 완료 후의 **최종 체크포인트 경로** — 위 관측 직후 디렉터리가 비어 있는 상태로
   바뀌었다. `configs/*.yaml` 의 `paths.sam3d_pipeline_config` 를 그 경로로 맞춰야 한다
   (절대경로도 받는다 — `PathsConfig.pipeline_config_path()`).
