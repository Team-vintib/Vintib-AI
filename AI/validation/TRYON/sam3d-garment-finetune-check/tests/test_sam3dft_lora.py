"""LoRA 부착 — 위험 타깃 거부(순수 로직)와 실제 주입(torch/peft 가드).

핵심 검사는 **SparseLinear 타깃을 부착 전에 막는가**다 (REPORT.md §10). 그 검사는
`(이름, 객체)` 쌍만 보므로 torch 없이 테스트된다 — 가짜 모듈로 확인한다.
"""

from __future__ import annotations

import pytest

from garment3d.config import LoraConfig
from garment3d.train.lora import (
    LoraAttachError,
    assert_lora_targets_safe,
    check_lora_targets,
    resolve_backbone,
)


class _FakeLinear:
    """순수 nn.Linear 흉내 — dense 텐서를 받는 안전한 타깃."""


class SparseLinear:
    """이름이 중요하다 — 검사기가 클래스 이름(MRO)으로 위험을 판별한다."""


class _DerivedSparseLinear(SparseLinear):
    """서브클래스도 위험으로 잡혀야 한다."""


class _FakeModel:
    def __init__(self, modules):
        self._modules = modules

    def named_modules(self):
        return list(self._modules)


def test_safe_targets_are_collected():
    model = _FakeModel(
        [
            ("", _FakeModel([])),
            ("blocks.0.attn.to_qkv", _FakeLinear()),
            ("blocks.0.attn.to_out", _FakeLinear()),
            ("blocks.0.norm1", object()),
        ]
    )
    report = check_lora_targets(model.named_modules(), ["to_qkv", "to_out"])
    assert report.ok
    assert [name for name, _ in report.safe] == [
        "blocks.0.attn.to_qkv",
        "blocks.0.attn.to_out",
    ]
    assert report.unsafe == []
    assert report.unmatched == []


def test_sparse_linear_target_is_flagged_unsafe():
    model = _FakeModel([("blocks.0.mlp.0", SparseLinear())])
    report = check_lora_targets(model.named_modules(), ["0"])
    assert not report.ok
    assert report.unsafe == [("blocks.0.mlp.0", "SparseLinear")]
    assert "SparseTensor" in report.problem_summary()


def test_sparse_linear_subclass_is_flagged_unsafe():
    model = _FakeModel([("x.out_layer", _DerivedSparseLinear())])
    report = check_lora_targets(model.named_modules(), ["out_layer"])
    assert report.unsafe and report.unsafe[0][1] == "_DerivedSparseLinear"


def test_unmatched_targets_are_reported():
    model = _FakeModel([("attn.to_qkv", _FakeLinear())])
    report = check_lora_targets(model.named_modules(), ["to_qkv", "to_kv"])
    assert report.unmatched == ["to_kv"]
    assert "찾지 못한" in report.problem_summary()


def test_empty_target_list_is_not_ok():
    model = _FakeModel([("attn.to_qkv", _FakeLinear())])
    assert not check_lora_targets(model.named_modules(), []).ok


def test_root_module_is_ignored():
    """`named_modules()` 의 첫 원소는 이름이 빈 문자열(루트)이다 — 매칭 대상이 아니다."""
    report = check_lora_targets([("", _FakeLinear())], ["to_qkv"])
    assert report.safe == [] and report.unsafe == []


def test_assert_rejects_known_unsafe_names_before_walking():
    """이름만으로도 막는다 — 모델을 로드하기 전에 config 오류를 잡기 위해."""
    for name in ("mlp", "input_layer", "out_layer", "skip_connection"):
        with pytest.raises(LoraAttachError, match="SparseLinear"):
            assert_lora_targets_safe(_FakeModel([]), ["to_qkv", name])


def test_assert_passes_on_default_config_targets():
    model = _FakeModel(
        [
            ("blocks.0.attn.to_qkv", _FakeLinear()),
            ("blocks.0.cross.to_q", _FakeLinear()),
            ("blocks.0.cross.to_kv", _FakeLinear()),
            ("blocks.0.attn.to_out", _FakeLinear()),
        ]
    )
    report = assert_lora_targets_safe(model, LoraConfig().target_modules)
    assert len(report.safe) == 4


def test_resolve_backbone_unwraps_nested_wrappers():
    """generator → reverse_fn → (CFG) backbone → backbone 을 끝까지 따라간다."""

    class Leaf:
        pass

    leaf = Leaf()

    class Cfg:
        backbone = leaf

    class Reverse:
        backbone = Cfg()

    class Generator:
        reverse_fn = Reverse()

    pipeline = type("P", (), {"models": {"ss_generator": Generator()}})()
    assert resolve_backbone(pipeline, "ss_generator") is leaf


def test_resolve_backbone_without_wrapper_returns_module():
    module = object()
    pipeline = type("P", (), {"models": {"m": module}})()
    assert resolve_backbone(pipeline, "m") is module


def test_resolve_backbone_missing_key_raises():
    pipeline = type("P", (), {"models": {}})()
    with pytest.raises(LoraAttachError, match="ss_generator"):
        resolve_backbone(pipeline, "ss_generator")


# ── 아래부터 torch/peft 필요 ──────────────────────────────────────────────────


def test_attach_lora_injects_and_marks_only_lora_trainable():
    pytest.importorskip("torch")
    pytest.importorskip("peft")

    from garment3d.train.dummy_flow import build_dummy_flow_module
    from garment3d.train.lora import attach_lora, lora_state_dict, mark_only_lora_trainable

    module = build_dummy_flow_module()
    base_total = sum(p.numel() for p in module.parameters())

    model = attach_lora(module, LoraConfig(rank=4, alpha=8))
    trainable = mark_only_lora_trainable(model)

    assert trainable > 0
    assert trainable < base_total, "LoRA 파라미터는 베이스보다 훨씬 작아야 한다"
    assert all(not p.requires_grad for n, p in model.named_parameters() if "lora_" not in n)
    assert lora_state_dict(model), "어댑터 가중치만 추려져야 한다"
    assert all("lora_" in key for key in lora_state_dict(model))


def test_attach_lora_refuses_unsafe_targets():
    pytest.importorskip("torch")
    pytest.importorskip("peft")

    from garment3d.train.lora import attach_lora
    from garment3d.train.dummy_flow import build_dummy_flow_module

    with pytest.raises(LoraAttachError):
        attach_lora(build_dummy_flow_module(), LoraConfig(target_modules=["mlp"]))


def test_load_lora_state_dict_strict_rejects_unknown_keys():
    torch = pytest.importorskip("torch")
    pytest.importorskip("peft")

    from garment3d.train.lora import attach_lora, load_lora_state_dict

    from garment3d.train.dummy_flow import build_dummy_flow_module

    model = attach_lora(build_dummy_flow_module(), LoraConfig(rank=4))
    with pytest.raises(LoraAttachError, match="rank/target_modules"):
        load_lora_state_dict(model, {"nonexistent.lora_A.default.weight": torch.zeros(1)})
