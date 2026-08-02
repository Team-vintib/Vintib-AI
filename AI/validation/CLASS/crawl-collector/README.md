# 쇼핑몰 상품 사진·카테고리 수집기 (VLM 카테고리 분류 파인튜닝용)

`VLM_DATA_COLLECTION_BRIEF.md`가 요구한 데이터셋 — **(상품 사진, 소분류 코드 30종)** 쌍 —
을 지정한 쇼핑몰 경로에서 수집한다. PoC/스파이크 코드이고 프로덕션 경로가 아니다.

수집 범위(사용자 확정 2026-08-01): **카테고리만 자동 라벨링**한다. 색상은 상품명에서 후보만
뽑아 `color_hints`로 남기고 `primary_color`는 비워 둔다 — 상품명의 색상어는 대표 이미지가
아니라 옵션 전체를 나열하는 경우가 많아 오라벨 위험이 크다.

## 설치

```bash
cd AI
pip install -r validation/CLASS/crawl-collector/requirements-crawl.txt
playwright install chromium     # render: playwright 스펙을 쓸 때만
```

## 사용법

```bash
cd AI/validation/CLASS/crawl-collector

# 1) 매핑 규칙만 시험 — 새 사이트 카테고리 트리를 조사할 때 제일 먼저 하는 일
python crawl.py --map-only "홈 > 아우터 > 자켓 > 블루종" "상의 > 니트/맨투맨"

# 2) 새 사이트 스펙 검증 — 요청은 하되 아무것도 저장하지 않는다
python crawl.py --spec sites/my-mall.yaml --url "https://..." --limit 5 --dry-run

# 3) 실제 수집
python crawl.py --spec sites/my-mall.yaml --url "https://..." --limit 200 --out ./out
```

재실행하면 이미 수집한 `source_url`과 이미지 해시를 건너뛴다(이어받기).

## 새 쇼핑몰 추가하기 — 코드를 고치지 않는다

`sites/_TEMPLATE.yaml`을 복사해 셀렉터를 채우면 끝이다. 사이트마다 파서를 새로 짜지 않는다.

1. 개발자도구로 목록 페이지의 상품 카드 셀렉터를 찾아 `listing.item_selector`에 넣는다.
2. `--dry-run --limit 5`로 몇 건 잡히는지 본다. **0건이면 JS로 그리는 SPA**일 가능성이 크다 →
   `render: playwright` + `listing.wait_selector`를 넣는다.
3. 출력에 찍힌 `[원본 카테고리]` 문자열을 보고, 키워드 규칙이 이미 맞히면 그대로 두고
   틀리면 `category_map`에 정확 일치 항목을 추가한다.

`follow_detail: false`(목록에서 이미지·카테고리를 바로 뽑기)를 기본으로 삼는 게 좋다 —
상품 수만큼 요청이 줄고, 목록 URL 자체가 카테고리라 라벨이 흔들리지 않는다.

## 산출물

```
out/images/<site>/<sha256 앞16자>.jpg
out/items.jsonl      # mapped        — 바로 학습에 쓸 수 있는 행
out/review.jsonl     # needs_review  — 사람이 사진 보고 확정할 행
out/unmapped.jsonl   # unmapped      — 우리 taxonomy에 없는 카테고리
```

행 스키마는 `schema.py`의 `CollectedItem` 참고(브리핑 §4.1 필드명을 그대로 쓴다).
수집이 끝나면 커버리지 리포트가 출력된다 — 소분류 30종 중 0건인 코드, 촬영유형 분포,
혼동쌍 균형을 여기서 확인하고 부족한 카테고리를 추가로 긁는다(브리핑 §4.3).

## 카테고리 매핑 설계 (브리핑 §5)

원본 쇼핑몰 카테고리를 우리 30종 코드로 옮기는 규칙은 **2단**이다.

| 단계 | 위치 | 성격 | 신뢰도 |
|---|---|---|---|
| 1. 사이트별 정확 매핑 | `sites/*.yaml`의 `category_map` | 사람이 사이트 트리를 조사해 확정한 데이터 | 1.0 |
| 2. 공용 키워드 규칙 | `mapping_rules.py`의 `RULES` | 사이트 무관한 한국어 의류 용어 사전(코드라 CI에서 테스트됨) | 0.5~0.95 |

판정 결과는 항상 3상태로 남는다.

