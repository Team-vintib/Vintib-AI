# [AI] 품질 검수 서비스 프로토타입 — 설계

> 대상 티켓: 에픽 `S15P11A108-211 [PROD] 상품 등록·판매`
> → 작업 `-304 [PROD-009 | AI] 품질 검수 서비스 구현`. 브랜치는 `feat/211-quality-inspection-service`.
>
> **에픽이 211인 이유** (2026-07-27 Jira 확인, 사용자 확정): 이 설계의 초안은 에픽
> `-299 [INS] 품질 검수` → 스토리 `-300` → 작업 `-301 [INS-001 | AI] 품질 판단 모델 검증`을
> 대상으로 적었으나, `-299`는 **모델 검증 체인**이고 실제 서비스 구현 작업 `-304`의 상위 에픽은
> `-211`이다. **이번 스프린트의 이 서비스 작업은 전부 `-211` 아래에 할당한다.**
> 모델 검증 근거(LAB-12)는 `-301`에서 나온 것이라 아래 본문에서 계속 인용한다.
>
> 근거 문서: 노션 `[QUAL] 품질 검수`(LAB-17) / `[AI] AI 품질 판단 기능 모델 검증문서`(LAB-12)
> / `품질 검증 전략`(LAB-30) / `로컬 GPU 활용 방안`(LAB-23) / `작업 프로세스`(LAB-29)
>
> 산출 범위(이번 라운드): **목업 데이터 기반 프로토타입** — 마스크 → 하자 항목 리스트화 →
> 점수 → Attention Map 까지 전 경로가 실제로 동작하고, **세그멘테이션 모델만 레지스트리 키
> 한 줄로 갈아끼운다**.
>
> ⚠️ **구현 세션 주의**: 루트 세션은 `.claude/settings.json`의 PreToolUse 훅이 `AI/` 수정을
> 차단한다(확인함). 코드 구현은 **AI 스코프 세션**에서, 루트 세션은 `.claude/` 문서까지만.

---

## Context — 왜 지금 이걸 만드는가

빈티지·세컨핸드 의류는 **상태(컨디션)가 곧 가격**인데, 판매자의 주관적 서술 말고는 구매자가
믿을 근거가 없다. Jira `-301`이 요구하는 건 "판매자가 별도 입력 없이 신뢰도 높은 컨디션 정보를
얻고, 구매자는 실물 없이 상태를 신뢰"하는 것이다.

모델 후보 검증(LAB-12)은 이미 끝났다.

| 모델 | 결론 |
| --- | --- |
| WinCLIP | **부적합.** 정합성 버그, 깨끗한 옷에서 FP, 프린트를 손상으로 오인, 정상(0.213~0.437) vs 오염(0.364~0.484) 점수 구간 중첩 |
| **CLIPSeg** (`CIDAS/clipseg-rd64-refined`) | **채택.** 오염을 의류 특성 반영해 잘 분리. 단 ⑴ 찢어짐·훼손 판단 약함 ⑵ 미세 오염은 탐지되나 뚜렷하지 않음 |

그런데 LAB-12의 "다음 단계"가 **"해당 데이터를 활용할 이후 기능 또는 처리 파이프라인 설계 필요"**
에서 멈춰 있다. 즉 **확률 마스크는 나오는데 그 다음이 없다** — 마스크를 판매자가 소명할 수 있는
항목 리스트로 바꾸는 로직, 가격책정이 소비할 점수, FE에 보여줄 오버레이가 전부 미설계다.

동시에 흔들리는 것들이 있다: 모델 자체는 고도화 예정이고(프롬프트 세트·임계치·해상도), BE 상품
등록 API도 개발 중이다. 그래서 이번 라운드의 목표는 **"동작하는 완결 파이프라인을 목업으로 먼저
세우고, 흔들리는 부분(모델·임계치·BE 계약)을 전부 교체 가능한 경계 뒤로 밀어 넣는 것"** 이다.
`app/chat/`(003)에서 검증된 방식을 그대로 따른다.

### 확정된 결정 (사용자 승인)

