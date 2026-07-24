"""
CatVTON 파인튜닝 스크립트

CatVTON의 "Concatenation is All You Need" 접근을 따른다:
- person(agnostic) 이미지와 garment 이미지를 공간적으로 이어붙여 하나의 입력으로 구성
- 텍스트 인코더는 사용하지 않음 (CatVTON은 text-free)
- 전체 UNet을 학습하지 않고, self-attention 레이어만 파라미터 효율적으로 학습
  (원 논문 기준 전체 899M 중 49.57M만 학습)
- Loss는 garment(마스크) 영역에 대해서만 계산

범위 안내:
- 본 스크립트는 "학습 코드" 자체에 집중한다. 실제 데이터셋(인물+의류+정답 시착
  이미지 쌍)의 수집·정리는 별도 작업이며 이 스크립트의 범위 밖이다.
- data_root 아래에 person/cloth/agnostic/agnostic_mask 4개 폴더가 이미
  준비되어 있다고 가정하고, train/val 분리와 학습 루프만 담당한다.
- train/val 분리는 --val_ratio, --split_seed로 제어하며, 고정 시드를 쓰므로
  동일 데이터셋에 대해 항상 같은 분리 결과를 재현할 수 있다.

사용 전 준비물:
- 데이터셋: (person_image, cloth_image, mask_image) 등 CatVTONFinetuneDataset
  docstring에 명시된 폴더 구조로 이미 정리되어 있어야 함
- base checkpoint: booksforcharlie/stable-diffusion-inpainting (기존 추론 스크립트와 동일)

실행 예:
python train_catvton.py \
    --data_root /path/to/dataset \
    --output_dir ./checkpoints/catvton_vintage_ft \
    --base_ckpt booksforcharlie/stable-diffusion-inpainting \
    --resume_attn_ckpt zhengchong/CatVTON \
    --resolution 768 1024 \
    --val_ratio 0.1 \
    --split_seed 42 \
    --batch_size 2 \
    --num_epochs 20 \
    --learning_rate 1e-5 \
    --mixed_precision bf16
"""

import argparse
import os
import random
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import numpy as np
from tqdm import tqdm

from diffusers import AutoencoderKL, UNet2DConditionModel, DDIMScheduler
from diffusers.optimization import get_scheduler
from huggingface_hub import snapshot_download
from accelerate import Accelerator
from accelerate.utils import ProjectConfiguration


# =========================================================
# 0. 데이터셋
# =========================================================

