# 상품 카테고리 VLM 고도화용 크롤링 수집기 (CLASS)

> 근거: `AI/validation/CLASS/VLM_DATA_COLLECTION_BRIEF.md`, CH012(상품 정보 분류 검증,
> `origin/feat/211-product-info-model`). 브랜치는 현재 `feat/211-vlm-finetuning` 유지.

## 배경/목표

VLM(Qwen3-VL-4B) 카테고리 분류 정확도를 파인튜닝으로 끌어올리려는데 정답셋이 8건뿐이다.
쇼핑몰에서 **상품 사진 + 카테고리**를 긁어와, 원본 사이트 카테고리를 **우리 taxonomy 30종
소분류 코드**로 매핑한 학습 데이터셋(JSONL + 이미지)을 만드는 수집기를 `AI/validation/CLASS/`
아래에 만든다. 프로덕션 코드가 아니다(PoC/스파이크).

**확정 사항(사용자, 2026-08-01)**
- 사이트별 하드코딩 파서가 아니라 **범용 사이트 스펙(YAML)** 방식 — 새 쇼핑몰은 YAML 한 장 추가.
  실행 시 대상 경로(URL)를 인자로 넘긴다.
- 렌더링은 **httpx(정적) + Playwright(SPA) 둘 다** 지원. 스펙의 `render` 키로 전환.
- 라벨링 범위는 **카테고리만 자동**. 색상은 상품명에서 후보(hint)만 뽑고 `primary_color`는
  비워 둔 채 사람이 검수한다(브리핑 §5의 매핑 신뢰도 검수 흐름과 동일하게 취급).

## 작업 내용

`AI/validation/CLASS/crawl-collector/`에 모듈을 역할별로 쪼갠다. **순수 로직(매핑/스키마/색상
힌트)과 I/O(fetch/parse/download)를 분리**해서, 전자는 CI(`requirements-dev.txt`만 설치)에서
그대로 테스트되게 하고 후자의 무거운 의존성(selectolax·PyYAML·Playwright)은 전부 함수 내부
지연 import로 둔다.

- **라벨 정의**: CH012의 `taxonomy.py`/`color.py`에서 크롤러가 쓰는 부분만 `labels.py`로 미러링
  (다른 브랜치에 있어 import 불가). 정본 위치와 동기화 필요를 파일 헤더에 명시.
- **매핑 엔진(이번 작업의 핵심, 브리핑 §5)**: `(source_site, source_category_raw) -> subcategory_code`
  를 2단으로 푼다.
  1. 사이트 스펙의 `category_map` 정확 일치(원본 카테고리 경로 문자열 → 코드), 신뢰도 1.0.
  2. 실패 시 `mapping_rules.py`의 공용 키워드 규칙 — **가장 긴 매칭 키워드 길이로 점수화**해서
     "후드집업"이 "후드"를 이기게 한다. 배제어(`exclude`)로 오탐 차단.
  - 결과는 `mapped` / `needs_review`(점수 낮거나 1·2위 동점) / `unmapped`(§5.5, taxonomy 확장
    논의용) 3상태 + `mapping_confidence` 수치로 남긴다. 우겨넣지 않는다.
- **수집 스키마**: 브리핑 §4.1 그대로 — `image`, `subcategory_code`, `primary_color`(null),
  `secondary_color`, `shot_type`, `source_site`, `source_category_raw` + 매핑 메타·이미지 해시.
- **수집기**: robots.txt 준수(기본값), 요청 간 지연·지터, 이미지 sha256 중복 제거, 재실행 시
  이어받기(수집 완료 URL 기록). 산출물(이미지·JSONL)은 `.gitignore`에 넣는다.
- **커버리지 리포트**: 브리핑 §4.3의 편향(대분류 6종·촬영유형 3종·혼동쌍)을 수집 후 바로 볼 수
  있게 소분류별 건수·미매핑 목록을 요약 출력한다.

## 구현 목록

- [x] `labels.py` — 소분류 30종·대분류·팔레트 코드 미러
- [x] `mapping_rules.py` — 소분류별 한국어/영어 키워드 규칙 레지스트리
- [x] `mapping.py` — 정규화·점수화·3상태 매핑 엔진(표준 라이브러리만)
- [x] `color_hint.py` — 상품명 색상어 → 팔레트 후보(자동 확정 아님)
- [x] `schema.py` — `CollectedItem` + JSONL 읽기/쓰기 + 커버리지 집계
- [x] `site_spec.py` — 사이트 스펙 YAML 로더/검증(yaml 지연 import)
- [x] `fetcher.py` — httpx/Playwright 렌더 백엔드, robots, rate limit
- [x] `parser.py` — 스펙 셀렉터 기반 목록/상세 추출(selectolax 지연 import)
- [x] `downloader.py` — 이미지 저장 + 해시 중복 제거
- [x] `crawl.py` — CLI(`--spec`, URL, `--limit`, `--out`, `--delay`, `--dry-run`, `--map-only`)
- [x] `sites/_TEMPLATE.yaml` + 정적/SPA 예시 스펙
- [x] `test_class_crawl_mapping.py` — 매핑·색상힌트·스펙 순수 로직 테스트 51건(CI 실행)
- [x] `README.md`, `requirements-crawl.txt`, `.gitignore` 산출물 경로 추가

## 구현 중 계획과 달라진 점

- **경로 구분자를 계층(`>`)과 병렬(`/`)로 나눴다.** 처음엔 `/`도 계층으로 잘랐는데, 그러면
  `"숄더백/토트백"`이 마지막 세그먼트 `"토트백"`만 보고 0.95 신뢰도로 자동 확정돼 버렸다 —
  브리핑 §5.2가 지목한 1:N 케이스가 조용히 오라벨된다. 지금은 병렬 항목이 서로 다른 코드로
  갈리면 `needs_review`, 같은 코드로 수렴하면(`"니트/스웨터"` → 둘 다 KNIT) 그대로 매핑한다.
- 1·2위 코드 동점도 신뢰도 상한(`TIE_CONFIDENCE_CAP`)으로 눌러 자동 확정을 막았다.
- **검수행을 상품명으로 갈라내는 단계를 추가했다.** 카테고리가 후보를 2~3개로 좁혀 놓은
  상태라 상품명을 그 후보 안에서만 받으면 오라벨 없이 검수량이 준다(번개장터
  `후드티/후드집업` 실측 12건 중 11건 자동 확정). 상품명 자체가 모호하면 채택하지 않는다.
- 사이트 스펙에 `listing.category_urls`(`{url, category}` 목록)를 추가했다 — 실제 쇼핑몰은
  소분류마다 URL이 달라, 없으면 카테고리 수만큼 YAML을 복사해야 했다.
- 대상 사이트: **무신사는 robots.txt가 `User-agent: * / Disallow: /`라 제외**하고 번개장터로
  대체했다(사용자 확인 2026-08-02). 브리핑 §4.2의 도메인 갭 관점에서도 중고 플랫폼이 낫다.

## 미결정

- 실제 대상 쇼핑몰 — 사용자가 경로(URL)를 지정하면 그 사이트 스펙 YAML을 추가한다.
  예시 스펙 2종은 구조 설명용이며 실제 사이트 DOM에 맞춰 검증되지 않았다.
- 촬영유형(`shot_type`)은 크롤링으로 판별 불가 — 스펙의 기본값 선언 또는 사후 라벨링.
