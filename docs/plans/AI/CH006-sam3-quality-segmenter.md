# SAM3(+마스킹 전처리) 품질 검수 세그멘터 통합 — 설계

## 배경 / 목표

이번 세션의 검증(`validation/QUAL/sam3-condition-check/sam3_qc_test_masking.ipynb` 등)에서
SAM3 어텐션이 CLIPSeg보다 육안상 더 만족스럽다고 판단해, 그 결과(SAM3 PCS + 의류 마스크
바깥을 검정으로 채우는 마스킹 전처리)를 실제 서비스(`worker/models/`)에 반영하는 게 목표다.

⚠️ **참고**: bbox 크롭 vs 마스킹 비교는 이번 세션에서 임계치(`score`/`mask_threshold`/
`GARMENT_OVERLAP_MIN` 등)를 계속 조정하며 진행 중이었고, "결론(실행 후 채울 것)" 항목이
채워진 정량 비교 결과가 아니라 육안 판단 기준의 결정이다. 라벨링된 검증셋 확보 전이라는
점(LAB-46/007 계획의 공통 한계)은 이 통합 이후에도 그대로 남는다 — `condition_score` 등급
경계·가중치 확정은 여전히 별도 작업이다.

## 왜 단순 스왑이 아닌가 — 계약 불일치

`worker/models/clipseg/segmenter.py`의 `DefectSegmenter.segment()` 계약은 **CLIPSeg 전용
모양**이다:

```python
class SegmentationResult:
    masks: dict[str, np.ndarray]   # 프롬프트 문자열 -> (H,W) 연속 확률 히트맵 [0,1]
    clean_mask: np.ndarray         # "clean fabric" 대조 프롬프트의 같은 모양 히트맵
    ...
```

그리고 `findings.py`(정규화 → 3×3 섹션 풀링 → 임계치 이진화 → flood-fill blob 추출 → 프롬프트
간 병합)는 이 **연속 히트맵**을 전제로 짜여 있다.

SAM3 PCS는 이미 **인스턴스**(마스크+박스+score)를 직접 준다 — 확률 히트맵이 아니다. 그대로
꽂으면 안 되고 아래 두 방식 중 하나를 골라야 한다.

### 방식 A — 어댑터 (기존 코드 재사용, 빠름)

SAM3 인스턴스를 계단함수 형태의 "가짜 확률 히트맵"으로 래스터화하고, `clean_mask`는 0으로
채워 기존 `findings.py`/`overlay.py`를 안 건드리고 그대로 태운다.

- 장점: `findings.py`/`overlay.py`/`scoring.py` 전부 무수정. 새 코드는 `segmenter.py`의
  새 클래스 하나뿐.
- 단점: SAM3가 이미 알고 있는 인스턴스 정보(개별 마스크 경계)를 히트맵으로 뭉갰다가
  이진화·flood-fill로 다시 뽑아내는 우회 — SAM3를 쓰는 이유(정밀한 인스턴스 마스크)가
  퇴색한다. `clean_mask` 대조 정규화 개념 자체가 SAM3엔 없어 억지로 끼워 맞추는 것.

### 방식 B — 네이티브 경로 (새 추출 함수, 정직하지만 손이 더 감)

`findings.py`에 `extract_findings_from_instances(...)` 같은 병행 경로를 추가해서, 이진화·
flood-fill 없이 SAM3 인스턴스에서 바로 `_Blob`(bbox·area_ratio·peak·section_no)을 만든다.
섹션 넘버링은 인스턴스 마스크/bbox 중심이 3×3 그리드 어디에 속하는지로 계산(로직은 다르지만
개념은 `_section_peaks`와 동일).

- 장점: SAM3 출력을 있는 그대로 쓴다. `clean fabric` 대조 같은 CLIPSeg 전용 개념을
  억지로 안 만든다.
