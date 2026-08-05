"""DPO 스캐폴드 — best-of-N 후보 → 선호쌍 → DPO 학습 루프.

**채택한 정식화**: flow/diffusion 모델에는 토큰 로그확률이 없으므로 Diffusion-DPO 계열의
*암묵적 보상*을 쓴다 — 정책과 참조모델의 **denoising 손실 차**를 로그확률 비 대신 넣는다.

```
z = -β · [ (L_policy(chosen) - L_ref(chosen)) - (L_policy(rejected) - L_ref(rejected)) ]
loss = -log σ(z)
```

부호 규약이 핵심이다: 여기서 `L` 은 **손실**이라 작을수록 좋다. chosen 의 손실이
(참조 대비) 더 줄어들면 `z` 가 커지고 loss 가 줄어든다. `dpo_logits()` 한 함수에 그 부호를
모아 두고 numpy/torch 양쪽이 같은 함수를 쓴다 — 부호를 두 군데 적으면 반드시 어긋난다.

참조모델은 **LoRA 어댑터를 끈 같은 베이스**를 쓰는 것을 전제한다(별도 가중치 복제 불필요).
그 스위칭은 호출자가 `ref_loss_fn` 으로 주입한다 — peft 버전별 API 차이를 여기 묶지 않기 위함.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol, Sequence

from ..config import DpoConfig
from ..contracts import PreferencePair
from .sft import TrainState, checkpoint_path, iter_micro_steps, should_save


@dataclass(frozen=True)
class Candidate:
    """best-of-N 후보 한 건. 산출물 자체가 아니라 **경로와 점수만** 담는다."""

    sample_id: str
    index: int
    path: Path
    score: float

    def __post_init__(self) -> None:
        if self.score != self.score:  # NaN
            raise ValueError(f"후보 {self.sample_id}#{self.index} 의 점수가 NaN 입니다")


class CandidateGenerator(Protocol):
    """샘플 하나에서 N 개 후보를 만든다. 실구현은 SAM 3D 추론을 N 번 돌린다."""

    name: str

    def generate(self, sample_id: str, num_candidates: int, out_dir: Path) -> list[Path]: ...


class CandidateScorer(Protocol):
    """후보를 점수화한다. **높을수록 좋다.**"""

    name: str

    def score(self, path: Path) -> float: ...


class DummyCandidateGenerator:
    """빈 파일 N 개를 만드는 더미. 파이프라인 배관 확인 전용."""

    name = "dummy"

    def generate(self, sample_id: str, num_candidates: int, out_dir: Path) -> list[Path]:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        for i in range(num_candidates):
            path = out_dir / f"{sample_id}_cand{i:02d}.txt"
            path.write_text(f"{sample_id}#{i}\n", encoding="utf-8")
            paths.append(path)
        return paths


class DeterministicScorer:
    """경로 문자열 해시로 점수를 매기는 더미 스코어러. 재현 가능한 순위를 준다."""

    name = "deterministic_hash"

    def score(self, path: Path) -> float:
        import hashlib

        digest = hashlib.sha256(str(Path(path).name).encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "little") / 0xFFFFFFFF


def collect_candidates(
    sample_id: str,
    generator: CandidateGenerator,
    scorer: CandidateScorer,
    num_candidates: int,
    out_dir: Path,
) -> list[Candidate]:
    """후보를 만들고 점수를 매겨 **점수 내림차순**으로 돌려준다."""
    if num_candidates < 2:
        raise ValueError(f"선호쌍을 만들려면 후보가 2개 이상 필요합니다: {num_candidates}")
    paths = generator.generate(sample_id, num_candidates, out_dir)
    candidates = [
        Candidate(sample_id=sample_id, index=i, path=Path(p), score=scorer.score(p))
        for i, p in enumerate(paths)
    ]
    return sorted(candidates, key=lambda c: c.score, reverse=True)


def build_preference_pairs(
    candidates: Sequence[Candidate],
    *,
    min_margin: float = 0.0,
    scorer: str = "unknown",
    strategy: str = "extremes",
) -> list[PreferencePair]:
    """후보 목록에서 선호쌍을 만든다. **순수 로직 — torch 없이 테스트된다.**

    Args:
        strategy:
            - `extremes`: 최고 vs 최저 한 쌍만. 신호가 가장 뚜렷하고 쌍 수가 적다(기본).
            - `best_vs_rest`: 최고 vs 나머지 전부. 쌍이 N-1 개로 늘어난다.
        min_margin: 점수 차가 이보다 작은 쌍은 버린다. 스코어러 노이즈가 선호로 학습되는 걸 막는다.
    """
    if len(candidates) < 2:
        return []
    ordered = sorted(candidates, key=lambda c: c.score, reverse=True)
    best = ordered[0]

    if strategy == "extremes":
        losers: Iterable[Candidate] = [ordered[-1]]
    elif strategy == "best_vs_rest":
        losers = ordered[1:]
    else:
        raise ValueError(f"알 수 없는 strategy: {strategy!r}")

    pairs = []
    for loser in losers:
        if best.score - loser.score < min_margin:
            continue
        pairs.append(
            PreferencePair(
                sample_id=best.sample_id,
                chosen_path=best.path,
                rejected_path=loser.path,
                chosen_score=best.score,
                rejected_score=loser.score,
                scorer=scorer,
            )
        )
    return pairs


def dpo_logits(
    policy_chosen: Any,
    policy_rejected: Any,
    ref_chosen: Any,
    ref_rejected: Any,
    beta: float,
) -> Any:
    """DPO 로짓 `z`. **부호 규약이 여기 한 곳에만 있다.**

    입력은 **손실**(작을수록 좋음)이다. float 이든 torch 텐서든 같은 산술로 동작한다.
    """
    return -beta * ((policy_chosen - ref_chosen) - (policy_rejected - ref_rejected))


def flow_dpo_loss(
    policy_chosen: Any,
    policy_rejected: Any,
    ref_chosen: Any,
    ref_rejected: Any,
    beta: float,
) -> Any:
    """`-log σ(z)`. torch 텐서를 받는다."""
    import torch

    z = dpo_logits(policy_chosen, policy_rejected, ref_chosen, ref_rejected, beta)
    return -torch.nn.functional.logsigmoid(z)


class DpoTrainer:
    """DPO 학습 루프. `SftTrainer` 와 같은 체크포인트·스텝 규약을 쓴다.

    `policy_loss_fn` / `ref_loss_fn` 은 `(batch) -> (loss, detail)` 이다. 참조모델은 LoRA 를
    끈 같은 모듈이어야 하며, **그래디언트가 흐르지 않아야 한다**(`ref_loss_fn` 안에서
    `torch.no_grad()` 를 쓰거나 결과를 detach 해야 한다). 이 클래스는 그걸 강제하지 않고
    `_detach()` 로 한 번 더 끊는다 — 실수로 참조모델까지 학습되는 사고가 가장 비싸다.
    """

    def __init__(
        self,
        policy_loss_fn: Callable[[dict[str, Any]], tuple[Any, dict[str, float]]],
        ref_loss_fn: Callable[[dict[str, Any]], tuple[Any, dict[str, float]]],
        settings: DpoConfig,
        checkpoint_dir: Path,
        *,
        trainable_params: Iterable[Any],
        tag: str = "dpo",
    ) -> None:
        import torch

        self.policy_loss_fn = policy_loss_fn
        self.ref_loss_fn = ref_loss_fn
        self.settings = settings
        self.checkpoint_dir = Path(checkpoint_dir)
        self.tag = tag
        self.state = TrainState()

        torch.manual_seed(settings.seed)
        params = [p for p in trainable_params if p.requires_grad]
        if not params:
            raise RuntimeError("학습 가능한 파라미터가 없습니다 (LoRA 부착 확인)")
        self.optimizer = torch.optim.AdamW(params, lr=settings.learning_rate)

    @staticmethod
    def _detach(value: Any) -> Any:
        return value.detach() if hasattr(value, "detach") else value

    def step_loss(self, chosen_batch: dict[str, Any], rejected_batch: dict[str, Any]) -> Any:
        """한 쌍에 대한 DPO 손실."""
        policy_chosen, _ = self.policy_loss_fn(chosen_batch)
        policy_rejected, _ = self.policy_loss_fn(rejected_batch)
        ref_chosen, _ = self.ref_loss_fn(chosen_batch)
        ref_rejected, _ = self.ref_loss_fn(rejected_batch)
        return flow_dpo_loss(
            policy_chosen,
            policy_rejected,
            self._detach(ref_chosen),
            self._detach(ref_rejected),
            self.settings.beta,
        )

    def save(self, step: int, module: Any | None = None) -> Path:
        import torch

        from .lora import lora_state_dict

        path = checkpoint_path(self.checkpoint_dir, step, tag=self.tag)
        path.parent.mkdir(parents=True, exist_ok=True)
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

    def train(
        self,
        pair_provider: Callable[[int], tuple[dict[str, Any], dict[str, Any]]],
        *,
        module: Any | None = None,
        on_log: Callable[[int, float], None] | None = None,
    ) -> TrainState:
        """`settings.max_steps` 만큼 업데이트한다."""
        settings = self.settings
        remaining = settings.max_steps - self.state.step
        if remaining <= 0:
            return self.state

        # `SftTrainer.train` 과 같은 이유로 시작점을 미리 고정한다(저장 시 state.step 을 갱신하면
        # 이후 스텝 번호가 어긋난다).
        start_step = self.state.step
        for micro in iter_micro_steps(remaining, 1):
            step = start_step + micro.global_step
            chosen_batch, rejected_batch = pair_provider(step)
            loss = self.step_loss(chosen_batch, rejected_batch).mean()
            loss.backward()
            self.optimizer.step()
            self.optimizer.zero_grad(set_to_none=True)

            value = float(loss.detach())
            self.state.step = step
            self.state.loss_history.append(value)
            self.state.samples_seen += settings.batch_size
            if on_log is not None:
                on_log(step, value)

            if should_save(step, settings.save_every, settings.max_steps):
                self.save(step, module)

        self.state.step = settings.max_steps
        return self.state
