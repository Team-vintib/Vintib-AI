# [AI] 브랜드 유사도 그래프 추천 서비스 — 설계 & 프로세스

> **스코프 독립성**: 이 스코프는 **개인화 취향 맞춤 상품 추천 서비스와 완전히 독립**이다
> (`.claude/plans/ai/002-personalized-recommendation-mvp.md`). 두 문서 사이에 순서·의존관계가
> 없다. 브랜드 그래프 구현 착수는 **개인화 추천 MVP가 끝난 뒤 별도로** 진행하며, 개인화 라운드에서는
> 이 스코프의 코드를 건드리지 않는다(그 반대도 동일).
>
> 산출 범위(설계 라운드): **설계 확정 + Notion `Vintiv 기록` 보고서 발행**.
> 코드 구현은 CLAUDE.md 규율에 따라 이 계획 승인 후 별도 티켓(-193/-186)에서 진행.
> 관련 에픽: `S15P11A108-206 [REC] 추천` / 티켓 `-186`(추천 API 서빙 구조 설계) · `-193`(추천 서비스 구현) · `-199`(고도화).

> ⚠️ **임베딩 소스 변경 — CLIP 이미지 → 브랜드 텍스트** (사용자 확정):
> 브랜드 유사도는 **이미지가 개입하지 않는다.** 우리가 큐레이션한 **브랜드 소개·평가 텍스트**를
> 임베딩해 유사도를 책정한다(= 우리가 정해둔 기준대로 그래프를 보인다). 아래 설계는 이 방침으로
> 갱신됐다. **주의**: `AI/app/recommend/pipeline/`에 이미 들어와 있는 구현은 **CLIP 이미지 기반**이라
> 이 방침과 어긋난다 — 텍스트 기반으로 **재작성이 필요**하며, 그 코드 작업은 (루트 세션 훅 제약상)
> **AI 스코프 세션**에서 이 계획 승인 후 진행한다.

---

## 배경 / 목표

- 레퍼런스: Fruits Family **Brand Radar**(`fruitsfamily.com/brand-radar/...`) — 임베딩 벡터 유사도 기준으로 브랜드를 2D 맵에 배치한 네트워크 시각화.
- 기존 Notion 리서치에서 추천은 3방향(상품/라이브 방송/브랜드 그래프)으로 검토됐고, **방향 C(브랜드 그래프)는 LAB-14에서 "방향성 리서치"까지만** 진행되고 기술 설계는 별도 티켓으로 미뤄져 있었다. 이 문서가 그 기술 설계·프로세스를 확정한다.
- **MVP 목표**: 브랜드 유사도 기반 2D 그래프 맵을 서빙한다. `entity` 파라미터로 **브랜드 ↔ 판매 상점(seller)** 유사도로 전환 가능하게 추상화한다.
- 유사도 기준은 **우리가 큐레이션한 브랜드 소개·평가 텍스트**다 — 상품 이미지가 아니라 우리가 정한 브랜드 서술을 벡터화해 "우리 기준의 유사도"를 그린다.

### 확정된 결정 (사용자 승인)
| 항목 | 결정 |
| --- | --- |
| 이번 산출 범위 | 설계 + Notion 보고서만 (구현은 후속) |
| MVP 브랜드 데이터 | **큐레이션 시드 브랜드셋** (AI 파트 내부 자체 완결) |
| 브랜드 벡터 임베딩 소스 | **브랜드 텍스트 임베딩** — 큐레이션한 브랜드 소개·평가 텍스트 기반. **이미지/CLIP 미개입** (기존 "CLIP 이미지 집계" 결정을 대체) |
| 임베딩 모델 | 방향 A에서 스파이크한 **텍스트 임베딩**(`kanana-nano-2.1b-embedding` / `bge-m3`) 재사용 — 새 모델 도입 없음 |
| MVP 서빙/저장 | **인메모리 사전계산 아티팩트** (BE 의존 없음, pgvector 이관 가능 포맷 유지) |

---

## 설계 요약

### 1. 아키텍처 — 오프라인(배치) / 온라인(서빙) 분리

```
[오프라인 배치 파이프라인]                       [온라인 서빙 (FastAPI)]
시드 브랜드셋(소개·평가 텍스트)                     아티팩트 인메모리 로드
   → 텍스트 임베딩(kanana-nano / bge-m3)               │
   → 브랜드별 벡터 집계(텍스트 여러 개면 평균)  GET /recommend/graph?entity=&focus=&k=
   → 코사인 유사도 → kNN 엣지                GET /recommend/{entity}/{id}/similar?k=
   → 2D 레이아웃 투영(UMAP/PCA)                        │
   → 아티팩트 저장(JSON) ─────────────────────▶  응답: nodes[x,y,size,thumb] + edges[weight]
```
- 무거운 계산(텍스트 임베딩, 레이아웃)은 전부 오프라인. 서빙은 사전계산 결과 조회만 → 저지연.
- 브랜드 노드 수는 작음(수십~수백) → MVP는 인메모리로 충분. 아티팩트 포맷은 후속 pgvector 이관과 호환되게 설계.

