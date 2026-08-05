"""SFT — 스텝 스케줄/체크포인트 규약(순수)과 1-step 스모크(torch 가드)."""

from __future__ import annotations

from pathlib import Path

import pytest

from garment3d.config import LoraConfig, SftConfig
from garment3d.train.sft import (
    Sam3dFlowLoss,
    TrainState,
    checkpoint_path,
    iter_micro_steps,
    latest_checkpoint,
    should_save,
)


def test_micro_steps_count_is_updates_times_accum():
    """`max_steps` 는 optimizer 업데이트 횟수다 — 누적을 늘려도 업데이트 수는 그대로."""
    steps = list(iter_micro_steps(3, grad_accum_steps=4))
    assert len(steps) == 12
    assert sum(1 for s in steps if s.is_update) == 3
    assert [s.global_step for s in steps if s.is_update] == [1, 2, 3]


def test_micro_steps_marks_only_last_micro_as_update():
    steps = list(iter_micro_steps(1, grad_accum_steps=3))
    assert [s.is_update for s in steps] == [False, False, True]
    assert [s.micro_index for s in steps] == [0, 1, 2]


def test_micro_steps_zero_max_steps_yields_nothing():
    assert list(iter_micro_steps(0)) == []


@pytest.mark.parametrize("bad", [-1])
def test_micro_steps_rejects_negative_max_steps(bad: int):
    with pytest.raises(ValueError):
        list(iter_micro_steps(bad))


def test_micro_steps_rejects_zero_accum():
    with pytest.raises(ValueError):
        list(iter_micro_steps(1, grad_accum_steps=0))


def test_should_save_includes_final_step():
    """max_steps 가 save_every 의 배수가 아닐 때 마지막 학습분이 사라지면 안 된다."""
    assert should_save(10, save_every=5, max_steps=13)
    assert not should_save(11, save_every=5, max_steps=13)
    assert should_save(13, save_every=5, max_steps=13)


def test_should_save_with_zero_save_every_only_saves_final():
    assert not should_save(5, save_every=0, max_steps=10)
    assert should_save(10, save_every=0, max_steps=10)


def test_checkpoint_path_is_zero_padded_and_sortable(tmp_path: Path):
    paths = [checkpoint_path(tmp_path, step) for step in (2, 10, 1000)]
    assert [p.name for p in paths] == [
        "sft_step0000002.pt",
        "sft_step0000010.pt",
        "sft_step0001000.pt",
    ]
    assert sorted(p.name for p in paths) == [p.name for p in paths]


def test_latest_checkpoint_picks_highest_step(tmp_path: Path):
    assert latest_checkpoint(tmp_path) is None
    for step in (1, 20, 3):
        checkpoint_path(tmp_path, step).write_bytes(b"x")
    assert latest_checkpoint(tmp_path).name == "sft_step0000020.pt"


def test_latest_checkpoint_respects_tag(tmp_path: Path):
    checkpoint_path(tmp_path, 1, tag="dpo").write_bytes(b"x")
    assert latest_checkpoint(tmp_path, tag="sft") is None
    assert latest_checkpoint(tmp_path, tag="dpo") is not None


def test_train_state_roundtrip():
    state = TrainState(step=5, samples_seen=40, loss_history=[1.0, 0.5])
    assert TrainState.from_dict(state.to_dict()) == state


def test_train_state_from_empty_dict_is_zeroed():
    assert TrainState.from_dict({}) == TrainState()


def test_sam3d_flow_loss_delegates_to_upstream_loss():
    """upstream `FlowMatching.loss(x1, *cond)` 를 그대로 부르는지 (REPORT.md §7)."""
    calls = []

    class FakeGenerator:
        def loss(self, x1, *args, **kwargs):
            calls.append((x1, args, kwargs))
            return 0.25, {"flow_matching_loss": 0.25}

    loss_fn = Sam3dFlowLoss(FakeGenerator(), backbone=object())
    total, detail = loss_fn({"x1": "LATENT", "cond_args": ("A",), "cond_kwargs": {"cfg": True}})

    assert total == 0.25
    assert detail == {"flow_matching_loss": 0.25}
    assert calls == [("LATENT", ("A",), {"cfg": True})]