- **mapped** (`confidence >= 0.70`) — 자동 확정.
- **needs_review** — 자동으로 정하지 않고 사람에게 넘긴다. 세 경우다:
  - 모호 규칙(`ambiguous=True`): `"정장 자켓"`, `"패딩"`, 아이템어 없는 `"팬츠"` 등 사진을 봐야 정해지는 것.
  - 사이트가 우리보다 넓은 1:N 카테고리: `"숄더백/토트백"`, `"니트/맨투맨"`처럼 한 카테고리에 우리 코드 둘이 나열된 경우.
  - 1·2위 코드가 같은 강도로 걸린 경우.
- **unmapped** — 규칙이 하나도 안 걸림. `"원피스"`, `"양말"`처럼 우리 taxonomy에 아예 없는
  카테고리다. **비슷한 코드에 욱여넣지 않고** 따로 모아 taxonomy 확장 논의 근거로 쓴다(§5.5).

매칭은 **규칙 나열 순서가 아니라 가장 긴 키워드가 이긴다**. `"후드집업"`이 `HOODIE`의
`"후드"`(2자)와 `HOODIE_ZIP_UP`의 `"후드집업"`(4자)에 동시에 걸려도 후자가 이긴다 — 순서
의존 매칭은 규칙이 늘수록 조용히 깨진다. 오탐은 배제어(`exclude`)로 막는다(`"데님 자켓"`이
`DENIM`으로 가지 않게, 쇼핑몰 네비게이션의 `"베스트상품"`이 조끼 `VEST`로 가지 않게).

## 파일

| 파일 | 역할 | 무거운 의존성 |
|---|---|---|
| `labels.py` | 소분류 30종·팔레트 코드 (CH012 `taxonomy.py`/`color.py`의 미러) | 없음 |
| `mapping_rules.py` | 키워드 규칙 레지스트리 + 임계값 | 없음 |
| `mapping.py` | 매핑 엔진(정규화·점수화·3상태 판정) | 없음 |
| `color_hint.py` | 상품명 → 팔레트 색상 **후보** | 없음 |
| `schema.py` | `CollectedItem`·JSONL·커버리지 리포트 | 없음 |
| `site_spec.py` | 사이트 스펙 YAML 로더/검증 | PyYAML(지연) |
| `fetcher.py` | httpx/Playwright + robots + rate limit | httpx·playwright(지연) |
| `parser.py` | 셀렉터 기반 DOM 추출 | selectolax(지연) |
| `downloader.py` | 이미지 저장 + sha256 중복 제거 | 없음 |
| `crawl.py` | CLI | 위 전부 |

무거운 의존성은 전부 **함수 내부 지연 import**라, 위 표에서 "없음"인 모듈은
`requirements-crawl.txt` 없이도 import·테스트된다 — 그래서
`test_class_crawl_mapping.py`가 CI(`requirements-dev.txt`만 설치)에서 그대로 돈다.

## 수집 시 주의

- **robots.txt를 기본으로 준수**하고 요청 간 지연(기본 1.5초, 지터 포함)을 둔다.
  `--ignore-robots`가 있지만 수집이 허용된 대상에만 쓸 것.
- 학습 데이터로 쓰는 이미지의 출처(`source_site`, `source_url`)를 행마다 남긴다 —
  나중에 재현·삭제 요청 대응에 필요하다.
- 브리핑 §4.2: 신상품 쇼핑몰만 긁으면 **도메인 갭**(스튜디오 제품샷 ↔ 개인이 스마트폰으로
  찍은 중고 사진)이 그대로 남는다. 중고/리세일 플랫폼을 섞고, 최소한 `shot_type`을
  라벨링해서 나중에 촬영유형별로 나눠 평가할 수 있게 할 것.

## 한계 / TODO

- `sites/example-*.yaml`은 **구조 설명용**이다. 실제 사이트 DOM으로 검증되지 않았다 —
  대상 쇼핑몰이 정해지면 셀렉터를 실제 값으로 바꾸고 `--dry-run`으로 확인해야 한다.
- `shot_type`은 크롤링으로 판별할 수 없다. 스펙의 `shot_type_default`로 선언하거나 사후 라벨링.
- `labels.py`는 CH012 정의의 복사본이다. `origin/feat/211-product-info-model`이 합쳐지면
  이 파일을 지우고 `product-info-check/taxonomy.py`를 직접 import하도록 바꿀 것.
