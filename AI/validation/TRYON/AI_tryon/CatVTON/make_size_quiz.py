"""팀원용 "사이즈 맞히기" 퀴즈 이미지를 만든다.

4명(철수/영희/둘리/마이콜) 각각의 M/L/XL/2XL 청바지 결과를 랜덤 순서로 섞어서 한 줄로
나열한 퀴즈 이미지를 만든다 -- 사진에는 위치 번호(1~4)만 붙고 실제 사이즈는 안 보인다.
정답은 별도 텍스트 파일에만 적는다.

영희는 최종 수정본(size_fit_alpha3_jeans_fitaware_younghee_20260804_130809, 셔츠 색/
blur_factor/기장 버그 다 고친 버전)을, 나머지 세 명은 그 전 배치(size_fit_alpha3_
jeans_fitaware_20260804_113209)를 그대로 쓴다.
"""

import random

from PIL import Image, ImageDraw, ImageFont

SIZES = ["M", "L", "XL", "2XL"]
SOURCES = {
    "younghee": "result/size_fit_alpha3_jeans_fitaware_younghee_20260804_130809",
    "cheolsu": "result/size_fit_alpha3_jeans_fitaware_20260804_113209",
    "dooly": "result/size_fit_alpha3_jeans_fitaware_20260804_113209",
    "maikol": "result/size_fit_alpha3_jeans_fitaware_20260804_113209",
}

OUT_DIR = "result/size_quiz_20260804"
THUMB = (300, 400)
LABEL_H = 50

random.seed()  # 매 실행 랜덤 -- 정답은 아래에서 바로 기록하니 재현성 필요 없음

answer_lines = ["# 사이즈 퀴즈 정답지\n"]

for person, src_dir in SOURCES.items():
    order = SIZES.copy()
    random.shuffle(order)

    combo = Image.new("RGB", (THUMB[0] * 4, THUMB[1] + LABEL_H), "white")
    draw = ImageDraw.Draw(combo)
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except OSError:
        font = ImageFont.load_default()

    for i, size in enumerate(order):
        img = Image.open(f"{src_dir}/tryon_{person}_{size}.png").convert("RGB")
        img = img.resize(THUMB)
        x = i * THUMB[0]
        combo.paste(img, (x, LABEL_H))
        label = str(i + 1)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        draw.text((x + THUMB[0] // 2 - tw // 2, 8), label, fill="black", font=font)

    out_path = f"{OUT_DIR}/quiz_{person}.png"
    combo.save(out_path)
    print(f"완료 -> {out_path} (순서: {order})")

    answer_lines.append(f"## {person}")
    for i, size in enumerate(order):
        answer_lines.append(f"- {i + 1}번 -> {size}")
    answer_lines.append("")

with open(f"{OUT_DIR}/answers.md", "w", encoding="utf-8") as f:
    f.write("\n".join(answer_lines))
print(f"\n정답지 -> {OUT_DIR}/answers.md")
