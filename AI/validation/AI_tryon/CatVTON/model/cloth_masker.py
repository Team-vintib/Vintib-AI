import os
from PIL import Image
from typing import Union
import numpy as np
import cv2
from diffusers.image_processor import VaeImageProcessor
import torch

from model.SCHP import SCHP  # type: ignore
from model.DensePose import DensePose  # type: ignore

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
    },
}
# 'hat'/'shoes'는 이 딕셔너리들을 쓰지 않는다 — 둘 다 다른 옷(상의/바지)을 보호할 방법이
# PROTECT_CLOTH_PARTS에 없어서, 일반 로직(strong/weak mask 조합)을 타면 몸통까지 통째로 마스크에
# 잡히는 문제가 실측으로 확인됐다(S15P11A108-367). 대신 `_hat_mask()`/`_shoes_mask()`(각각 Hair
# 라벨, DensePose 'feet' 기반 기하학적 추정)로 완전히 별도 처리한다 — `cloth_agnostic_mask()`의
# `if part == 'hat'/'shoes':` 분기 참고.
MASK_CLOTH_PARTS = {
    'upper': ['Upper-clothes', 'Coat', 'Dress', 'Jumpsuits'],
    'lower': ['Pants', 'Skirt', 'Dress', 'Jumpsuits'],
    'overall': ['Upper-clothes', 'Dress', 'Pants', 'Skirt', 'Coat', 'Jumpsuits'],
    'inner': ['Upper-clothes'],
    'outer': ['Coat',],
}
MASK_DENSE_PARTS = {
    'upper': ['torso', 'big arms', 'forearms'],
    'lower': ['thighs', 'legs'],
    'overall': ['torso', 'thighs', 'legs', 'big arms', 'forearms'],
    'inner': ['torso'],
    'outer': ['torso', 'big arms', 'forearms'],
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
    def _hat_mask(
        schp_lip_mask: np.ndarray,
        schp_atr_mask: np.ndarray,
        dilate_kernel: np.ndarray,
    ) -> Image.Image:
        """머리카락(+기존에 쓰고 있던 모자) 바운딩 박스를 위쪽으로 확장해 모자 자리를 추정한다.

        DensePose엔 머리 인덱스가 없어서(SMPL 몸 표면 모델에 두피/모발이 없음) 못 쓰고,
        SCHP 'Hair'/'Hat' 라벨 + 기하학적 확장으로 대체한다. 얼굴은 무조건 보존한다.
        """
        hair_area = part_mask_of(['Hair'], schp_lip_mask, LIP_MAPPING) | \
            part_mask_of(['Hair'], schp_atr_mask, ATR_MAPPING)
        existing_hat_area = part_mask_of(['Hat'], schp_lip_mask, LIP_MAPPING) | \
            part_mask_of(['Hat'], schp_atr_mask, ATR_MAPPING)
        face_protect_area = part_mask_of('Face', schp_lip_mask, LIP_MAPPING).astype(bool)

        head_area = (hair_area | existing_hat_area).astype(np.uint8)
        rows, cols = np.where(head_area > 0)

        if len(rows) == 0:
            # 머리카락조차 인식하지 못하면(대머리, 인식 실패 등) 무리하게 추정하지 않고 빈 마스크를 돌려준다.
            mask_area = np.zeros_like(head_area)
        else:
            top, bottom = int(rows.min()), int(rows.max())
            left, right = int(cols.min()), int(cols.max())
            head_height = bottom - top
            head_width = right - left

            # 실측 결과 머리카락 bbox에 딱 맞춰버리면 챙 있는 모자가 옆으로 잘리고 위로도 부족했다.
            # 모자는 사람 몸 실루엣(머리) 범위를 넘어서 나오는 게 정상이라, 위/좌우 전부 여유를
            # 크게 두고 background 영역까지 마스크에 포함시킨다 — 임시값, 결과 보고 계속 조정.
            extend_top = max(0, top - int(head_height * 0.9))
            width_margin = int(head_width * 0.4)
            extend_left = max(0, left - width_margin)
            extend_right = min(head_area.shape[1] - 1, right + width_margin)

            mask_area = head_area.copy()
            mask_area[extend_top:bottom + 1, extend_left:extend_right + 1] = 1
            mask_area = mask_area & (~face_protect_area)

            mask_area = cv2.dilate(mask_area.astype(np.uint8), dilate_kernel, iterations=1)

        return Image.fromarray((mask_area * 255).astype(np.uint8))

    @staticmethod
    def _shoes_mask(
        densepose_mask: np.ndarray,
        schp_lip_mask: np.ndarray,
        schp_atr_mask: np.ndarray,
        dilate_kernel: np.ndarray,
    ) -> Image.Image:
        """발(DensePose 'feet') + 기존에 신고 있던 신발 라벨을 발목 위쪽(바지 밑단 근처)까지 확장한다.

        'hat'과 같은 이유로 upper/lower 등 일반 로직을 못 탄다 — 'shoes'는 다른 옷(상의/바지)을
        보호할 PROTECT_CLOTH_PARTS 정의가 없어서, 일반 로직을 타면 몸통까지 통째로 마스크에
        잡혀버리는 문제가 실측으로 확인됐다(S15P11A108-367).
        """
        feet_area = part_mask_of(['feet'], densepose_mask, DENSE_INDEX_MAP)
        existing_shoes_area = part_mask_of(['Left-shoe', 'Right-shoe'], schp_lip_mask, LIP_MAPPING) | \
            part_mask_of(['Left-shoe', 'Right-shoe'], schp_atr_mask, ATR_MAPPING)

        shoe_area = (feet_area.astype(bool) | existing_shoes_area.astype(bool)).astype(np.uint8)
        rows, cols = np.where(shoe_area > 0)

        if len(rows) == 0:
            mask_area = np.zeros_like(shoe_area)
        else:
            top, bottom = int(rows.min()), int(rows.max())
            left, right = int(cols.min()), int(cols.max())
            foot_height = bottom - top

            # 발목 위쪽(바지 밑단과 겹치는 지점)까지 확장 — 부츠처럼 발목을 덮는 신발 대응.
            extend_top = max(0, top - int(foot_height * 0.8))
            # 신발이 맨발 실루엣보다 옆으로 살짝 튀어나오는 경우 대응.
            width_margin = max(1, int((right - left) * 0.15))
            extend_left = max(0, left - width_margin)
            extend_right = min(shoe_area.shape[1] - 1, right + width_margin)

            mask_area = shoe_area.copy()
            mask_area[extend_top:bottom + 1, extend_left:extend_right + 1] = 1

            mask_area = cv2.dilate(mask_area.astype(np.uint8), dilate_kernel, iterations=1)

        return Image.fromarray((mask_area * 255).astype(np.uint8))

    @staticmethod
    def cloth_agnostic_mask(
        densepose_mask: Image.Image,
        schp_lip_mask: Image.Image,
        schp_atr_mask: Image.Image,
        part: str='overall',
        fit_type: str='regular',
        **kwargs
    ):
        assert part in ['upper', 'lower', 'overall', 'inner', 'outer', 'hat', 'shoes'], f"part should be one of ['upper', 'lower', 'overall', 'inner', 'outer', 'hat', 'shoes'], but got {part}"
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

        if part == 'hat':
            # 'hat'은 아래 upper/lower 등과 같은 일반 로직(=MASK_CLOTH_PARTS/MASK_DENSE_PARTS 둘 다
            # 채워져 있다고 가정)을 못 탄다 — DensePose엔 머리 인덱스가 없고(MASK_DENSE_PARTS['hat']=[]),
            # 사람이 이미 모자를 쓰고 있지 않으면 SCHP 'Hat' 라벨도 비어 있다
            # (MASK_CLOTH_PARTS['hat']=['Hat']가 빈 마스크가 됨). 그 상태로 일반 로직을 그대로 타면
            # "보호 대상이 아닌 모든 영역"이 마스크로 잡혀버려서(사실상 전신) 완전히 잘못된 결과가 나온다.
            # 그래서 SCHP 'Hair' 라벨(+ 기존에 모자를 쓰고 있었다면 그 'Hat' 라벨)의 바운딩 박스를
            # 구해 위쪽으로 확장하는 방식으로 별도 처리한다.
            return AutoMasker._hat_mask(schp_lip_mask, schp_atr_mask, dilate_kernel)

        if part == 'shoes':
            # 'shoes'도 같은 이유로 일반 로직을 못 탄다(PROTECT_CLOTH_PARTS['shoes']가 상의/바지를
            # 보호할 방법이 없어서, 일반 로직을 타면 몸통까지 통째로 마스크에 잡힌다 — 실측으로 확인됨).
            # DensePose 'feet' 인덱스(+ 기존에 신고 있었다면 신발 라벨)를 발목 위쪽까지 확장한다.
            return AutoMasker._shoes_mask(densepose_mask, schp_lip_mask, schp_atr_mask, dilate_kernel)

        # Strong Protect Area (Hands, Face, Accessory, Feet)
        hands_protect_area = part_mask_of(['hands', 'feet'], densepose_mask, DENSE_INDEX_MAP)
        # 손 보호 팽창은 dilate_kernel(다른 용도들과 공용)보다 작게 별도로 쓴다 — 실측에서
        # 손이 주머니에 들어간 지점 주변 원단까지 같이 보호돼 버려(원본이 안 지워지는 문제,
        # S15P11A108-367) 폭을 줄였다. 손가락 경계 자체는 여전히 보호하되, 그 여백만 좁힌다.
        hands_dilate_kernel = np.ones((max(1, dilate_kernel.shape[0] // 2), max(1, dilate_kernel.shape[1] // 2)), np.uint8)
        hands_protect_area = cv2.dilate(hands_protect_area, hands_dilate_kernel, iterations=1)
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
        # hat/shoes는 위에서 이미 별도 분기로 빠지므로 여기 도달하는 part는 항상
        # upper/lower/overall/inner/outer다 — MASK_CLOTH_PARTS.get(part, [])는 그 경우 전부 빈
        # 리스트를 주므로 accessory_parts는 원래 목록 그대로 유지된다(기존 동작과 동일).
        accessory_parts = [
            p for p in ['Hat', 'Glove', 'Sunglasses', 'Bag', 'Left-shoe', 'Right-shoe', 'Scarf', 'Socks']
            if p not in MASK_CLOTH_PARTS.get(part, [])
        ]
        accessory_protect_area = part_mask_of(accessory_parts, schp_lip_mask, LIP_MAPPING) | \
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

        # [신규] fit_type에 따른 마스크 조정 (strong_protect_area는 이미 제외된 상태이므로
        # 얼굴/손/발은 이 단계와 무관하게 항상 보존된다)
        mask_area = adjust_mask_for_fit(mask_area, densepose_mask, fit_type)
        mask_area = mask_area & (~strong_protect_area)  # 안전을 위해 재확인

        return Image.fromarray((mask_area * 255).astype(np.uint8))
        
    def __call__(
        self,
        image: Union[str, Image.Image],
        mask_type: str = "upper",
        fit_type: str = "regular",
    ):
        assert mask_type in ['upper', 'lower', 'overall', 'inner', 'outer', 'hat', 'shoes'], f"mask_type should be one of ['upper', 'lower', 'overall', 'inner', 'outer', 'hat', 'shoes'], but got {mask_type}"
        assert fit_type in ['regular', 'oversized', 'cropped'], f"fit_type should be one of ['regular', 'oversized', 'cropped'], but got {fit_type}"
        preprocess_results = self.preprocess_image(image)
        mask = self.cloth_agnostic_mask(
            preprocess_results['densepose'], 
            preprocess_results['schp_lip'], 
            preprocess_results['schp_atr'], 
            part=mask_type,
            fit_type=fit_type,
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