- 단점: `findings.py`에 새 함수 + 새 테스트가 필요하다(§7의 "테스트 공백" 참고). 프롬프트
  간 병합(`_merge_across_prompts`)도 SAM3에 맞게 다시 판단해야 한다(SAM3는 프롬프트마다
  독립 호출이라 CLIPSeg와 같은 중복 검출 위험이 있을 수 있음 — 003/005 계획의 "임계치는
  백엔드마다 묶는다" 원칙과 같은 이유로 병합 로직도 백엔드별로 갈릴 수 있다).

**권장: 방식 B.** 방식 A는 SAM3 도입의 실익(정밀 인스턴스)을 스스로 깎아 먹는다. 다만 손이
더 가므로 최종 선택은 §확인 필요한 미결정 사항에서 사용자가 확정한다.

## 작업 내용

1. **`worker/models/sam3/` 새 패키지** — `worker/models/clipseg/`와 같은 파일 규약
   (`registry.py`/`segmenter.py`/`contracts.py` 등)을 따르되, `contracts.py`는
   `worker/models/clipseg/contracts.py`와 **같은 필드셋**을 그대로 미러링한다(BE 계약은
   안 바뀌므로 새로 설계하지 않는다 — 006 계획의 "워커별 폴더" 관례를 따름).
2. **마스킹 전처리는 세그멘터 내부**에 둔다 — `sam3_qc_test_masking.ipynb`의
   `crop_to_garment()`(의류 bbox 크롭 + 마스크 밖 검정 채움) 로직을 SAM3 세그멘터의
   전처리 단계로 이식한다. 이건 어느 방식(A/B)을 택하든 동일하게 필요하다.
3. **`registry.py`에 `SEGMENTER_BACKENDS["sam3_pcs"]`(가칭) 추가** — `model_id`,
   임계치(`score`/`mask_threshold`/`garment_score` 등, 이번 세션에서 조정한 값 기준)를
   백엔드별로 분리해서 넣는다(003/005 계획의 "임계치는 백엔드별로 묶는다" 원칙).
   `ACTIVE_SEGMENTER`는 여전히 `"mock"`으로 둔다 — 실백엔드 전환은 사용자만 한다
   (`AI/CLAUDE.md` 하드 룰, GMS와는 무관하지만 같은 원칙 적용).
4. **의존성** — `worker/models/sam3/requirements.txt` 신규(=
   `validation/QUAL/sam3-condition-check/requirements-sam3.txt` 이식, `transformers>=5.0`).
   `worker/requirements.txt`(torch/transformers 없음) 규약은 그대로 유지 — 006 계획의
   "모델 의존성은 각자 conda 환경" 원칙 그대로.
5. **gated 접근** — `facebook/sam3`는 HF gated repo. 배포 환경에서 접근 승인된 계정의
   토큰을 워커에 어떻게 넘길지(`HF_TOKEN` 환경변수 등)를 정리한다.
6. **`worker/quality_check_worker_example.py`는 무수정** — `build_segmenter(QUALITY_BACKEND)`
   팩토리 하나로 백엔드가 갈리므로, 오케스트레이션 코드는 이미 이 스왑을 지원한다.

## 영향받는 기존 코드 (건드리게 되는 것)

- `worker/models/clipseg/registry.py`의 `test_clipseg_backends.py::test_expected_backends_are_available`가
  `set(_BACKENDS) == {"mock", "clipseg_rd64_refined"}`를 하드 assert 하고 있어, 새 백엔드
  키를 추가하면 **이 테스트가 바로 깨진다** — 같이 갱신해야 한다(단, 이 assert는
  `worker/models/clipseg/`의 레지스트리를 보는 것이라, SAM3를 별도 패키지
  `worker/models/sam3/`에 독립 레지스트리로 두면 이 테스트 자체를 안 건드릴 수도 있다 —
  세그멘터 팩토리를 CLIPSeg 전용으로 유지할지, 두 백엔드를 아우르는 공통 레지스트리로 합칠지도
  결정 필요, 아래 미결정 사항 참고).
- `findings.py`/`overlay.py`(방식 A 선택 시 무수정, 방식 B 선택 시 신규 함수 추가).

## 지금 없는 것 — 새로 써야 하는 테스트

현재 `AI/test/worker/clipseg/`에는 `segmenter.py`(실제 세그멘테이션 호출)·`findings.py`
(마스크→Finding 변환)·`overlay.py`를 직접 검증하는 테스트가 없다(레지스트리 구조·프롬프트
조립·시나리오 로더·점수 상수 구조만 검증됨). SAM3 경로는 **이 공백을 새로 메워야** 한다 —
최소한 순수 로직(섹션 넘버링, blob/인스턴스 → Finding 변환)은 torch 없이 단위테스트 가능하게
설계한다(mock 인스턴스 dict를 입력으로 주는 방식, `MockSegmenter`가 이미 하는 것과 같은 패턴).

## 구현 목록

- [ ] 방식 A vs B 확정 (아래 미결정 사항)
- [ ] `worker/models/sam3/` 패키지 골격 (`registry.py`/`segmenter.py`/`contracts.py`)
- [ ] 마스킹 전처리(`crop_to_garment` 변형) 이식
- [ ] `SEGMENTER_BACKENDS`에 SAM3 백엔드 추가 (또는 별도 레지스트리, 미결정 사항 참고)
- [ ] `worker/models/sam3/requirements.txt` 작성
- [ ] `test_clipseg_backends.py::test_expected_backends_are_available` 갱신(영향 있을 경우)
- [ ] SAM3 경로 신규 테스트 — 섹션 넘버링, Finding 변환 (torch 없이 순수 로직 부분)
- [ ] gated 토큰 전달 방식 문서화
- [ ] `ruff`/`black`/`pytest` 로컬 통과 확인 후 커밋 (push는 사용자)
- [ ] AI/CLAUDE.md 참조 문서 표에 필요시 갱신

## 확인이 필요한 미결정 사항

1. **방식 A(어댑터) vs 방식 B(네이티브)** — 권장은 B지만 최종 확정 필요.
2. **레지스트리를 합칠지 분리할지** — `SEGMENTER_BACKENDS`(현재 CLIPSeg 전용 레지스트리)에
   SAM3 키를 얹을지, 아니면 `worker/models/sam3/registry.py`로 완전히 분리해 워커가 실행 시
   `QUALITY_BACKEND` 값에 따라 어느 패키지의 `build_segmenter()`를 쓸지 분기할지.
3. **SAM3 임계치 확정값** — `score`/`mask_threshold`/`garment_score`/`GARMENT_OVERLAP_MIN`
   등을 이번 세션 스파이크의 마지막 실험값으로 그대로 가져올지, 별도로 재확인할지.
4. **gated 토큰 배포 방식** — 팀 계정 토큰을 워커 실행 환경에 어떻게 두는지(환경변수 vs
   `hf auth login` 캐시 공유 등)는 인프라 쪽과 협의가 필요할 수 있다.
5. **sVLM 설명 생성 파이프라인은 이 계획 밖이다** — 다음 작업으로 예고된 불릿 리스트·설명
   생성(LAB-43 연장)은 findings 추출 로직이 안정된 뒤 별도 계획 문서로 다룬다.
