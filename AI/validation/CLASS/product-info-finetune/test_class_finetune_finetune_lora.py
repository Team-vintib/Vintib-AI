"""`aihub_finetune_lora.py`의 순수 함수 테스트.

`load_model()`/학습 루프 본체는 peft/torch/transformers가 필요해 CI에서 못 돈다. 여기서
고정하는 건 `run_name()`뿐이다 — `lora_` 접두어는 노트북의 `method_of()`가 last-N과
구분해 그래프를 나누는 데 쓰는 계약이라, 접두어가 바뀌면 노트북 플랏이 조용히 잘못 묶인다.
"""

from __future__ import annotations

import aihub_finetune_lora as lora
import aihub_finetune_plots as fp


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


def test_run_name_warm_start_gets_distinct_suffix() -> None:
    """색상 독립학습과 순차학습(카테고리 체크포인트에서 이어받음)은 같은 하이퍼파라미터를
    써도 서로 다른 폴더에 저장돼야 한다 — 하나가 다른 하나를 덮어쓰면 비교가 불가능하다."""
    scratch = lora.run_name("color", "masked", 16, 1e-4, alpha=32)
    warm = lora.run_name("color", "masked", 16, 1e-4, alpha=32, warm_start=True)
    assert warm != scratch
    assert warm == scratch + "_warm"


def test_run_name_warm_start_still_classified_correctly() -> None:
    """`_warm` 접미사가 붙어도 `aihub_finetune_plots.method_of()`의 접두어 분류는
    그대로 동작해야 한다 — 안 그러면 순차학습 run이 플랏/리더보드에서 "기타"로 빠진다."""
    warm = lora.run_name("color", "masked", 16, 1e-4, alpha=32, warm_start=True)
    assert fp.method_of(warm) == "LoRA"
