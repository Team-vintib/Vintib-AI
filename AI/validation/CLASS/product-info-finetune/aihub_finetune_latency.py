"""last-N/LoRA 파인튜닝된 backbone과 원본(zero-shot) backbone의 실제 forward 지연시간을
잰다 — 모델 두 개를 따로 배포하기로 한 결정이 지연시간 기준(브리핑: CPU p50 ≤200ms)을
넘기지 않는지 확인한다.

브리핑의 123ms 기준선(`product-info-check/latency.py`)은 원본 zero-shot backbone
기준이었다. 지금은 카테고리·색상을 **모델 두 개**로 서빙하기로 했으니, 순차로 두 번
돌렸을 때 합산 시간이 실제로 얼마인지 재야 한다. `product-info-check`의 모델 레지스트리는
안 건드리고(다른 스파이크 폴더 파일) 이 폴더에 독립 스크립트로 둔다 — 파인튜닝
체크포인트를 곧바로 불러와 쓸 수 있다.

기본은 **CPU**로 잰다 — 원래 123ms 기준선도 CPU였고 실제 배포 기준도 CPU라 비교
가능해야 한다(`--device cuda`로 바꿀 수는 있음).

`--sample-image`를 주면 랜덤 텐서가 아니라 **실제 이미지 1장**으로 디코드(PIL)+전처리
(`aihub_preprocess.render_variant`)+backbone forward를 전부 포함한 진짜 end-to-end
지연시간도 잰다 — 이게 없으면 backbone forward(14~17ms)만 재고 실제 병목인 이미지
디코드는 빠진 숫자다. 두 모델을 다 주면 디코드를 한 번만 하고 공유하는 "합산" 숫자도
같이 나온다(실제 배포에서 같은 이미지를 두 번 디코드할 이유가 없어서).

사용법:
    python aihub_finetune_latency.py \\
        --last-n-checkpoint artifacts_finetune/vit_last4_category_.../checkpoint.pt \\
        --unfreeze-layers 4 \\
        --lora-checkpoint artifacts_finetune/lora_r16_a32_..._warm/checkpoint.pt \\
        --r 16 --alpha 32 \\
        --sample-image ../product-info-check/inputs/apc.png
"""

from __future__ import annotations

import argparse
import statistics
import sys
import threading
import time
from pathlib import Path
from typing import Any

import aihub_finetune_vit as vit

DEFAULT_WARMUP = 3
DEFAULT_ITERATIONS = 20
LATENCY_BUDGET_MS = 200.0  # 브리핑 §11 수용 기준(CPU p50)


def compute_stats(latencies_ms: list[float]) -> dict[str, float]:
    """mean/p50/p95를 계산한다. 보간 없이 정렬된 목록에서 인덱스로 집는다
    (`product-info-check/latency.py`의 `LatencyResult.stats()`와 같은 방식)."""
    ordered = sorted(latencies_ms)

    def _percentile(p: float) -> float:
        index = min(len(ordered) - 1, int(len(ordered) * p))
        return ordered[index]

    return {
        "mean": statistics.mean(latencies_ms),
        "p50": _percentile(0.50),
        "p95": _percentile(0.95),
        "n": float(len(latencies_ms)),
    }


def load_original(model_id: str, device: str) -> Any:
    import aihub_embed

    model, processor = aihub_embed.load_model(model_id, device)
    return model, processor


def load_last_n(
    model_id: str, unfreeze_layers: int, checkpoint_path: Path | None, device: str
) -> Any:
    import torch

    model = vit.load_model(model_id, unfreeze_layers, device)
    if checkpoint_path is not None:
        checkpoint = torch.load(checkpoint_path, map_location=device)
        compatible = vit.drop_incompatible_keys(checkpoint["backbone_state_dict"], model)
        model.load_state_dict(compatible, strict=False)
    model.eval()
    return model


def load_lora(
    model_id: str,
    r: int,
    alpha: int,
    dropout: float,
    target_modules: tuple[str, ...],
    checkpoint_path: Path | None,
    device: str,
) -> Any:
    import torch

    import aihub_finetune_lora as lora

    model = lora.load_model(model_id, r, alpha, dropout, target_modules, device)
    if checkpoint_path is not None:
        checkpoint = torch.load(checkpoint_path, map_location=device)
        compatible = vit.drop_incompatible_keys(checkpoint["backbone_state_dict"], model)
        model.load_state_dict(compatible, strict=False)
    model.eval()
    return model


def benchmark_forward(
    model: Any, device: str, *, warmup: int, iterations: int, batch_size: int = 1
) -> dict[str, float]:
    """단일 모델의 `get_image_features()` forward 시간만 잰다(이미지 디코드 제외 —
    파인튜닝 여부에 따라 달라지는 건 backbone 연산량뿐이라 이 부분만 격리한다)."""
    import torch

    pixel_values = torch.randn(batch_size, 3, 224, 224, device=device)
    with torch.no_grad():
        for _ in range(warmup):
            model.get_image_features(pixel_values=pixel_values)
        latencies = []
        for _ in range(iterations):
            start = time.perf_counter()
            model.get_image_features(pixel_values=pixel_values)
            latencies.append((time.perf_counter() - start) * 1000)
    return compute_stats(latencies)


