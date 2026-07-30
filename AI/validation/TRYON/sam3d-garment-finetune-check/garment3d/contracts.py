"""데이터 컨트랙트 — 아직 없는 데이터가 "들어올 자리"를 스키마로 못박는다.

이 모듈은 **데이터 비의존**이다. 파일을 읽지 않고 경로와 메타데이터의 형태만 규정한다.
실제 로딩은 `garment3d.data`(더미) / 나중의 실데이터 어댑터가 맡는다.

핵심 설계 근거는 `REPORT.md` §4·5 — SAM 3D 의 SFT 타깃은 두 단계로 갈린다.

- stage 1 (기하): mesh → 64³ occupancy → sparse structure latent. **공개 코드로 만들 수 있다.**
- stage 2 (SLat): 릴리스에 타깃 생성 코드가 없다. 그래서 `SupervisionAvailability` 가
  "이 샘플로 무엇을 감독할 수 있는지"를 명시적으로 계산한다 — 조용히 반쪽 학습이 되는 걸 막는다.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

Quaternion = Annotated[list[float], Field(min_length=4, max_length=4)]
Vec3 = Annotated[list[float], Field(min_length=3, max_length=3)]


class GarmentCategory(str, Enum):
    """의류 대분류. 카테고리별 지표 집계와 프롬프트 분기에 쓴다."""

    TOP = "top"
    BOTTOM = "bottom"
    OUTER = "outer"
    DRESS = "dress"
    UNKNOWN = "unknown"


class CameraIntrinsics(BaseModel):
    """핀홀 내부 파라미터. 픽셀 단위."""

    model_config = ConfigDict(extra="forbid")

    fx: float
    fy: float
    cx: float
    cy: float
    width: int
    height: int

    @field_validator("fx", "fy")
    @classmethod
    def _positive_focal(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("초점거리는 양수여야 합니다")
        return value


class CameraExtrinsics(BaseModel):
    """외부 파라미터를 (회전 쿼터니언, 이동, 스케일) 로 표현한다.

    SAM 3D 의 레이아웃 표현과 같은 분해다 — `inference_utils.py::update_layout` 이
    `(translation, scale, quaternion)` 으로 주고받는다. 회전행렬 대신 쿼터니언을 쓰는 이유도
    그쪽에 맞추기 위한 것이다(`matrix_to_quaternion` 왕복을 줄인다).

    쿼터니언 순서는 `pytorch3d` 관례인 **(w, x, y, z)** 다.
    """

    model_config = ConfigDict(extra="forbid")

    rotation_quat: Quaternion = Field(default_factory=lambda: [1.0, 0.0, 0.0, 0.0])
    translation: Vec3 = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: float = 1.0

    @field_validator("rotation_quat")
    @classmethod
    def _nonzero_quat(cls, value: list[float]) -> list[float]:
        if all(abs(v) < 1e-12 for v in value):
            raise ValueError("쿼터니언이 영벡터입니다")
        return value


class Camera(BaseModel):
    """카메라. **둘 다 optional 이다** — 실데이터에 없을 가능성이 높다.

    `extrinsics` 가 없으면 레이아웃(R, t, s) 감독을 못 한다. 그 판단은
    `SupervisionAvailability.layout` 이 담당한다.
    """

    model_config = ConfigDict(extra="forbid")

    intrinsics: CameraIntrinsics | None = None
    extrinsics: CameraExtrinsics | None = None


class GarmentSample(BaseModel):
    """의류 단독 재구성 학습 샘플 한 건.

    경로는 전부 **상대경로 허용**이다. 실제 해석은 `GarmentSampleIndex.root` 기준으로
    `resolve_paths()` 가 한다 — 데이터셋을 옮겨도 인덱스 파일을 안 고치게.
    """

    model_config = ConfigDict(extra="forbid")

    sample_id: str
    image_path: Path
    garment_mask_path: Path
    mesh_path: Path | None = None
    camera: Camera | None = None
    texture_path: Path | None = None
    category: GarmentCategory = GarmentCategory.UNKNOWN
    # 라이선스·출처·원본 ID 등. 학습에 쓰지 않지만 데이터 확보 단계에서 필요해진다.
    meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("sample_id")
    @classmethod
    def _nonempty_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("sample_id 가 비었습니다")
        return value

    def resolve_paths(self, root: Path) -> GarmentSample:
        """상대경로를 `root` 기준 절대경로로 바꾼 복사본을 돌려준다."""

        def _abs(path: Path | None) -> Path | None:
            if path is None:
                return None
            return path if path.is_absolute() else (root / path)

        return self.model_copy(
            update={
                "image_path": _abs(self.image_path),
                "garment_mask_path": _abs(self.garment_mask_path),
                "mesh_path": _abs(self.mesh_path),
                "texture_path": _abs(self.texture_path),
            }
        )


class SupervisionAvailability(BaseModel):
    """이 샘플로 실제 감독 가능한 신호. `audit_sample()` 이 계산한다.

    데이터 확보 단계의 판별 체크리스트를 코드로 옮긴 것이다 — "메시만 있고 매칭 실사가 없다"
    같은 경우를 학습 시작 전에 걸러낸다.
    """

    model_config = ConfigDict(extra="forbid")

    #: (이미지, 메시) 쌍이 성립하는가 → visually-grounded SFT 의 전제
    paired_image_mesh: bool
    #: 기하(stage 1) 타깃을 만들 수 있는가
    geometry: bool
    #: 레이아웃(R, t, s) 타깃을 만들 수 있는가 → extrinsic 필요
    layout: bool
    #: 텍스처(stage 2 / SLat) 타깃을 만들 수 있는가
    texture: bool
    #: 사람이 읽을 사유. 왜 False 인지 남긴다.
    notes: list[str] = Field(default_factory=list)

    @property
    def trainable(self) -> bool:
        """최소한 기하 감독이라도 되는가."""
        return self.geometry


def audit_sample(
    sample: GarmentSample, *, slat_encoder_available: bool = False
) -> SupervisionAvailability:
    """샘플 하나가 어떤 감독을 지원하는지 판정한다.

    파일 존재 여부는 보지 않는다 — 이 함수는 데이터 비의존이고, 실재 확인은
    `garment3d.data.verify_index()` 가 별도로 한다.

    Args:
        sample: 판정 대상.
        slat_encoder_available: SLat 인코더(가중치+특징 생성기)가 실제로 연결됐는지.
            기본 False 인 이유는 `REPORT.md` §5 — 릴리스에 없다.
    """
    notes: list[str] = []

    paired = sample.mesh_path is not None
    if not paired:
        notes.append(
            "mesh_path 가 없습니다 — 실사-메시 페어링이 없으면 SFT 가 아니라 합성 렌더 학습입니다"
        )

    geometry = paired
    layout = paired and sample.camera is not None and sample.camera.extrinsics is not None
    if paired and not layout:
        notes.append("카메라 extrinsic 이 없어 layout(R, t, s) 은 감독할 수 없습니다")

    texture = paired and slat_encoder_available
    if paired and not slat_encoder_available:
        notes.append(
            "SLat 인코더가 연결되지 않아 texture(stage 2) 는 감독할 수 없습니다 (REPORT.md §5)"
        )

    return SupervisionAvailability(
        paired_image_mesh=paired,
        geometry=geometry,
        layout=layout,
        texture=texture,
        notes=notes,
    )


class GarmentSampleIndex(BaseModel):
    """샘플 목록 + 경로 기준점. jsonl 로 저장한다.

    **데이터 주입 지점이다.** 실데이터가 들어오면 이 인덱스를 만드는 어댑터만 새로 쓰면 되고,
    전처리·학습·평가는 손대지 않는다.
    """

    model_config = ConfigDict(extra="forbid")

    root: Path
    samples: list[GarmentSample] = Field(default_factory=list)

    def resolved(self) -> list[GarmentSample]:
        return [s.resolve_paths(self.root) for s in self.samples]

    def to_jsonl(self, path: Path) -> Path:
        """샘플을 한 줄 하나씩 쓴다. `root` 는 저장하지 않는다(읽는 쪽이 정한다)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [s.model_dump_json() for s in self.samples]
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        return path

    @classmethod
    def from_jsonl(cls, path: Path, root: Path | None = None) -> GarmentSampleIndex:
        path = Path(path)
        samples = [
            GarmentSample.model_validate_json(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return cls(root=Path(root) if root is not None else path.parent, samples=samples)


class PreferencePair(BaseModel):
    """DPO 선호쌍. best-of-N 후보 중 승자/패자 한 쌍.

    후보 자체(mesh/latent)는 무거워서 스키마에 담지 않고 **경로와 점수만** 담는다.
    """

    model_config = ConfigDict(extra="forbid")

    sample_id: str
    chosen_path: Path
    rejected_path: Path
    chosen_score: float
    rejected_score: float
    #: 어떤 스코어러가 매겼는지. 스코어러를 바꿨을 때 과거 쌍과 섞이는 걸 막는다.
    scorer: str = "unknown"

    @field_validator("rejected_score")
    @classmethod
    def _finite(cls, value: float) -> float:
        if value != value:  # NaN
            raise ValueError("점수가 NaN 입니다")
        return value

    @property
    def margin(self) -> float:
        return self.chosen_score - self.rejected_score
