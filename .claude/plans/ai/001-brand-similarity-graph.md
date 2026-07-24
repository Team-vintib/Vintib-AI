# [AI] 브랜드 유사도 그래프 추천 서비스 — 설계 & 프로세스

> 산출 범위(이번 라운드): **설계 확정 + Notion `Vintiv 기록` 보고서 발행**.
> 코드 구현은 CLAUDE.md 규율에 따라 이 계획 승인 후 별도 티켓(-193/-186)에서 진행.
> 관련 에픽: `S15P11A108-206 [REC] 추천` / 티켓 `-186`(추천 API 서빙 구조 설계) · `-193`(추천 서비스 구현) · `-199`(고도화).

---

## 배경 / 목표

- 레퍼런스: Fruits Family **Brand Radar**(`fruitsfamily.com/brand-radar/...`) — 임베딩 벡터 유사도 기준으로 브랜드를 2D 맵에 배치한 네트워크 시각화.
- 기존 Notion 리서치에서 추천은 3방향(상품/라이브 방송/브랜드 그래프)으로 검토됐고, **방향 C(브랜드 그래프)는 LAB-14에서 "방향성 리서치"까지만** 진행되고 기술 설계는 별도 티켓으로 미뤄져 있었다. 이 문서가 그 기술 설계·프로세스를 확정한다.
- **MVP 목표**: 브랜드 유사도 기반 2D 그래프 맵을 서빙한다. `entity` 파라미터로 **브랜드 ↔ 판매 상점(seller)** 유사도로 전환 가능하게 추상화한다.
- **개인화(취향 맞춤)는 MVP 밖**: 사용자 로그가 필요하므로 후속 개발 방향으로만 설계에 포함(LangGraph 등).

### 확정된 결정 (사용자 승인)
| 항목 | 결정 |
| --- | --- |
| 이번 산출 범위 | 설계 + Notion 보고서만 (구현은 후속) |
| MVP 브랜드-상품 데이터 | **큐레이션 시드 브랜드셋** (AI 파트 내부 자체 완결) |
| 브랜드 벡터 임베딩 소스 | **CLIP 이미지 집계** (브랜드 보유 상품 이미지 임베딩 평균/중심) |
| MVP 서빙/저장 | **인메모리 사전계산 아티팩트** (BE 의존 없음, pgvector 이관 가능 포맷 유지) |

---

## 설계 요약

### 1. 아키텍처 — 오프라인(배치) / 온라인(서빙) 분리

```
[오프라인 배치 파이프라인]                       [온라인 서빙 (FastAPI)]
시드 브랜드셋(이미지)                              아티팩트 인메모리 로드(numpy 캐시)
   → CLIP 이미지 임베딩                                │
   → 브랜드별 벡터 집계(평균/중심)          GET /recommend/graph?entity=&focus=&k=
   → 코사인 유사도 → kNN 엣지                GET /recommend/{entity}/{id}/similar?k=
   → 2D 레이아웃 투영(UMAP/PCA)                        │
   → 아티팩트 저장(parquet/json) ──────────────▶  응답: nodes[x,y,size,thumb] + edges[weight]
```
- 무거운 계산(CLIP 임베딩, 레이아웃)은 전부 오프라인. 서빙은 사전계산 결과 조회만 → 저지연.
- 브랜드 노드 수는 작음(수십~수백) → MVP는 인메모리 numpy로 충분. 아티팩트 포맷은 후속 pgvector 이관과 호환되게 설계.

### 2. 오프라인 파이프라인 (구현은 후속)
- **시드 데이터**: `AI/test/recommendation-brand-graph/data/brands/<brand>/*.jpg` + `brands.yaml`(id, name, 대표 이미지 목록). 빈티지 대표 브랜드 수십 개를 큐레이션.
- 단계별 모듈(설계):
  - `embed.py` — CLIP 이미지 임베딩. `model_selection/model_registry.py`의 CLIP 후보(`clip-ViT-B-32`) 재사용, heavy import는 함수 내부 lazy.
  - `aggregate.py` — 브랜드별 상품 임베딩 평균/중심 벡터(medoid 대안, 이상치 제거 옵션).
  - `similarity.py` — 코사인 유사도 행렬 → kNN 엣지(k≈6~10, 임계값 필터).
  - `layout.py` — 2D 투영(UMAP 우선, 미설치 시 PCA/t-SNE 폴백, 결정적 seed).
  - `build_artifact.py` — 오케스트레이션 → 아티팩트 저장.
- **아티팩트 스키마**(entity_type별):
  - `vectors.parquet`(id, name, vector, product_count, thumbnail)
  - `layout.json`(id, x, y)  · `edges.json`(source, target, weight)  · `meta.json`(entity_type, embedding_model, built_at, n)

### 3. 온라인 서빙 (greenfield — AI 첫 production 모듈)
- 위치: `AI/app/recommend/`(router · service · schema). `AI/main.py`에 라우터 등록.
- 엔드포인트(초안):
  - `GET /recommend/graph?entity=brand&focus={id}&k={n}` → 맵: `nodes[{id,name,x,y,size,thumbnail}]`, `edges[{source,target,weight}]`. `focus` 없으면 전체 맵, 있으면 focus 중심 kNN 서브그래프.
  - `GET /recommend/{entity}/{id}/similar?k={n}` → 유사 엔티티 랭킹(포커스 패널·카드 리스트 재사용).
