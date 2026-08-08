# CH031 시세 조회 — LLM 속성 추출(1단계)로 매칭 정확도 보강

## 배경 / 목표

CH030은 정규식/브랜드 별칭 사전만으로 상품명을 정규화해 "동일 상품" 매칭 키를 만든다.
당근마켓 사례를 참고하면 그쪽은 3단계 구조다: 1단계 LLM로 자유텍스트 → 정규화된 속성
(모델/용량/상태 등) 추출 → 2단계 그 속성들의 정확 키로 집계(업서트) → 3단계 유사 매물은
임베딩이 아니라 키워드+동의어 매칭(범용 임베딩은 효과가 없었다고 명시). 2·3단계는 지금
구조(정확 키 매칭)와 이미 같고, **1단계(LLM 속성 추출)만 없다** — 정규식이 그 역할을
대신해 오탈자·표기 변형(예: "아이폰16프로" vs "iPhone 16 Pro")에 약하다.

이번 계획은 1단계만 LLM으로 보강한다. 벡터DB·임베딩 유사도는 추가하지 않는다.

**GMS 하드 룰**: 코드만 작성한다. 새 백엔드도 커밋 기본값은 항상 `regex`이고, `llm`으로의
전환·실행은 사용자만 한다.

## 작업 내용

1. **`gms.py`**: `generate_content()`에 `use_search: bool = True` 추가. `False`면 `tools`
   필드를 안 붙인다(속성 추출은 웹검색 그라운딩이 필요 없음).
2. **`attribute_extraction.py`**(신규): `ExtractedAttributes` + `RegexAttributeExtractor`
   (기존 `normalize_title`/`resolve_brand_id`를 감쌈, 기본값) + `LlmAttributeExtractor`
   (GMS `gemini-3.5-flash`, `use_search=False`, 느슨한 JSON 파싱, 실패 시 `None`→regex 폴백)
   + `build_attribute_extractor(key)` 팩토리.
3. **`registry.py`**: `ATTRIBUTE_EXTRACTOR_BACKENDS`/`ACTIVE_ATTRIBUTE_EXTRACTOR`(기본
   `regex`), `PRICING_ATTRIBUTE_EXTRACTOR` 배포 환경변수로만 실전환(`PRICING_COMPS_SOURCE`
   와 같은 패턴, `config.py`).
4. **`product_match.py::build_match_keys()`**: 추출기 주입 방식으로 리팩터링(동작 동일,
   기존 테스트 유지).
5. **`comps.py::InternalTextCompsSource`**: 추출기를 만들어 `build_match_keys()`에 전달.
6. **신규 테스트**: `LlmAttributeExtractor` 네트워크 monkeypatch 검증(성공/실패 폴백),
   커밋 기본값 `regex` 가드 테스트.

## 구현 목록

- [ ] `gms.generate_content()`에 `use_search` 파라미터 추가
- [ ] `attribute_extraction.py`(Regex/Llm 추출기 + 팩토리) 신규 작성 + 테스트
- [ ] `registry.py`/`config.py`에 attribute extractor 스왑 지점 추가(기본 `regex`)
- [ ] `product_match.py::build_match_keys()` 추출기 주입 리팩터링
- [ ] `comps.py::InternalTextCompsSource` 배선
- [ ] 커밋 기본값 `regex` 가드 테스트 추가
- [ ] `docker-compose.yml`에 `PRICING_ATTRIBUTE_EXTRACTOR` 환경변수 추가

## 확인이 필요한 미결정 사항

- 프롬프트에 브랜드 별칭 사전을 통째로 넣어 강제할지, 자유 텍스트로 뽑고 사후 매칭할지 —
  실측 없이 정하기보다 구현 시 둘 다 시도 가능하게 만들어둔다.
- 실행·비용 확인은 전적으로 사용자 몫(GMS 하드 룰).

## 검증

```bash
cd AI && ruff check . && black --check . && pytest -q
```
`LlmAttributeExtractor`는 네트워크 monkeypatch로 CI 검증, 실제 GMS 호출은 사용자가 직접.