| 항목 | 결정 |
| --- | --- |
| BE 연동 | **동기 REST 기본** + 비동기 큐 경로는 `RemoteWorkerSegmenter` 백엔드 스텁으로 준비만 |
| 판매자 소명 | **BE가 저장.** AI는 finding `key`와 `statement_required` 플래그까지만 제공 |
| Attention Map | **서버가 PNG 생성 + URL 반환.** Pillow를 `requirements.txt`에 추가, 기존 `RESULTS_DIR`/StaticFiles 재사용 |
| 산출물 | 이 계획 + 노션 `[QUAL]` 하위 설계 페이지. 별도 고도화 전략 문서는 만들지 않고 §고도화 경로로 대체 |

---

## 서비스 흐름과 AI/BE 경계

사용자가 제시한 흐름에 담당 주체를 매핑한다. **AI는 "판정과 산출물 생성"만, 상태 저장·집행은 BE**
— 003 계획의 "판정 위임" 선례와 동일한 경계다.

| # | 단계 | 담당 |
| --- | --- | --- |
| 1 | 판매자 "상품 등록" 클릭 | FE |
| 2 | 상품 이미지 업로드 | FE → BE |
| 3 | 검수 요청 | BE → **`POST /quality/inspections`** (AI) |
| 3' | 프롬프트 세트 선택 → 세그멘테이션 추론 → 확률 마스크 | **AI** |
| 4 | **마스크 → 하자 항목 리스트화** (부위 넘버링 + 확률 + severity + 소명 대상 플래그) | **AI** |
| 4' | 항목별 소명 입력·저장, 상품 상세 반영 | FE 입력 → **BE** 저장 |
| 5 | **Attention Map PNG 생성 + 공개 URL** | **AI** |
| 6 | 상품 등록 확정 | BE |
| 7 | 가격책정 (`condition_score` 소비) | 후속 범위 — 이번 라운드 밖 |

**동기를 택한 근거**: 상품 등록은 판매자가 화면에서 기다리는 인터랙티브 흐름이라 job 폴링을
끼우면 UX가 나빠진다. 목업·로컬 CLIPSeg 모두 즉시 응답이 가능하다(CLIPSeg는 CLIP ViT-B/16 +
소형 디코더로 시착 모델보다 훨씬 가볍다). 실서비스에서 GPU 워커 경유가 불가피해지면
`ACTIVE_SEGMENTER = "remote_worker"` 한 줄로 게이트웨이 큐(`POST /ai/quality_check`) 경로로
넘어가고, **API 계약과 downstream(findings/scoring/overlay)은 그대로 유지된다.**

---

## 아키텍처

```
BE 상품등록 ──POST /quality/inspections──▶ QualityInspectionService
                                              │
                                              ├─ 1) PromptSet 선택       prompts.py
                                              │     카테고리 × 기본색(LIGHT/DARK/PATTERNED)
                                              │
                                              ├─ 2) DefectSegmenter (ABC)  ★유일한 모델 교체 지점
                                              │     Mock(기본) / ClipSeg(지연 import) / RemoteWorker(스텁)
                                              │        └─ 출력: 프롬프트별 확률 마스크 (H×W float)
                                              │
                                              ├─ 3) findings.py  마스크 → 항목 리스트
                                              │     ├ clean 대조 정규화
                                              │     ├ 3×3 섹션 넘버링 + 섹션별 확률   ← LAB-30 요구
                                              │     ├ blob 추출(4-연결) → bbox·area·peak
                                              │     └ severity + status(DETECTED/SUSPECTED)
                                              │
                                              ├─ 4) scoring.py   condition_score / grade
                                              │
                                              └─ 5) overlay.py   히트맵 PNG → RESULTS_DIR → 공개 URL
                                                        │
                                              InspectionStore (인메모리, TTL) ── GET /quality/inspections/{id}
```

**교체 지점은 3곳뿐이다.**

1. **모델** — `app/quality/registry.py`의 `ACTIVE_SEGMENTER` 키 한 줄
2. **프롬프트·임계치** — `app/quality/prompts.py` + `registry.py`의 백엔드별 설정
3. **BE 계약** — `app/quality/schemas.py` 한 파일

---

## 모듈 구조

`AI/CLAUDE.md`의 도메인 우선 규약대로 `app/quality/` 자체완결 패키지. (도메인명은 게이트웨이
`FeatureType`의 기존 키 `quality_check`와 노션 용어 "품질 검수"에 맞춘다.)

