"""PEFT LoRA 부착 — 안전한 타깃만 허용한다.

**핵심 방어**: `sp.SparseLinear` 는 `nn.Linear` 서브클래스인데 forward 가 `SparseTensor` 를
받는다. PEFT 의 `lora.Linear` 는 `isinstance(m, nn.Linear)` 로 잡아 놓고
`base_layer(x) + lora_B(lora_A(x))` 를 계산하므로, `lora_A`(순수 `nn.Linear`)가
`SparseTensor` 를 받아 **런타임에 터진다.** 근거·전체 표는 `REPORT.md` §10.

그래서 부착 **전에** 타깃을 검사해 거부한다. 주석 경고만 남기면 언젠가 누가 `mlp` 를 넣는다.

torch/peft 없이도 이 모듈은 import 된다 — 검사 함수(`check_lora_targets`)는 순수 로직이라
CI 에서 그대로 테스트된다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from ..config import LoraConfig as LoraSettings

#: forward 가 `SparseTensor` 를 받는 `nn.Linear` 서브클래스. LoRA 를 붙이면 깨진다.
UNSAFE_MODULE_CLASSES = frozenset({"SparseLinear"})

#: 사람이 흔히 넣으려 하는 위험 타깃 이름. 이름만으로도 미리 경고할 수 있다.
KNOWN_UNSAFE_TARGET_NAMES = frozenset({"mlp", "input_layer", "out_layer", "skip_connection"})


class LoraAttachError(RuntimeError):
    """LoRA 를 붙일 수 없다."""


@dataclass
class LoraTargetReport:
    """타깃 검사 결과."""

    #: 붙일 수 있는 (전체이름, 클래스이름) 목록
    safe: list[tuple[str, str]] = field(default_factory=list)
    #: 붙이면 깨지는 목록
    unsafe: list[tuple[str, str]] = field(default_factory=list)
    #: config 에 있었지만 모델에서 하나도 못 찾은 타깃 이름
    unmatched: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.unsafe and bool(self.safe)

    def problem_summary(self) -> str:
        parts = []
        if self.unsafe:
            listed = ", ".join(f"{n} ({c})" for n, c in self.unsafe[:5])
            parts.append(
                f"SparseTensor 를 받는 모듈 {len(self.unsafe)}개가 타깃에 있습니다: {listed}"
                " — REPORT.md §10 참고"
            )
        if not self.safe:
            parts.append("붙일 수 있는 모듈이 하나도 없습니다")
        if self.unmatched:
            parts.append(f"모델에서 찾지 못한 타깃 이름: {sorted(self.unmatched)}")
        return " / ".join(parts)


def _class_names(module: Any) -> set[str]:
    """모듈 클래스와 그 조상들의 이름. torch import 없이 SparseLinear 를 판별하려는 것."""
    try:
        return {klass.__name__ for klass in type(module).__mro__}
    except AttributeError:  # pragma: no cover - 이상한 객체 방어
        return {type(module).__name__}


def check_lora_targets(
    named_modules: Iterable[tuple[str, Any]],
    target_modules: Iterable[str],
) -> LoraTargetReport:
    """`named_modules()` 를 훑어 타깃별 안전/위험을 분류한다.

    순수 함수다 — `(이름, 객체)` 쌍만 받으므로 torch 없이 테스트된다. `target_modules` 는
    PEFT 와 같은 규약으로 **전체 이름의 마지막 조각(suffix) 매칭**이다.
    """
    targets = list(target_modules)
    report = LoraTargetReport()
    matched: set[str] = set()

    for full_name, module in named_modules:
        if not full_name:
            continue
        leaf = full_name.rsplit(".", 1)[-1]
        hit = next((t for t in targets if leaf == t or full_name.endswith(f".{t}")), None)
        if hit is None:
            continue
        matched.add(hit)
        classes = _class_names(module)
        entry = (full_name, type(module).__name__)
        if classes & UNSAFE_MODULE_CLASSES:
            report.unsafe.append(entry)
        else:
            report.safe.append(entry)

    report.unmatched = [t for t in targets if t not in matched]
    return report


def assert_lora_targets_safe(model: Any, target_modules: Iterable[str]) -> LoraTargetReport:
    """검사해서 문제가 있으면 던진다. 성공 시 리포트를 돌려준다."""
    targets = list(target_modules)
    named = KNOWN_UNSAFE_TARGET_NAMES & set(targets)
    if named:
        raise LoraAttachError(
            f"타깃 {sorted(named)} 는 SparseLinear 계열이라 PEFT LoRA 가 깨집니다 "
            "(REPORT.md §10). configs 의 target_modules 에서 제거하세요."
        )

    report = check_lora_targets(model.named_modules(), targets)
    if not report.ok:
        raise LoraAttachError(report.problem_summary())
    return report


def resolve_backbone(pipeline: Any, model_key: str) -> Any:
    """`pipeline.models[key]` 에서 실제 트랜스포머를 꺼낸다.

    generator 는 flow matching 래퍼이고 트랜스포머는 `reverse_fn.backbone` 에 있다 —
    `inference_pipeline.py:620` 의 `is_mm_dit()` 가 그 경로로 속성을 확인한다. CFG 래퍼가
    한 겹 더 있을 수 있어 `backbone` 을 따라 끝까지 내려간다.
    """
    try:
        module = pipeline.models[model_key]
    except (KeyError, TypeError) as exc:
        raise LoraAttachError(f"pipeline.models 에 {model_key!r} 가 없습니다") from exc

    node = getattr(module, "reverse_fn", module)
    # CFG 래퍼(classifier_free_guidance.py)가 backbone 을 또 감쌀 수 있다.
    seen = 0
    while hasattr(node, "backbone") and seen < 8:
        node = node.backbone
        seen += 1
    return node


def attach_lora(model: Any, settings: LoraSettings) -> Any:
    """LoRA 어댑터를 주입한다. 검사를 통과하지 못하면 붙이지 않는다.

    `peft.inject_adapter_in_model` 을 쓴다 — `get_peft_model` 은 HF `PreTrainedModel` 을
    전제한 편의 API 라서, 순수 `nn.Module` 인 SAM 3D 백본에는 주입 API 가 맞다.

    Returns:
        LoRA 가 주입된 같은 모듈(제자리 수정 후 반환).
    """
    assert_lora_targets_safe(model, settings.target_modules)

    try:
        from peft import LoraConfig, inject_adapter_in_model
    except ImportError as exc:
        raise LoraAttachError("peft 가 필요합니다: pip install peft") from exc

    peft_config = LoraConfig(
        r=settings.rank,
        lora_alpha=settings.alpha,
        lora_dropout=settings.dropout,
        target_modules=list(settings.target_modules),
        bias="none",
    )
    return inject_adapter_in_model(peft_config, model)


def mark_only_lora_trainable(model: Any) -> int:
    """LoRA 파라미터만 학습 가능하게 만들고, 학습 대상 파라미터 수를 돌려준다."""
    trainable = 0
    for name, param in model.named_parameters():
        is_lora = "lora_" in name
        param.requires_grad = is_lora
        if is_lora:
            trainable += param.numel()
    return trainable


def lora_state_dict(model: Any) -> dict[str, Any]:
    """어댑터 가중치만 추린다. 베이스 수 GB 를 체크포인트에 넣지 않기 위한 것."""
    return {name: p.detach().cpu() for name, p in model.named_parameters() if "lora_" in name}


def load_lora_state_dict(model: Any, state: dict[str, Any], *, strict: bool = True) -> None:
    """`lora_state_dict()` 산출물을 되돌린다.

    Raises:
        LoraAttachError: `strict` 인데 모델에 없는 키가 있을 때. LoRA rank/타깃을 바꾼 뒤
            옛 체크포인트를 올리면 조용히 일부만 로드되는 사고가 난다.
    """
    own = dict(model.named_parameters())
    missing = [key for key in state if key not in own]
    if missing and strict:
        raise LoraAttachError(
            f"체크포인트에만 있는 LoRA 키 {len(missing)}개: {missing[:3]} — "
            "rank/target_modules 가 바뀌었는지 확인하세요."
        )
    for key, value in state.items():
        if key in own:
            with _no_grad():
                own[key].copy_(value)


def _no_grad():
    """torch 를 lazy import 하기 위한 컨텍스트 헬퍼."""
    import torch

    return torch.no_grad()