# ── 아래부터 torch/peft 필요 ──────────────────────────────────────────────────


def _make_trainer(tmp_path: Path, **overrides):
    torch = pytest.importorskip("torch")
    pytest.importorskip("peft")

    from garment3d.train.dummy_flow import DummyFlowLoss, build_dummy_flow_module
    from garment3d.train.sft import SftTrainer, prepare_lora_model

    options = {"max_steps": 2, "grad_accum_steps": 2, "save_every": 1, "log_every": 1}
    options.update(overrides)
    settings = SftConfig(**options)
    module = build_dummy_flow_module()
    model, trainable = prepare_lora_model(module, LoraConfig(rank=4))
    assert trainable > 0

    loss_fn = DummyFlowLoss(model, seed=settings.seed)
    trainer = SftTrainer(loss_fn, settings, tmp_path / "ckpt")
    generator = torch.Generator().manual_seed(0)

    def provider(_step):
        return {"x1": torch.randn(1, 8, 16, generator=generator)}

    return trainer, provider, model


def test_sft_smoke_runs_and_saves(tmp_path: Path):
    trainer, provider, _ = _make_trainer(tmp_path)
    logs: list[tuple[int, float]] = []
    state = trainer.train(provider, on_log=lambda s, v: logs.append((s, v)))

    assert state.step == 2
    assert state.samples_seen == 2 * 2  # batch_size * grad_accum * updates
    assert [step for step, _ in logs] == [1, 2]
    assert all(value == value for _, value in logs), "손실이 NaN 이면 안 된다"
    assert (tmp_path / "ckpt" / "sft_step0000002.pt").is_file()


def test_sft_lora_weights_actually_change(tmp_path: Path):
    """LoRA 만 학습 가능하게 해 놓고 실제로 갱신되는지 — 옵티마이저가 빈 파라미터를 잡았으면 안 된다."""
    torch = pytest.importorskip("torch")
    trainer, provider, model = _make_trainer(tmp_path, learning_rate=0.1)

    from garment3d.train.lora import lora_state_dict

    before = {k: v.clone() for k, v in lora_state_dict(model).items()}
    trainer.train(provider)
    after = lora_state_dict(model)

    changed = [k for k in before if not torch.allclose(before[k], after[k])]
    assert changed, "LoRA 파라미터가 하나도 갱신되지 않았다"


def test_sft_resume_continues_from_checkpoint(tmp_path: Path):
    trainer, provider, _ = _make_trainer(tmp_path)
    trainer.train(provider)
    saved = tmp_path / "ckpt" / "sft_step0000002.pt"

    trainer2, provider2, _ = _make_trainer(tmp_path, max_steps=4)
    state = trainer2.load(saved)
    assert state.step == 2

    state = trainer2.train(provider2)
    assert state.step == 4
    assert (tmp_path / "ckpt" / "sft_step0000004.pt").is_file()


def test_sft_train_is_noop_when_already_done(tmp_path: Path):
    trainer, provider, _ = _make_trainer(tmp_path)
    trainer.state.step = 2
    assert trainer.train(provider).step == 2
    assert not (tmp_path / "ckpt").exists()


def test_sft_trainer_requires_trainable_params(tmp_path: Path):
    pytest.importorskip("torch")

    from garment3d.train.dummy_flow import DummyFlowLoss, build_dummy_flow_module
    from garment3d.train.sft import SftTrainer

    module = build_dummy_flow_module()
    for param in module.parameters():
        param.requires_grad = False

    with pytest.raises(RuntimeError, match="학습 가능한 파라미터"):
        SftTrainer(DummyFlowLoss(module), SftConfig(max_steps=1), tmp_path / "ckpt")
