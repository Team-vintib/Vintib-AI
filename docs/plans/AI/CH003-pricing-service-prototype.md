# [AI] 가격 책정 프로토타입 서비스 — 설계

> 대상 티켓: 에픽 `S15P11A108-211 [PROD] 상품 등록·판매` → 스토리 `-313 [PROD-010] 가격 책정`
> → 작업 `-338 [PROD-010 | AI] 가격 책정 서비스 구현`. 브랜치는 `feat/211-pricing-model-validation`.
>
> 선행: `-333 가격 책정 모델 검증`(CH002). 이 문서는 그 실측 위에 세운다.
>
> 근거 문서: `.claude/plans/ai/CH002-pricing-model-selection.md` / 노션 `웹검색 테스트`(LAB-47)
> / `이미지 기반 상품 가격 책정 전략`(LAB-15) / `가격 책정 레퍼런스 비교`(LAB-21)
>
> BE 계약: `.claude/requests/be/002-pricing-async.md`
>
> 산출 범위: **mock 백엔드 기준 완결 파이프라인.** 실검색(GMS)은 레지스트리 키 한 줄로 전환된다.

---

## Context — 왜 이 구조인가

CH002 V1에서 GMS를 통한 LLM 웹검색이 동작한다는 걸 확인했고, V2에서 **가장 싼 모델·가장 적은
검색 라운드에서도 7.7초**가 걸린다는 걸 실측했다. 동기 REST로는 상품 등록 화면을 그만큼 세운다.

여기서 갈림길이 있었고, **문서와 초기 판단이 둘 다 틀렸다.**

- `docs/infra-architecture.md`는 가격책정을 "동기"로 규정하고 있었다 → 7.7초라 성립 불가.
- "품질검수와 같은 워커 큐로 간다"도 틀렸다 → `app/quality/router.py`가 큐를 쓰는 진짜 이유는
  지연이 아니라 **"노트북이 공유기 뒤라 인바운드 불가"** 다. 가격 책정에는 GPU도 torch도 NAT도
  없고 GMS로 나가는 아웃바운드 HTTPS뿐이다. 워커 큐로 보내면 HTTP 호출만 하는 기능이
  "누군가 노트북을 켜 놔야 도는" 상태가 되어 가용성이 오히려 나빠진다.

→ **`ai` 컨테이너 내 비동기.** 지연은 *비동기*를 요구하는 것이지 *노트북 워커*를 요구하지 않는다.

### 확정된 결정 (사용자 승인)

| 항목 | 결정 |
| --- | --- |
| 실행 위치 | ai 컨테이너 내 백그라운드 (`BackgroundTasks` + 동기 콜백) |
| BE 계약 | 품질검수와 동일 — 접수 시 `job_id`, 결과는 `GET /ai/jobs/{job_id}` |
| 상태 입력 | 품질검수 결과(`condition_score` + `condition_grade`)를 요청 payload로 |
| comps 백엔드 | mock + LLM 웹검색 2개. 네이버 정가 앵커는 범위 밖 |

---

## 핵심 설계 결정 4가지

### 1. `FeatureType`을 건드리지 않는다 ★

폴링 계약은 **이미 feature-agnostic이다** — `get_job_status`는 `result:{job_id}`만 읽고
`JobResult`에 `type` 필드가 없다. 그래서 `"pricing"`을 `FeatureType`에 넣을 이유가 없고,
넣으면 오히려 세 가지가 깨진다.

1. `/ai/workers/status`가 `get_args(FeatureType)`를 순회하므로 pricing이 **영구 오프라인**으로
   노출된다. BE가 그 값으로 가용성을 판단하면(001이 그렇게 안내했다) 워커가 필요 없는 기능이
   영구 불가로 표시된다.
2. `POST /ai/pricing`이 유효해져 **아무도 안 꺼내가는 고아 job**이 쌓인다.
3. `GET /ai/workers/poll?feature=pricing`이 유효해져 노트북 워커가 job을 가로채고 방치한다.

대신 게이트웨이에 헬퍼 2개를 추가했다 — `new_local_job_id()`(큐 없이 `result:` 시딩),
`store_job_result()`(네 곳에 중복돼 있던 `r.set` 통합).

### 2. `BackgroundTasks` + 동기 콜백

Starlette는 백그라운드 콜백이 코루틴이 **아니면** 스레드풀에서 돌린다. 블로킹 HTTP 호출이
이벤트 루프를 막지 않는다. `app/chat/router.py`에 이미 선례가 있다. `asyncio.create_task`는
배제 — 7.7초 블로킹이 루프를 막으면 `/health`와 폴링까지 같이 죽는다.

### 3. 동시성은 접수 시점 거부(503)

`threading.BoundedSemaphore(2)`. job 함수 *안에서* 대기하면 그 스레드가 스레드풀을 점유하는데,
게이트웨이 엔드포인트가 전부 동기 `def`라 같은 풀을 쓴다 → 결과 폴링이 굶는다. 슬롯을 못 잡으면
job_id도 발급하지 않는다(존재하지 않는 job을 폴링하게 만들지 않기 위해).