### 2. 오프라인 파이프라인 (⚠️ 기존 구현은 CLIP 이미지 기반 — 텍스트 기반으로 재작성 필요)
`AI/app/recommend/pipeline/`에 2026-07-24자 구현이 있으나 **이미지(CLIP) 전제**라 이번 텍스트 방침과
어긋난다. 아래 설계대로 **AI 세션에서 재작성**한다(계획↔코드 정합화).
- **시드 데이터**: `AI/app/recommend/data/brands.yaml`(id, name, **description/소개**, **evaluation/평가**, thumbnail). `brands.example.yaml`도 텍스트 필드 기준으로 갱신. **이미지 디렉터리 불필요.** 빈티지 대표 브랜드 수십 개를 큐레이션.
  - 브랜드 텍스트 소스 주: BE `brand` 테이블은 `id`,`name`뿐이라 소개·평가 텍스트가 없다 → 이 텍스트는 **AI 파트가 큐레이션한 시드 데이터**다(BE 의존 없음, MVP 자체완결).
- 단계별 모듈(설계):
  - `embed.py` — **텍스트 임베딩**. `model_selection/model_registry.py`의 `EMBEDDING_MODELS`(`kanana-nano-embedding`/`bge-m3`) 재사용, heavy import는 함수 내부 lazy. **CLIP/이미지 로직 제거.**
  - `aggregate.py` — 브랜드가 소개·평가 등 텍스트를 여러 개 가지면 임베딩 평균/중심 벡터(단일 텍스트면 그대로).
  - `similarity.py` — 코사인 유사도 행렬 → kNN 엣지(k≈6~10, 임계값 필터). (기존 재사용 가능)
  - `layout.py` — 2D 투영(UMAP 우선, 미설치 시 PCA/t-SNE 폴백, 결정적 seed). (기존 재사용 가능)
  - `build_artifact.py` — 오케스트레이션 → 아티팩트 저장. **이미지 경로 수집부를 텍스트 로딩으로 교체.**
- **아티팩트 스키마**(entity_type별, JSON — 서빙이 표준 라이브러리로 읽도록): `meta.json`(entity_type, embedding_model, dim, count, built_at) · `nodes.json`([id,name,x,y,size,thumbnail]) · `edges.json`([source,target,weight]) · `neighbors.json`({id:[[nid,score]]}, 상위 N 사전계산). 유사도·이웃을 오프라인에서 미리 계산해 서빙 요청 시 행렬 연산이 없다. (스키마 자체는 임베딩 소스와 무관하게 유지)

### 3. 온라인 서빙 (구현됨 — 임베딩 소스와 독립)
- 위치: `AI/app/recommend/`(router · service · schemas · artifact · pipeline/). `AI/app/main.py`에 라우터 등록됨.
- 엔드포인트:
  - `GET /recommend/graph?entity=brand&focus={id}&k={n}` → 맵: `nodes[{id,name,x,y,size,thumbnail}]`, `edges[{source,target,weight}]`. `focus` 없으면 전체 맵, 있으면 focus 중심 kNN 서브그래프.
  - `GET /recommend/{entity}/{id}/similar?k={n}` → 유사 엔티티 랭킹(포커스 패널·카드 리스트 재사용).
- service: 아티팩트(JSON)를 표준 라이브러리로 인메모리 로드/캐시, similar/graph 질의 처리(요청 시점 행렬 연산 없음). 아티팩트 미생성 시 503. **서빙 코드는 임베딩이 이미지든 텍스트든 무관** — 아티팩트만 읽으므로 이번 변경의 영향 없음(파이프라인만 재작성).

### 4. 엔티티 추상화 (브랜드 → 상점 전환)
- 파이프라인 전 구간을 추상 "EntityGroup"으로 파라미터화 → `aggregate` 단계의 `group_by` 키만 `brand_id ↔ seller_id`로 교체.
- 아티팩트/엔드포인트는 `entity_type`로 분기. 코드 신규 작성 없이 설정 전환.

### 5. 개인화(취향 맞춤) — 별도 독립 스코프
- 개인화 취향 맞춤 상품 추천은 **이 문서의 스코프가 아니다.** 별도 문서
  `.claude/plans/ai/002-personalized-recommendation-mvp.md`에서 독립적으로 설계·구현한다.
