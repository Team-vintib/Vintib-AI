# 이 폴더에 대해

`worker/models/catvton/`(프로덕션 참조 구현, `tryon_worker_example.py`가 그대로 import해서
쓴다)를 `S15P11A108-367`(데이터 특징 추출 기법 검증) 실험용으로 그대로 복제해 왔다
(2026-07-29 기준 스냅샷, 자동 동기화 안 됨).

**`worker/models/catvton/`은 건드리지 않는다.** 여기서 `model/cloth_masker.py`(특징
추출/마스킹), `model/pipeline.py` 등을 자유롭게 고쳐 실험하고, 결과를 원본과 비교한다.
쓸만한 개선이 나오면 그때 `worker/models/catvton/`에 반영한다(validation → 프로덕션 승격
경로, `CLAUDE.md` "app/shared/ — validation/에서 승격 시 여기로"와 같은 원칙).

무거운 서드파티 코드(`detectron2/`, `densepose/`)까지 포함된 전체 복제라 `pyproject.toml`의
`extend-exclude`에 lint/format 대상에서 제외해 뒀다(`tryondiffusion`과 동일 처리).

실행 방법은 `worker/README.md`의 CatVTON 워커 절, 원본 검증 스크립트는
`verify_fit_tryon.py`/`benchmark_catvton.py` 참고.
