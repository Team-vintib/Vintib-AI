# [AI] 개인화 취향 맞춤 상품 추천 서비스 (MVP) — 설계

> 산출 범위(이번 라운드): **설계 확정 + FastAPI 서빙 MVP 구현**(사용자 승인 후).
> 이 문서가 이번 구현 라운드의 **유일한 대상**이다.
>
> **독립성**: 이 스코프는 `001-brand-similarity-graph.md`(브랜드 유사도 그래프)와 **완전히 독립**이다.
> 두 문서 사이에 순서·의존관계가 없다. 이번 라운드에서 **브랜드 그래프 관련 코드(graph/similar,
> pipeline의 CLIP 임베딩 등)는 절대 건드리지 않는다.** 개인화 추천은 이미지/CLIP을 쓰지 않고
> 텍스트·로그 신호로만 구성한다.

---

## 배경 / 목표

- 사용자 로그 기반 **개인화(취향 맞춤) 상품 추천**을 REST API로 서빙한다. FE 상품 카드 리스트가
  그대로 렌더링할 수 있는 응답을 돌려준다.
- 방향 A(콘텐츠 기반 상품 추천) 스파이크(`AI/test/model_selection/recommendation_benchmark.py`)에서
  검증한 텍스트 임베딩을 재사용한다. **새 모델 도입 없음.**

### 확정된 결정 (사용자 승인)
| 항목 | 결정 |
| --- | --- |
| 이번 산출 범위 | 설계 + FastAPI 서빙 MVP 구현 |
| 데이터 | **목업 우선** — 카탈로그·유저 신호 모두 목업으로 전체 파이프라인을 굴리고, 나중에 데이터 입력부(`SignalProvider`/카탈로그 로더)만 실데이터로 교체 |
| 임베딩 baseline | **kanana-nano-2.1b-embedding** (`model_registry.ACTIVE_EMBEDDING` 현행 유지) |
| 이미지/CLIP | **스코프 밖** — 텍스트/로그 신호로만 구성 |
| 모듈 배치 | `app/recommend/personalize/`(서브패키지) — 기존 graph 코드와 물리 분리 |
| 서빙 numpy | `requirements.txt`에 **numpy 추가**(경량, 랭킹 연산용). 임베딩 모델 등 무거운 의존성은 `requirements-pipeline.txt`(CI 미설치) |

> **구현 세션 주의**: 모노레포 루트 세션은 하네스 훅으로 파트 코드(BE/FE/AI) 수정이 차단된다.
> 이 계획의 코드 구현은 **AI 스코프 세션에서** 수행한다(루트 세션은 `.claude/` 문서까지만).

---

## 아키텍처 — 브랜드 그래프와의 결정적 차이

```
[오프라인 배치 — 사전계산/캐시]                 [온라인 서빙 — 요청 시점 계산]
전체 상품 카탈로그(title/brand/category 텍스트)     1) 유저 신호 로드(온보딩/찜/구매)
  → 텍스트 임베딩(kanana-nano)                      2) 취향 벡터 집계(상호작용 상품 임베딩 평균)
  → item_vectors.npy + item_meta.json 캐시  ─────▶  3) 후보 필터(브랜드/카테고리/판매상태)
      (상품 임베딩만 — 유저 개인화 없음)              4) 취향벡터 vs 후보 코사인 재정렬 + 폴백 백필
                                                    5) 페이지네이션 → 상품 카드 응답
```

- **브랜드 그래프(001)**: nodes/edges/2D 좌표까지 **전부 오프라인 사전계산**, 서빙은 조회만.
- **개인화(002)**: 유저별 취향 벡터가 **요청마다 달라지므로 완전 사전계산 불가**.
  오프라인은 **상품 임베딩 캐시까지만**, 취향 집계·필터·랭킹은 **온라인**에서 계산한다.
  이 차이가 두 서비스의 핵심 구분점이다.

---

## 단계별 폴백 (콜드스타트 티어)

요청 시점 신호에 따라 티어를 자동 선택하고, 응답 `strategy` 필드로 어떤 티어를 썼는지 노출한다.

