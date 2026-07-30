import os
from PIL import Image
from typing import Union
import numpy as np
import cv2
from diffusers.image_processor import VaeImageProcessor
import torch

from model.SCHP import SCHP  # type: ignore
from model.DensePose import DensePose  # type: ignore
from model.adaptive_fit import compute_mask_adjustment

DENSE_INDEX_MAP = {
    "background": [0],
    "torso": [1, 2],
    "right hand": [3],
    "left hand": [4],
    "right foot": [5],
    "left foot": [6],
    "right thigh": [7, 9],
    "left thigh": [8, 10],
    "right leg": [11, 13],
    "left leg": [12, 14],
    "left big arm": [15, 17],
    "right big arm": [16, 18],
    "left forearm": [19, 21],
    "right forearm": [20, 22],
    "face": [23, 24],
    "thighs": [7, 8, 9, 10],
    "legs": [11, 12, 13, 14],
    "hands": [3, 4],
    "feet": [5, 6],
    "big arms": [15, 16, 17, 18],
    "forearms": [19, 20, 21, 22],
}

ATR_MAPPING = {
    'Background': 0, 'Hat': 1, 'Hair': 2, 'Sunglasses': 3, 
    'Upper-clothes': 4, 'Skirt': 5, 'Pants': 6, 'Dress': 7,
    'Belt': 8, 'Left-shoe': 9, 'Right-shoe': 10, 'Face': 11, 
    'Left-leg': 12, 'Right-leg': 13, 'Left-arm': 14, 'Right-arm': 15,
    'Bag': 16, 'Scarf': 17
}

LIP_MAPPING = {
    'Background': 0, 'Hat': 1, 'Hair': 2, 'Glove': 3, 
    'Sunglasses': 4, 'Upper-clothes': 5, 'Dress': 6, 'Coat': 7,
    'Socks': 8, 'Pants': 9, 'Jumpsuits': 10, 'Scarf': 11, 
    'Skirt': 12, 'Face': 13, 'Left-arm': 14, 'Right-arm': 15,
    'Left-leg': 16, 'Right-leg': 17, 'Left-shoe': 18, 'Right-shoe': 19
}

PROTECT_BODY_PARTS = {
    'upper': ['Left-leg', 'Right-leg'],
    'lower': ['Right-arm', 'Left-arm', 'Face'],
    'overall': [],
    'inner': ['Left-leg', 'Right-leg'],
    'outer': ['Left-leg', 'Right-leg'],
}
PROTECT_CLOTH_PARTS = {
    'upper': {
        'ATR': ['Skirt', 'Pants'],
        'LIP': ['Skirt', 'Pants']
    },
    'lower': {
        'ATR': ['Upper-clothes'],
        'LIP': ['Upper-clothes', 'Coat']
    },
    'overall': {
        'ATR': [],
        'LIP': []
    },
    'inner': {
        'ATR': ['Dress', 'Coat', 'Skirt', 'Pants'],
        'LIP': ['Dress', 'Coat', 'Skirt', 'Pants', 'Jumpsuits']
    },
    'outer': {
        'ATR': ['Dress', 'Pants', 'Skirt'],
        'LIP': ['Upper-clothes', 'Dress', 'Pants', 'Skirt', 'Jumpsuits']
    }
}
MASK_CLOTH_PARTS = {
    'upper': ['Upper-clothes', 'Coat', 'Dress', 'Jumpsuits'],
    'lower': ['Pants', 'Skirt', 'Dress', 'Jumpsuits'],
    'overall': ['Upper-clothes', 'Dress', 'Pants', 'Skirt', 'Coat', 'Jumpsuits'],
    'inner': ['Upper-clothes'],
    'outer': ['Coat',]
}
MASK_DENSE_PARTS = {
    'upper': ['torso', 'big arms', 'forearms'],
    'lower': ['thighs', 'legs'],
    'overall': ['torso', 'thighs', 'legs', 'big arms', 'forearms'],
    'inner': ['torso'],
    'outer': ['torso', 'big arms', 'forearms']
}
    
