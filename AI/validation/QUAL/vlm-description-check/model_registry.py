"""하자 짧은 설명 생성(sVLM) 후보 레지스트리.

설계: .claude/plans/ai/CH009-quality-defect-vlm.md "1. 후보 선정"

model_selection/model_registry.py 관례와 동일 — 키 하나(ACTIVE_VLM)만 바꾸면 스왑된다.
지금은 사용자 지시로 최신세대 Qwen-VL(3~4B, Instruct)부터 가동 여부를 점검한다 —
CH009 표에 있던 Qwen2-VL-2B-Instruct보다 한 세대 위 모델이다. Moondream2/SmolVLM2/
PaliGemma2는 CH009 표에는 있지만 아직 이 레지스트리에 등록하지 않았다(1차 점검 대상 아님).
"""

VLM_MODELS: dict[str, str] = {
    # 최신세대, 사용자 지정 1차 검증 대상. bf16 가중치 ~8.9GB — RTX 4070 Laptop(8GB)
    # 단독으로는 못 올린다. 4bit 양자화 전제.
    "qwen3-vl-4b-instruct": "Qwen/Qwen3-VL-4B-Instruct",
    # 같은 세대의 더 작은 크기 — 4B가 VRAM/지연시간 예산을 못 맞추면 다음 후보.
    "qwen3-vl-2b-instruct": "Qwen/Qwen3-VL-2B-Instruct",
    # CH009 원안 후보(이전 세대). 세대 비교용으로만 남겨 둔다.
    "qwen2-vl-2b-instruct": "Qwen/Qwen2-VL-2B-Instruct",
}
ACTIVE_VLM = "qwen3-vl-4b-instruct"  # <- 여기 키만 바꾸면 스왑

# 4bit: bitsandbytes nf4, RTX 4070 8GB에 맞춤. none: 양자화 없이 bf16(대형 GPU에서만 실행 가능).
QUANTIZATION_MODES = ("4bit", "none")
ACTIVE_QUANTIZATION = "4bit"

# 데모용 고정 카테고리(`worker.models.sam3.contracts.GarmentCategory`의 값 문자열).
# 이 스파이크에는 실제 카테고리 분류(FashionCLIP)가 없어서, 부위명 표시(§2 텍스트 위치
# 힌트·최종 JSON의 section)에 쓸 카테고리를 여기 하나로 고정해 둔다 — 실제 서비스에서는
# 상품 등록 파이프라인의 분류 브랜치 결과를 받는다. 샘플 이미지가 하의(청바지 등)여도
# 이 값 기준 부위명이 나온다는 점을 감안해서 결과를 읽을 것.
DEMO_GARMENT_CATEGORY = "TOP_SHIRT"
