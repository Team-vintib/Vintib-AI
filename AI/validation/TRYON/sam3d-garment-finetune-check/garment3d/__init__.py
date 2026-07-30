"""SAM 3D 의류 단독 파인튜닝 파이프라인 + turntable vs I2V 비교 하네스.

**스파이크/스캐폴드 코드입니다. 프로덕션 코드가 아닙니다.**

데이터가 아직 없는 단계라, 데이터가 들어올 자리를 컨트랙트(`contracts.py`)와 config
(`config.py`)로 못박고 더미 픽스처로 끝까지 도는 코드만 갖춘다. 실데이터가 들어오면
`configs/*.yaml` 의 백엔드 이름과 `paths.sample_index` 만 바꿔 연결한다.

upstream 조사 결과(무엇이 공개돼 있고 무엇이 stub 인지)는 `REPORT.md` 참고.
"""

from .config import Config
from .contracts import (
    Camera,
    CameraExtrinsics,
    CameraIntrinsics,
    GarmentCategory,
    GarmentSample,
    GarmentSampleIndex,
    PreferencePair,
    SupervisionAvailability,
    audit_sample,
)

__all__ = [
    "Camera",
    "CameraExtrinsics",
    "CameraIntrinsics",
    "Config",
    "GarmentCategory",
    "GarmentSample",
    "GarmentSampleIndex",
    "PreferencePair",
    "SupervisionAvailability",
    "audit_sample",
]
