"""LoRA SFT 학습 루프 — 스텝 스케줄(순수) + torch 루프(가드) 로 나눠 둔다.

**upstream 손실을 재구현하지 않는다.** `FlowMatching.loss(x1, *cond)` 가 공개돼 있으므로
(`REPORT.md` §7) `Sam3dFlowLoss` 가 그걸 그대로 호출한다. 우리 몫은 옵티마이저·gradient
누적·체크포인트·resume 뿐이다.

스텝 스케줄(`iter_micro_steps`, `should_save`)은 **순수 로직**이라 torch 없이 CI 에서
테스트된다. 실제 학습은 `SftTrainer` 이고 torch 가 있을 때만 돈다.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Protocol

from ..config import LoraConfig as LoraSettings
from ..config import SftConfig
from .lora import attach_lora, load_lora_state_dict, lora_state_dict, mark_only_lora_trainable


class FlowLossFn(Protocol):
    """`batch → (loss_tensor, detail_dict)`. 실모델과 더미가 같은 얼굴을 갖게 한다."""

    def __call__(self, batch: dict[str, Any]) -> tuple[Any, dict[str, float]]: ...

    def parameters(self) -> Iterable[Any]: ...


# ── 순수 로직: 스텝 스케줄과 체크포인트 경로 ─────────────────────────────────


@dataclass(frozen=True)
class MicroStep:
    """gradient 누적 단위 한 칸."""

    global_step: int
    micro_index: int
    #: 이 마이크로스텝 뒤에 optimizer.step() 을 부르는가
    is_update: bool


def iter_micro_steps(max_steps: int, grad_accum_steps: int = 1) -> Iterator[MicroStep]:
    """`max_steps` 번의 **업데이트**를 위해 필요한 마이크로스텝을 순서대로 낸다.

    `max_steps` 는 optimizer 업데이트 횟수다(마이크로배치 횟수가 아니다). 누적 스텝을 바꿨을 때
    학습량이 조용히 달라지는 걸 막기 위한 규약이다.
    """
    if max_steps < 0:
        raise ValueError(f"max_steps 는 0 이상이어야 합니다: {max_steps}")
    if grad_accum_steps < 1:
        raise ValueError(f"grad_accum_steps 는 1 이상이어야 합니다: {grad_accum_steps}")

    for step in range(1, max_steps + 1):
        for micro in range(grad_accum_steps):
            yield MicroStep(step, micro, micro == grad_accum_steps - 1)


def should_save(step: int, save_every: int, max_steps: int) -> bool:
    """`save_every` 배수이거나 마지막 스텝이면 저장한다.

    마지막 스텝을 포함하는 게 중요하다 — `max_steps` 가 `save_every` 의 배수가 아닐 때
    마지막 학습분이 통째로 사라지는 사고가 흔하다.
    """
    if save_every <= 0:
        return step == max_steps
    return step % save_every == 0 or step == max_steps


def checkpoint_path(checkpoint_dir: Path, step: int, *, tag: str = "sft") -> Path:
    return Path(checkpoint_dir) / f"{tag}_step{step:07d}.pt"


def latest_checkpoint(checkpoint_dir: Path, *, tag: str = "sft") -> Path | None:
    """가장 큰 step 번호의 체크포인트. 없으면 None."""
    directory = Path(checkpoint_dir)
    if not directory.is_dir():
        return None
    found = sorted(directory.glob(f"{tag}_step*.pt"))
    return found[-1] if found else None


@dataclass
class TrainState:
    """resume 에 필요한 최소 상태."""

    step: int = 0
    samples_seen: int = 0
    #: 최근 로그된 손실들. 리포트에 그대로 실린다.
    loss_history: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> TrainState:
        return cls(
            step=int(raw.get("step", 0)),
            samples_seen=int(raw.get("samples_seen", 0)),
            loss_history=list(raw.get("loss_history", [])),
        )


# ── torch 루프 ───────────────────────────────────────────────────────────────


class SftTrainer:
    """LoRA SFT. torch 가 있을 때만 동작한다.

    `batch_provider` 는 `(step) -> batch dict` 다. 데이터 로더를 여기서 만들지 않는 이유는
    **데이터 의존 로직을 밖으로 밀어내기 위한 것** — 더미도 실데이터도 같은 훅으로 들어온다.
    """

    def __init__(
        self,
        loss_fn: FlowLossFn,
        settings: SftConfig,
        checkpoint_dir: Path,
        *,
        tag: str = "sft",
    ) -> None:
        import torch

        self.loss_fn = loss_fn
        self.settings = settings
        self.checkpoint_dir = Path(checkpoint_dir)
        self.tag = tag
        self.state = TrainState()

        torch.manual_seed(settings.seed)
        trainable = [p for p in loss_fn.parameters() if p.requires_grad]
        if not trainable:
            raise RuntimeError(
                "학습 가능한 파라미터가 없습니다 — LoRA 부착과 "
                "mark_only_lora_trainable() 을 먼저 수행하세요."
            )
        self.optimizer = torch.optim.AdamW(
            trainable, lr=settings.learning_rate, weight_decay=settings.weight_decay
        )

    def save(self, step: int) -> Path:
        """LoRA 가중치 + optimizer + 상태를 남긴다. 베이스 가중치는 넣지 않는다."""
        import torch

        path = checkpoint_path(self.checkpoint_dir, step, tag=self.tag)
        path.parent.mkdir(parents=True, exist_ok=True)
        module = getattr(self.loss_fn, "module", None)
        torch.save(
            {
                "step": step,
                "state": self.state.to_dict(),
                "lora": lora_state_dict(module) if module is not None else {},
                "optimizer": self.optimizer.state_dict(),
                "settings": self.settings.model_dump(mode="json"),
            },
            path,
        )
        return path

    def load(self, path: Path, *, strict: bool = True) -> TrainState:
        """체크포인트에서 이어받는다."""
        import torch

        payload = torch.load(path, map_location="cpu", weights_only=False)
        self.state = TrainState.from_dict(payload.get("state", {}))
        module = getattr(self.loss_fn, "module", None)
        if module is not None and payload.get("lora"):
            load_lora_state_dict(module, payload["lora"], strict=strict)
        if payload.get("optimizer"):
            self.optimizer.load_state_dict(payload["optimizer"])
        return self.state

    def train(
        self,
        batch_provider: Callable[[int], dict[str, Any]],
        *,
        on_log: Callable[[int, float], None] | None = None,
    ) -> TrainState:
        """`settings.max_steps` 업데이트만큼 돈다. `state.step` 부터 이어서 진행한다."""
        settings = self.settings
        remaining = settings.max_steps - self.state.step
        if remaining <= 0:
            return self.state

        # ⚠️ 루프 안에서 `self.state.step` 을 읽어 오프셋으로 쓰면, 저장할 때 그 값을 갱신하는
        #    순간 이후 스텝 번호가 어긋난다(1 다음이 3 이 된다). 시작점을 미리 고정한다.
        start_step = self.state.step
        accumulated = 0.0
        for micro in iter_micro_steps(remaining, settings.grad_accum_steps):
            step = start_step + micro.global_step
            batch = batch_provider(step)
            loss, _detail = self.loss_fn(batch)
            (loss / settings.grad_accum_steps).backward()
            accumulated += float(loss.detach())

            if not micro.is_update:
                continue

            self.optimizer.step()
            self.optimizer.zero_grad(set_to_none=True)
            mean_loss = accumulated / settings.grad_accum_steps
            accumulated = 0.0
            self.state.step = step
            self.state.samples_seen += settings.batch_size * settings.grad_accum_steps

            if settings.log_every > 0 and step % settings.log_every == 0:
                self.state.loss_history.append(mean_loss)
                if on_log is not None:
                    on_log(step, mean_loss)

            if should_save(step, settings.save_every, settings.max_steps):
                self.save(step)

        self.state.step = settings.max_steps
        return self.state


class Sam3dFlowLoss:
    """실모델 손실 — upstream generator 의 `loss()` 를 그대로 호출한다.

    `REPORT.md` §7 참고. `generator` 는 `pipeline.models["ss_generator"]` 처럼 generator
    래퍼 자체이고, LoRA 는 그 안쪽 `reverse_fn.backbone` 에 붙어 있다(`resolve_backbone`).

    ⚠️ **어떤 손실이 계산되는지는 로드된 generator 클래스가 정한다.** 릴리스 체크포인트의
    `ss_generator` 는 순수 `FlowMatching` 이 아니라 `ShortCut(FlowMatching)` 이고, `loss()` 를
    오버라이드해 flow matching 항과 self-consistency 항을 섞는다. 시그니처가 같아 이 어댑터는
    그대로 동작하지만, 손실 항의 의미를 해석할 때는 그 사실을 알아야 한다. 또한 그 yaml 의
    `loss_weights` 는 `shape: 0` 이라 기본값 그대로면 **형태 항이 학습에 기여하지 않는다** —
    의류 형태를 학습시키려면 가중치를 조정해야 한다(config 판단).

    조건(`cond`)은 `batch["cond_args"]` / `batch["cond_kwargs"]` 로 그대로 전달한다 —
    stage 별로 조건 규약이 달라서 여기서 해석하지 않는다.
    """

    name = "sam3d"

    def __init__(self, generator: Any, backbone: Any) -> None:
        self.generator = generator
        #: LoRA 부착/체크포인트 대상. `SftTrainer.save()` 가 이 속성을 본다.
        self.module = backbone

    def parameters(self) -> Iterable[Any]:
        return self.module.parameters()

    def __call__(self, batch: dict[str, Any]) -> tuple[Any, dict[str, float]]:
        args = batch.get("cond_args", ())
        kwargs = batch.get("cond_kwargs", {})
        total, detail = self.generator.loss(batch["x1"], *args, **kwargs)
        return total, {k: float(v) for k, v in (detail or {}).items()}


def prepare_lora_model(backbone: Any, lora_settings: LoraSettings) -> tuple[Any, int]:
    """LoRA 부착 + LoRA 만 학습 가능하게. `(모델, 학습 파라미터 수)`."""
    model = attach_lora(backbone, lora_settings)
    return model, mark_only_lora_trainable(model)