schp_public_protect_parts = ['Hat', 'Hair', 'Sunglasses', 'Left-shoe', 'Right-shoe', 'Bag', 'Glove', 'Scarf']
schp_protect_parts = {
    'upper': ['Left-leg', 'Right-leg', 'Skirt', 'Pants', 'Jumpsuits'],  
    'lower': ['Left-arm', 'Right-arm', 'Upper-clothes', 'Coat'],
    'overall': [],
    'inner': ['Left-leg', 'Right-leg', 'Skirt', 'Pants', 'Jumpsuits', 'Coat'],
    'outer': ['Left-leg', 'Right-leg', 'Skirt', 'Pants', 'Jumpsuits', 'Upper-clothes']
}
schp_mask_parts = {
    'upper': ['Upper-clothes', 'Dress', 'Coat', 'Jumpsuits'],
    'lower': ['Pants', 'Skirt', 'Dress', 'Jumpsuits', 'socks'],
    'overall': ['Upper-clothes', 'Dress', 'Pants', 'Skirt', 'Coat', 'Jumpsuits', 'socks'],
    'inner': ['Upper-clothes'],
    'outer': ['Coat',]
}

dense_mask_parts = {
    'upper': ['torso', 'big arms', 'forearms'],
    'lower': ['thighs', 'legs'],
    'overall': ['torso', 'thighs', 'legs', 'big arms', 'forearms'],
    'inner': ['torso'],
    'outer': ['torso', 'big arms', 'forearms']
}

def vis_mask(image, mask):
    image = np.array(image).astype(np.uint8)
    mask = np.array(mask).astype(np.uint8)
    mask[mask > 127] = 255
    mask[mask <= 127] = 0
    mask = np.expand_dims(mask, axis=-1)
    mask = np.repeat(mask, 3, axis=-1)
    mask = mask / 255
    return Image.fromarray((image * (1 - mask)).astype(np.uint8))

def part_mask_of(part: Union[str, list],
                 parse: np.ndarray, mapping: dict):
    if isinstance(part, str):
        part = [part]
    mask = np.zeros_like(parse)
    for _ in part:
        if _ not in mapping:
            continue
        if isinstance(mapping[_], list):
            for i in mapping[_]:
                mask += (parse == i)
        else:
            mask += (parse == mapping[_])
    return mask

def hull_mask(mask_area: np.ndarray):
    ret, binary = cv2.threshold(mask_area, 127, 255, cv2.THRESH_BINARY)
    contours, hierarchy = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hull_mask = np.zeros_like(mask_area)
    for c in contours:
        hull = cv2.convexHull(c)
        hull_mask = cv2.fillPoly(np.zeros_like(mask_area), [hull], 255) | hull_mask
    return hull_mask


# =========================================================
# [신규] 핏(fit) 유형에 따른 마스크 조정 로직
#    strong_protect_area(얼굴/손/발) 계산 이후, 최종 마스크에만 적용된다.
#    즉 얼굴/손/발은 이 로직과 무관하게 항상 보존됨.
# =========================================================

def adjust_mask_for_fit(
    mask_area: np.ndarray,
    densepose_mask: np.ndarray,
    fit_type: str = "regular",
) -> np.ndarray:
    """
    fit_type에 따라 최종 마스크 영역을 확장/축소한다.
    - regular: 원본 마스크 그대로 (기존 CatVTON 동작과 동일)
    - oversized: 팔(forearm) 영역까지 마스크 포함 + 추가 팽창 (여유 볼륨 표현)
    - cropped: torso 하단부를 마스크에서 제외 (기장을 짧게)

    주의: 이 함수의 배율/비율 값들은 초기 실험용 근사치이며,
    실제 결과를 보면서 튜닝이 필요하다.
    """
    if fit_type == "regular":
        return mask_area

    mask_area = mask_area.astype(np.uint8)

    if fit_type == "oversized":
        forearm_area = part_mask_of(['forearms'], densepose_mask, DENSE_INDEX_MAP).astype(np.uint8)
        mask_area = mask_area | forearm_area
        kernel = np.ones((15, 15), np.uint8)
        mask_area = cv2.dilate(mask_area, kernel, iterations=2)

    elif fit_type == "cropped":
        torso_area = part_mask_of(['torso'], densepose_mask, DENSE_INDEX_MAP)
        torso_rows = np.where(torso_area.any(axis=1))[0]
        if len(torso_rows) > 0:
            torso_top, torso_bottom = torso_rows.min(), torso_rows.max()
            # torso 상단부터 70% 지점까지만 남기고 그 아래는 마스크에서 제외
            cutoff = torso_top + int((torso_bottom - torso_top) * 0.7)
            mask_area = mask_area.copy()
            mask_area[cutoff:, :] = 0

    else:
        raise ValueError(f"Unknown fit_type: {fit_type} (expected 'regular', 'oversized', or 'cropped')")

    return mask_area


