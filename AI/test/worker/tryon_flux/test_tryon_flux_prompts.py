"""worn-reference 생성 프롬프트 조립 검증(-567).

인물이 사이즈별로 확대되는 프레이밍 버그(`AI/docs/tryon-advancement-strategy.md` §10.3)와
하의 색상이 부수적으로 바뀌는 문제(§10.5 "다음 단계")에 대한 보존 지시문이 실제로 프롬프트에
들어가는지만 본다 — 프롬프트 문구가 모델 출력을 100% 강제하진 않으므로(소프트 제약), 여기서는
"문구가 빠지지 않았는지"까지만 보장한다.
"""

from tryon_flux.prompts import build_dress_prompt, build_regular_dress_prompt, fit_descriptor


def test_dress_prompt는_프레이밍_보존_문구를_포함한다():
    prompt = build_dress_prompt(
        "a black wide-brim nylon bucket hat", "fitting comfortably in a regular fit", False
    )

    assert "do not zoom in" in prompt
    assert "framing" in prompt


def test_dress_prompt는_하의_색상_유지_문구를_포함한다():
    prompt = build_dress_prompt(
        "a black wide-brim nylon bucket hat", "fitting comfortably in a regular fit", False
    )

    assert "pants" in prompt
    assert "exactly the same color" in prompt


def test_regular_dress_prompt도_보존_문구를_포함한다():
    prompt = build_regular_dress_prompt("a dark navy denim jacket")

    assert "do not zoom in" in prompt
    assert "exactly the same color" in prompt


def test_강조가_필요한_극단_핏은_emphasis_문구가_먼저_온다():
    fit_phrase, needs_emphasis = fit_descriptor(0.60)
    prompt = build_dress_prompt("a dark navy denim jacket", fit_phrase, needs_emphasis)

    assert prompt.startswith("IMPORTANT:")
    assert "skin-tight" in prompt