def benchmark_sequential(
    models: list[Any], device: str, *, warmup: int, iterations: int
) -> dict[str, float]:
    """모델 여러 개를 **순서대로** 다 돌렸을 때 걸리는 총 시간 — 모델 두 개 배포의
    실제 비용이다."""
    import torch

    pixel_values = torch.randn(1, 3, 224, 224, device=device)
    with torch.no_grad():
        for _ in range(warmup):
            for model in models:
                model.get_image_features(pixel_values=pixel_values)
        latencies = []
        for _ in range(iterations):
            start = time.perf_counter()
            for model in models:
                model.get_image_features(pixel_values=pixel_values)
            latencies.append((time.perf_counter() - start) * 1000)
    return compute_stats(latencies)


def benchmark_threaded(
    models: list[Any], device: str, *, warmup: int, iterations: int
) -> dict[str, float]:
    """CPU에서 torch 연산이 계산 중 GIL을 놓아준다는 점을 이용해, 스레드로 동시에
    돌리면 순차 실행보다 빨라지는지 확인한다(코어 여유가 있을 때만 유효)."""
    import torch

    pixel_values = torch.randn(1, 3, 224, 224, device=device)

    def _forward(model: Any) -> None:
        with torch.no_grad():
            model.get_image_features(pixel_values=pixel_values)

    def _run_once() -> float:
        threads = [threading.Thread(target=_forward, args=(model,)) for model in models]
        start = time.perf_counter()
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return (time.perf_counter() - start) * 1000

    for _ in range(warmup):
        _run_once()
    latencies = [_run_once() for _ in range(iterations)]
    return compute_stats(latencies)


def benchmark_end_to_end(
    model: Any, processor: Any, image_path: Path, device: str, *, warmup: int, iterations: int
) -> dict[str, float]:
    """실제 이미지 파일에서 **디코드 → 전처리 → backbone forward**까지 전부 포함해 잰다.

    `benchmark_forward()`는 랜덤 텐서라 PIL 디코드가 빠져 있다 — 이 프로젝트에서 이미
    확인했듯(STEP3) 진짜 병목은 그쪽이다. 헤드/zero-shot 마지막 단계(행렬곱 1회)는
    무시할 수준이라 안 잰다.
    """
    import torch
    from PIL import Image

    import aihub_preprocess

    def _once() -> float:
        start = time.perf_counter()
        with Image.open(image_path) as image:
            prepared = aihub_preprocess.render_variant(image, None, "raw")
        inputs = processor(images=[prepared], return_tensors="pt")
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.no_grad():
            model.get_image_features(**inputs)
        return (time.perf_counter() - start) * 1000

    for _ in range(warmup):
        _once()
    latencies = [_once() for _ in range(iterations)]
    return compute_stats(latencies)