# =========================================================
# [신규] 체형-의류 스펙 차이 기반 적응형 마스킹
#    body_measurements/garment_measurements가 둘 다 있을 때만 fit_type 고정 3단계를
#    대체한다 — 하나라도 없으면 위 adjust_mask_for_fit()로 그대로 폴백한다.
#    "어느 측정값 쌍을 쓸지" 고르는 로직(compute_mask_adjustment)은 cv2가 필요 없어서
#    adaptive_fit.py에 있다(CI에서 바로 테스트됨). 여기는 계산된 값을 실제 마스크 배열에
#    적용하는 부분(distance transform 등, cv2 필요)만 담당한다.
# =========================================================


_LENGTH_REFERENCE_DENSE_PARTS = {"upper": ["torso"], "lower": ["thighs", "legs"]}


def apply_adaptive_adjustment(
    mask_area: np.ndarray,
    densepose_mask: np.ndarray,
    dilation_px: float,
    cutoff_ratio: float,
    part: str = "upper",
) -> np.ndarray:
    """`compute_mask_adjustment()`가 계산한 연속값을 실제 마스크 배열에 적용한다.

    `adjust_mask_for_fit()`의 고정 커널 dilate(오버사이즈)·70% 고정 컷오프(크롭)를 대체하는
    연속 버전 — 고정 커널 반복 대신 distance transform을 재threshold해서 팽창/수축 폭을
    픽셀 단위로 정밀하게 조절한다.

    **길이 컷오프 기준 신체 부위는 `part`에 따라 다르다.** `adjust_mask_for_fit`의 원래
    `cropped` 로직은 항상 torso 행 범위를 썼는데(상의 전용으로만 쓰였으니 문제 없었다),
    바지(`part='lower'`)에 그대로 재사용하면 torso 행 범위(대개 다리 마스크보다 훨씬 위쪽)를
    기준으로 컷오프를 계산해버려서 다리 마스크 전체가 거의 다 잘려나간다 — 실사진으로 검증
    중 발견한 버그. `part='lower'`면 다리(thighs/legs) 행 범위를 기준으로 삼는다.
    """
    mask_area = mask_area.astype(np.uint8)

    if dilation_px != 0.0:
        mask_area = _resize_by_distance_transform(mask_area, dilation_px)

    if cutoff_ratio < 1.0:
        reference_parts = _LENGTH_REFERENCE_DENSE_PARTS.get(part, ["torso"])
        reference_area = part_mask_of(reference_parts, densepose_mask, DENSE_INDEX_MAP)
        reference_rows = np.where(reference_area.any(axis=1))[0]
        if len(reference_rows) > 0:
            top, bottom = reference_rows.min(), reference_rows.max()
            cutoff = top + int((bottom - top) * cutoff_ratio)
            mask_area = mask_area.copy()
            mask_area[cutoff:, :] = 0

    return mask_area


def _resize_by_distance_transform(mask_area: np.ndarray, dilation_px: float) -> np.ndarray:
    """`dilation_px`만큼 마스크를 연속적으로 팽창(양수)하거나 수축(음수)한다."""
    if dilation_px > 0:
        # 배경 픽셀마다 "마스크까지 거리"를 구해서, 그 거리가 dilation_px 이내인 픽셀까지
        # 새로 포함시킨다 — 고정 커널 dilate보다 부드럽고 연속적으로 조절 가능하다.
        outside_distance = cv2.distanceTransform((1 - mask_area).astype(np.uint8), cv2.DIST_L2, 5)
        return (outside_distance <= dilation_px).astype(np.uint8)

    # 마스크 픽셀마다 "경계까지 거리"를 구해서, |dilation_px|보다 안쪽(먼) 픽셀만 남긴다.
    inside_distance = cv2.distanceTransform(mask_area, cv2.DIST_L2, 5)
    return (inside_distance > abs(dilation_px)).astype(np.uint8)