| 파일 | 책임 |
| --- | --- |
| `schemas.py` | 요청/응답 모델 + `DefectType`/`FindingStatus`/`Severity`/`ConditionGrade` enum. **BE 계약 변경 시 여기만** |
| `registry.py` | `SEGMENTER_BACKENDS` + `ACTIVE_SEGMENTER`, **백엔드별로 묶인 임계치**, 하자 분류 체계(`DEFECT_TAXONOMY`), 점수 가중치 |
| `prompts.py` | 카테고리 × 기본색 프롬프트 세트, 3×3 섹션 부위 라벨 맵 |
| `segmenter.py` | `DefectSegmenter` ABC → `MockSegmenter`(기본) / `ClipSegSegmenter`(지연 import) / `RemoteWorkerSegmenter`(스텁) |
| `findings.py` | 확률 마스크 → 하자 항목 리스트 (정규화·섹션 넘버링·blob 추출·severity) — 순수 numpy |
| `scoring.py` | findings → `condition_score`(0~100) + `condition_grade` |
| `overlay.py` | Pillow로 히트맵 오버레이 PNG 생성·저장, 공개 URL 반환 |
| `store.py` | `InspectionStore` ABC → `InMemoryInspectionStore`(기본) / `RedisInspectionStore`(스텁) |
| `service.py` | 오케스트레이션 + `@lru_cache` DI 팩토리(= 스왑 지점) |
| `router.py` | `APIRouter()`만 정의. 도메인 예외 → HTTP 매핑 |
| `data/mock_inspections.json` | 목업 시나리오 5건(오염 명확 / 미세 오염 / 찢어짐 / 깨끗함 / 프린트) — 커밋 |
| `pipeline/render_overlays.py` | **발표자료용** 배치 오버레이 렌더 스크립트(실 CLIPSeg 사용, `requirements-pipeline` 계열) |
| `tests/` | 순수 로직 유닛테스트 + `TestClient` API 테스트 |

**재사용할 기존 자산** (새로 만들지 않는다):

- `app/chat/registry.py` — 백엔드 딕셔너리 + `ACTIVE_*` + **임계치를 백엔드별로 묶는** 패턴을 그대로.
- `app/chat/service.py` / `app/recommend/personalize/service.py` — `@lru_cache` 팩토리 DI.
- `app/recommend/personalize/catalog.py`의 `_seeded_vector()`(sha256 → `np.random.default_rng`)
  — **torch 없이 결정적 목업 마스크**를 만드는 방식.
- `app/gateway/router.py`의 `RESULTS_DIR` + `app/main.py`의 `StaticFiles` 마운트 — 오버레이 PNG
  저장·서빙 경로를 새로 만들지 않고 그대로 쓴다.
- `app/recommend/personalize/router.py`의 예외 → HTTP 매핑(503/404/422) 방식.
- `test/clipseg-condition-check/verify_clipseg.py`의 **tokenizer/image_processor 분리 호출 우회**
  — 통합 `processor(...)` 호출 시 kwarg가 섞여 에러나는 문제를 이미 밟았으므로, 이 회피 로직을
  `ClipSegSegmenter`로 **복사 승격**한다(`test/`를 프로덕션에서 import하지 않는 규약 준수).

---

## API 스펙

### 1) `POST /quality/inspections` — 동기 검수

```jsonc
{
  "product_id": 1042,                 // BE 채번. AI는 에코만 함
  "image_urls": ["https://.../front.jpg", "https://.../back.jpg"],
  "category": "TOP_KNIT",             // 프롬프트 세트 선택 키
  "base_color": "LIGHT"               // LIGHT | DARK | PATTERNED — 프롬프트 보정
}
```