class CatVTONFinetuneDataset(Dataset):
    """
    데이터 디렉토리 구조 (VITON-HD 스타일을 가정):

    data_root/
      person/          # 사람이 옷을 입은 정답 이미지 (학습 타겟)
      cloth/            # 그 옷의 단독 상품 이미지 (조건 입력)
      agnostic/         # 옷 영역이 제거된 사람 이미지 (조건 입력)
      agnostic_mask/    # 옷 agnostic 마스크 (흑백, 옷 영역=흰색)

    네 폴더의 파일명이 서로 대응(같은 stem)해야 한다.

    ---
    데이터셋 수집/정리는 본 스크립트의 범위 밖이다. 아래 두 경로 중 하나로
    이미 준비된 데이터를 가리키기만 하면 된다:
      - VITON-HD/DressCode 등 공개 데이터셋을 위 구조로 변환한 경로
      - 자체 수집한 빈티지 의류 데이터를 동일 구조로 정리한 경로
    """

    def __init__(
        self,
        data_root: str,
        height: int = 1024,
        width: int = 768,
        split: str = "train",
        val_ratio: float = 0.1,
        split_seed: int = 42,
    ):
        assert split in ("train", "val", "all"), f"split은 train/val/all 중 하나여야 합니다: {split}"

        self.data_root = Path(data_root)
        self.height = height
        self.width = width
        self.split = split

        self.person_dir = self.data_root / "person"
        self.cloth_dir = self.data_root / "cloth"
        self.agnostic_dir = self.data_root / "agnostic"
        self.mask_dir = self.data_root / "agnostic_mask"

        all_filenames = sorted(
            [f.stem for f in self.person_dir.glob("*.jpg")]
            + [f.stem for f in self.person_dir.glob("*.png")]
        )
        if len(all_filenames) == 0:
            raise ValueError(
                f"{self.person_dir} 에서 이미지를 찾지 못했습니다. "
                f"데이터 경로와 폴더 구조를 확인하세요. "
                f"(본 스크립트는 데이터셋이 이미 위 구조로 준비되어 있다고 가정합니다.)"
            )

        self.filenames = self._split_filenames(all_filenames, split, val_ratio, split_seed)
        print(f"[INFO] split='{split}': {len(self.filenames)}개 샘플 "
              f"(전체 {len(all_filenames)}개 중)")

    @staticmethod
    def _split_filenames(filenames, split, val_ratio, seed):
        """
        파일명 리스트를 고정 시드로 셔플한 뒤 train/val로 분리한다.
        같은 seed를 쓰면 매 실행마다 동일한 분리 결과가 나와, 재현성이 보장된다.
        """
        if split == "all":
            return filenames

        rng = random.Random(seed)
        shuffled = filenames.copy()
        rng.shuffle(shuffled)

        num_val = max(1, int(len(shuffled) * val_ratio))
        val_files = set(shuffled[:num_val])

        if split == "val":
            return sorted(val_files)
        else:  # train
            return sorted([f for f in shuffled if f not in val_files])

    def __len__(self):
        return len(self.filenames)

    def _load_rgb(self, path_no_ext: Path) -> Image.Image:
        for ext in (".jpg", ".jpeg", ".png"):
            p = path_no_ext.with_suffix(ext)
            if p.exists():
                return Image.open(p).convert("RGB")
        raise FileNotFoundError(f"{path_no_ext} 관련 이미지 파일을 찾을 수 없습니다.")

    def _load_mask(self, path_no_ext: Path) -> Image.Image:
        for ext in (".jpg", ".jpeg", ".png"):
            p = path_no_ext.with_suffix(ext)
            if p.exists():
                return Image.open(p).convert("L")
        raise FileNotFoundError(f"{path_no_ext} 관련 마스크 파일을 찾을 수 없습니다.")

    def __getitem__(self, idx):
        stem = self.filenames[idx]

        person = self._load_rgb(self.person_dir / stem)
        cloth = self._load_rgb(self.cloth_dir / stem)
        agnostic = self._load_rgb(self.agnostic_dir / stem)
        mask = self._load_mask(self.mask_dir / stem)

        person = person.resize((self.width, self.height))
        cloth = cloth.resize((self.width, self.height))
        agnostic = agnostic.resize((self.width, self.height))
        mask = mask.resize((self.width, self.height))

        def to_tensor(img, is_mask=False):
            arr = np.array(img).astype(np.float32)
            if is_mask:
                arr = arr / 255.0
                arr = torch.from_numpy(arr).unsqueeze(0)  # (1, H, W)
            else:
                arr = arr / 127.5 - 1.0  # [-1, 1]
                arr = torch.from_numpy(arr).permute(2, 0, 1)  # (3, H, W)
            return arr

        return {
            "person": to_tensor(person),
            "cloth": to_tensor(cloth),
            "agnostic": to_tensor(agnostic),
            "mask": to_tensor(mask, is_mask=True),
        }


# =========================================================
# 1. 학습 가능한 파라미터 선택 (self-attention만)
# =========================================================

def freeze_unet_except_self_attention(unet: UNet2DConditionModel):
    """
    CatVTON 원 논문의 파라미터 효율적 학습 방식을 재현한다.
    self-attention(attn1) 계열 레이어만 학습 가능하게 열고, 나머지는 동결.
    """
    trainable_params = []
    for name, param in unet.named_parameters():
        if "attn1" in name:  # self-attention 레이어만 학습
            param.requires_grad = True
            trainable_params.append(param)
        else:
            param.requires_grad = False

    total = sum(p.numel() for p in unet.parameters())
    trainable = sum(p.numel() for p in trainable_params)
    print(f"[INFO] 전체 파라미터: {total / 1e6:.2f}M, 학습 파라미터: {trainable / 1e6:.2f}M "
          f"({100 * trainable / total:.2f}%)")

    return trainable_params


def compute_batch_loss(batch, unet, vae, noise_scheduler, weight_dtype, device):
    """
    한 배치에 대해 CatVTON 방식(concatenation)의 diffusion loss를 계산한다.
    train/validation 양쪽에서 동일하게 재사용한다.
    """
    person = batch["person"].to(device, dtype=weight_dtype)
    cloth = batch["cloth"].to(device, dtype=weight_dtype)
    agnostic = batch["agnostic"].to(device, dtype=weight_dtype)
    mask = batch["mask"].to(device, dtype=weight_dtype)

    with torch.no_grad():
        person_latents = vae.encode(person).latent_dist.sample() * vae.config.scaling_factor
        agnostic_latents = vae.encode(agnostic).latent_dist.sample() * vae.config.scaling_factor
        cloth_latents = vae.encode(cloth).latent_dist.sample() * vae.config.scaling_factor

        condition_latents = torch.cat([agnostic_latents, cloth_latents], dim=3)
        target_latents = torch.cat([person_latents, cloth_latents], dim=3)

        mask_latent = F.interpolate(mask, size=agnostic_latents.shape[-2:], mode="nearest")
        mask_cat = torch.cat([mask_latent, torch.zeros_like(mask_latent)], dim=3)

    noise = torch.randn_like(target_latents)
    bsz = target_latents.shape[0]
    timesteps = torch.randint(
        0, noise_scheduler.config.num_train_timesteps, (bsz,), device=target_latents.device
    ).long()
    noisy_latents = noise_scheduler.add_noise(target_latents, noise, timesteps)

    unet_input = torch.cat([noisy_latents, mask_cat, condition_latents], dim=1)

    encoder_hidden_states = torch.zeros(
        (bsz, 1, unet.config.cross_attention_dim), device=device, dtype=weight_dtype
    )

    model_pred = unet(unet_input, timesteps, encoder_hidden_states).sample

    half_width = model_pred.shape[3] // 2
    pred_person_region = model_pred[:, :, :, :half_width]
    noise_person_region = noise[:, :, :, :half_width]

    loss = F.mse_loss(
        pred_person_region.float() * mask_latent,
        noise_person_region.float() * mask_latent,
        reduction="mean",
    )
    return loss


