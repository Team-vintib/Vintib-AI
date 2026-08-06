import json
import os
import uuid
from datetime import UTC, datetime
from typing import get_args

import aiofiles
import redis
from fastapi import APIRouter, File, Header, HTTPException, Query, UploadFile

from app.chat import rag_store
from app.core.config import settings
from app.gateway.schemas import FeatureType, Job, JobResult, new_job
from app.recommend.personalize import embedding_store

# app.chat.service가 이 모듈의 enqueue_job()을 가져다 쓰므로(순환 import 방지를 위해
# 여기서는 최상단에서 app.chat.service를 import하지 않는다 — 아래 _ingest_chat_rag_result()
# 안에서 지연 import한다).

router = APIRouter()

r = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    password=settings.redis_password or None,
    decode_responses=True,
)

QUEUE_PREFIX = "queue:"
RESULT_PREFIX = "result:"
DEAD_LETTER_KEY = "dead_letter"
RESULT_TTL_SECONDS = 3600
POLL_TIMEOUT_SECONDS = 5
MAX_RETRY = 3

# 워커 생존 신호. 워커가 팀원 노트북이라 항상 떠 있지 않은데, 이게 없으면 BE·FE가
# "처리 중"과 "아무도 안 듣고 있음"을 구별할 수 없다 — job은 둘 다 queued로 보인다.
# poll 할 때마다 갱신하고, poll 주기(최대 5초)의 여유를 둔 값으로 만료시킨다.
WORKER_SEEN_PREFIX = "worker:last_seen:"
WORKER_SEEN_TTL_SECONDS = POLL_TIMEOUT_SECONDS * 6