| 티어 | 조건 | 로직 | 신호 출처(현 상태) |
| --- | --- | --- | --- |
| **T0 popularity** | 유저 식별 불가(익명) 또는 신호 0 | `view_count` 인기순 + (요청) 카테고리 기본 | `product.view_count` (스키마 有) |
| **T1 onboarding** | 온보딩 관심 브랜드/카테고리만 존재 | 관심 브랜드/카테고리로 후보 필터 → 관심 카테고리 프로토타입 벡터로 콘텐츠 유사도 정렬 | `member_interest_brand/category` (스키마 有, **API 미구현**) |
| **T2 interaction** | 찜/구매 로그 존재 | 상호작용 상품 임베딩 평균 = 취향 벡터 → 후보 코사인 재정렬 | `wish`, `orders` (스키마 有, **API 미구현**) |

- 티어는 **누적적**: T2 유저도 취향 신호가 약하면 T1 필터를 병행, 결과가 `size`에 못 미치면 T0로 백필.
- **미구현 신호(T1/T2 원천)는 코드에 억지로 채우지 않는다.** 신호 로더를 `SignalProvider`
  인터페이스로 추상화하고, 현재는 **빈 결과를 반환하는 스텁**(사실상 모든 유저가 T0로 폴백) +
  코드 내 `TODO(BE)` 주석 + `.claude/requests/be/001-personalized-rec-signals.md`로 데이터 요청.
  BE API가 생기면 **스텁 구현만 교체**한다.

---

## 신호 조달 방식 — 미결정(BE 요청 문서로 질문)

AI가 유저 로그/온보딩을 어떻게 읽을지는 1단계 인벤토리에서 불명확 → 임의 결정하지 않는다.
아래 옵션을 `.claude/requests/be/`에 질문으로 남기고, MVP는 **옵션 A 인터페이스로 스텁**한다.

- **옵션 A (권장·스텁 채택)**: BE가 인증 후 유저 신호를 내부 REST로 노출 → AI가 `httpx`로 조회.
- **옵션 B**: BE가 추천 요청 시 신호를 바디에 실어 AI로 push(AI 무상태).
- **옵션 C**: AI가 Postgres 직접 접근(`config.py`에 DB 설정 존재) — 결합도 높아 MVP 비권장.

→ `SignalProvider`를 옵션 A 형태 인터페이스로 정의하되 실제 호출부는 빈 스텁 + `TODO(BE)`.
확정은 BE 회신 후.

---

## API 스펙

**엔드포인트**: `GET /recommend/products` (기존 `/recommend/graph`, `/recommend/{entity}/{id}/similar`와 충돌 없음)

**요청 파라미터**
| 파라미터 | 타입 | 기본 | 설명 |
| --- | --- | --- | --- |
| `user_id` | int? | none | **잠정** — 신호 조달 방식 확정 전까지 쿼리로 수신. 없으면 익명(T0). 인증 확정 시 헤더/BE 주입으로 이전(`TODO`) |
| `category_id` | int? | none | 카테고리 필터 |
| `brand_id` | int? | none | 브랜드 필터 |
| `page` | int | 1 | 1-base 페이지 |
| `size` | int | 20 | 1~100 |

**응답** (상품 카드 리스트 — `product`/`product_image`/`brand` 컬럼 매핑)
```jsonc
{
  "strategy": "popularity | onboarding | interaction",
  "personalized": false,
  "page": 1, "size": 20, "total": 137,
  "items": [
    {
      "product_id": 101,              // product.id
      "title": "빈티지 리바이스 데님 자켓",  // product.title  (※ 'name' 아님)
      "thumbnail": "https://.../a.jpg",     // product_image.image_url where is_primary
      "price": 89000,                 // product.price (경매 예정=null 가능)
      "brand": "Levi's",              // brand.name (nullable)
      "sale_type": "DIRECT_SALE",     // product.sale_type
      "sale_status": "ON_SALE",       // product.sale_status
      "score": 0.83                   // 랭킹 점수(디버그/정렬 근거, FE 무시 가능)
    }
  ]
}
```
> 필드명은 스키마 컬럼 기준 **잠정안**이다. FE 상품 카드 컴포넌트/타입이 아직 코드에 없어
> (FE `src`에 카드 없음, BE 도메인 DTO 없음) 재사용할 확정 스키마가 없다. `[PROD-006]`/`HOME-001/002`
> 카드 응답 필드 계약 확정을 BE 요청 문서에 포함한다.

