"""Model registry for the model-selection spike.

To swap which candidate a notebook cell exercises, change the ACTIVE_* value below
(or just pass a different dict value straight into loaders.load_*() from a cell) —
that's the whole "swap mechanism".
"""

# --- Feature 2 (라이브 댓글 관리): 실시간 경량 분류기 ---
# 라벨셋이 모델마다 다름 — kor_unsmile은 10라벨 multi-label/sigmoid,
# kcelectra_bad_sentence는 2라벨 single-label/softmax. loaders.py에서
# model.config.problem_type으로 분기 처리.
CLASSIFIER_MODELS = {
    "kor_unsmile": "smilegate-ai/kor_unsmile",
    "kcelectra_bad_sentence": "JminJ/kcElectra_base_Bad_Sentence_Classifier",
}
ACTIVE_CLASSIFIER = "kor_unsmile"  # <- 여기 키만 바꾸면 스왑

# --- Feature 2(비실시간 경로) + Feature 3(재정렬): kanana-1.5-instruct 계열 ---
GENERATIVE_MODELS = {
    "kanana-2.1b": "kakaocorp/kanana-1.5-2.1b-instruct-2505",
    "kanana-8b": "kakaocorp/kanana-1.5-8b-instruct-2505",  # 무거움(~16GB+), 수동 실행 전용
}
ACTIVE_GENERATIVE = "kanana-2.1b"  # <- 여기 키만 바꾸면 스왑

# --- Feature 3 (추천 알고리즘): 임베딩 모델 ---
EMBEDDING_MODELS = {
    "kanana-nano-embedding": "kakaocorp/kanana-nano-2.1b-embedding",  # loaders.load_kanana_embedding() 사용
    "bge-m3": "BAAI/bge-m3",  # loaders.load_bge_m3() 사용 — 다른 라이브러리
}
ACTIVE_EMBEDDING = "kanana-nano-embedding"  # <- 여기 키만 바꾸면 스왑

# 인기 기반 랭킹(popularity ranking)은 모델이 아닌 단순 카운트 로직이라
# 여기 레지스트리 대상이 아님 — recommendation.ipynb 마지막 마크다운 셀 참고.

# --- Feature 2 (라이브 댓글 관리): 의도 분류 게이트 (정상/악성/반복질문) ---
# 반복질문 여부를 위한 라벨링 데이터가 아직 없어(Notion "라이브 댓글 관리 — 분산 Agent
# 아키텍처 설계" 문서 "필요 데이터" 참고) 둘 다 zero-shot/규칙 기반 후보다.
# 라벨 데이터가 쌓이면 전용 다중클래스 헤드 파인튜닝으로 교체 검토.
INTENT_STRATEGIES = {
    "kor_unsmile_plus_rule": "kor_unsmile로 악성 판정 + 규칙 기반(물음표/키워드)으로 반복질문 후보 탐지. 추가 모델 로딩 없음, 가장 빠름.",
    "kanana_zero_shot": "kanana-1.5-instruct 프롬프트로 정상/악성/반복질문 3-way 분류. 생성 모델 1회 호출이라 상대적으로 느림.",
}
ACTIVE_INTENT = "kor_unsmile_plus_rule"  # <- 여기 키만 바꾸면 스왑 (chat_agent.py에서 사용)