```jsonc
{
  "inspection_id": "insp_1042_7f3c",
  "product_id": 1042,
  "model": { "backend": "mock", "model_id": null, "prompt_set": "top_knit/light" },
  "condition_score": 78.5,
  "condition_grade": "B",             // S | A | B | C
  "summary": "오염 2건, 보풀 1건이 확인되었습니다.",
  "findings": [
    {
      "key": "stain_5_1",             // 안정 키 — BE가 소명을 이 키에 매핑
      "defect_type": "STAIN",
      "status": "DETECTED",           // DETECTED | SUSPECTED
      "image_index": 0,
      "section_no": 5,                // LAB-30 "각 부위 넘버링"
      "section": "CHEST_CENTER",
      "confidence": 0.81,             // LAB-30 "확률값"
      "area_ratio": 0.031,
      "bbox": [0.42, 0.35, 0.55, 0.47],   // 정규화 좌표 (FE가 원본 해상도에 매핑)
      "severity": "MODERATE",         // MINOR | MODERATE | MAJOR
      "matched_prompt": "a stain on fabric",
      "statement_required": true,     // 판매자 소명 입력 대상
      "needs_seller_review": false    // 모델 신뢰도가 낮아 판매자 확인이 필수인 항목
    }
  ],
  "section_scores": [
    { "section_no": 1, "section": "SHOULDER_LEFT", "score": 0.04 }
    // … 9개
  ],
  "attention_maps": [
    { "image_index": 0, "defect_type": "STAIN", "url": "https://…/results/quality/insp_1042_7f3c/0_stain.png" }
  ],
  "notes": ["구멍·찢어짐은 모델 검증상 신뢰도가 낮아 판매자 확인이 필요합니다."],
  "latency_ms": 42.1
}
```

### 2) `GET /quality/inspections/{inspection_id}` — 재조회

`InspectionStore`(TTL)에서 조회. 없으면 404.

### 3) `GET /quality/prompt-sets` — 활성 설정 노출 (디버그·데모용)

현재 `ACTIVE_SEGMENTER`, 백엔드별 임계치, 카테고리×색상 프롬프트 세트, 하자 분류 체계와
**각 항목의 검증 여부**를 그대로 돌려준다. "모델을 갈아끼웠다"를 API로 확인할 수 있게 하는 용도.

| 상황 | 응답 | 근거 |
| --- | --- | --- |
| 요청 필드 누락 / 미등록 카테고리 | 422 | FastAPI 기본 검증 + enum |
| 활성 백엔드 준비 안 됨(torch 미설치, 워커 미연결) | 503 | `SegmenterNotReady` — `CatalogNotReady` 선례 |
| 이미지 다운로드 실패 (실 백엔드에서만) | 502 | `ImageFetchFailed` |
| 검수 id 없음 / TTL 만료 | 404 | — |

기존 도메인과 동일하게 `{success,data,error}` 봉투로 감싸지 않는다.

---

## 하자 항목 리스트화 로직 (이 계획의 핵심)

LAB-30이 요구한 "원하는 결과물 : 각 부위 넘버링(분류) / 확률값", "컨벌루션해서 섹션 특정"을
**두 축으로 나눠** 구현한다.

**축 1 — 섹션 넘버링 (사람이 읽는 위치).** 마스크를 3×3 그리드로 나눠 섹션별 확률(max/mean)을
집계하고, 카테고리별 부위 라벨을 붙인다. 별도 컨볼루션 층을 학습시키지 않고 **평균 풀링으로
같은 목적을 달성**한다 — 프로토타입에 학습 단계를 넣지 않기 위한 선택이며, 나중에 학습형 헤드로
바꿔도 이 출력 스키마는 그대로다.

| 카테고리 | 섹션 1~9 라벨 |
| --- | --- |
| 상의/아웃터 | SHOULDER_LEFT · COLLAR · SHOULDER_RIGHT / SLEEVE_LEFT · CHEST_CENTER · SLEEVE_RIGHT / HEM_LEFT · HEM_CENTER · HEM_RIGHT |
| 하의 | WAIST_LEFT · WAIST_CENTER · WAIST_RIGHT / THIGH_LEFT · CROTCH · THIGH_RIGHT / HEM_LEFT · SHIN_CENTER · HEM_RIGHT |

**축 2 — blob 추출 (개별 하자 1건).** `clean fabric` 대조로 정규화한 뒤 임계치 이진화 →
4-연결 flood fill로 연결요소를 뽑고, 각 blob이 finding 1건이 된다(bbox·area_ratio·peak
confidence). 순수 numpy + 파이썬 큐로 구현해 **scipy 없이** 돌아간다. 프롬프트별로 뽑은 blob이
같은 위치에서 겹치면 최고 확률 프롬프트의 `defect_type`을 대표로 삼는다.

