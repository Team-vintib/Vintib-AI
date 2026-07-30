"""DPO — 선호쌍 구성과 손실 부호 규약(순수), 그리고 1-step 스모크(torch 가드)."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from garment3d.config import DpoConfig, LoraConfig
from garment3d.train.dpo import (
    Candidate,
    DeterministicScorer,
    DummyCandidateGenerator,
    build_preference_pairs,
    collect_candidates,
    dpo_logits,
)


def _candidates(scores: list[float]) -> list[Candidate]:
    return [
        Candidate(sample_id="s", index=i, path=Path(f"c{i}.ply"), score=score)
        for i, score in enumerate(scores)
    ]


def test_candidate_rejects_nan_score():
    with pytest.raises(ValueError):
        Candidate(sample_id="s", index=0, path=Path("c.ply"), score=float("nan"))


def test_extremes_strategy_pairs_best_with_worst():
    pairs = build_preference_pairs(_candidates([0.2, 0.9, 0.5]), scorer="test")
    assert len(pairs) == 1
    assert pairs[0].chosen_score == 0.9
    assert pairs[0].rejected_score == 0.2
    assert pairs[0].margin == pytest.approx(0.7)
    assert pairs[0].scorer == "test"


def test_best_vs_rest_strategy_makes_n_minus_one_pairs():
    pairs = build_preference_pairs(_candidates([0.2, 0.9, 0.5]), strategy="best_vs_rest")
    assert len(pairs) == 2
    assert {p.rejected_score for p in pairs} == {0.2, 0.5}
    assert all(p.chosen_score == 0.9 for p in pairs)


def test_min_margin_filters_noisy_pairs():
    """스코어러 노이즈가 선호로 학습되는 걸 막는 장치다."""
    assert build_preference_pairs(_candidates([0.50, 0.52]), min_margin=0.05) == []
    assert len(build_preference_pairs(_candidates([0.50, 0.70]), min_margin=0.05)) == 1


def test_fewer_than_two_candidates_yields_no_pairs():
    assert build_preference_pairs(_candidates([0.5])) == []
    assert build_preference_pairs([]) == []


def test_unknown_strategy_raises():
    with pytest.raises(ValueError, match="strategy"):
        build_preference_pairs(_candidates([0.1, 0.9]), strategy="tournament")


def test_collect_candidates_sorts_desc_and_requires_two(tmp_path: Path):
    candidates = collect_candidates(
        "s1", DummyCandidateGenerator(), DeterministicScorer(), 4, tmp_path / "cand"
    )
    assert len(candidates) == 4
    assert [c.score for c in candidates] == sorted((c.score for c in candidates), reverse=True)
    assert all(c.path.is_file() for c in candidates)

    with pytest.raises(ValueError, match="2개 이상"):
        collect_candidates(
            "s1", DummyCandidateGenerator(), DeterministicScorer(), 1, tmp_path / "cand"
        )


def test_deterministic_scorer_is_stable_across_processes(tmp_path: Path):
    """경로 이름 기반 sha256 이라 프로세스가 달라도 같은 순위가 나와야 한다."""
    scorer = DeterministicScorer()
    assert scorer.score(tmp_path / "a.ply") == scorer.score(Path("other") / "a.ply")
    assert scorer.score(tmp_path / "a.ply") != scorer.score(tmp_path / "b.ply")
    assert 0.0 <= scorer.score(tmp_path / "a.ply") <= 1.0


def test_dpo_logits_sign_convention_rewards_lower_chosen_loss():
    """입력은 **손실**이다 — chosen 이 참조 대비 더 줄어들면 로짓이 양수여야 한다.

    이 부호가 뒤집히면 학습이 정확히 반대로 간다. 그래서 별도 테스트를 둔다.
    """
    # chosen 손실이 참조보다 0.2 줄고, rejected 는 그대로 → chosen 쪽이 개선됐다.
    logit = dpo_logits(
        policy_chosen=0.8, policy_rejected=1.0, ref_chosen=1.0, ref_rejected=1.0, beta=1.0
    )
    assert logit > 0

    # 반대 상황
    flipped = dpo_logits(
        policy_chosen=1.0, policy_rejected=0.8, ref_chosen=1.0, ref_rejected=1.0, beta=1.0
    )
    assert flipped < 0
    assert logit == pytest.approx(-flipped)


def test_dpo_logits_scales_with_beta():
    args = dict(policy_chosen=0.5, policy_rejected=1.0, ref_chosen=1.0, ref_rejected=1.0)
    assert dpo_logits(beta=0.2, **args) == pytest.approx(2 * dpo_logits(beta=0.1, **args))


def test_dpo_logits_zero_when_policy_matches_reference():
    assert dpo_logits(1.0, 2.0, 1.0, 2.0, beta=0.5) == pytest.approx(0.0)


def test_dpo_loss_matches_negative_log_sigmoid():
    """torch 구현이 `-log σ(z)` 와 일치하는지 순수 수식으로 교차검증한다."""
    pytest.importorskip("torch")

    from garment3d.train.dpo import flow_dpo_loss

    torch = pytest.importorskip("torch")
    args = (
        torch.tensor(0.8),
        torch.tensor(1.0),
        torch.tensor(1.0),
        torch.tensor(1.0),
    )
    value = float(flow_dpo_loss(*args, beta=1.0))
    expected = -math.log(1 / (1 + math.exp(-0.2)))
    assert value == pytest.approx(expected, rel=1e-5)


# ── 아래부터 torch/peft 필요 ──────────────────────────────────────────────────


def test_dpo_smoke_runs_and_saves(tmp_path: Path):
    torch = pytest.importorskip("torch")
    pytest.importorskip("peft")

    from copy import deepcopy

    from garment3d.train.dpo import DpoTrainer
    from garment3d.train.dummy_flow import DummyFlowLoss, build_dummy_flow_module
    from garment3d.train.sft import prepare_lora_model

    module = build_dummy_flow_module()
    policy, _ = prepare_lora_model(module, LoraConfig(rank=4))
    reference = deepcopy(module)
    for param in reference.parameters():
        param.requires_grad = False

    settings = DpoConfig(max_steps=2, save_every=1, learning_rate=0.05)
    trainer = DpoTrainer(
        DummyFlowLoss(policy, seed=0),
        DummyFlowLoss(reference, seed=0),
        settings,
        tmp_path / "ckpt",
        trainable_params=policy.parameters(),
    )

    generator = torch.Generator().manual_seed(0)

    def provider(_step):
        return (
            {"x1": torch.randn(1, 8, 16, generator=generator)},
            {"x1": torch.randn(1, 8, 16, generator=generator)},
        )

    state = trainer.train(provider, module=policy)
    assert state.step == 2
    assert len(state.loss_history) == 2
    assert all(value == value for value in state.loss_history)
    assert (tmp_path / "ckpt" / "dpo_step0000002.pt").is_file()


def test_dpo_reference_model_is_not_trained(tmp_path: Path):
    """참조모델까지 학습되면 DPO 가 무의미해진다 — 가장 비싼 실수라 명시적으로 막는다."""
    torch = pytest.importorskip("torch")
    pytest.importorskip("peft")

    from copy import deepcopy

    from garment3d.train.dpo import DpoTrainer
    from garment3d.train.dummy_flow import DummyFlowLoss, build_dummy_flow_module
    from garment3d.train.sft import prepare_lora_model

    module = build_dummy_flow_module()
    policy, _ = prepare_lora_model(module, LoraConfig(rank=4))
    reference = deepcopy(module)
    for param in reference.parameters():
        param.requires_grad = False
    before = [p.detach().clone() for p in reference.parameters()]

    trainer = DpoTrainer(
        DummyFlowLoss(policy, seed=0),
        DummyFlowLoss(reference, seed=0),
        DpoConfig(max_steps=1, save_every=0, learning_rate=0.5),
        tmp_path / "ckpt",
        trainable_params=policy.parameters(),
    )
    generator = torch.Generator().manual_seed(0)
    trainer.train(
        lambda _s: (
            {"x1": torch.randn(1, 8, 16, generator=generator)},
            {"x1": torch.randn(1, 8, 16, generator=generator)},
        )
    )

    after = list(reference.parameters())
    assert all(torch.allclose(b, a) for b, a in zip(before, after))
