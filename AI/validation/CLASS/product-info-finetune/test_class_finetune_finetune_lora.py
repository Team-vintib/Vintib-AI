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


def test_run_name_varies_by_alpha_dropout_and_target_modules() -> None:
    """`r`/`lr_adapter`가 같아도 alpha·dropout·target_modules만 바뀌면 폴더가 겹치면
    안 된다 — 이전 버전은 이 셋을 이름에 안 넣어서 스윕 중 서로 덮어썼다."""
    base_name = lora.run_name("category", "masked", 8, 1e-4)
    assert base_name != lora.run_name("category", "masked", 8, 1e-4, alpha=32)
    assert base_name != lora.run_name("category", "masked", 8, 1e-4, dropout=0.1)
    assert base_name != lora.run_name(
        "category", "masked", 8, 1e-4, target_modules=("q_proj", "k_proj", "v_proj", "out_proj")
    )


def test_run_name_target_modules_tag_is_order_independent() -> None:
    """`--target-modules`를 다른 순서로 줘도(사용자 입력 순서) 같은 조합이면 같은 이름이어야
    한다 — 정렬 안 하면 순서만 바꿔도 새 폴더가 생겨 스윕 결과가 쓸데없이 흩어진다."""
    name_a = lora.run_name(
        "category", "masked", 8, 1e-4, target_modules=("q_proj", "v_proj", "k_proj")
    )
    name_b = lora.run_name(
        "category", "masked", 8, 1e-4, target_modules=("k_proj", "v_proj", "q_proj")
    )
    assert name_a == name_b
