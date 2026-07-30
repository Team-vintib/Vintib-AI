"""CLI — `python -m garment3d.cli <subcommand>`.

모든 서브커맨드가 `--config` 와 `--set key.path=value` 를 받는다. **데이터·백엔드 전환은
코드 수정 없이 여기로만 한다.**

```bash
python -m garment3d.cli smoke                       # 더미 엔드투엔드
python -m garment3d.cli preprocess --dummy 3        # 전처리만
python -m garment3d.cli sft --set sft.max_steps=2   # LoRA SFT (torch 필요)
python -m garment3d.cli dpo --set dpo.max_steps=2   # DPO   (torch 필요)
python -m garment3d.cli audit                       # 데이터 감독 가능성 점검
```
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Config, parse_overrides
from .contracts import GarmentSampleIndex, audit_sample
from .data import make_dummy_index, verify_index
from .pipeline import run_smoke
from .preprocess import preprocess_index, summarize


def _load_config(args: argparse.Namespace) -> Config:
    config = Config.from_yaml(args.config) if args.config else Config()
    if args.set:
        config = config.merged(parse_overrides(args.set))
    return config


def _load_index(config: Config, dummy: int | None, work_dir: Path) -> GarmentSampleIndex:
    """실인덱스가 지정돼 있으면 그걸, 아니면 더미를 만든다.

    **데이터 주입 지점**: `paths.sample_index` 가 설정되는 순간 더미 경로는 안 쓰인다.
    """
    paths = config.paths.expanded()
    if paths.sample_index is not None:
        return GarmentSampleIndex.from_jsonl(paths.sample_index, root=paths.data_root)
    count = dummy if dummy is not None else 2
    return make_dummy_index(work_dir / "data", count=count)


def cmd_audit(args: argparse.Namespace) -> int:
    """샘플별로 어떤 감독이 가능한지 + 파일 실재 여부를 찍는다."""
    config = _load_config(args)
    index = _load_index(config, args.dummy, Path(args.work_dir))
    slat = config.preprocess.latent_encoder == "sam3d_slat"

    missing = verify_index(index)
    for sample in index.resolved():
        availability = audit_sample(sample, slat_encoder_available=slat)
        flags = "".join(
            [
                "G" if availability.geometry else "-",
                "L" if availability.layout else "-",
                "T" if availability.texture else "-",
            ]
        )
        print(f"{sample.sample_id:<24} [{flags}] {' / '.join(availability.notes) or 'ok'}")
    if missing:
        print("\n없는 파일:")
        for sample_id, paths in missing.items():
            print(f"  {sample_id}: {paths}")
    print("\n범례: G=geometry L=layout T=texture")
    return 1 if missing else 0


def cmd_preprocess(args: argparse.Namespace) -> int:
    config = _load_config(args)
    index = _load_index(config, args.dummy, Path(args.work_dir))
    results = preprocess_index(index.resolved(), config, write_cache=not args.no_cache)
    print(json.dumps(summarize(results), ensure_ascii=False, indent=2))
    for entry in results:
        status = "ok" if entry.ok else "FAIL"
        print(f"  [{status}] {entry.sample_id}: {' / '.join(entry.reasons) or '-'}")
    return 0 if all(entry.ok for entry in results) else 1


def cmd_smoke(args: argparse.Namespace) -> int:
    config = _load_config(args)
    result = run_smoke(
        config,
        work_dir=Path(args.work_dir),
        num_samples=args.dummy or 2,
        write_media=args.write_media,
    )
    print(json.dumps(result.preprocess_summary, ensure_ascii=False, indent=2))
    print(json.dumps(result.aggregate, ensure_ascii=False, indent=2))
    for note in result.notes:
        print(f"  note: {note}")
    print(f"리포트: {result.report_markdown} / {result.report_html}")
    return 0


def cmd_sft(args: argparse.Namespace) -> int:
    """더미 flow 모듈에 LoRA 를 붙여 SFT 를 돌린다. torch/peft 가 필요하다."""
    config = _load_config(args)
    try:
        import torch
    except ImportError:
        print("torch 가 없습니다 — requirements.txt 를 설치하세요.", file=sys.stderr)
        return 2

    from .train.dummy_flow import DummyFlowLoss, build_dummy_flow_module
    from .train.sft import SftTrainer, prepare_lora_model

    module = build_dummy_flow_module(device=config.sft.device)
    model, trainable = prepare_lora_model(module, config.lora)
    print(f"학습 파라미터 {trainable:,}개 (LoRA only)")

    loss_fn = DummyFlowLoss(model, seed=config.sft.seed)
    trainer = SftTrainer(loss_fn, config.sft, config.paths.expanded().checkpoint_dir)
    if config.sft.resume is not None:
        state = trainer.load(config.sft.resume)
        print(f"resume: step {state.step}")

    generator = torch.Generator().manual_seed(config.sft.seed)

    def provider(_step: int) -> dict:
        return {"x1": torch.randn(config.sft.batch_size, 8, 16, generator=generator)}

    state = trainer.train(provider, on_log=lambda s, v: print(f"  step {s} loss {v:.5f}"))
    print(f"완료: step={state.step} samples={state.samples_seen}")
    return 0


def cmd_dpo(args: argparse.Namespace) -> int:
    """더미 후보로 선호쌍을 만들고 DPO 를 돌린다. torch 가 필요하다."""
    config = _load_config(args)
    try:
        import torch
    except ImportError:
        print("torch 가 없습니다 — requirements.txt 를 설치하세요.", file=sys.stderr)
        return 2

    from copy import deepcopy

    from .train.dpo import (
        DeterministicScorer,
        DpoTrainer,
        DummyCandidateGenerator,
        build_preference_pairs,
        collect_candidates,
    )
    from .train.dummy_flow import DummyFlowLoss, build_dummy_flow_module
    from .train.sft import prepare_lora_model

    work_dir = Path(args.work_dir)
    candidates = collect_candidates(
        "dummy_000",
        DummyCandidateGenerator(),
        DeterministicScorer(),
        config.dpo.num_candidates,
        work_dir / "candidates",
    )
    pairs = build_preference_pairs(
        candidates, min_margin=config.dpo.min_margin, scorer=DeterministicScorer().name
    )
    print(f"선호쌍 {len(pairs)}개 (margin>={config.dpo.min_margin})")
    if not pairs:
        print("쌍이 없어 학습을 건너뜁니다 — min_margin 을 낮추거나 후보를 늘리세요.")
        return 1

    module = build_dummy_flow_module(device=config.dpo.device)
    policy, trainable = prepare_lora_model(module, config.lora)
    # 참조모델은 **LoRA 부착 직후**의 복사본이다. lora_B 가 0 초기화라 이 시점의 출력은 베이스와
    # 같으므로 "SFT 시작점 = 참조" 규약이 성립한다. 실전에서 SFT 체크포인트로 시작한다면 그
    # 가중치를 로드한 뒤 복사해야 한다 — 그러지 않으면 참조가 베이스가 되어 β 해석이 달라진다.
    reference = deepcopy(module)
    for param in reference.parameters():
        param.requires_grad = False
    print(f"학습 파라미터 {trainable:,}개")

    policy_loss = DummyFlowLoss(policy, seed=config.dpo.seed)
    ref_loss = DummyFlowLoss(reference, seed=config.dpo.seed)

    trainer = DpoTrainer(
        policy_loss,
        ref_loss,
        config.dpo,
        config.paths.expanded().checkpoint_dir,
        trainable_params=policy.parameters(),
    )
    generator = torch.Generator().manual_seed(config.dpo.seed)

    def provider(_step: int):
        chosen = {"x1": torch.randn(config.dpo.batch_size, 8, 16, generator=generator)}
        rejected = {"x1": torch.randn(config.dpo.batch_size, 8, 16, generator=generator)}
        return chosen, rejected

    state = trainer.train(
        provider, module=policy, on_log=lambda s, v: print(f"  step {s} loss {v:.5f}")
    )
    print(f"완료: step={state.step}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="garment3d", description=__doc__)
    parser.add_argument("--config", type=Path, default=None, help="yaml config 경로")
    parser.add_argument(
        "--set", action="append", default=[], metavar="KEY=VALUE", help="config 오버라이드"
    )
    parser.add_argument("--work-dir", default="artifacts/work", help="더미 데이터·중간 산출물 루트")
    parser.add_argument("--dummy", type=int, default=None, help="더미 샘플 개수")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("audit", help="샘플별 감독 가능성 점검").set_defaults(func=cmd_audit)

    preprocess = sub.add_parser("preprocess", help="mesh → occupancy → latent")
    preprocess.add_argument("--no-cache", action="store_true", help="디스크에 쓰지 않는다")
    preprocess.set_defaults(func=cmd_preprocess)

    smoke = sub.add_parser("smoke", help="더미 엔드투엔드 (전처리→렌더→I2V→평가→리포트)")
    smoke.add_argument("--write-media", action="store_true", help="PNG/GIF 도 저장")
    smoke.set_defaults(func=cmd_smoke)

    sub.add_parser("sft", help="LoRA SFT (torch 필요)").set_defaults(func=cmd_sft)
    sub.add_parser("dpo", help="DPO (torch 필요)").set_defaults(func=cmd_dpo)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