- 두 서비스의 핵심 차이: 브랜드 그래프는 **전부 오프라인 사전계산**(조회만), 개인화는 유저 취향
  벡터가 요청마다 달라져 **온라인 계산**이 필요하다. 서로 의존하지 않는다.

---

## 재사용 자산 (기존 코드/문서)
- `AI/test/model_selection/model_registry.py` — 모델 레지스트리 + `ACTIVE_*` 스왑 패턴. **텍스트 임베딩 후보(`kanana-nano-embedding`/`bge-m3`)** 정의.
- `AI/test/model_selection/recommendation_benchmark.py` — Recall@K/Precision@K/NDCG@K 벤치마크 라이브러리(유사도 sanity check·평가 재사용).
- `AI/test/recommendation-embedding-finetune/` — **bge-m3 텍스트 임베딩** 파인튜닝 파이프라인(브랜드 텍스트 임베딩 품질 개선 시 재사용), 아이템 split→pair 반누수 패턴.
- Notion: LAB-14(방향성/모델), LAB-10(pgvector 전제 — 단, CLIP 이미지 전제는 본 문서에서 텍스트로 대체됨), WBS169(LangGraph). 신규 보고서는 이들을 링크로 참조하고 중복 서술하지 않음.

## 진행 프로세스 (순서)
1. **(설계 라운드)** 설계 확정 → Vintiv 기록 보고서 발행 → 리포 계획 저장.
2. (후속 -193) 시드 브랜드셋 큐레이션(**소개·평가 텍스트**) + 오프라인 파이프라인 **텍스트 기반 재작성** → 아티팩트 생성·시각 검증.
3. (후속 -186/-193) FastAPI 서빙 모듈 + 엔드포인트(이미 구현, 아티팩트 연동 확인).
4. (후속, FE 스코프) 네트워크 그래프 화면 연동 — 채택 시 `.claude/requests/fe/`로 요청.
5. (고도화 -199) pgvector 이관 + 개인화(별도 002 스코프). 실카탈로그 전환 시 `.claude/requests/be/`로 brand/seller 노출 요청.

## 검증 방법 (후속 구현 시)
- 오프라인: 아티팩트 생성 후 알려진 유사 브랜드쌍 sanity check + 2D 레이아웃 matplotlib 시각 확인.
- 서빙: `/recommend/graph`·`/similar` 응답 스키마·지연 확인(httpx).
- CI: production 코드 heavy import 금지, ML 테스트 `importorskip`, `ruff check .` / `black --check .` / `pytest -q` 로컬 통과 후 커밋.

---

## 구현 목록

### 설계 라운드 (설계 + 보고서)
- [ ] 본 설계안(텍스트 임베딩 방침) 최종 확정
- [ ] Vintiv 기록 DB에 **설계/기술문서** 페이지 생성 — 브랜드 유사도 그래프 서비스 설계 + 아키텍처(오프라인/온라인) + 엔티티 추상화, LAB-14/LAB-10/WBS169 문서 링크(임베딩 소스는 텍스트로 명시)
- [x] 본 계획을 리포 `.claude/plans/ai/001-brand-similarity-graph.md`로 저장(프로젝트 컨벤션)

### 후속 티켓 (승인·별도 진행, 개인화 MVP 이후)
- [ ] 시드 브랜드셋 큐레이션(brands.yaml — **소개·평가 텍스트**, 이미지 불필요)
- [ ] 오프라인 파이프라인 **텍스트 기반 재작성**(embed/aggregate/build_artifact의 이미지→텍스트) + 아티팩트
- [ ] `requirements-pipeline.txt`에서 CLIP/Pillow 의존성 제거, 텍스트 임베딩 의존성(transformers/kanana, FlagEmbedding/bge-m3)로 정리
- [ ] 순수 로직 유닛 테스트(유사도·스키마) / ML 스파이크 테스트 importorskip 가드
- [ ] (고도화) pgvector 이관 + 개인화는 002 스코프에서

## 열린 질문
- 브랜드 그래프의 캡스톤 실제 채택 여부는 LAB-14에서 여전히 "팀 논의 필요"로 남아 있음 — 이 설계는 "넣는다면" 전제.
- 시드 브랜드셋 규모/목록(빈티지 대표 브랜드 몇 개, 브랜드당 소개·평가 텍스트 분량)은 후속 구현 착수 시 확정.
- 브랜드 소개·평가 텍스트의 큐레이션 출처/작성 주체(직접 작성 vs 공개 자료 발췌)는 시드 구성 시 확정.