def benchmark_end_to_end_combined(
    models: list[Any],
    processor: Any,
    image_path: Path,
    device: str,
    *,
    warmup: int,
    iterations: int,
) -> dict[str, float]:
    """디코드+전처리는 **한 번만** 하고(두 모델이 같은 처리된 텐서를 공유), 그 뒤 각
    backbone forward만 순서대로 돌린다 — 실제 배포에서 이미지를 두 번 디코드할 이유가
    없으니, 이게 "모델 두 개 배포"의 진짜 end-to-end 비용이다.
    """
    import torch
    from PIL import Image

    import aihub_preprocess

    def _once() -> float:
        start = time.perf_counter()
        with Image.open(image_path) as image:
            prepared = aihub_preprocess.render_variant(image, None, "raw")
        inputs = processor(images=[prepared], return_tensors="pt")
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.no_grad():
            for model in models:
                model.get_image_features(**inputs)
        return (time.perf_counter() - start) * 1000

    for _ in range(warmup):
        _once()
    latencies = [_once() for _ in range(iterations)]
    return compute_stats(latencies)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="last-N/LoRA 파인튜닝 backbone의 forward 지연시간을 원본과 비교 실측"
    )
    parser.add_argument("--model-id", default=vit.DEFAULT_MODEL_ID)
    parser.add_argument("--last-n-checkpoint", type=Path, default=None)
    parser.add_argument("--unfreeze-layers", type=int, default=4)
    parser.add_argument("--lora-checkpoint", type=Path, default=None)
    parser.add_argument("--r", type=int, default=16)
    parser.add_argument("--alpha", type=int, default=32)
    parser.add_argument("--dropout", type=float, default=0.05)
    parser.add_argument("--target-modules", nargs="*", default=["q_proj", "v_proj"])
    parser.add_argument(
        "--device", default="cpu", help="기본 CPU — 원래 123ms 기준선도 CPU였다"
    )
    parser.add_argument("--warmup", type=int, default=DEFAULT_WARMUP)
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument(
        "--sample-image",
        type=Path,
        default=None,
        help="실제 이미지 1장 경로 — 주면 디코드+전처리 포함 진짜 end-to-end 지연시간도 잰다",
    )
    args = parser.parse_args(argv)

    print(f"device={args.device} warmup={args.warmup} iterations={args.iterations}\n")

    original, processor = load_original(args.model_id, args.device)
    original_stats = benchmark_forward(
        original, args.device, warmup=args.warmup, iterations=args.iterations
    )
    print(
        f"원본(zero-shot) backbone       : "
        f"p50={original_stats['p50']:.1f}ms p95={original_stats['p95']:.1f}ms"
    )

    models_to_combine: list[Any] = []
    labeled_models: list[tuple[str, Any]] = []

    if args.last_n_checkpoint is not None:
        last_n = load_last_n(
            args.model_id, args.unfreeze_layers, args.last_n_checkpoint, args.device
        )
        last_n_stats = benchmark_forward(
            last_n, args.device, warmup=args.warmup, iterations=args.iterations
        )
        print(
            f"last-N={args.unfreeze_layers} backbone             : "
            f"p50={last_n_stats['p50']:.1f}ms p95={last_n_stats['p95']:.1f}ms"
        )
        models_to_combine.append(last_n)
        labeled_models.append((f"last-N={args.unfreeze_layers}", last_n))

    if args.lora_checkpoint is not None:
        lora_model = load_lora(
            args.model_id,
            args.r,
            args.alpha,
            args.dropout,
            tuple(args.target_modules),
            args.lora_checkpoint,
            args.device,
        )
        lora_stats = benchmark_forward(
            lora_model, args.device, warmup=args.warmup, iterations=args.iterations
        )
        print(
            f"LoRA r={args.r} backbone               : "
            f"p50={lora_stats['p50']:.1f}ms p95={lora_stats['p95']:.1f}ms"
        )
        models_to_combine.append(lora_model)
        labeled_models.append((f"LoRA r={args.r}", lora_model))

    if len(models_to_combine) == 2:
        seq_stats = benchmark_sequential(
            models_to_combine, args.device, warmup=args.warmup, iterations=args.iterations
        )
        print(
            f"\n순차 실행(두 모델 합산)         : "
            f"p50={seq_stats['p50']:.1f}ms p95={seq_stats['p95']:.1f}ms"
        )

        thread_stats = benchmark_threaded(
            models_to_combine, args.device, warmup=args.warmup, iterations=args.iterations
        )
        print(
            f"스레드 동시 실행(CPU 병렬 시도)  : "
            f"p50={thread_stats['p50']:.1f}ms p95={thread_stats['p95']:.1f}ms"
        )

        seq_verdict = "통과" if seq_stats["p50"] <= LATENCY_BUDGET_MS else "초과"
        thread_verdict = "통과" if thread_stats["p50"] <= LATENCY_BUDGET_MS else "초과"
        print(
            f"\n(참고) 브리핑 §11 기준(≤{LATENCY_BUDGET_MS:.0f}ms) 대비: "
            f"순차={seq_verdict}, 스레드={thread_verdict}"
        )
    else:
        print(
            "\n(--last-n-checkpoint와 --lora-checkpoint를 둘 다 줘야 순차/스레드 비교가 나온다)",
            file=sys.stderr,
        )

    if args.sample_image is not None:
        print(f"\n--- end-to-end(실제 이미지 1장: {args.sample_image.name}) ---")

        original_e2e = benchmark_end_to_end(
            original,
            processor,
            args.sample_image,
            args.device,
            warmup=args.warmup,
            iterations=args.iterations,
        )
        print(
            f"원본(zero-shot) end-to-end     : "
            f"p50={original_e2e['p50']:.1f}ms p95={original_e2e['p95']:.1f}ms"
        )

        for label, model in labeled_models:
            model_e2e = benchmark_end_to_end(
                model,
                processor,
                args.sample_image,
                args.device,
                warmup=args.warmup,
                iterations=args.iterations,
            )
            print(
                f"{label} end-to-end{' ' * max(0, 15 - len(label))}: "
                f"p50={model_e2e['p50']:.1f}ms p95={model_e2e['p95']:.1f}ms"
            )

        if len(models_to_combine) == 2:
            combined_e2e = benchmark_end_to_end_combined(
                models_to_combine,
                processor,
                args.sample_image,
                args.device,
                warmup=args.warmup,
                iterations=args.iterations,
            )
            print(
                f"\n두 모델 합산 end-to-end(디코드 1회 공유): "
                f"p50={combined_e2e['p50']:.1f}ms p95={combined_e2e['p95']:.1f}ms"
            )
            combined_verdict = "통과" if combined_e2e["p50"] <= LATENCY_BUDGET_MS else "초과"
            print(f"(참고) 브리핑 §11 기준(≤{LATENCY_BUDGET_MS:.0f}ms) 대비: {combined_verdict}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