---

## 에러/경계 처리

| 상황 | 응답 | 근거 |
| --- | --- | --- |
| 익명(user_id 없음) | **200**, T0 popularity, `personalized:false` | 콜드스타트 폴백이 정상 경로(오류 아님) |
| 신규 유저(신호 0) | 200, T0/T1 | 동일 |
| 카탈로그(임베딩 캐시) 없음 | **503** `detail:"item embedding artifact not built"` | 기존 graph `ArtifactNotFound` 503과 동일 스탠스 |
| 필터 결과 0건 | 200, `items:[]`, `total:0` | 빈 리스트는 오류 아님 |
| 잘못된 파라미터 | 422 (FastAPI 검증) | 기존 패턴 |

- 기존 `app/recommend` 엔드포인트는 BE `{success,data,error}` 봉투를 쓰지 않고 raw pydantic +
  `HTTPException`을 쓴다. MVP는 **AI 서비스 내부 일관성을 위해 기존 방식 유지**. AI 응답도 BE 봉투로
  감쌀지는 BE 요청 문서에서 확정.
- "로그인 필수" 강제 변형이 필요하면 BE `SSO_LOGIN_FAILED(U002/401)` 매핑 가능하나, MVP 기본은
  **익명 허용(폴백)**.

---

## 모듈 구조 / 의존성 / 테스트

- **위치**(기존 graph 코드 불변):
  - `app/recommend/personalize/router.py` — `APIRouter`, `GET /products`. 검증·변환만.
  - `app/recommend/personalize/service.py` — 티어 선택·필터·랭킹·폴백·페이지네이션(순수 로직).
  - `app/recommend/personalize/schemas.py` — 요청/응답 pydantic.
  - `app/recommend/personalize/signals.py` — `SignalProvider` 인터페이스 + 빈 스텁(`TODO(BE)`).
  - `app/recommend/pipeline/embed_catalog.py` — 상품 텍스트 임베딩 오프라인 캐시(무거운 import 지연).
  - `app/main.py`에 `personalize_router`를 `/recommend` prefix로 **추가 등록**(graph 라우터 유지).
- **아이템 임베딩 캐시 아티팩트**: `item_vectors.npy`(L2 정규화) + `item_meta.json`(product_id/title/
  brand/category/price/sale_status/thumbnail/view_count). 서빙은 이 캐시만 읽는다.
- **의존성**: 서빙 경로는 표준 라이브러리 + `numpy`(requirements.txt). 임베딩 모델·torch 등은
  `requirements-pipeline.txt`(CI 미설치). production에 무거운 라이브러리 추가 금지.
- **테스트**: 티어 선택·필터·코사인 랭킹·폴백 백필·페이지네이션 = 순수 로직 유닛테스트(CI 실행).
  임베딩 로더/카탈로그 빌드 = `pytest.importorskip("torch")` 가드.
- 마무리: `ruff check .` / `black --check .` / `pytest -q` 로컬 통과 후 커밋(직접 push 금지).

---

## 목업 우선 구현 세부 (규칙 수준 — 상세 코드는 구현 세션에서)

구현 세션이 재설계 없이 아래 규칙대로 만든다. 실데이터 전환 시 바뀌는 건 데이터 입력부뿐이다.

