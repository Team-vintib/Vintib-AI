"""라이브 댓글 관리 백엔드 레지스트리 — 분류기 스왑 지점 + 평가 파이프라인 설정.

`test/model_selection/model_registry.py`의 프로덕션판. `ACTIVE_*` 키 하나만 바꾸면 구현이
교체된다. `test/` 코드를 프로덕션에서 import하지 않는 규약에 따라 모델 ID는 여기서 재선언한다
(`app/recommend/pipeline/embed_catalog.py` 선례).

**`EMBEDDER_BACKENDS`/`RETRIEVER_BACKENDS`는 이제 평가 파이프라인 전용이다**
(`app/chat/evaluation.py`, `test/chat/test_chat_evaluation.py`, `S15P11A108-196`). 실제 반복질문
답변 생성은 `chat_rag` 워커(`worker/chat_rag_worker_example.py`)가 처리하고, 게이트웨이는
`app/chat/rag_store.py`로 문서만 오가므로 여기 값을 참조하지 않는다(`S15P11A108-444`). 생성
쪽 스왑 지점(`GENERATOR_BACKENDS`)은 그래서 삭제했다 — 워커 코드 자체가 그 역할을 한다.

**임계치를 백엔드별로 묶어 둔 이유**: `chat_agent.ipynb` 5.3의 결론이
"임베딩 모델마다 코사인 유사도 스케일이 달라 0.8 같은 고정 임계치를 모델 무관하게 재사용하면
안 된다"였다. 그래서 클러스터링/그라운딩 임계치는 전역 상수가 아니라 `EMBEDDER_BACKENDS[key]`
안에 함께 둔다 — 임베더를 갈아끼우면 임계치도 같이 따라온다.

설계: .claude/plans/ai/003-live-comment-moderation-prototype.md
"""

from typing import TypedDict

# --- 1차 필터: 악성(욕설/혐오) 분류기 -------------------------------------
# 값은 HF 모델 ID. rule_based는 모델이 필요 없어 None이다(CI에서 그대로 동작).
CLASSIFIER_BACKENDS: dict[str, str | None] = {
    "rule_based": None,  # 기본 — 사전 + 우회패턴 정규화. 의존성 없음
    # 아래는 classifier_benchmark.ipynb(210건) 실측 결과 기준 후보.
    "kcelectra_base_hate": "beomi/beep-KcELECTRA-base-hate",  # acc 99.5%, 악성 recall 98.8%
    "kor_unsmile": "smilegate-ai/kor_unsmile",  # 기존 baseline, 악성 recall 58.3%
}
ACTIVE_CLASSIFIER = "kcelectra_base_hate"  # <- 여기 키만 바꾸면 스왑(CH030, rule_based recall 16.7%가 너무 낮아 교체)


class EmbedderConfig(TypedDict):
    """임베더 한 종류의 모델 ID + 그 모델 기준으로 잡은 임계치."""

    model_id: str | None
    cluster_similarity: float  # B-2: 같은 질문으로 묶을 코사인 하한
    grounding_threshold: float  # B-3: 이 밑이면 근거 부족으로 무응답


# 참고값 — 노션 `[AI] 반복질문 판정 정책 기준`(LAB-8)의 제안치.
# 특정 임베딩 모델을 전제하지 않은 값이라 그대로 쓰지 않고, 백엔드별 실측치로 대체한다.
POLICY_CLUSTER_SIMILARITY = 0.8
POLICY_GROUNDING_THRESHOLD = 0.35

EMBEDDER_BACKENDS: dict[str, EmbedderConfig] = {
    # 기본 — 문자 bigram 해싱 기반 결정적 임베딩. torch 불필요, CI에서 그대로 검증된다.
    # 아래 두 값은 목업 세트 실측으로 잡았다(tests/test_chat_faq.py가 이 분리를 고정한다):
    #   cluster 0.30 — 같은 질문 패러프레이즈 최저 0.308 vs 다른 질문 최고 0.224
    #   grounding 0.35 — 지식베이스에 있는 질문 0.52~0.85 vs 없는 질문 최고 0.334
    # 알려진 한계: 어휘가 거의 안 겹치는 표현("재고 남았나요?" ↔ "재고 아직 남아 있나요?" = 0.330)은
    # 근거가 있는데도 무응답으로 떨어진다. bigram 어휘 매칭의 구조적 한계라 실임베더 전환 시 해소된다.
    "mock_bigram": {
        "model_id": None,
        "cluster_similarity": 0.30,
        "grounding_threshold": 0.35,
    },
    # 실모델 후보. 채택 시 반드시 해당 모델 기준으로 임계치를 다시 스윕해야 한다.
    # kanana_nano(카카오)는 배제하기로 결정됨(S15P11A108-444) — kure_v1만 후보로 남긴다.
    "kure_v1": {
        "model_id": "nlpai-lab/KURE-v1",
        "cluster_similarity": 0.65,  # ipynb 5.3: 0.60~0.70에서 precision/recall 1.0
        "grounding_threshold": POLICY_GROUNDING_THRESHOLD,  # 미검증 — CHAT-003에서 확정
    },
}
ACTIVE_EMBEDDER = "mock_bigram"  # <- 여기 키만 바꾸면 스왑