class AutoMasker:
    def __init__(
        self, 
        densepose_ckpt='./Models/DensePose', 
        schp_ckpt='./Models/SCHP', 
        device='cuda'):
        np.random.seed(0)
        torch.manual_seed(0)
        torch.cuda.manual_seed(0)
        
        self.densepose_processor = DensePose(densepose_ckpt, device)
        self.schp_processor_atr = SCHP(ckpt_path=os.path.join(schp_ckpt, 'exp-schp-201908301523-atr.pth'), device=device)
        self.schp_processor_lip = SCHP(ckpt_path=os.path.join(schp_ckpt, 'exp-schp-201908261155-lip.pth'), device=device)
        
        self.mask_processor = VaeImageProcessor(vae_scale_factor=8, do_normalize=False, do_binarize=True, do_convert_grayscale=True)

    def process_densepose(self, image_or_path):
        return self.densepose_processor(image_or_path, resize=1024)

    def process_schp_lip(self, image_or_path):
        return self.schp_processor_lip(image_or_path)

    def process_schp_atr(self, image_or_path):
        return self.schp_processor_atr(image_or_path)
        
    def preprocess_image(self, image_or_path):
        return {
            'densepose': self.densepose_processor(image_or_path, resize=1024),
            'schp_atr': self.schp_processor_atr(image_or_path),
            'schp_lip': self.schp_processor_lip(image_or_path)
        }
    
    @staticmethod
    def cloth_agnostic_mask(
        densepose_mask: Image.Image,
        schp_lip_mask: Image.Image,
        schp_atr_mask: Image.Image,
        part: str='overall',
        fit_type: str='regular',
        body_measurements: dict | None = None,
        garment_measurements: dict | None = None,
        **kwargs
    ):
        assert part in ['upper', 'lower', 'overall', 'inner', 'outer'], f"part should be one of ['upper', 'lower', 'overall', 'inner', 'outer'], but got {part}"
        assert fit_type in ['regular', 'oversized', 'cropped'], f"fit_type should be one of ['regular', 'oversized', 'cropped'], but got {fit_type}"
        w, h = densepose_mask.size
        
        dilate_kernel = max(w, h) // 250
        dilate_kernel = dilate_kernel if dilate_kernel % 2 == 1 else dilate_kernel + 1
        dilate_kernel = np.ones((dilate_kernel, dilate_kernel), np.uint8)
        
        kernal_size = max(w, h) // 25
        kernal_size = kernal_size if kernal_size % 2 == 1 else kernal_size + 1
        
        densepose_mask = np.array(densepose_mask)
        schp_lip_mask = np.array(schp_lip_mask)
        schp_atr_mask = np.array(schp_atr_mask)
        
        # Strong Protect Area (Hands, Face, Accessory, Feet)
        hands_protect_area = part_mask_of(['hands', 'feet'], densepose_mask, DENSE_INDEX_MAP)
        hands_protect_area = cv2.dilate(hands_protect_area, dilate_kernel, iterations=1)
        hands_protect_area = hands_protect_area & \
            (part_mask_of(['Left-arm', 'Right-arm', 'Left-leg', 'Right-leg'], schp_atr_mask, ATR_MAPPING) | \
             part_mask_of(['Left-arm', 'Right-arm', 'Left-leg', 'Right-leg'], schp_lip_mask, LIP_MAPPING))
        face_protect_area = part_mask_of('Face', schp_lip_mask, LIP_MAPPING)

        strong_protect_area = hands_protect_area | face_protect_area 

        # Weak Protect Area (Hair, Irrelevant Clothes, Body Parts)
        body_protect_area = part_mask_of(PROTECT_BODY_PARTS[part], schp_lip_mask, LIP_MAPPING) | part_mask_of(PROTECT_BODY_PARTS[part], schp_atr_mask, ATR_MAPPING)
        hair_protect_area = part_mask_of(['Hair'], schp_lip_mask, LIP_MAPPING) | \
            part_mask_of(['Hair'], schp_atr_mask, ATR_MAPPING)
        cloth_protect_area = part_mask_of(PROTECT_CLOTH_PARTS[part]['LIP'], schp_lip_mask, LIP_MAPPING) | \
            part_mask_of(PROTECT_CLOTH_PARTS[part]['ATR'], schp_atr_mask, ATR_MAPPING)
        accessory_protect_area = part_mask_of((accessory_parts := ['Hat', 'Glove', 'Sunglasses', 'Bag', 'Left-shoe', 'Right-shoe', 'Scarf', 'Socks']), schp_lip_mask, LIP_MAPPING) | \
            part_mask_of(accessory_parts, schp_atr_mask, ATR_MAPPING) 
        weak_protect_area = body_protect_area | cloth_protect_area | hair_protect_area | strong_protect_area | accessory_protect_area
        
        # Mask Area
        strong_mask_area = part_mask_of(MASK_CLOTH_PARTS[part], schp_lip_mask, LIP_MAPPING) | \
            part_mask_of(MASK_CLOTH_PARTS[part], schp_atr_mask, ATR_MAPPING)
        background_area = part_mask_of(['Background'], schp_lip_mask, LIP_MAPPING) & part_mask_of(['Background'], schp_atr_mask, ATR_MAPPING)
        mask_dense_area = part_mask_of(MASK_DENSE_PARTS[part], densepose_mask, DENSE_INDEX_MAP)
        
        original_shape = mask_dense_area.shape[:2]  # (height, width)
        mask_dense_area = cv2.resize(mask_dense_area.astype(np.uint8), None, fx=0.25, fy=0.25, interpolation=cv2.INTER_NEAREST)
        mask_dense_area = cv2.dilate(mask_dense_area, dilate_kernel, iterations=2)
        mask_dense_area = cv2.resize(mask_dense_area, (original_shape[1], original_shape[0]), interpolation=cv2.INTER_NEAREST)

        mask_area = (np.ones_like(densepose_mask) & (~weak_protect_area) & (~background_area)) | mask_dense_area

        mask_area = hull_mask(mask_area * 255) // 255  # Convex Hull to expand the mask area
        mask_area = mask_area & (~weak_protect_area)
        mask_area = cv2.GaussianBlur(mask_area * 255, (kernal_size, kernal_size), 0)
        mask_area[mask_area < 25] = 0
        mask_area[mask_area >= 25] = 1
        mask_area = (mask_area | strong_mask_area) & (~strong_protect_area) 
        mask_area = cv2.dilate(mask_area, dilate_kernel, iterations=1)

        # [신규] 체형-의류 스펙 차이 기반 적응형 조정 우선, 측정값이 없으면 fit_type 고정
        # 3단계로 폴백한다(strong_protect_area는 이미 제외된 상태이므로 얼굴/손/발은 이
        # 단계와 무관하게 항상 보존된다)
        adjustment = compute_mask_adjustment(part, body_measurements, garment_measurements)
        if adjustment is not None:
            dilation_px, cutoff_ratio = adjustment
            mask_area = apply_adaptive_adjustment(
                mask_area, densepose_mask, dilation_px, cutoff_ratio, part=part
            )
        else:
            mask_area = adjust_mask_for_fit(mask_area, densepose_mask, fit_type)
        mask_area = mask_area & (~strong_protect_area)  # 안전을 위해 재확인

        return Image.fromarray((mask_area * 255).astype(np.uint8))
        
    def __call__(
        self,
        image: Union[str, Image.Image],
        mask_type: str = "upper",
        fit_type: str = "regular",
        body_measurements: dict | None = None,
        garment_measurements: dict | None = None,
    ):
        assert mask_type in ['upper', 'lower', 'overall', 'inner', 'outer'], f"mask_type should be one of ['upper', 'lower', 'overall', 'inner', 'outer'], but got {mask_type}"
        assert fit_type in ['regular', 'oversized', 'cropped'], f"fit_type should be one of ['regular', 'oversized', 'cropped'], but got {fit_type}"
        preprocess_results = self.preprocess_image(image)
        mask = self.cloth_agnostic_mask(
            preprocess_results['densepose'],
            preprocess_results['schp_lip'],
            preprocess_results['schp_atr'],
            part=mask_type,
            fit_type=fit_type,
            body_measurements=body_measurements,
            garment_measurements=garment_measurements,
        )
        return {
            'mask': mask,
            'densepose': preprocess_results['densepose'],
            'schp_lip': preprocess_results['schp_lip'],
            'schp_atr': preprocess_results['schp_atr']
        }


