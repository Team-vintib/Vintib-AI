"""`aihub_finetune_plots.py`의 순수 함수 테스트.

실제 렌더링(`plot_per_method`/`plot_best_per_method`)은 matplotlib이 필요해 CI에서
못 돈다(`validation/requirements-test.txt`). 여기서 고정하는 건 그 앞단 — run 이름으로
방법을 분류하는 규칙과 기준선 문자열 파싱이다. 분류 규칙이 틀리면 last-N과 LoRA가 같은
그래프에 뒤섞이거나("기타"로 다 몰리거나) 해서 비교가 무의미해진다.
"""

from __future__ import annotations

import pytest

import aihub_finetune_plots as fp


def test_method_of_classifies_known_prefixes() -> None:
    assert fp.method_of("vit_last4_category_masked_lr1e-05") == "last-N 언프리즈"
    assert fp.method_of("lora_r8_a16_d0.05_qv_category_masked_lr0.0001") == "LoRA"
    assert fp.method_of("full_category_masked") == "전체 파인튜닝"


def test_method_of_falls_back_to_etc_for_unknown_prefix() -> None:
    assert fp.method_of("random_experiment_x") == "기타"


def test_parse_baseline_without_task_prefix_applies_to_all() -> None:
    """태스크 접두어가 없으면 (None, 라벨, 값) — 모든 태스크의 베스트-run 플랏에 그려진다."""
    assert fp.parse_baseline("선형 프로브 val=0.8058") == (None, "선형 프로브 val", 0.8058)


def test_parse_baseline_with_task_prefix_scopes_to_that_task() -> None:
    """color/category는 val_accuracy 절대값이 비교 대상이 아니라서, 기준선도 태스크별로
    분리해야 한다 — 그래서 접두어를 준 값은 그 태스크 플랏에만 그려져야 한다."""
    assert fp.parse_baseline("category:선형 프로브 val=0.8058") == (
        "category",
        "선형 프로브 val",
        0.8058,
    )
    assert fp.parse_baseline("color:zero-shot val=0.5951") == ("color", "zero-shot val", 0.5951)


def test_parse_baseline_uses_rightmost_equals_when_label_has_one() -> None:
    """라벨 자체에 '='가 들어갈 일은 거의 없지만, rpartition이라 마지막 '='만 값 구분자로
    쓴다는 걸 고정해둔다."""
    assert fp.parse_baseline("a=b val=0.5") == (None, "a=b val", 0.5)


def test_parse_baseline_rejects_missing_equals() -> None:
    with pytest.raises(ValueError):
        fp.parse_baseline("no-equals-sign")