- service: 아티팩트를 numpy로 인메모리 로드/캐시, similar/graph 질의 처리.
- **의존성 규율(AI CI)**: production `requirements.txt`엔 `numpy`만 추가. CLIP/UMAP 등 heavy 라이브러리는 오프라인 전용이라 `test/requirements-test.txt`에만. ML 테스트는 `pytest.importorskip` 가드, 순수 로직 테스트(유사도/스키마)는 CI에서 그대로 실행.

### 4. 엔티티 추상화 (브랜드 → 상점 전환)
- 파이프라인 전 구간을 추상 "EntityGroup"으로 파라미터화 → `aggregate` 단계의 `group_by` 키만 `brand_id ↔ seller_id`로 교체.
- 아티팩트/엔드포인트는 `entity_type`로 분기. 코드 신규 작성 없이 설정 전환.

### 5. 개인화(취향 맞춤) — 후속 방향 & 기술 리서치
- **필요 신호**: view/click/like/purchase 로그 + 온보딩 관심 브랜드/카테고리(`member_interest_brand/category`, ONBOARD-002, 티켓 -244/-228). → BE 의존.
- **접근**: 사용자 취향 벡터 = 상호작용 아이템/브랜드 임베딩 집계 → 맵 재중심화·엣지 재가중, 개인화 similar. 모델 확장 경로 content(cold) → CF/세션기반(SASRec/GRU4Rec, warm) → two-tower.
- **LangGraph**: 기존 문서(WBS169 `추천/검색 LangGraph 활용방안`) 결론 재사용 — 무거운 배치 임베딩/학습은 LangGraph 밖(데이터 파이프라인), LangGraph는 **실시간 서빙 오케스트레이션**(세그먼트 분기·재순위)·**콜드스타트 대화형 온보딩**·**라이브 세션 checkpointer 취향 추적**·**검색 질의 라우팅**에 사용. 스코어링 모델은 별도 경량 서빙 유지.
- **LLM 재정렬/설명 생성**: 상위 N개에만 `kanana-1.5-instruct` 재사용(댓글 agent와 동일 스택).
- 최신 트렌드 메모: LLM-as-recommender, agentic cold-start recommender(RAG+LLM), 검색·추천 공용 벡터 인덱스.

---

## 재사용 자산 (기존 코드/문서)
- `AI/test/model_selection/model_registry.py` — 모델 레지스트리 + `ACTIVE_*` 스왑 패턴, CLIP 후보 정의.
- `AI/test/model_selection/recommendation_benchmark.py` — Recall@K/Precision@K/NDCG@K 벤치마크 라이브러리(유사도 sanity check·평가 재사용).
- `AI/test/recommendation-embedding-finetune/` — bge-m3 파인튜닝 파이프라인(텍스트 임베딩 필요 시 재사용), 아이템 split→pair 반누수 패턴.
- Notion: LAB-14(방향성/모델), LAB-10(pgvector·CLIP 전제), WBS169(LangGraph). 신규 보고서는 이들을 링크로 참조하고 중복 서술하지 않음.

## 진행 프로세스 (순서)
1. **(이번 라운드)** 설계 확정 → Vintiv 기록 보고서 발행 → 리포 계획 저장.
2. (후속 -193) 시드 브랜드셋 큐레이션 + 오프라인 파이프라인 구현 → 아티팩트 생성·시각 검증.
3. (후속 -186/-193) FastAPI 서빙 모듈 + 엔드포인트 구현.
4. (후속, FE 스코프) 네트워크 그래프 화면 연동 — 채택 시 `.claude/requests/fe/`로 요청.
5. (고도화 -199) pgvector 이관 + 개인화(LangGraph·로그 신호). 실카탈로그 전환 시 `.claude/requests/be/`로 brand/seller↔product↔image 노출 요청.

## 검증 방법 (후속 구현 시)
- 오프라인: 아티팩트 생성 후 알려진 유사 브랜드쌍 sanity check + 2D 레이아웃 matplotlib 시각 확인.
- 서빙: `/recommend/graph`·`/similar` 응답 스키마·지연 확인(httpx).
- CI: production 코드 heavy import 금지, ML 테스트 `importorskip`, `ruff check .` / `black --check .` / `pytest -q` 로컬 통과 후 커밋.

---

## 구현 목록

### 이번 라운드 (설계 + 보고서)
- [ ] 본 설계안 최종 확정
- [ ] Vintiv 기록 DB에 **설계/기술문서** 페이지 생성 — 브랜드 유사도 그래프 서비스 설계 + 아키텍처(오프라인/온라인) + 엔티티 추상화 + 개인화/LangGraph 리서치 요약, LAB-14/LAB-10/WBS169 문서 링크
- [ ] 본 계획을 리포 `.claude/plans/ai/001-brand-similarity-graph.md`로 저장(프로젝트 컨벤션)

### 후속 티켓 (승인·별도 진행)
- [ ] 시드 브랜드셋 큐레이션(brands.yaml + 이미지)
- [ ] 오프라인 파이프라인(embed/aggregate/similarity/layout/build_artifact) + 아티팩트
- [ ] FastAPI `app/recommend/` 서빙 모듈 + 엔드포인트, `requirements.txt`에 numpy 추가
- [ ] 순수 로직 유닛 테스트(유사도·스키마) / ML 스파이크 테스트 importorskip 가드
- [ ] (고도화) pgvector 이관 + 개인화(LangGraph) + BE/FE 요청 문서

## 열린 질문
- 브랜드 그래프의 캡스톤 실제 채택 여부는 LAB-14에서 여전히 "팀 논의 필요"로 남아 있음 — 이 설계는 "넣는다면" 전제.
- 시드 브랜드셋 규모/목록(빈티지 대표 브랜드 몇 개, 브랜드당 이미지 수)은 후속 구현 착수 시 확정.