if __name__ == '__main__':
    pass

# 
# import os
# from PIL import Image
# from typing import Union
# import numpy as np
# import cv2
# from diffusers.image_processor import VaeImageProcessor
# import torch

# from model.SCHP import SCHP  # type: ignore
# from model.DensePose import DensePose  # type: ignore

# DENSE_INDEX_MAP = {
#     "background": [0],
#     "torso": [1, 2],
#     "right hand": [3],
#     "left hand": [4],
#     "right foot": [5],
#     "left foot": [6],
#     "right thigh": [7, 9],
#     "left thigh": [8, 10],
#     "right leg": [11, 13],
#     "left leg": [12, 14],
#     "left big arm": [15, 17],
#     "right big arm": [16, 18],
#     "left forearm": [19, 21],
#     "right forearm": [20, 22],
#     "face": [23, 24],
#     "thighs": [7, 8, 9, 10],
#     "legs": [11, 12, 13, 14],
#     "hands": [3, 4],
#     "feet": [5, 6],
#     "big arms": [15, 16, 17, 18],
#     "forearms": [19, 20, 21, 22],
# }

# ATR_MAPPING = {
#     'Background': 0, 'Hat': 1, 'Hair': 2, 'Sunglasses': 3, 
#     'Upper-clothes': 4, 'Skirt': 5, 'Pants': 6, 'Dress': 7,
#     'Belt': 8, 'Left-shoe': 9, 'Right-shoe': 10, 'Face': 11, 
#     'Left-leg': 12, 'Right-leg': 13, 'Left-arm': 14, 'Right-arm': 15,
#     'Bag': 16, 'Scarf': 17
# }