# --- 반복질문 RAG 검색: 평가 파이프라인 전용(모듈 docstring 참고) ----------
RETRIEVER_BACKENDS: dict[str, str] = {
    "mock": "목업 FAQ JSON + 결정적 bigram 임베딩 코사인 검색",
}
ACTIVE_RETRIEVER = "mock"  # <- 여기 키만 바꾸면 스왑(평가용)

# --- 스팸 탐지 상태 저장소 -------------------------------------------------
STATE_STORE_BACKENDS: dict[str, str] = {
    "memory": "프로세스 인메모리 슬라이딩 윈도우 (단일 워커 전용)",
    "redis": "Redis 공유 상태 (미구현 — S15P11A108-188, 다중 워커 필수)",
}
ACTIVE_STATE_STORE = "memory"  # <- 여기 키만 바꾸면 스왑

# --- 판정 임계치 (모델과 무관한 규칙 파라미터) -----------------------------
# "5초에 6개"로 조정(-571 후속) — "10초에 10개"는 도배 판정이 너무 느슨해서(초당 1개
# 페이스로 계속 쳐도 안 걸림) 실사용 테스트에서 사실상 무제한처럼 느껴졌다. 그렇다고
# 예전 "4개"로 되돌리면 반복질문 테스트하려고 같은 문구를 빠르게 3번만 보내도(근접중복
# 2개 이상) 도배로 막혀서 테스트 자체가 안 됐던 문제가 재발한다 — 그 중간값으로 잡았다.
SPAM_WINDOW_SECONDS = 5.0  # 슬라이딩 윈도우 길이
SPAM_MAX_MESSAGES = 6  # 윈도우 내 이 개수 이상이면 도배
SPAM_SIMILARITY = 0.85  # 근접중복 판정 하한(SequenceMatcher ratio)
SPAM_DUPLICATE_COUNT = (
    6  # 윈도우 내 근접중복이 이 개수 이상이면 도배 — 위와 같은 이유로 동일하게 맞춤
)
ABUSE_THRESHOLD = 0.5  # 악성 판정 하한

# --- 반복 위반 시 임시 채팅 차단(-571 후속, CH025) --------------------------
# 방송(live_id) 단위로 격리한다 — 채팅 자체가 방송 단위 공간이라 다른 방송 위반과 섞이면 안 됨.
TIMEOUT_VIOLATION_WINDOW_SECONDS = 10.0  # 이 안에서 반복 위반해야 카운트된다
TIMEOUT_VIOLATION_THRESHOLD = 3  # 윈도우 내 이 횟수 이상 차단되면 음소거
TIMEOUT_MUTE_SECONDS = 15.0  # 음소거 지속 시간

MIN_CLUSTER_SIZE = 2  # 같은 질문이 이 횟수 이상 들어와야 답변 생성

# 같은 클러스터라도 이 시간이 지나면 다시 답변을 생성한다(CH025 후속). 방송이 오래 가면
# 나중에 들어온 시청자는 예전 답변을 못 봤을 텐데, "이미 답변됨"으로 영영 무응답이면 안
# 된다는 판단(사용자 확인) — 그렇다고 매 메시지마다 다시 생성하면 같은 질문 폭주 한 번에
# 워커가 계속 재생성을 반복하므로, 쿨다운으로 재생성 빈도를 제한한다.
ANSWER_COOLDOWN_SECONDS = 300.0
RETRIEVE_TOP_K = 3  # 평가 파이프라인(MockRetriever) 전용 — 이미 순위 매겨진 결과 중 상위 k개.

# chat_rag 워커에 넘길 후보 문서 개수 상한(app/chat/rag_store.fetch_documents의 limit).
# RETRIEVE_TOP_K와 의미가 다르다 — 이건 "순위 매겨진 결과"가 아니라 "워커가 랭킹을 매길
# 재료" 전체다. 너무 작게 잡으면(예: 3) 방송 초반에 한 번만 언급된 정보(사이즈 등)가 이후
# STT 문서가 쌓이면서 "최근 N개" 밖으로 밀려나 영영 근거로 못 쓰인다(S15P11A108-444 실측으로
# 발견). 방송 하나당 문서 수가 원래 많지 않다고 가정하고 설계했으니(워커 인메모리 랭킹의
# 전제) 넉넉하게 잡는다 — 그래도 무제한은 아니게 상한은 둔다.
CHAT_RAG_CANDIDATE_LIMIT = 200


def embedder_config(key: str | None = None) -> EmbedderConfig:
    """활성 임베더의 설정(모델 ID + 임계치)을 돌려준다."""
    resolved = key or ACTIVE_EMBEDDER
    try:
        return EMBEDDER_BACKENDS[resolved]
    except KeyError as exc:
        raise ValueError(f"등록되지 않은 임베더 백엔드입니다: {resolved!r}") from exc
