"""config — 모든 데이터 의존 지점과 백엔드 선택을 여기 한곳으로 모은다.

`app/pricing/registry.py` 의 `ACTIVE_*` 관례를 따른다: 백엔드는 이름(문자열)으로 고르고
**기본값은 항상 비용·의존성이 없는 쪽**(`dummy` / `numpy`)이다. 실백엔드 전환은 yaml 한 줄이다.

hydra 를 쓰지 않은 이유: 이 스캐폴드는 `sam3d_objects` 와 **별도 프로세스로도 돌아야 하고**
(평가·리포트는 kaolin 없이 돌린다) CI 에서 pydantic 만으로 검증되는 편이 낫다.
`sam3d_objects` 쪽 hydra config 는 `pipeline.yaml` 경로 하나로만 참조한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ── 백엔드 레지스트리 (이름 → 구현) ──────────────────────────────────────────
#
# 실제 구현 클래스는 각 모듈이 자기 레지스트리에 등록한다. 여기 상수는 **기본 선택값**이다.
VOXELIZER_BACKENDS = ("numpy", "sam3d")
LATENT_BACKENDS = ("dummy", "sam3d_ss", "sam3d_slat")
RENDERER_BACKENDS = ("dummy", "sam3d")
I2V_BACKENDS = ("dummy", "http_stub")
POSE_BACKENDS = ("dummy", "mediapipe")
FLOW_BACKENDS = ("dummy", "opencv_farneback")
PERCEPTUAL_BACKENDS = ("l2", "lpips")
FACE_BACKENDS = ("dummy", "insightface")


class PathsConfig(BaseModel):
    """**데이터 주입 지점.** 실데이터가 들어오면 여기만 바꾼다."""

    model_config = ConfigDict(extra="forbid")

    #: SAM 3D Objects 리포 클론. `sam3d` 백엔드들이 여기서 import 한다.
    sam3d_repo: Path = Path("~/workspace/sam-3d-objects")
    #: `pipeline.yaml` 위치. **상대경로면 `sam3d_repo` 기준, 절대경로면 그대로 쓴다** —
    #: 체크포인트를 리포 클론 밖에 받는 경우가 흔하다(실제로 이 프로젝트에서는 S15P11A108
    #: 리포 루트에 받았다). 해석은 `pipeline_config_path()` 가 한다.
    sam3d_pipeline_config: Path = Path("checkpoints/hf/pipeline.yaml")
    #: 샘플 인덱스(jsonl). **TODO: 실데이터 확보 후 여기를 채운다.**
    sample_index: Path | None = None
    #: 데이터 루트. 인덱스의 상대경로 기준점.
    data_root: Path = Path("data")
    #: 전처리 산출물(occupancy npz, latent pt) 캐시.
    cache_dir: Path = Path("artifacts/cache")
    #: 체크포인트.
    checkpoint_dir: Path = Path("artifacts/checkpoints")
    #: 렌더/비디오/리포트 산출물.
    output_dir: Path = Path("artifacts/outputs")

    def expanded(self) -> PathsConfig:
        """`~` 를 펼친 복사본. 경로를 쓰는 쪽은 항상 이걸 거친다."""
        return self.model_copy(
            update={
                name: Path(value).expanduser()
                for name, value in self.model_dump().items()
                if isinstance(value, (str, Path))
            }
        )

    def pipeline_config_path(self) -> Path:
        """`pipeline.yaml` 의 실제 경로. 상대경로면 `sam3d_repo` 기준으로 붙인다.

        체크포인트를 리포 클론 안에 두지 않는 경우를 위해 절대경로를 그대로 통과시킨다 —
        경로를 붙이는 로직이 호출처마다 흩어지면 반드시 한쪽이 어긋난다.
        """
        paths = self.expanded()
        candidate = paths.sam3d_pipeline_config
        return candidate if candidate.is_absolute() else paths.sam3d_repo / candidate


class PreprocessConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    #: `numpy` = 의존성 없는 표면 복셀화(테스트용). `sam3d` = open3d 경유 upstream 함수.
    #: ⚠️ 두 백엔드는 동일 결과를 보장하지 않는다 — 학습 데이터 생성은 `sam3d` 만 쓴다.
    voxelizer: Literal["numpy", "sam3d"] = "numpy"
    resolution: int = 64
    #: `dummy` = 결정적 난수 latent(테스트용). `sam3d_ss` = stage 1 실인코더.
    #: `sam3d_slat` = stage 2 — **미구현(REPORT.md §5)**.
    latent_encoder: Literal["dummy", "sam3d_ss", "sam3d_slat"] = "dummy"
    #: watertight 아닌 메시를 자동 수선할지. cloth 메시는 open surface 가 흔하다.
    repair_non_watertight: bool = True
    #: 리메시 목표 면 수. None 이면 리메시하지 않는다.
    target_faces: int | None = None
    #: occupancy 활성 복셀이 이보다 적으면 샘플을 버린다(빈 메시·정규화 실패 감지).
    min_active_voxels: int = 8


class LoraConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int = 16
    alpha: int = 32
    dropout: float = 0.0
    #: ⚠️ `SparseLinear` 모듈(`input_layer`/`out_layer`/`mlp.*`)을 넣으면 PEFT 가 깨진다.
    #: 근거는 `REPORT.md` §10. `assert_lora_targets_safe()` 가 부착 전에 막는다.
    target_modules: list[str] = Field(default_factory=lambda: ["to_qkv", "to_q", "to_kv", "to_out"])
    #: `pipeline.models` 의 어느 키에 붙일지. 기하만 = ["ss_generator"].
    target_models: list[str] = Field(default_factory=lambda: ["ss_generator"])


class SftConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_steps: int = 1000
    batch_size: int = 1
    grad_accum_steps: int = 1
    learning_rate: float = 1e-4
    weight_decay: float = 0.0
    #: 몇 스텝마다 체크포인트를 남길지.
    save_every: int = 100
    log_every: int = 10
    seed: int = 42
    #: `resume` 이 가리키는 체크포인트에서 이어서 학습한다. None 이면 처음부터.
    resume: Path | None = None
    #: 학습 대상 stage. `REPORT.md` §5 때문에 texture 는 데이터 준비가 막혀 있다.
    stage: Literal["geometry", "texture"] = "geometry"
    device: str = "cpu"


class DpoConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    #: best-of-N 후보 수.
    num_candidates: int = 4
    #: 승자-패자 점수 차가 이보다 작으면 쌍을 버린다(노이즈 쌍 제거).
    min_margin: float = 0.05
    #: DPO 온도. 클수록 참조모델에서 멀어지는 걸 강하게 벌한다.
    beta: float = 0.1
    max_steps: int = 200
    learning_rate: float = 5e-6
    batch_size: int = 1
    save_every: int = 50
    seed: int = 42
    device: str = "cpu"


class RenderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: Literal["dummy", "sam3d"] = "dummy"
    #: 한 바퀴를 몇 프레임으로 쪼갤지. I2V 비교는 **프레임 수를 맞춰야** 지표가 비교된다.
    num_frames: int = 24
    resolution: int = 256
    fov: float = 60.0
    pitch_deg: float = 15.0
    yaw_start_deg: float = -45.0
    radius: float = 1.0
    fps: int = 12
    #: mp4 로도 저장할지. imageio-ffmpeg 가 없으면 GIF 만 남는다.
    write_mp4: bool = True


class I2vConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: Literal["dummy", "http_stub"] = "dummy"
    #: API 키를 **직접 적지 않는다.** 이 이름의 환경변수에서 읽는다.
    api_key_env: str = "VIDEOGEN_API_KEY"
    endpoint: str | None = None
    model: str = "unset"
    prompt: str = "rotate the garment 360 degrees, fixed camera, neutral background"
    num_frames: int = 24
    fps: int = 12
    resolution: int = 256
    #: 시작/끝 키프레임 조건. 턴테이블과 달리 I2V 는 한 바퀴가 닫히지 않는 경우가 많다.
    use_end_keyframe: bool = False
    #: depth 맵 조건 입력 자리. 어댑터가 지원하지 않으면 무시된다.
    use_depth_condition: bool = False
    timeout_sec: float = 300.0


class EvalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pose_backend: Literal["dummy", "mediapipe"] = "dummy"
    flow_backend: Literal["dummy", "opencv_farneback"] = "dummy"
    perceptual_backend: Literal["l2", "lpips"] = "l2"
    face_backend: Literal["dummy", "insightface"] = "dummy"
    #: 실루엣 마스크를 프레임에서 뽑을 때 배경으로 볼 밝기 임계치(0~255).
    #: 렌더 배경이 검정이라 기본값이 낮다. I2V 출력 배경은 다를 수 있어 케이스별로 조정한다.
    background_threshold: int = 12
    #: 회전 대칭 검사에서 짝지을 프레임 간격(프레임 수의 절반이 기본).
    symmetry_offset: int | None = None
    #: 얼굴 임베딩 유사도를 계산할지. 의류 단독 크롭에는 얼굴이 없다.
    measure_identity: bool = True


class ReportConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    formats: list[Literal["markdown", "html"]] = Field(default_factory=lambda: ["markdown", "html"])
    #: 플롯을 그릴지. matplotlib 이 없으면 자동으로 표만 남긴다.
    plots: bool = True
    title: str = "turntable vs I2V 비교"


class Config(BaseModel):
    """루트 config."""

    model_config = ConfigDict(extra="forbid")

    paths: PathsConfig = Field(default_factory=PathsConfig)
    preprocess: PreprocessConfig = Field(default_factory=PreprocessConfig)
    lora: LoraConfig = Field(default_factory=LoraConfig)
    sft: SftConfig = Field(default_factory=SftConfig)
    dpo: DpoConfig = Field(default_factory=DpoConfig)
    render: RenderConfig = Field(default_factory=RenderConfig)
    i2v: I2vConfig = Field(default_factory=I2vConfig)
    eval: EvalConfig = Field(default_factory=EvalConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Config:
        """dict → Config. yaml 없이도 쓸 수 있는 경로다(테스트가 이걸 쓴다)."""
        return cls.model_validate(raw or {})

    @classmethod
    def from_yaml(cls, path: Path | str) -> Config:
        """yaml 파일 하나를 읽는다. PyYAML 이 없으면 명확한 에러를 낸다."""
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover - 환경 의존
            raise RuntimeError("PyYAML 이 필요합니다: pip install pyyaml") from exc

        text = Path(path).read_text(encoding="utf-8")
        return cls.from_dict(yaml.safe_load(text) or {})

    def merged(self, overrides: dict[str, Any]) -> Config:
        """중첩 dict 를 깊게 병합한 새 Config. CLI 의 `--set a.b=c` 를 받는 자리다."""
        return Config.from_dict(_deep_merge(self.model_dump(mode="json"), overrides))


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """`override` 를 `base` 위에 깊게 덮는다. dict 가 아닌 값은 통째로 교체."""
    out = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def parse_overrides(pairs: list[str]) -> dict[str, Any]:
    """`["sft.max_steps=5", "render.backend=dummy"]` → 중첩 dict.

    값은 json 으로 먼저 파싱해 보고(숫자/bool/null/리스트), 실패하면 문자열로 둔다.
    """
    import json

    out: dict[str, Any] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise ValueError(f"'키=값' 형식이 아닙니다: {pair!r}")
        key, _, raw = pair.partition("=")
        try:
            value: Any = json.loads(raw)
        except (ValueError, TypeError):
            value = raw
        cursor = out
        parts = key.strip().split(".")
        for part in parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[parts[-1]] = value
    return out