# LIP_MAPPING = {
#     'Background': 0, 'Hat': 1, 'Hair': 2, 'Glove': 3, 
#     'Sunglasses': 4, 'Upper-clothes': 5, 'Dress': 6, 'Coat': 7,
#     'Socks': 8, 'Pants': 9, 'Jumpsuits': 10, 'Scarf': 11, 
#     'Skirt': 12, 'Face': 13, 'Left-arm': 14, 'Right-arm': 15,
#     'Left-leg': 16, 'Right-leg': 17, 'Left-shoe': 18, 'Right-shoe': 19
# }

# PROTECT_BODY_PARTS = {
#     'upper': ['Left-leg', 'Right-leg'],
#     'lower': ['Right-arm', 'Left-arm', 'Face'],
#     'overall': [],
#     'inner': ['Left-leg', 'Right-leg'],
#     'outer': ['Left-leg', 'Right-leg'],
# }
# PROTECT_CLOTH_PARTS = {
#     'upper': {
#         'ATR': ['Skirt', 'Pants'],
#         'LIP': ['Skirt', 'Pants']
#     },
#     'lower': {
#         'ATR': ['Upper-clothes'],
#         'LIP': ['Upper-clothes', 'Coat']
#     },
#     'overall': {
#         'ATR': [],
#         'LIP': []
#     },
#     'inner': {
#         'ATR': ['Dress', 'Coat', 'Skirt', 'Pants'],
#         'LIP': ['Dress', 'Coat', 'Skirt', 'Pants', 'Jumpsuits']
#     },
#     'outer': {
#         'ATR': ['Dress', 'Pants', 'Skirt'],
#         'LIP': ['Upper-clothes', 'Dress', 'Pants', 'Skirt', 'Jumpsuits']
#     }
# }
# MASK_CLOTH_PARTS = {
#     'upper': ['Upper-clothes', 'Coat', 'Dress', 'Jumpsuits'],
#     'lower': ['Pants', 'Skirt', 'Dress', 'Jumpsuits'],
#     'overall': ['Upper-clothes', 'Dress', 'Pants', 'Skirt', 'Coat', 'Jumpsuits'],
#     'inner': ['Upper-clothes'],
#     'outer': ['Coat',]
# }
# MASK_DENSE_PARTS = {
#     'upper': ['torso', 'big arms', 'forearms'],
#     'lower': ['thighs', 'legs'],
#     'overall': ['torso', 'thighs', 'legs', 'big arms', 'forearms'],
#     'inner': ['torso'],
#     'outer': ['torso', 'big arms', 'forearms']
# }
    
# schp_public_protect_parts = ['Hat', 'Hair', 'Sunglasses', 'Left-shoe', 'Right-shoe', 'Bag', 'Glove', 'Scarf']
# schp_protect_parts = {
#     'upper': ['Left-leg', 'Right-leg', 'Skirt', 'Pants', 'Jumpsuits'],  
#     'lower': ['Left-arm', 'Right-arm', 'Upper-clothes', 'Coat'],
#     'overall': [],
#     'inner': ['Left-leg', 'Right-leg', 'Skirt', 'Pants', 'Jumpsuits', 'Coat'],
#     'outer': ['Left-leg', 'Right-leg', 'Skirt', 'Pants', 'Jumpsuits', 'Upper-clothes']
# }
# schp_mask_parts = {
#     'upper': ['Upper-clothes', 'Dress', 'Coat', 'Jumpsuits'],
#     'lower': ['Pants', 'Skirt', 'Dress', 'Jumpsuits', 'socks'],
#     'overall': ['Upper-clothes', 'Dress', 'Pants', 'Skirt', 'Coat', 'Jumpsuits', 'socks'],
#     'inner': ['Upper-clothes'],
#     'outer': ['Coat',]
# }

