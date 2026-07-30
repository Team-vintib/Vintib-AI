"""전처리 오케스트레이션 — 샘플 하나를 학습 타깃까지 끌고 간다.

`sample → mesh 로드 → 위생검사(→ 필요시 수선) → 64³ occupancy → latent → 캐시`

**데이터 의존 로직은 여기 한 곳뿐이다**(파일을 읽고 캐시에 쓴다). 위생검사·복셀화·인코딩은
전부 순수 함수라 각각 단위테스트가 된다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..config import Config
from ..contracts import GarmentSample, SupervisionAvailability, audit_sample
from ..data import load_mesh
from .latent import Latent, LatentEncoder, build_latent_encoder
from .mesh_utils import MeshHealth, RepairUnavailableError, check_mesh, repair_watertight
from .voxelize import OccupancyGrid, VoxelizeError, voxelize


@dataclass
class PreprocessResult:
    """샘플 한 건의 전처리 결과. 실패도 결과다 — 예외로 파이프라인을 끊지 않는다."""

    sample_id: str
    ok: bool
    availability: SupervisionAvailability | None = None
    health: MeshHealth | None = None
    occupancy: OccupancyGrid | None = None
    latent: Latent | None = None
    occupancy_path: Path | None = None
    latent_path: Path | None = None
    #: 실패·스킵 사유. 사람이 읽고 데이터 쪽을 고치는 근거가 된다.
    reasons: list[str] = field(default_factory=list)


def preprocess_sample(
    sample: GarmentSample,
    config: Config,
    *,
    encoder: LatentEncoder | None = None,
    write_cache: bool = True,
) -> PreprocessResult:
    """샘플 하나를 전처리한다.

    Args:
        sample: **경로가 이미 해석된**(`resolve_paths`) 샘플.
        encoder: 주입하면 그걸 쓴다. None 이면 config 의 백엔드로 만든다
            (`sam3d_ss` 는 모듈 주입이 필요해 None 으로는 만들 수 없다).
        write_cache: False 면 디스크에 쓰지 않는다(테스트에서 유용).
    """
    slat_available = config.preprocess.latent_encoder == "sam3d_slat"
    availability = audit_sample(sample, slat_encoder_available=slat_available)
    result = PreprocessResult(sample_id=sample.sample_id, ok=False, availability=availability)
    # 성공한 샘플에도 감독 제약을 남긴다 — "texture 감독 불가" 같은 사실이 조용히 사라지면
    # 반쪽 학습을 하고 있다는 걸 아무도 모른다.
    result.reasons.extend(availability.notes)

    if not availability.geometry:
        result.reasons.append("기하 감독이 불가능해 전처리를 건너뜁니다")
        return result

    assert sample.mesh_path is not None  # availability.geometry 가 보장한다
    mesh = load_mesh(sample.mesh_path)
    health = check_mesh(mesh)
    result.health = health

    if not health.is_watertight and config.preprocess.repair_non_watertight:
        try:
            mesh, health = repair_watertight(mesh)
            result.health = health
            result.reasons.append(f"수선 시도 결과: {health.summary()}")
        except RepairUnavailableError as exc:
            # 수선 라이브러리가 없어도 표면 복셀화 자체는 되므로 계속 간다. 다만 기록은 남긴다.
            result.reasons.append(f"수선 불가(계속 진행): {exc}")

    if config.preprocess.target_faces is not None:
        from .mesh_utils import remesh

        try:
            mesh = remesh(mesh, config.preprocess.target_faces)
        except RepairUnavailableError as exc:
            result.reasons.append(f"리메시 불가(원본 유지): {exc}")

    try:
        occupancy = voxelize(
            mesh,
            backend=config.preprocess.voxelizer,
            resolution=config.preprocess.resolution,
            min_active_voxels=config.preprocess.min_active_voxels,
        )
    except VoxelizeError as exc:
        result.reasons.append(f"복셀화 실패: {exc}")
        return result
    result.occupancy = occupancy

    encoder = encoder or build_latent_encoder(config.preprocess.latent_encoder)
    result.latent = encoder.encode(occupancy)

    if write_cache:
        cache_dir = config.paths.expanded().cache_dir
        result.occupancy_path = occupancy.save(cache_dir / "occupancy" / f"{sample.sample_id}.npz")
        result.latent_path = result.latent.save(cache_dir / "latent" / f"{sample.sample_id}.npz")

    result.ok = True
    return result


def preprocess_index(
    samples: list[GarmentSample],
    config: Config,
    *,
    encoder: LatentEncoder | None = None,
    write_cache: bool = True,
) -> list[PreprocessResult]:
    """여러 샘플. 실패한 샘플은 결과에 남기고 계속 진행한다."""
    encoder = encoder or build_latent_encoder(config.preprocess.latent_encoder)
    return [
        preprocess_sample(sample, config, encoder=encoder, write_cache=write_cache)
        for sample in samples
    ]


def summarize(results: list[PreprocessResult]) -> dict[str, int]:
    """전처리 배치 요약. 데이터 확보 단계에서 "몇 %가 쓸 수 있는가"를 보는 숫자."""
    return {
        "total": len(results),
        "ok": sum(1 for r in results if r.ok),
        "failed": sum(1 for r in results if not r.ok),
        "watertight": sum(1 for r in results if r.health is not None and r.health.is_watertight),
        "layout_supervisable": sum(
            1 for r in results if r.availability is not None and r.availability.layout
        ),
        "texture_supervisable": sum(
            1 for r in results if r.availability is not None and r.availability.texture
        ),
    }
