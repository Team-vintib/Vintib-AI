"""더미 flow matching 모듈 — 스모크 테스트용 최소 대체물.

**목적**: 수 GB 체크포인트 없이 학습 루프(옵티마이저·누적·체크포인트·resume·LoRA 부착)를
끝까지 돌려 보는 것. 모델 품질은 목적이 아니다.

보간식은 upstream `FlowMatching` 을 **그대로 따랐다**
(`generator/flow_matching/model.py:116-127`):

- `x_t = (1 - (1 - σ_min)·t)·x0 + t·x1`   (eq. 22)
- `target = x1 - (1 - σ_min)·x0`          (eq. 23)

그래서 스모크가 통과한다는 게 "실모델에서도 같은 형태로 호출된다"는 최소 근거가 된다.
실모델을 쓸 때는 이 클래스 대신 `Sam3dFlowLoss` 가 upstream `loss()` 를 직접 부른다.
"""

from __future__ import annotations

from typing import Any


def build_dummy_flow_module(
    in_channels: int = 8,
    hidden_channels: int = 16,
    *,
    device: str = "cpu",
) -> Any:
    """`to_qkv`/`to_out` 이름의 `nn.Linear` 를 가진 최소 모듈.

    이름을 실모델과 맞춘 이유는 **LoRA 타깃 설정을 그대로 시험할 수 있게** 하기 위함이다
    (`configs/garment_lora.yaml` 의 `target_modules` 를 바꾸지 않고 스모크가 돈다).
    """
    import torch
    from torch import nn

    class TinyAttention(nn.Module):
        """이름만 실모델 규약을 따른 self-attention 흉내. dense 텐서만 다룬다."""

        def __init__(self, channels: int) -> None:
            super().__init__()
            self.to_qkv = nn.Linear(channels, channels * 3)
            self.to_out = nn.Linear(channels, channels)

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            qkv = self.to_qkv(x)
            q, k, v = qkv.chunk(3, dim=-1)
            attn = torch.softmax(q @ k.transpose(-1, -2) / (q.shape[-1] ** 0.5), dim=-1)
            return self.to_out(attn @ v)

    class TinyFlowBackbone(nn.Module):
        """`(B, C, N)` latent 를 받아 같은 형태의 velocity 를 예측한다."""

        def __init__(self) -> None:
            super().__init__()
            self.proj_in = nn.Linear(in_channels, hidden_channels)
            self.t_embed = nn.Linear(1, hidden_channels)
            self.attn = TinyAttention(hidden_channels)
            self.proj_out = nn.Linear(hidden_channels, in_channels)

        def forward(
            self, x: "torch.Tensor", t: "torch.Tensor", cond: "torch.Tensor | None" = None
        ) -> "torch.Tensor":
            # (B, C, N) -> (B, N, C)
            h = self.proj_in(x.transpose(1, 2))
            h = h + self.t_embed(t.reshape(-1, 1).to(h.dtype))[:, None, :]
            if cond is not None:
                h = h + cond.mean(dim=1, keepdim=True).to(h.dtype)[..., : h.shape[-1]]
            h = h + self.attn(h)
            return self.proj_out(h).transpose(1, 2)

    return TinyFlowBackbone().to(device)


class DummyFlowLoss:
    """`(loss, detail)` 을 돌려주는 flow matching 손실. upstream 보간식과 동일.

    `FlowLossFn` 프로토콜을 만족하므로 `SftTrainer` 가 실모델과 구분 없이 쓴다.

    ⚠️ **DPO 에서 쓸 때 주의**: `t`/`x0` 를 인스턴스 전용 generator 로 뽑으므로, 정책과
    참조모델에 **같은 seed** 를 주고 **같은 순서**로 호출해야 두 모델이 동일한 `x_t` 를 본다.
    그게 어긋나면 손실 차가 모델 차이가 아니라 노이즈 차이가 되고 DPO 신호가 망가진다.
    `DpoTrainer.step_loss` 가 (chosen, rejected) 순서를 양쪽에 동일하게 적용한다.
    """

    name = "dummy"

    def __init__(self, module: Any, *, sigma_min: float = 0.0, seed: int = 0) -> None:
        self.module = module
        self.sigma_min = sigma_min
        import torch

        self._generator = torch.Generator(device="cpu").manual_seed(seed)

    def parameters(self):
        return self.module.parameters()

    def __call__(self, batch: dict[str, Any]) -> tuple[Any, dict[str, float]]:
        """`batch["x1"]` = 타깃 latent `(B, C, N)`, `batch["cond"]` = 조건(optional)."""
        import torch

        x1 = batch["x1"]
        cond = batch.get("cond")
        batch_size = x1.shape[0]

        t = torch.rand(batch_size, generator=self._generator).to(x1.device)
        x0 = torch.randn(x1.shape, generator=self._generator).to(x1.device)

        tb = t.reshape(-1, *([1] * (x1.ndim - 1)))
        x_t = (1 - (1 - self.sigma_min) * tb) * x0 + tb * x1
        target = x1 - (1 - self.sigma_min) * x0

        prediction = self.module(x_t, t, cond)
        loss = torch.nn.functional.mse_loss(prediction, target)
        return loss, {"flow_matching_loss": float(loss.detach())}