# dense_mask_parts = {
#     'upper': ['torso', 'big arms', 'forearms'],
#     'lower': ['thighs', 'legs'],
#     'overall': ['torso', 'thighs', 'legs', 'big arms', 'forearms'],
#     'inner': ['torso'],
#     'outer': ['torso', 'big arms', 'forearms']
# }

# def vis_mask(image, mask):
#     image = np.array(image).astype(np.uint8)
#     mask = np.array(mask).astype(np.uint8)
#     mask[mask > 127] = 255
#     mask[mask <= 127] = 0
#     mask = np.expand_dims(mask, axis=-1)
#     mask = np.repeat(mask, 3, axis=-1)
#     mask = mask / 255
#     return Image.fromarray((image * (1 - mask)).astype(np.uint8))

# def part_mask_of(part: Union[str, list],
#                  parse: np.ndarray, mapping: dict):
#     if isinstance(part, str):
#         part = [part]
#     mask = np.zeros_like(parse)
#     for _ in part:
#         if _ not in mapping:
#             continue
#         if isinstance(mapping[_], list):
#             for i in mapping[_]:
#                 mask += (parse == i)
#         else:
#             mask += (parse == mapping[_])
#     return mask

# def hull_mask(mask_area: np.ndarray):
#     ret, binary = cv2.threshold(mask_area, 127, 255, cv2.THRESH_BINARY)
#     contours, hierarchy = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#     hull_mask = np.zeros_like(mask_area)
#     for c in contours:
#         hull = cv2.convexHull(c)
#         hull_mask = cv2.fillPoly(np.zeros_like(mask_area), [hull], 255) | hull_mask
#     return hull_mask
    

# class AutoMasker:
#     def __init__(
#         self, 
#         densepose_ckpt='./Models/DensePose', 
#         schp_ckpt='./Models/SCHP', 
#         device='cuda'):
#         np.random.seed(0)
#         torch.manual_seed(0)
#         torch.cuda.manual_seed(0)
        
#         self.densepose_processor = DensePose(densepose_ckpt, device)
#         self.schp_processor_atr = SCHP(ckpt_path=os.path.join(schp_ckpt, 'exp-schp-201908301523-atr.pth'), device=device)
#         self.schp_processor_lip = SCHP(ckpt_path=os.path.join(schp_ckpt, 'exp-schp-201908261155-lip.pth'), device=device)
        
#         self.mask_processor = VaeImageProcessor(vae_scale_factor=8, do_normalize=False, do_binarize=True, do_convert_grayscale=True)

#     def process_densepose(self, image_or_path):
#         return self.densepose_processor(image_or_path, resize=1024)

#     def process_schp_lip(self, image_or_path):
#         return self.schp_processor_lip(image_or_path)

#     def process_schp_atr(self, image_or_path):
#         return self.schp_processor_atr(image_or_path)
        
#     def preprocess_image(self, image_or_path):
#         return {
#             'densepose': self.densepose_processor(image_or_path, resize=1024),
#             'schp_atr': self.schp_processor_atr(image_or_path),
#             'schp_lip': self.schp_processor_lip(image_or_path)
#         }
    
#     @staticmethod
#     def cloth_agnostic_mask(
#         densepose_mask: Image.Image,
#         schp_lip_mask: Image.Image,
#         schp_atr_mask: Image.Image,
#         part: str='overall',
#         **kwargs
#     ):
#         assert part in ['upper', 'lower', 'overall', 'inner', 'outer'], f"part should be one of ['upper', 'lower', 'overall', 'inner', 'outer'], but got {part}"
#         w, h = densepose_mask.size
        
#         dilate_kernel = max(w, h) // 250
#         dilate_kernel = dilate_kernel if dilate_kernel % 2 == 1 else dilate_kernel + 1
#         dilate_kernel = np.ones((dilate_kernel, dilate_kernel), np.uint8)
        
#         kernal_size = max(w, h) // 25
#         kernal_size = kernal_size if kernal_size % 2 == 1 else kernal_size + 1
        
#         densepose_mask = np.array(densepose_mask)
#         schp_lip_mask = np.array(schp_lip_mask)
#         schp_atr_mask = np.array(schp_atr_mask)
        
