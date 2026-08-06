"""합성 프레임 시퀀스 생성기 — 더미 렌더러와 더미 I2V 어댑터가 공유한다.

**왜 필요한가**: 평가 지표(실루엣 IoU 변동·스케일 드리프트·텍스처 안정성)가 실제로 반응하는지
확인하려면 **결함을 의도적으로 주입한 시퀀스**가 있어야 한다. 결함 없는 시퀀스만으로는
"지표가 항상 0을 반환해도 테스트가 통과"한다.

주입 가능한 결함:

| 인자 | 재현하는 실패 모드 |
| --- | --- |
| `scale_drift` | 체형 스케일 드리프트 — 프레임이 갈수록 피사체가 커진다 |
| `flicker` | 텍스처 플리커 — 프레임마다 밝기·노이즈가 튄다 |
| `jitter` | 카메라/피사체 위치 흔들림 |
| `reverse` | 회전 방향 오류 |
| `identity_shift` | 얼굴/상단 영역이 프레임마다 달라진다 |
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SyntheticDefects:
    """주입할 결함의 세기. 전부 0 이면 "이상적인" 턴테이블이 나온다."""

    #: 마지막 프레임에서 실루엣이 몇 배가 되는지 (0.0 = 드리프트 없음)
    scale_drift: float = 0.0
    #: 프레임별 밝기/노이즈 진폭 (0~1)
    flicker: float = 0.0
    #: 프레임별 중심 이동 픽셀 진폭
    jitter: float = 0.0
    #: 회전 방향 반전
    reverse: bool = False
    #: 상단(얼굴) 영역 패턴이 프레임마다 달라지는 정도 (0~1)
    identity_shift: float = 0.0


def synth_turntable(
    num_frames: int = 24,
    resolution: int = 128,
    *,
    yaw_start_deg: float = 0.0,
    defects: SyntheticDefects | None = None,
    seed: int = 0,
) -> np.ndarray:
    """(T, H, W, 3) uint8 턴테이블 프레임.

    피사체는 "얇고 평평한 의류"를 모사한다 — 정면에서 가장 넓고 측면(90°)에서 가장 좁아진다.
    폭이 `|cos(yaw)|` 로 변하는 것이 그 모델이다. 세로 크기는 회전과 무관하므로,
    **세로 크기가 프레임마다 흔들리면 그건 드리프트다** — 스케일 지표가 잡아야 하는 신호다.
    """
    defects = defects or SyntheticDefects()
    rng = np.random.default_rng(seed)
    height = width = resolution
    frames = np.zeros((num_frames, height, width, 3), dtype=np.uint8)

    direction = -1.0 if defects.reverse else 1.0
    base_half_w = resolution * 0.22
    base_half_h = resolution * 0.30
    thickness = resolution * 0.05

    yy, xx = np.mgrid[0:height, 0:width]

    for t in range(num_frames):
        yaw = np.deg2rad(yaw_start_deg + direction * 360.0 * t / num_frames)
        drift = 1.0 + defects.scale_drift * (t / max(1, num_frames - 1))

        half_w = (abs(np.cos(yaw)) * base_half_w + thickness) * drift
        half_h = base_half_h * drift

        cx = width / 2 + defects.jitter * rng.standard_normal()
        cy = height / 2 + defects.jitter * rng.standard_normal()

        inside = (np.abs(xx - cx) <= half_w) & (np.abs(yy - cy) <= half_h)

        canvas = np.full((height, width, 3), 8, dtype=np.float64)  # 어두운 배경
        # 의류 본체: 회전에 따라 음영이 변한다(정면이 밝고 측면이 어둡다).
        shade = 90 + 70 * abs(np.cos(yaw))
        canvas[inside] = [shade, shade * 0.75, shade * 0.6]

        # 비대칭 마커("가슴 로고"). 정면(cos>0)에서만 보이고 x 위치가 sin(yaw) 에 따라 움직인다.
        # **이게 없으면 프레임이 yaw ↔ -yaw 에 완전히 대칭이 되어 회전 방향을 구분할 수 없다** —
        # 방향 오류(direction_flip_ratio)를 검출하려면 비대칭 단서가 반드시 있어야 한다.
        # 좌우 대칭 검사(rotation_symmetry_error)는 여전히 성립한다: yaw=-θ 프레임을 좌우
        # 반전하면 로고가 +sinθ 위치로 돌아오기 때문이다.
        if np.cos(yaw) > 0:
            logo_x = cx + np.sin(yaw) * half_w * 0.55
            logo_y = cy + half_h * 0.15
            logo_r = max(2.0, resolution * 0.045)
            logo = (np.abs(xx - logo_x) <= logo_r) & (np.abs(yy - logo_y) <= logo_r) & inside
            canvas[logo] = [235.0, 233.0, 222.0]

        # 상단 영역 = "얼굴" 대용. identity 지표가 여길 본다.
        #
        # 패턴을 **굵은 블록**으로 만든다. 픽셀 단위 iid 잡음으로 채우면 어떤 임베딩이든
        # 풀링 단계에서 평균이 같아져(대수의 법칙) identity 변화가 지표에 안 나타난다 —
        # 실제 얼굴은 풀링이 보존하는 스케일의 구조를 갖는다. 그걸 흉내내는 것이다.
        face_h = int(base_half_h * 0.5)
        face_top = max(0, int(cy - half_h) - face_h)
        face_bottom = max(face_top + 1, int(cy - half_h))
        face_left = int(cx - half_w * 0.4)
        face_right = max(face_left + 1, int(cx + half_w * 0.4))
        patch_h, patch_w = face_bottom - face_top, face_right - face_left
        face_seed = t if defects.identity_shift > 0 else 0
        face_rng = np.random.default_rng(1000 + int(face_seed * defects.identity_shift * 100))
        blocks = face_rng.uniform(60, 240, size=(3, 3, 3))
        patch = np.repeat(
            np.repeat(blocks, int(np.ceil(patch_h / 3)), axis=0),
            int(np.ceil(patch_w / 3)),
            axis=1,
        )[:patch_h, :patch_w]
        canvas[face_top:face_bottom, face_left:face_right] = patch

        if defects.flicker > 0:
            gain = 1.0 + defects.flicker * rng.standard_normal()
            canvas = canvas * gain
            canvas += defects.flicker * 40 * rng.standard_normal(canvas.shape)

        frames[t] = np.clip(canvas, 0, 255).astype(np.uint8)

    return frames


def synth_i2v(
    first_frame: np.ndarray,
    num_frames: int = 24,
    *,
    defects: SyntheticDefects | None = None,
    seed: int = 0,
) -> np.ndarray:
    """I2V 어댑터의 더미 출력 — **첫 프레임만 입력과 같고 뒤로 갈수록 흐트러진다.**

    실제 I2V 의 전형적 실패(첫 프레임 충실, 뒤로 갈수록 형태·정체성 붕괴)를 흉내내서,
    turntable 과 I2V 를 같은 지표로 비교했을 때 **차이가 나는 방향**이 맞는지 확인한다.
    """
    defects = defects or SyntheticDefects(scale_drift=0.25, flicker=0.15, identity_shift=0.8)
    height, width = first_frame.shape[:2]
    frames = synth_turntable(num_frames, resolution=max(height, width), defects=defects, seed=seed)[
        :, :height, :width
    ]
    frames = frames.copy()
    frames[0] = first_frame
    return frames


def frames_to_masks(frames: np.ndarray, threshold: int = 12) -> np.ndarray:
    """(T, H, W, 3) → (T, H, W) bool. 밝기 임계치로 전경을 뽑는다.

    렌더 배경이 어둡다는 가정이다. **I2V 출력은 배경이 밝을 수 있어** 임계치를 케이스별로
    맞춰야 한다 — `EvalConfig.background_threshold` 가 그 자리다. 임계치가 틀리면 실루엣
    지표 전체가 무의미해지므로, `harness` 가 전경 비율을 함께 리포트한다.
    """
    if frames.ndim != 4:
        raise ValueError(f"frames 형태가 (T, H, W, 3) 이 아닙니다: {frames.shape}")
    luma = frames.astype(np.float64).mean(axis=-1)
    return luma > threshold
