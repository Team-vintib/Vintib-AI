# CH030 — 채팅 욕설 판정기: rule_based → KcELECTRA-base-hate 교체

에픽 `S15P11A108-217`, 커밋 키 `S15P11A108-571`.

## 배경/목표

채팅 욕설/혐오 판정은 지금 `ACTIVE_CLASSIFIER = "rule_based"`(사전+우회패턴 정규화)로
동작한다 — `classifier_benchmark.ipynb` 실측 기준 accuracy 66.7%/악성 recall 16.7%로,
욕설 10건 중 8건 이상을 놓친다. 후보로만 registry에 있던 `kcelectra_base_hate`
(`beomi/beep-KcELECTRA-base-hate`)는 accuracy 99.5%/recall 98.8%로 훨씬 정확하다.

오늘 CPU 추론 지연시간을 직접 실측했다(`nlp` conda 환경, 4스레드): p95 253.09ms.
rule_based 설계 당시 잡아둔 목표(p95 300ms, `eval_report.md`) 안에는 들어오지만 여유가
크지 않다. 동시 다발 요청(라이브 방송 동접 다수가 동시에 채팅) 상황의 지연은 아직
실측 전이다.

## 작업 내용

- `AI/app/chat/registry.py`의 `ACTIVE_CLASSIFIER`를 `"kcelectra_base_hate"`로 변경.
  `rule_based`/`RuleBasedClassifier` 코드는 삭제하지 않고 `CLASSIFIER_BACKENDS`에 그대로
  둔다 — 원복은 이 한 줄만 되돌리면 된다(레지스트리 패턴이 이미 "백업"을 전제로 설계돼
  있음, 별도 legacy 파일 분리 불필요).
- **`AI/requirements.txt`(서빙 컨테이너, torch 없음)에 torch(CPU)+transformers 추가 필요.**
  지금 AI 컨테이너는 의도적으로 torch-free다(무거운 추론은 전부 `worker/`가 담당) — 이번이
  처음으로 서빙 경로에 실제 추론 모델이 들어가는 경우다. 이미지 크기/기동 메모리 증가를
  감수하는 결정임을 명시.
- **모델을 컨테이너 기동 시 미리 로드(eager)해야 한다.** `get_chat_service()`가
  `@lru_cache` 싱글턴이라 지금처럼 두면 배포 후 **첫 채팅 메시지**가 모델 로딩(실측
  132초, 캐시 있으면 더 짧음)을 그대로 떠안는다 — 라이브 방송 중 첫 채팅이 2분 넘게
  걸리는 건 용납 불가. `AI/app/main.py`에 startup 훅을 추가해 기동 시점에
  `get_chat_service()`를 미리 호출해둔다(이 코드베이스에 startup 훅 패턴이 아직 없어
  새로 추가).

## 구현 목록

- [ ] `AI/requirements.txt`에 `torch`(CPU wheel)/`transformers` 추가
- [ ] `AI/app/chat/registry.py`: `ACTIVE_CLASSIFIER = "kcelectra_base_hate"`
- [ ] `AI/app/main.py`: FastAPI startup 이벤트에서 `get_chat_service()` 미리 호출(모델 eager 로딩)
- [ ] 배포 후 실제 채팅 트래픽으로 지연시간 재확인(동시 요청 상황 포함)
- [ ] `AI/app/chat/artifacts/eval_report.md`류 산출물이 있으면 최신 판정기 기준으로 갱신 검토

## 확인 필요

- 동시 다발 요청 시 CPU 경합으로 p95가 300ms를 넘는지 — 넘으면 방송 채팅 체감 지연으로
  이어지므로, 넘을 경우 별도 대응(예: 짧은 텍스트만 빠르게 처리, 큐잉 등) 검토 필요
- 컨테이너 이미지 크기/메모리 증가분이 배포 환경(EC2 스펙) 안에서 감당되는지