# S3 권한이 없어서 EC2 로컬 디스크에 저장 → Caddy가 /results/* 로 서빙
RESULTS_DIR = os.getenv("RESULTS_DIR", "/app/results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def _check_worker_key(x_api_key: str | None):
    if not settings.worker_api_key or x_api_key != settings.worker_api_key:
        raise HTTPException(status_code=401, detail="invalid worker api key")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def store_job_result(
    job_id: str,
    status: str,
    *,
    result: dict | None = None,
    error: str | None = None,
    worker_id: str | None = None,
) -> None:
    """`result:{job_id}`에 상태를 기록한다. 모든 상태 전이가 거치는 유일한 지점.

    TTL을 한 곳에서만 관리하려고 뽑아냈다 — 이전에는 같은 `r.set(RESULT_PREFIX...)`가 네 곳에
    흩어져 있었다. `r`을 전역으로 조회하므로 테스트의 `monkeypatch.setattr(gateway_router, "r", ...)`
    가 이 함수를 통과하는 경로에도 그대로 먹는다.
    """
    payload = JobResult(
        job_id=job_id, status=status, result=result, error=error, worker_id=worker_id
    )
    r.set(f"{RESULT_PREFIX}{job_id}", payload.model_dump_json(), ex=RESULT_TTL_SECONDS)


def new_local_job_id() -> str:
    """**큐를 거치지 않는** job을 발급한다 — 이 프로세스가 직접 처리할 작업용.

    `enqueue_job`과 달리 `queue:{feature}`에 넣지 않는다. 가격 책정처럼 워커가 없는 기능은
    큐에 넣어 봐야 아무도 꺼내가지 않고 `/ai/workers/status`의 대기 건수만 부풀린다.

    **`FeatureType`을 쓰지 않는 것도 의도다.** 조회 경로(`GET /ai/jobs/{job_id}`)는
    `result:{job_id}`만 읽고 `JobResult`에는 `type` 필드가 없다 — 폴링 계약은 이미
    feature 와 무관하다. 반대로 `FeatureType`에 항목을 추가하면 워커가 없는 기능이
    `/ai/workers/status`에 영구 오프라인으로 노출되고, `POST /ai/{feature}`·
    `GET /ai/workers/poll`로 고아 job이 만들어질 수 있다.

    설계: .claude/plans/ai/CH003-pricing-service-prototype.md
    """
    job_id = str(uuid.uuid4())
    store_job_result(job_id, "queued")
    return job_id


def _ingest_stt_result(result: dict) -> None:
    """STT 워커 결과(텍스트+임베딩)를 pgvector에 저장한다. 계산은 워커가 이미 끝냈으므로
    여기선 통과만 시킨다(`AI/docs/chat-rag-storage.md`).

    저장 실패가 job 제출 자체를 실패로 만들면 안 된다 — 워커 입장에선 전사는 이미 끝난
    일이라, 저장소 장애 때문에 재시도 루프를 돌게 하지 않는다(다른 도메인의 그라운딩
    실패 처리와 같은 원칙, `app/chat/service.py` 참고).
    """
    try:
        rag_store.save_document(
            live_id=int(result["live_id"]),
            source_type="stt",
            content=result["text"],
            embedding=result.get("embedding"),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[gateway] STT 결과 저장 실패(live_id={result.get('live_id')}): {exc}")


def _ingest_quality_embedding_result(result: dict) -> None:
    """품질검수 워커가 실어 보낸 의류 임베딩(`garment_embedding`)을 pgvector에 upsert한다.

    계산은 워커가 이미 끝냈으므로 여기선 통과만 시킨다(`_ingest_stt_result`와 같은 구조).
    `garment_embedding`이 없으면(mock 백엔드, 의류 미검출, 임베딩 계산 실패) 조용히
    건너뛴다 — 검수 결과 자체는 이 필드 없이도 완결된 응답이다.

    저장 실패가 job 제출 자체를 실패로 만들면 안 된다 — 검수는 이미 끝난 일이라, 저장소
    장애 때문에 재시도 루프를 돌게 하지 않는다(`_ingest_stt_result`와 같은 원칙).
    """
    embedding = result.get("garment_embedding")
    if not embedding:
        return
    try:
        embedding_store.save_garment_embedding(
            product_id=int(result["product_id"]),
            embedding=embedding,
            model_id=result.get("garment_embedding_model_id", "unknown"),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[gateway] 의류 임베딩 저장 실패(product_id={result.get('product_id')}): {exc}")


def _ingest_chat_rag_result(job: Job, result: dict) -> None:
    """`chat_rag` 워커 결과(검색+랭킹+그라운딩+생성을 이미 마친 상태)를 답변 저장소에 반영한다.

    지연 import: `app.chat.service`가 이 모듈의 `enqueue_job()`을 top-level에서 import하므로,
    여기서 `app.chat.service`를 top-level에서 import하면 순환 import가 된다.
    """
    from app.chat.schemas import AnswerSource, FaqAnswer
    from app.chat.service import get_chat_service

    service = get_chat_service()
    ticket = job.payload["ticket"]

    if not result.get("grounded"):
        service.mark_chat_rag_ungrounded(ticket)
        return

    try:
        answer = FaqAnswer(
            ticket=ticket,
            live_id=job.payload["live_id"],
            question=job.payload["question"],
            cluster_size=job.payload["cluster_size"],
            answer=result["answer"],
            grounded=True,
            grounding_score=result.get("grounding_score", 0.0),
            sources=[AnswerSource(**s) for s in result.get("sources", [])],
            created_at=datetime.now(UTC),
        )
        service.save_generated_answer(answer)
    except Exception as exc:  # noqa: BLE001
        print(f"[gateway] chat_rag 결과 저장 실패(ticket={ticket}): {exc}")
        service.mark_chat_rag_ungrounded(ticket)


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


# ---------- 백엔드(Spring Boot)가 호출하는 쪽 ----------


@router.post("/{feature}")
def enqueue_job(feature: FeatureType, data: dict):
    job = new_job(feature, data)
    r.rpush(f"{QUEUE_PREFIX}{feature}", job.model_dump_json())
    store_job_result(job.job_id, "queued")
    return {"job_id": job.job_id}


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    raw = r.get(f"{RESULT_PREFIX}{job_id}")
    if raw is None:
        raise HTTPException(status_code=404, detail="job not found or expired")
    return json.loads(raw)


@router.get("/workers/status")
def get_worker_status():
    """기능별 워커 가용성. **워커가 팀원 노트북이라 항상 떠 있지 않다.**

    워커가 없으면 job은 `queued`로 남아 있다가 TTL(1시간)에 조용히 만료된다. BE·FE가 그걸
    "처리 중"과 구별하려면 이 정보가 필요하다 — 상품 등록 화면에서 "지금 검수 가능/불가"를
    미리 알리거나, 폴링을 언제 포기할지 판단하는 데 쓴다.

    `online`은 최근 poll 기록이 살아 있다는 뜻일 뿐, 그 워커가 지금 한가하다는 보장은 아니다.
    `queued`는 대기 중인 job 수다.

    **다른 `/workers/*`와 달리 API 키를 요구하지 않는다.** 저 셋은 워커가 *호출하는* 쪽이라
    인증이 필요하지만, 이건 워커에 *대한* 정보를 BE·FE에 알려주는 용도다. 노출되는 건 기능
    목록·온라인 여부·대기 job 수뿐이고, 이걸 못 보면 FE가 "지금 검수 가능한지"를 표시할 수 없다.
    """
    features: dict[str, dict] = {}
    for feature in get_args(FeatureType):
        last_seen = r.get(f"{WORKER_SEEN_PREFIX}{feature}")
        features[feature] = {
            "online": last_seen is not None,
            "last_seen": last_seen,
            "queued": r.llen(f"{QUEUE_PREFIX}{feature}"),
        }
    return {"features": features, "checked_at": _now_iso()}


# ---------- 로컬 노트북 워커가 호출하는 쪽 ----------


@router.get("/workers/poll")
def poll_job(
    feature: FeatureType = Query(...), x_api_key: str | None = Header(default=None)
):  # noqa: B008
    _check_worker_key(x_api_key)

    # 생존 신호를 BLPOP **전에** 찍는다. 뒤에 찍으면 job이 없어 5초를 블로킹하는 동안
    # 키가 만료돼, 한가한 워커가 죽은 것처럼 보인다.
    r.set(f"{WORKER_SEEN_PREFIX}{feature}", _now_iso(), ex=WORKER_SEEN_TTL_SECONDS)

    item = r.blpop([f"{QUEUE_PREFIX}{feature}"], timeout=POLL_TIMEOUT_SECONDS)
    if item is None:
        return {"job": None}

    _, raw_job = item
    job = json.loads(raw_job)

    store_job_result(job["job_id"], "processing")
    return {"job": job}


@router.post("/workers/result")
def submit_result(
    job: Job,
    status: str,
    result: dict | None = None,
    error: str | None = None,
    worker_id: str | None = None,
    x_api_key: str | None = Header(default=None),
):
    _check_worker_key(x_api_key)

    if status == "success":
        store_job_result(job.job_id, "success", result=result, worker_id=worker_id)
        if job.type == "stt" and result is not None:
            _ingest_stt_result(result)
        elif job.type == "chat_rag" and result is not None:
            _ingest_chat_rag_result(job, result)
        elif job.type == "quality_check" and result is not None:
            _ingest_quality_embedding_result(result)
        return {"ok": True}

    job.retry_count += 1
    if job.retry_count > MAX_RETRY:
        r.rpush(DEAD_LETTER_KEY, job.model_dump_json())
        store_job_result(job.job_id, "failed", error=error, worker_id=worker_id)
    else:
        r.rpush(f"{QUEUE_PREFIX}{job.type}", job.model_dump_json())
        store_job_result(job.job_id, "queued", worker_id=worker_id)

    return {"ok": True}


@router.post("/workers/upload-image")
async def upload_result_image(
    prefix: str = Query(...),
    file: UploadFile = File(...),  # noqa: B008
    x_api_key: str | None = Header(default=None),
):
    """
    워커(노트북)가 만든 결과 이미지를 EC2 디스크에 저장한다.
    S3 권한이 없어서 쓰는 대체 경로 — 저장 후 Caddy가 서빙 가능한 URL을 돌려준다.
    """
    _check_worker_key(x_api_key)

    target_dir = os.path.join(RESULTS_DIR, prefix)
    os.makedirs(target_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.png"
    filepath = os.path.join(target_dir, filename)
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(await file.read())

    url = f"{settings.public_base_url}/results/{prefix}/{filename}"
    return {"url": url}


@router.post("/workers/upload-json")
async def upload_result_json(
    prefix: str = Query(...),
    name: str = Query(...),
    data: dict | None = None,
    x_api_key: str | None = Header(default=None),
):
    """품질검수 리포트처럼 JSON 결과물을 저장할 때 쓰는 엔드포인트."""
    _check_worker_key(x_api_key)

    target_dir = os.path.join(RESULTS_DIR, prefix)
    os.makedirs(target_dir, exist_ok=True)

    filepath = os.path.join(target_dir, f"{name}.json")
    async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, ensure_ascii=False))

    url = f"{settings.public_base_url}/results/{prefix}/{name}.json"
    return {"url": url}
