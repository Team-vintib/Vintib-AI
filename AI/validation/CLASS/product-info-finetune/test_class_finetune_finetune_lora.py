"""`aihub_finetune_lora.py`의 순수 함수 테스트.

`load_model()`/학습 루프 본체는 peft/torch/transformers가 필요해 CI에서 못 돈다. 여기서
고정하는 건 `run_name()`뿐이다 — `lora_` 접두어는 노트북의 `method_of()`가 last-N과
구분해 그래프를 나누는 데 쓰는 계약이라, 접두어가 바뀌면 노트북 플랏이 조용히 잘못 묶인다.
"""

from __future__ import annotations

import aihub_finetune_lora as lora


def test_run_name_starts_with_lora_prefix() -> None:
    """노트북 method_of()가 이 접두어로 LoRA run을 분류한다 — 우연히 안 깨져야 한다."""
    assert lora.run_name("category", "masked", 8, 1e-4).startswith("lora_")


def test_run_name_varies_by_hyperparameter() -> None:
    base_name = lora.run_name("category", "masked", 8, 1e-4)
    assert base_name != lora.run_name("category", "masked", 16, 1e-4)  # rank
    assert base_name != lora.run_name("category", "masked", 8, 1e-3)  # lr
    assert base_name != lora.run_name("color", "masked", 8, 1e-4)  # task


def test_run_name_does_not_collide_with_last_n_naming() -> None:
    import aihub_finetune_vit as last_n

    lora_name = lora.run_name("category", "masked", 8, 1e-4)
    last_n_name = last_n.run_name("category", "masked", 2, 1e-5)
    assert lora_name != last_n_name
    assert lora_name.startswith("lora_")
    assert last_n_name.startswith("vit_last")