#         # Strong Protect Area (Hands, Face, Accessory, Feet)
#         hands_protect_area = part_mask_of(['hands', 'feet'], densepose_mask, DENSE_INDEX_MAP)
#         hands_protect_area = cv2.dilate(hands_protect_area, dilate_kernel, iterations=1)
#         hands_protect_area = hands_protect_area & \
#             (part_mask_of(['Left-arm', 'Right-arm', 'Left-leg', 'Right-leg'], schp_atr_mask, ATR_MAPPING) | \
#              part_mask_of(['Left-arm', 'Right-arm', 'Left-leg', 'Right-leg'], schp_lip_mask, LIP_MAPPING))
#         face_protect_area = part_mask_of('Face', schp_lip_mask, LIP_MAPPING)

#         strong_protect_area = hands_protect_area | face_protect_area 

#         # Weak Protect Area (Hair, Irrelevant Clothes, Body Parts)
#         body_protect_area = part_mask_of(PROTECT_BODY_PARTS[part], schp_lip_mask, LIP_MAPPING) | part_mask_of(PROTECT_BODY_PARTS[part], schp_atr_mask, ATR_MAPPING)
#         hair_protect_area = part_mask_of(['Hair'], schp_lip_mask, LIP_MAPPING) | \
#             part_mask_of(['Hair'], schp_atr_mask, ATR_MAPPING)
#         cloth_protect_area = part_mask_of(PROTECT_CLOTH_PARTS[part]['LIP'], schp_lip_mask, LIP_MAPPING) | \
#             part_mask_of(PROTECT_CLOTH_PARTS[part]['ATR'], schp_atr_mask, ATR_MAPPING)
#         accessory_protect_area = part_mask_of((accessory_parts := ['Hat', 'Glove', 'Sunglasses', 'Bag', 'Left-shoe', 'Right-shoe', 'Scarf', 'Socks']), schp_lip_mask, LIP_MAPPING) | \
#             part_mask_of(accessory_parts, schp_atr_mask, ATR_MAPPING) 
#         weak_protect_area = body_protect_area | cloth_protect_area | hair_protect_area | strong_protect_area | accessory_protect_area
        
#         # Mask Area
#         strong_mask_area = part_mask_of(MASK_CLOTH_PARTS[part], schp_lip_mask, LIP_MAPPING) | \
#             part_mask_of(MASK_CLOTH_PARTS[part], schp_atr_mask, ATR_MAPPING)
#         background_area = part_mask_of(['Background'], schp_lip_mask, LIP_MAPPING) & part_mask_of(['Background'], schp_atr_mask, ATR_MAPPING)
#         mask_dense_area = part_mask_of(MASK_DENSE_PARTS[part], densepose_mask, DENSE_INDEX_MAP)
        
#         original_shape = mask_dense_area.shape[:2]  # (height, width)
#         mask_dense_area = cv2.resize(mask_dense_area.astype(np.uint8), None, fx=0.25, fy=0.25, interpolation=cv2.INTER_NEAREST)
#         mask_dense_area = cv2.dilate(mask_dense_area, dilate_kernel, iterations=2)
#         mask_dense_area = cv2.resize(mask_dense_area, (original_shape[1], original_shape[0]), interpolation=cv2.INTER_NEAREST)

#         mask_area = (np.ones_like(densepose_mask) & (~weak_protect_area) & (~background_area)) | mask_dense_area

#         mask_area = hull_mask(mask_area * 255) // 255  # Convex Hull to expand the mask area
#         mask_area = mask_area & (~weak_protect_area)
#         mask_area = cv2.GaussianBlur(mask_area * 255, (kernal_size, kernal_size), 0)
#         mask_area[mask_area < 25] = 0
#         mask_area[mask_area >= 25] = 1
#         mask_area = (mask_area | strong_mask_area) & (~strong_protect_area) 
#         mask_area = cv2.dilate(mask_area, dilate_kernel, iterations=1)

#         return Image.fromarray(mask_area * 255)
        
#     def __call__(
#         self,
#         image: Union[str, Image.Image],
#         mask_type: str = "upper",
#     ):
#         assert mask_type in ['upper', 'lower', 'overall', 'inner', 'outer'], f"mask_type should be one of ['upper', 'lower', 'overall', 'inner', 'outer'], but got {mask_type}"
#         preprocess_results = self.preprocess_image(image)
#         mask = self.cloth_agnostic_mask(
#             preprocess_results['densepose'], 
#             preprocess_results['schp_lip'], 
#             preprocess_results['schp_atr'], 
#             part=mask_type,
#         )
#         return {
#             'mask': mask,
#             'densepose': preprocess_results['densepose'],
#             'schp_lip': preprocess_results['schp_lip'],
#             'schp_atr': preprocess_results['schp_atr']
#         }


# if __name__ == '__main__':
#     pass