- **목업 카탈로그**(`personalize/data/mock_catalog.json`): 빈티지 상품 ~18건. 필드는 응답 카드와 동일
  (`product_id, title, thumbnail, price, brand, brand_id, category_id, sale_type, sale_status, view_count`).
  카테고리 5종(아우터/원피스/셔츠/데님/니트)·브랜드 5종(Levi's/Nike/Uniqlo/Carhartt/Polo) + 브랜드 없는
  아이템 일부. 가시성 필터 검증용으로 `SOLD`/`DRAFT`/`PRIVATE` 각 1건 이상 포함.
- **가시성 필터**: 후보는 `sale_status ∈ {ON_SALE, AUCTION_SCHEDULED, AUCTION_IN_PROGRESS}`만.
  `DRAFT/PRIVATE/SOLD`는 제외.
- **목업 임베딩 벡터**(서빙에서 numpy로 결정적 생성, torch 불필요): 아이템 벡터 =
  `정규화( 카테고리_basis + 0.6·브랜드_basis + 0.15·상품_noise )`. 각 basis는 키로 시드한
  `np.random.default_rng`로 생성 → 같은 카테고리/브랜드끼리 가깝게 배치되어 재정렬 효과가 드러난다.
  실데이터 전환 시 이 벡터를 `item_vectors.npy`(kanana 임베딩) 로드로 교체.
- **티어 랭킹 규칙**:
  - T2(interaction): 취향벡터 = 상호작용 상품 벡터 평균(정규화) → 후보 전체를 코사인 내림차순. `personalized=True`.
  - T1(onboarding): 관심 카테고리/브랜드에 매칭되는 후보 = 프로토타입벡터(관심 카테고리·브랜드 아이템 평균)에
    코사인 정렬, **나머지 후보는 인기순(view_count)으로 뒤에 백필**. `personalized=True`.
  - T0(popularity): 후보를 `view_count` 내림차순. `personalized=False`.
  - 후보 0건이면 `items:[]`, `total:0`, `strategy:popularity`.
- **목업 신호**(`MockSignalProvider`, `TODO(BE)`): user_id=1 → 상호작용(데님 상품 2건)으로 T2,
  user_id=2 → 관심(원피스 카테고리 + Polo 브랜드)만으로 T1, 그 외/미지정/None → 빈 신호로 T0.
- **점수(score)**: 유사도 티어는 코사인, 인기 티어/백필은 `view_count/max_view` 정규화값(FE는 무시 가능).
- **페이지네이션**: 전체 정렬 리스트를 만든 뒤 `(page-1)*size` 슬라이스. `total`은 필터 후 후보 수.
- **CatalogNotReady**: 카탈로그 로더가 캐시를 못 읽으면 서비스가 예외 → 라우터 503. 목업 폴백이 있어
  MVP에선 실제로 발생하지 않지만 실데이터 경로 대비로 계약만 남긴다.

## 구현 목록

- [ ] `personalize/schemas.py` — 요청/응답 모델(위 API 스펙)
- [ ] `personalize/signals.py` — `SignalProvider` 인터페이스 + 빈 스텁(`TODO(BE)`)
- [ ] `personalize/service.py` — 티어 선택 + 필터 + 코사인 재정렬 + 폴백 백필 + 페이지네이션
- [ ] `personalize/router.py` — `GET /recommend/products`, 503/422 매핑
- [ ] `app/main.py`에 personalize 라우터 추가 등록(graph 유지)
- [ ] `pipeline/embed_catalog.py` — 상품 텍스트 임베딩 오프라인 캐시(지연 import)
- [ ] `requirements.txt`에 numpy 추가 / 임베딩 의존성은 `requirements-pipeline.txt`
- [ ] 순수 로직 유닛테스트(`app/recommend/personalize/tests/`) + 임베딩 테스트 importorskip 가드
- [ ] `.claude/requests/be/001-personalized-rec-signals.md` 작성(신호 조달 방식·필드·카드 계약 질문)
- [ ] ruff/black/pytest 로컬 통과 후 커밋

## 확인이 필요한 미결정 사항
- 신호 조달 방식(옵션 A/B/C) — BE 회신 대기. MVP는 옵션 A 인터페이스 + 빈 스텁으로 선진행.
- 유저 식별 전달 방식(쿼리 `user_id` 잠정 → 인증 헤더/BE 주입) — BE 인증 방식 확정 후.
- 상품 카드 응답 필드 계약(`title` vs `name` 등) — FE/BE 확정 스키마 나오면 정렬.
- AI 응답을 BE `{success,data,error}` 봉투로 감쌀지 여부.