@torch.no_grad()
def run_validation(unet, vae, noise_scheduler, val_dataloader, weight_dtype, accelerator):
    """검증 세트 전체에 대한 평균 loss를 계산한다."""
    unet.eval()
    total_loss = 0.0
    num_batches = 0

    for batch in val_dataloader:
        loss = compute_batch_loss(
            batch, unet, vae, noise_scheduler, weight_dtype, accelerator.device
        )
        total_loss += loss.item()
        num_batches += 1

    unet.train()
    return total_loss / max(1, num_batches)


# =========================================================
# 2. 메인 학습 루프
# =========================================================

def parse_args():
    parser = argparse.ArgumentParser(description="CatVTON 빈티지 의류 도메인 파인튜닝")

    parser.add_argument("--data_root", type=str, required=True,
                         help="person/cloth/agnostic/agnostic_mask 하위 폴더를 담은 데이터 루트")
    parser.add_argument("--output_dir", type=str, default="./checkpoints/catvton_vintage_ft")
    parser.add_argument("--base_ckpt", type=str,
                         default="booksforcharlie/stable-diffusion-inpainting")
    parser.add_argument("--resume_attn_ckpt", type=str, default="zhengchong/CatVTON",
                         help="파인튜닝 시작점으로 사용할 기존 CatVTON attention 가중치")

    parser.add_argument("--resolution", type=int, nargs=2, default=[768, 1024],
                         metavar=("WIDTH", "HEIGHT"))
    parser.add_argument("--val_ratio", type=float, default=0.1,
                         help="검증 세트로 뗄 비율 (0.1 = 10%%)")
    parser.add_argument("--split_seed", type=int, default=42,
                         help="train/val 분리 시 사용할 고정 시드 (재현성 보장)")
    parser.add_argument("--validate_every_n_epochs", type=int, default=1)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--num_epochs", type=int, default=20)
    parser.add_argument("--learning_rate", type=float, default=1e-5)
    parser.add_argument("--lr_scheduler", type=str, default="constant_with_warmup")
    parser.add_argument("--lr_warmup_steps", type=int, default=500)
    parser.add_argument("--gradient_accumulation_steps", type=int, default=4)
    parser.add_argument("--mixed_precision", type=str, default="bf16",
                         choices=["no", "fp16", "bf16"])
    parser.add_argument("--save_every_n_epochs", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dataloader_num_workers", type=int, default=4)

    return parser.parse_args()


def main():
    args = parse_args()
    width, height = args.resolution

    random.seed(args.seed)
    torch.manual_seed(args.seed)

    os.makedirs(args.output_dir, exist_ok=True)

    accelerator_project_config = ProjectConfiguration(
        project_dir=args.output_dir, logging_dir=os.path.join(args.output_dir, "logs")
    )
    accelerator = Accelerator(
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        mixed_precision=args.mixed_precision,
        project_config=accelerator_project_config,
    )

    weight_dtype = torch.float32
    if args.mixed_precision == "fp16":
        weight_dtype = torch.float16
    elif args.mixed_precision == "bf16":
        weight_dtype = torch.bfloat16

    # ---- 모델 로드 ----
    print("[INFO] 베이스 모델 로드 중...")
    vae = AutoencoderKL.from_pretrained(args.base_ckpt, subfolder="vae")
    unet = UNet2DConditionModel.from_pretrained(args.base_ckpt, subfolder="unet")
    noise_scheduler = DDIMScheduler.from_pretrained(args.base_ckpt, subfolder="scheduler")

    # ---- 기존 CatVTON attention 가중치로 초기화 (있으면 이어서 학습, 없으면 스킵) ----
    if args.resume_attn_ckpt:
        print(f"[INFO] 기존 CatVTON attention 가중치 로드: {args.resume_attn_ckpt}")
        attn_ckpt_path = snapshot_download(repo_id=args.resume_attn_ckpt)
        # attention 관련 state_dict만 필터링해서 로드 (파일 구조는 리포에 따라 다를 수 있음,
        # 실제 파일명은 huggingface repo 확인 후 조정 필요)
        mix_ckpt = os.path.join(attn_ckpt_path, "mix-48k-1024", "attention", "model.safetensors")
        if os.path.exists(mix_ckpt):
            from safetensors.torch import load_file
            attn_state_dict = load_file(mix_ckpt)
            missing, unexpected = unet.load_state_dict(attn_state_dict, strict=False)
            print(f"[INFO] attention 가중치 로드 완료 (missing={len(missing)}, "
                  f"unexpected={len(unexpected)})")
        else:
            print(f"[WARNING] {mix_ckpt} 를 찾지 못해 attention 사전학습 가중치 없이 진행합니다. "
                  f"실제 파일 경로를 huggingface.co/{args.resume_attn_ckpt} 에서 확인하세요.")

    vae.requires_grad_(False)
    trainable_params = freeze_unet_except_self_attention(unet)

    vae.to(accelerator.device, dtype=weight_dtype)

    # ---- 데이터셋 (train/val 분리) ----
    train_dataset = CatVTONFinetuneDataset(
        args.data_root, height=height, width=width,
        split="train", val_ratio=args.val_ratio, split_seed=args.split_seed,
    )
    val_dataset = CatVTONFinetuneDataset(
        args.data_root, height=height, width=width,
        split="val", val_ratio=args.val_ratio, split_seed=args.split_seed,
    )

    train_dataloader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.dataloader_num_workers,
    )
    val_dataloader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.dataloader_num_workers,
    )
    print(f"[INFO] 학습 샘플 수: {len(train_dataset)}, 검증 샘플 수: {len(val_dataset)}")

    # ---- 옵티마이저 & 스케줄러 ----
    optimizer = torch.optim.AdamW(trainable_params, lr=args.learning_rate)

    num_update_steps_per_epoch = len(train_dataloader) // args.gradient_accumulation_steps
    max_train_steps = args.num_epochs * num_update_steps_per_epoch

    lr_scheduler = get_scheduler(
        args.lr_scheduler,
        optimizer=optimizer,
        num_warmup_steps=args.lr_warmup_steps,
        num_training_steps=max_train_steps,
    )

    unet, optimizer, train_dataloader, val_dataloader, lr_scheduler = accelerator.prepare(
        unet, optimizer, train_dataloader, val_dataloader, lr_scheduler
    )

    # ---- 학습 루프 ----
    global_step = 0
    progress_bar = tqdm(range(max_train_steps), desc="Training", disable=not accelerator.is_local_main_process)

    for epoch in range(args.num_epochs):
        unet.train()
        epoch_loss = 0.0

        for batch in train_dataloader:
            with accelerator.accumulate(unet):
                loss = compute_batch_loss(
                    batch, unet, vae, noise_scheduler, weight_dtype, accelerator.device
                )

                accelerator.backward(loss)
                if accelerator.sync_gradients:
                    accelerator.clip_grad_norm_(trainable_params, 1.0)
                optimizer.step()
                lr_scheduler.step()
                optimizer.zero_grad()

            if accelerator.sync_gradients:
                progress_bar.update(1)
                global_step += 1
                epoch_loss += loss.detach().item()

        avg_loss = epoch_loss / max(1, len(train_dataloader))

        log_msg = f"[Epoch {epoch+1}/{args.num_epochs}] train_loss={avg_loss:.4f}"

        if (epoch + 1) % args.validate_every_n_epochs == 0 and len(val_dataset) > 0:
            val_loss = run_validation(unet, vae, noise_scheduler, val_dataloader, weight_dtype, accelerator)
            log_msg += f", val_loss={val_loss:.4f}"

        accelerator.print(log_msg)

        if accelerator.is_main_process and (epoch + 1) % args.save_every_n_epochs == 0:
            save_path = os.path.join(args.output_dir, f"epoch_{epoch+1}")
            os.makedirs(save_path, exist_ok=True)
            unwrapped_unet = accelerator.unwrap_model(unet)

            # self-attention 레이어만 저장 (파라미터 효율적 체크포인트)
            attn_state_dict = {
                k: v for k, v in unwrapped_unet.state_dict().items() if "attn1" in k
            }
            torch.save(attn_state_dict, os.path.join(save_path, "attention_weights.pt"))
            accelerator.print(f"[INFO] 체크포인트 저장: {save_path}")

    accelerator.print("[INFO] 학습 완료.")


if __name__ == "__main__":
    main()
