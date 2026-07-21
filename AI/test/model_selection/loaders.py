"""Shared model-loading helpers for the model-selection spike notebooks.

Throwaway/spike code for AI/test/model_selection/ — NOT production code.
Exists only so comment_moderation.ipynb and recommendation.ipynb don't each
duplicate the kanana-1.5-instruct loading logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch
from transformers import (
    AutoModel,
    AutoModelForCausalLM,
    AutoModelForSequenceClassification,
    AutoTokenizer,
)


def select_device() -> str:
    """Best available device on this machine. Dev laptop is Windows + RTX 4070: cuda > mps > cpu."""
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def select_dtype(device: str) -> torch.dtype:
    """bf16 on accelerators (matches how the kanana checkpoints ship); fp32 on plain
    cpu, since fp16/bf16 matmul support on plain CPU is inconsistent/slow."""
    if device in ("mps", "cuda"):
        return torch.bfloat16
    return torch.float32


@dataclass
class ClassifierBundle:
    name: str
    tokenizer: Any
    model: Any
    device: str


def load_sequence_classifier(model_id: str) -> ClassifierBundle:
    """Load a fine-tuned classifier (kor_unsmile / kcElectra bad-sentence). No training involved."""
    device = select_device()
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForSequenceClassification.from_pretrained(model_id).to(device)
    model.eval()
    return ClassifierBundle(name=model_id, tokenizer=tokenizer, model=model, device=device)


@dataclass
class CausalLMBundle:
    name: str
    tokenizer: Any
    model: Any
    device: str


def load_causal_lm(model_id: str) -> CausalLMBundle:
    """Load a kanana-1.5-instruct-family model for zero-shot prompting (no fine-tuning)."""
    device = select_device()
    dtype = select_dtype(device)
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    try:
        model = AutoModelForCausalLM.from_pretrained(model_id, dtype=dtype)
    except TypeError:
        # Older transformers versions use `torch_dtype=` instead of `dtype=`.
        model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=dtype)
    model = model.to(device)
    model.eval()
    return CausalLMBundle(name=model_id, tokenizer=tokenizer, model=model, device=device)


def generate_chat(bundle: CausalLMBundle, user_message: str, max_new_tokens: int = 200) -> str:
    """Single-turn generation through the kanana chat template. Shared by both notebooks —
    comment moderation prompts it directly, recommendation re-ranking reuses this unchanged."""
    messages = [{"role": "user", "content": user_message}]
    inputs = bundle.tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(bundle.model.device)
    with torch.no_grad():
        outputs = bundle.model.generate(**inputs, max_new_tokens=max_new_tokens)
    new_tokens = outputs[0][inputs["input_ids"].shape[-1] :]
    return bundle.tokenizer.decode(new_tokens, skip_special_tokens=True)


@dataclass
class EmbeddingBundle:
    name: str
    model: Any
    device: str


def load_kanana_embedding(model_id: str) -> EmbeddingBundle:
    """kakaocorp/kanana-nano-2.1b-embedding ships custom modeling code (Kanana2Vec),
    so trust_remote_code=True is required — this executes code from the model repo,
    that's expected/accepted for this spike."""
    device = select_device()
    model = AutoModel.from_pretrained(model_id, trust_remote_code=True).to(device)
    return EmbeddingBundle(name=model_id, model=model, device=device)


def load_bge_m3(model_id: str):
    """BAAI/bge-m3 uses a different library (FlagEmbedding), not plain transformers —
    kept as its own function rather than forced into the transformers-shaped bundles above."""
    from FlagEmbedding import BGEM3FlagModel

    device = select_device()
    use_fp16 = device == "cuda"  # fp16 mainly pays off on CUDA; skip on cpu/mps
    return BGEM3FlagModel(model_id, use_fp16=use_fp16, device=device)