**`clean fabric` 대조 정규화**: `p_norm = p_defect - CLEAN_MARGIN * p_clean`. LAB-12에서 WinCLIP이
프린트·솔기·단추 같은 정상 복잡 영역을 손상으로 오인했고, CLIPSeg 프롬프트에도 이미
`"clean fabric"`이 들어 있는데 검증 스크립트는 이를 **표시만 하고 활용하지 않았다.** 대조항으로
쓰면 정상 텍스처가 상쇄된다. 단 **CLIPSeg 기준 미검증**이므로 `CLEAN_MARGIN`을 registry 상수로
노출하고 실측으로 확정한다(0으로 두면 정규화 없음과 동일 — 안전한 기본값 확보).

**severity**: `area_ratio × peak_confidence`를 3구간으로. `MINOR` / `MODERATE` / `MAJOR`.

### 검증 실측을 스키마에 반영 — `status` / `needs_seller_review`

LAB-12 결론을 그대로 코드에 넣는다. **모델이 못 하는 걸 잘하는 척하지 않는 게 이 설계의 요점**이다.

| 하자 유형 | 프롬프트 | LAB-12 검증 | 취급 |
| --- | --- | --- | --- |
| `STAIN` / `DIRT_MARK` | `a stain on fabric`, `a dirty mark` | **양호** — 의류 특성 반영해 오염만 분리 | `DETECTED` 로 노출 |
| `HOLE_TEAR` | `a hole or tear in fabric` | **약함** — "찢어짐·훼손은 잘 판단하지 못함" | 항상 `SUSPECTED` + `needs_seller_review=true` |
| `DISCOLORATION` / `PILLING` / `FRAY` | (신규) | **미검증** | `verified=false` → `SUSPECTED` 로만 |

또한 미세 오염은 "탐지되나 뚜렷하지 않음"이므로, 확률이 `defect_threshold`는 넘지만
`confident_threshold` 미만인 구간도 `SUSPECTED`로 내린다. `SUSPECTED` 항목은 점수 감점 가중치가
낮고, FE에서 "AI가 의심하는 부분 — 확인해 주세요"로 표현할 수 있다.

### 점수 (`scoring.py`)

`condition_score = 100 − Σ(defect_type 가중치 × severity 계수 × status 계수)`, 하한 0.
`condition_grade`는 S(≥90) / A(≥75) / B(≥55) / C(그 외).

⚠️ **가중치·구간 경계는 현재 근거가 없는 임의값이다.** 003 계획이 grounding threshold를 다룬
방식대로 `registry.py`에 상수로 노출하고 "미확정"을 주석에 명시한다. 가격책정(에픽 밖)이 이 값을
소비하므로, **값 확정은 라벨링된 검증셋 확보 이후 별도 작업**임을 문서에 남긴다.

---

## 모델 스왑 설계

```python
SEGMENTER_BACKENDS = {
    # 기본 — 목업 시나리오 정의를 읽어 결정적 확률 마스크를 numpy로 합성. torch 불필요, CI 통과.
    "mock": {"model_id": None, "defect_threshold": …, "confident_threshold": …,
             "clean_margin": …, "min_area_ratio": …},
    # LAB-12 채택 모델. 임계치는 반드시 이 모델 기준으로 다시 스윕해야 한다.
    "clipseg_rd64_refined": {"model_id": "CIDAS/clipseg-rd64-refined", …},
    # 게이트웨이 큐(POST /ai/quality_check) 경유 — 비동기 전환용 스텁.
    "remote_worker": {"model_id": None, …},
}
ACTIVE_SEGMENTER = "mock"   # <- 여기 키만 바꾸면 스왑
```