### 4. "시세를 못 찾음"은 실패가 아니다

인프라 오류만 `failed`. comps 부족·파싱 실패·검색 미호출은 `success` + `priced: false` +
`reason_code`. LLM comps가 평균 1.7건인 이상 근거 부족은 정상 경로이고, 이걸 실패로 만들면
**BE가 재시도 루프를 돌고 그대로 GMS 과금**이 된다.

---

## 구현 목록

- [x] 배관 — `.dockerignore`에 `.env`(키가 이미지에 구워지고 있었다) / compose `GMS_API_KEY` /
      루트·AI `.env.example` / `config.gms_api_key` / `requirements.txt`에 `anthropic`
- [x] `AI/CLAUDE.md` 하드 룰을 `app/pricing/`까지 확장 (프로덕션에 GMS 경로가 처음 생겼다)
- [x] `app/gateway/router.py` — `store_job_result` / `new_local_job_id`, 기존 4곳 통합
- [x] `app/pricing/schemas.py` — `ConditionGrade`·`GarmentCategory`는 `app.quality.schemas`에서 import
- [x] `app/pricing/registry.py` — comps/pricer 후보 + 임계치. **`min_comps_for_pricing`은 백엔드별**
- [x] `app/pricing/gms.py` — timeout 90s / max_retries 1 **명시**(SDK 기본은 10분×2 = 최악 30분)
- [x] `app/pricing/comps.py` — mock(sha256 결정적) / llm_web_search(툴 규격 폴백, 검색 미호출 시 폐기)
- [x] `app/pricing/pricer.py` — 규칙 baseline. 기준점 앵커 계수, 트림, range 폭 상한
- [x] `app/pricing/service.py` — `estimate()`(순수) / `run_job()`(예외 삼킴) 분리
- [x] `app/pricing/router.py` + `main.py` 등록
- [x] `test/pricing/` 4종 50건 + `conftest.py`에 `FakeRedis`(`get` 추가) 승격
- [x] 문서 — `infra-architecture.md`(§6 판단 기준에 "③ 외부 API 지연" 추가) / `api-reference.md`
- [x] `.claude/requests/be/002-pricing-async.md`
- [ ] 실검색 전환 후 재검증 — **사용자가 직접 실행**(AI/CLAUDE.md 하드 룰)

---

## 임계치에서 주의한 것

**상태 계수에 `score/100`을 쓰지 않았다.** comps 자체가 상태 불명의 중고라 중앙값은 이미
"평균적 중고"의 가격이다. 그대로 곱하면 70점짜리 평범한 물건이 30% 할인된다. 기준점 앵커를
쓴다 — `clamp(1 + (score - 70) × 0.008, 0.60, 1.25)`.

**`min_comps_for_pricing`을 백엔드별로 뒀다.** mock은 항상 5건이지만 LLM은 실측 평균 1.7건이라
전역 상수 3으로 잡으면 LLM 백엔드가 항상 `INSUFFICIENT_COMPS`가 된다.

**range 폭에 상한을 뒀다.** 폭을 무한정 넓히면 적중률은 100%가 되지만 아무 쓸모가 없다
(CH002 §V4).

⚠️ **이 계수·경계는 전부 근거 없는 임의값이다.** 실판매가 정답셋(30~50건, CH002 미완)으로
캘리브레이션하기 전에는 산출 가격의 정확도를 주장할 수 없다. LAB-32가 `condition_score`
가중치에 남긴 것과 같은 성격의 부채다.

---

## 범위 밖

슬롯 A(VLM 속성 추출) · 슬롯 D(comps 유사도 필터) · 네이버 정가 앵커 · LLM pricer 구현
(레지스트리에 키만) · 결과 영속 저장(TTL 1시간이 전부, 저장은 BE) · 재시도/dead-letter
(GMS 재시도는 곧 과금) · `pause_turn` 이어받기 · 가시성 타임아웃 · uvicorn `--workers` 조정

---

## 리스크 · 열린 질문

- **가격 정확도를 아직 말할 수 없다.** MAPE 측정에는 정답셋이 필요하고 그건 CH002의 미완 항목이다.
- LLM comps 평균 1.7건은 LAB-15가 "설득력의 첫 지표"로 꼽은 **비교 매물 개수(n)** 를 만족하지
  못한다. 프롬프트 완화·모델 상향·네이버 정가 앵커 중 무엇이 효과적인지 미확인.
- 컨테이너 재시작 시 in-flight job은 `processing`으로 방치된다. 워커 경로의 알려진 한계와
  같은 성격이고, BE 폴링 타임아웃이 안전망이다.
- uvicorn 워커를 2개 이상으로 늘리면 세마포어가 프로세스별이라 실효 동시성이 배수가 된다.
  현재 `Dockerfile`은 단일 프로세스라 문제없다.
- `condition_score`를 BE DB가 저장하지 않는다(등급만 있다). 002 요청서로 넘겼다.
