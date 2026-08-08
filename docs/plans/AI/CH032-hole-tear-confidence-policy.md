# CH032 — HOLE_TEAR도 confidence 비교로 DETECTED 판정

## 배경/목표

`worker/models/sam3/registry.py`의 `DEFECT_TAXONOMY[HOLE_TEAR]`는 `trusted: False`로
고정돼 있어, confidence가 아무리 높아도(실측 0.78~0.82) 항상 `SUSPECTED`로만 나온다
(`findings.py::_status_of()`가 `trusted=False`면 즉시 `SUSPECTED`를 반환하고
`confident_threshold` 비교 자체를 안 함). 근거는 LAB-46 실측 — SAM3가 암홀·넥라인·
밑단·소매끝 같은 구조적 개구부를 구멍으로 오인하는 오탐이 반복 확인됐다는 것.

요청: 이 블랭킷 정책을 풀고, STAIN/DIRT_MARK처럼 **confidence를 `confident_threshold`
(현재 0.55)와 비교**해서 그 이상이면 DETECTED로 승격되게 바꾼다.

## 작업 내용

`_status_of()`(findings.py)는 이미 `trusted=True`인 유형에 대해 이 비교를 수행하는
공통 로직을 갖고 있다 — 새 로직을 만들 필요 없이, `DEFECT_TAXONOMY[HOLE_TEAR]["trusted"]`
값만 `False` → `True`로 바꾸면 된다.

## 구현 목록

- [ ] `worker/models/sam3/registry.py`: `DEFECT_TAXONOMY[DefectType.hole_tear]["trusted"]`를 `True`로 변경
- [ ] 같은 항목의 `evidence` 주석을 "LAB-46 근거로 blanket SUSPECTED였으나, confidence 비교로 전환(CH032)"로 갱신 — 왜 바뀌었는지 이력 남기기

## 리스크 (승인 전 확인 필요)

- LAB-46이 지적한 **구조적 개구부 오탐**은 여전히 존재하는 위험이다. `confident_threshold`
  (0.55)를 넘는 오탐이면 이제 사용자에게 "확정 하자"로 보여진다 — 오탐률이 알려진 만큼,
  임계치를 HOLE_TEAR 전용으로 더 높게(예: 0.7~0.8) 잡을지, 아니면 STAIN/DIRT_MARK와
  같은 0.55를 그대로 쓸지 결정이 필요하다. 라벨링된 검증셋이 없어 어느 쪽도 실측 근거는
  없다 — 이번 결정도 임의값 스윕 대상에 추가된다.
- 이번 변경은 `trusted` 플래그 하나만 바꾸는 것이라, **임계치를 유형별로 분리하려면**
  `confident_threshold`를 세그먼터 전역 설정에서 유형별 설정으로 옮기는 추가 작업이 필요하다
  (이번 계획 범위 밖 — 필요해지면 별도 계획).