- **임계치를 백엔드별로 묶는다.** 003의 교훈("임베딩 모델마다 유사도 스케일이 달라 고정 임계치를
  모델 무관하게 재사용하면 안 된다")이 여기도 그대로 적용된다 — CLIPSeg의 sigmoid 확률 스케일은
  프롬프트·체크포인트마다 다르다. 백엔드를 바꾸면 임계치가 따라온다.
- `ClipSegSegmenter`는 `transformers`/`torch`를 **함수 내부에서 지연 import**한다
  (`requirements-pipeline.txt` 계열, CI 미설치). 미설치 시 기동이 아니라 **첫 호출에서 503**.
- `MockSegmenter`는 하드코딩 응답이 아니라 **실제 확률 마스크를 합성**한다 —
  findings/scoring/overlay 전 경로가 목업에서도 실제로 실행되므로, 실모델로 갈아끼웠을 때
  downstream이 이미 검증된 상태가 된다.
- 모델 ID는 `test/`에서 import하지 않고 재선언한다(`embed_catalog.py` 선례).
- `app/shared/` 승격은 하지 않는다 — quality 도메인 단독 자산이다.

---

## Attention Map 산출

- `overlay.py`가 원본 이미지 위에 확률 마스크를 컬러맵(jet 근사)으로 알파 합성해 PNG를 만든다.
  `verify_clipseg.py`가 matplotlib으로 하던 일을 **Pillow만으로** 다시 쓴다(matplotlib은 서빙
  경로에 넣지 않는다).
- `requirements.txt`에 `Pillow`를 추가한다 — 서빙 경로에 들어가는 유일한 신규 의존성이며,
  경량이라 "서빙은 표준 라이브러리·경량 의존성만" 규약과 충돌하지 않는다.
- 저장은 기존 `RESULTS_DIR`(`app/gateway/router.py`) 아래 `quality/{inspection_id}/` 로,
  URL은 `settings.public_base_url` + `/results/...` 로 조립. **새 저장·서빙 경로를 만들지 않는다.**
- 산출물은 `.gitignore`에 추가(`app/recommend/artifacts/` 선례). `RESULTS_DIR`은 이미 컨테이너
  볼륨이라 리포에 안 들어오지만, 로컬 개발 기본값용으로 한 줄 추가.
- **발표자료용**은 `pipeline/render_overlays.py` — 실 CLIPSeg로 이미지 폴더를 배치 처리해
  `원본 | 프롬프트별 히트맵` 비교 PNG를 뽑는다. `overlay.py`의 렌더러를 재사용하고,
  LAB-12에 붙일 그림을 이 스크립트로 재현 가능하게 만든다.

---

## 목업 데이터

`data/mock_inspections.json` — 시나리오별로 `{product_id, category, base_color, blobs:[{defect_type,
center, radius, peak}]}`. `MockSegmenter`가 이 정의로 가우시안 블롭 확률 마스크를 합성한다.
`_seeded_vector()`와 같은 방식(sha256 → `default_rng`)으로 노이즈까지 결정적이라 CI에서 재현된다.

| 시나리오 | 목적 |
| --- | --- |
| 오염 명확 (상의, LIGHT) | 기본 경로 — `DETECTED` STAIN 다건, 섹션 넘버링 확인 |
| 미세 오염 (하의, DARK) | 저확률 구간이 `SUSPECTED`로 내려가는지 |
| 찢어짐 (하의, DARK) | `HOLE_TEAR`가 항상 `SUSPECTED` + `needs_seller_review`인지 |
| 깨끗함 (상의, LIGHT) | findings 0건, score 100, grade S |
| 프린트 있는 옷 (상의, PATTERNED) | **오탐 방어** — `clean` 대조 정규화로 디자인이 하자로 안 잡히는지 (WinCLIP 실패 케이스의 회귀 방지) |

---

## 고도화 경로 (모델을 갈아끼울 때 손댈 곳)

프로토타입 구조 안에서 **registry/prompts 교체만으로** 실험 가능하게 만드는 것이 1·2·6이다.

| # | 기법 | 근거 | 손대는 곳 |
| --- | --- | --- | --- |
| 1 | `clean fabric` 대조 정규화 | WinCLIP이 프린트·솔기를 손상으로 오인. CLIPSeg도 같은 위험 | `CLEAN_MARGIN` 스윕 |
| 2 | 카테고리·색상별 프롬프트 세트 + 프롬프트 앙상블(동일 하자를 여러 표현으로 평균) | LAB-30 Input 설계가 명시한 요구 | `prompts.py` |
| 3 | 의류 영역 마스크로 배경 제외 | 배경·소품 오탐 제거. `test/garment-mask-finetune-check/`의 세그멘테이션 헤드 자산 재사용 가능 | `segmenter.py` 전처리 |
| 4 | 임계치 스윕 | LAB-12 "다음 단계"의 정량 비교 항목. 라벨링된 오염 유/무 소규모 검증셋 필요 | 백엔드별 임계치 |
| 5 | 찢어짐 보완 모델 병행 | CLIPSeg의 확인된 약점. 텍스트 프롬프트로는 구조적 한계 가능성 | `DefectSegmenter` 구현체 추가 |
| 6 | 타일 추론 (이미지 분할 → 타일별 추론 → 마스크 합성) | CLIPSeg 입력이 224×224라 미세 오염이 뭉개진다 — "탐지되나 뚜렷하지 않음"의 유력한 원인 | `ClipSegSegmenter` 내부 |

---

## 검증 방법

```bash
cd AI
pip install -r requirements-dev.txt
ruff check . && black --check . && pytest -q
uvicorn app.main:app --reload --port 8000
```

- `GET /health` → 200, `GET /docs`에 `/quality/*` 3개 노출.
- **목업 E2E**: 5개 시나리오를 `POST /quality/inspections`에 흘려 ① 오염 명확 → `DETECTED` STAIN이
  기대 섹션에 ② 미세 오염 → `SUSPECTED` ③ 찢어짐 → `needs_seller_review=true`
  ④ 깨끗함 → findings 0 / score 100 / grade S ⑤ 프린트 → 오탐 0건 확인.
- **오버레이**: 응답의 `attention_maps[].url`이 실제 파일로 존재하고 브라우저에서 렌더되는지.
- **모델 스왑**: `ACTIVE_SEGMENTER`를 `clipseg_rd64_refined`로 바꿨을 때 — torch 미설치 환경에서
  **503**(기동 실패가 아님), 설치 환경에서 실제 추론. 후자는 `pytest.importorskip("torch")` 가드.
- **유닛테스트**(전부 torch 불필요, CI에서 실행): blob 추출 경계(인접/대각/최소 면적), 섹션 넘버링
  좌표 매핑, `clean` 정규화 부호, severity 구간 경계, status 강등 규칙, 점수 단조성(하자가 늘면
  점수가 내려간다), API 422/503/404.
- **발표자료**: `python -m app.quality.pipeline.render_overlays --input <이미지 폴더>` 로
  실 CLIPSeg 오버레이 PNG 생성(LAB-12 첨부 그림 재현).

---

## 구현 목록

- [ ] 이 계획을 리포 `.claude/plans/ai/005-quality-inspection-prototype.md`로 저장 (프로젝트 컨벤션)
- [ ] `app/quality/schemas.py` — 요청/응답 + `DefectType`/`FindingStatus`/`Severity`/`ConditionGrade`
- [ ] `app/quality/registry.py` — `SEGMENTER_BACKENDS` + `ACTIVE_SEGMENTER` + 백엔드별 임계치 +
      `DEFECT_TAXONOMY`(검증 여부 포함) + 점수 가중치(미확정 명시)
- [ ] `app/quality/prompts.py` — 카테고리 × 기본색 프롬프트 세트 + 3×3 섹션 부위 라벨 맵
- [ ] `app/quality/segmenter.py` — `DefectSegmenter` ABC + `MockSegmenter` + `ClipSegSegmenter`
      (지연 import, `verify_clipseg.py`의 tokenizer/image_processor 분리 호출 승격) + `RemoteWorkerSegmenter` 스텁
- [ ] `app/quality/findings.py` — clean 대조 정규화 → 섹션 집계 → blob 추출 → severity/status
- [ ] `app/quality/scoring.py` — `condition_score` / `condition_grade`
- [ ] `app/quality/overlay.py` — Pillow 히트맵 오버레이 + `RESULTS_DIR` 저장 + 공개 URL
- [ ] `app/quality/store.py` — `InspectionStore` ABC + 인메모리(TTL) + Redis 스텁
- [ ] `app/quality/service.py` — 오케스트레이션 + `@lru_cache` 팩토리
- [ ] `app/quality/router.py` — 엔드포인트 3개 + 예외 → HTTP 매핑
- [ ] `app/main.py`에 라우터 등록(`prefix="/quality"`, `tags=["quality"]`) — 기존 등록 유지
- [ ] `requirements.txt`에 `Pillow` 추가, `.gitignore`에 로컬 오버레이 산출물 경로 추가
- [ ] `app/quality/data/mock_inspections.json` — 시나리오 5건
- [ ] `app/quality/pipeline/render_overlays.py` — 발표자료용 배치 렌더
- [ ] `app/quality/tests/` — 유닛 + `TestClient` API 테스트
- [ ] `ruff check .` / `black --check .` / `pytest -q` 로컬 통과 후 목업 E2E 확인 → 커밋
      (push는 사용자가 직접)
- [ ] `AI/CLAUDE.md` 참조 문서 표에 이 도메인 한 줄 추가 여부 검토

### 작업 종료 후 — 노션 문서 작성

노션 `공통PJT/실험실`의 `[QUAL] 품질 검수`(LAB-17) **하위 항목**으로 `[AI] 품질 검수 서비스
프로토타입 설계` 페이지 생성. 데이터소스 `collection://5dc51c23-e8ff-4345-9f79-9c13016d2b5b`,
`문서유형=아키텍처 설계`, `상위 항목=LAB-17`. 구성:

- [ ] **What** — `app/quality/` 프로토타입. 동기 검수 API 1개 + 조회 2개. 마스크 → 하자 항목 →
      점수 → Attention Map 전 경로 동작, 모델은 목업 기본
- [ ] **Why** — LAB-12가 "마스크는 나오지만 그 다음 파이프라인 미설계"에서 멈춰 있었고, 모델·임계치·
      BE 계약이 전부 미확정이라 **완결 파이프라인을 목업으로 먼저 세우고 경계 뒤만 교체**하려는 의도
- [ ] **How** — 5단 파이프라인 + 교체 지점 3곳(`ACTIVE_SEGMENTER` / `prompts.py`+임계치 / `schemas.py`)
- [ ] **왜 그 기술인가 + 비교군** (표): CLIPSeg vs WinCLIP(LAB-12 실측 재사용) / 동기 REST vs
      비동기 큐(상품 등록은 인터랙티브 흐름) / 소명 저장 BE 위임 vs AI 보관 / 섹션 평균 풀링 vs
      학습형 컨볼루션 헤드 / 서버 PNG vs 마스크 배열 JSON
- [ ] **고찰 사항** — ⑴ 찢어짐 약점은 프롬프트로 해결되지 않을 가능성 ⑵ 점수 가중치·등급 경계가
      근거 없는 임의값이고 가격책정이 이를 소비함 ⑶ `CLEAN_MARGIN` 대조 정규화는 CLIPSeg 기준 미검증
      ⑷ 라벨링된 검증셋이 없어 정량 지표(오염 유/무 분리도)가 여전히 없음 — LAB-12 "다음 단계" 미해소
- [ ] LAB-12 / LAB-30 / LAB-23 은 **링크로 참조**하고 내용을 중복 서술하지 않는다 (001 선례)
- [ ] 생성 후 `notion-fetch`로 본문 재확인 — 긴 한국어 본문이 통째로 깨져 들어간 사례 있음

---

## 확인이 필요한 미결정 사항

- **BE 계약 미확정**: `category` / `base_color` 값을 BE 상품 등록 스키마가 어떤 이름으로 갖고
  있는지 미확인. 우선 AI 자체 enum으로 두고, BE 확정 시 `schemas.py`에서만 매핑한다.
- **소명 저장 스키마**: BE가 finding `key`를 어디에 보관할지(상품 상세 하위 테이블?) 미정.
  이번 라운드에서는 `.claude/requests/be/` 문서를 만들지 않고 여기에만 남긴다(003 선례).
- **점수 가중치·등급 경계 확정** — 라벨링된 검증셋 확보 후 별도 작업.
- **재검수 정책**: 판매자가 이미지를 교체하면 재검수인가, 기존 소명은 유지인가 — BE·FE와 협의 필요.
- **다중 이미지 집계**: 현재는 이미지별 finding을 한 리스트에 합치고 점수는 전체 합산.
  대표 이미지 가중을 둘지는 미정.
