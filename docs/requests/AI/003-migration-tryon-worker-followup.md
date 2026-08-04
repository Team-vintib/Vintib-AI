# AI 디렉터리 구조 마이그레이션 — 시착·워커 파트 후속 확인 요청

- **요청자 파트**: AI (구조 마이그레이션 담당, `feat/27-ai-structure-migration`)
- **대상 파트**: AI — 시착(TRYON) / 워커 담당자
- **관련 티켓**: `S15P11A108-189`(이번 마이그레이션) / `-191`, `-194`(시착 워커)

## 배경

`AI/docs/infra-architecture.md`가 규정한 구조(`AI/app`=라우팅, `worker/`=추론,
`AI/test`=실제 테스트, `AI/validation`=PoC)에 맞춰 디렉터리를 재배치했습니다.
그 과정에서 **시착·워커 쪽에 담당자 확인이 필요한 항목**이 생겼습니다.

이 문서의 항목은 제가 직접 처리하지 않고 남깁니다 — 담당자 로컬 작업물과 충돌할 수 있거나,
판단이 필요한 사안입니다.

---

## 1. `AI/tryon_service/` 를 삭제했습니다 — 확인 부탁드립니다

`-191`(커밋 `23895fe`, 7/24)의 작업물입니다. **되돌리려면 `git revert`, 원본 열람은
`git show 23895fe`** 입니다.

삭제 근거:

- 최초 커밋부터 실행 불가였습니다. 내부 import가 전부 `from app.*`인데 `AI/tryon_service/`에
  커밋됐고, 그 시점 `AI/app/`은 존재하지도 않았습니다(이틀 뒤 `d0549bb`로 다른 내용으로 생성).
- `api/routes/tryon.py`가 최초 커밋부터 `schemas/tryon.py`와 **바이트 단위로 동일**했습니다.
  `main.py`가 import하는 `router`가 애초에 없었습니다.
- Celery + 워커의 Redis 직접 접속 설계라 인프라 문서 §2("워커는 Redis에 직접 접속하지 않는다")와
  충돌합니다. `celery`는 `requirements.txt`에 없습니다.
- **결정적으로, `worker/tryon_worker_example.py`(`ef4ecfb [-194]`, 7/26)가 이미 대체합니다.**
  삭제한 `tasks.py`가 가진 것(체크포인트·bf16·DensePose/SCHP·768×1024·blur 9·seed 42)을 전부
  포함하고, safety checker 우회 · 원본 합성 · 마스크 프리뷰 · `base_worker` 폴링까지 더 있습니다.

**확인해 주실 것**: `-194`가 `-191`을 의도적으로 대체한 게 맞는지, 아니면 `tryon_service/`에
아직 살아 있어야 할 게 있는지.

### 살려둔 계약 — 빠진 게 없는지 봐주세요

`AI/app/tryon/schemas.py`로 옮겼습니다(`-181`/`-182` 결정이라 대체된 적 없다고 판단).

| 남김 | `MaskType`(upper/lower/overall/inner/outer) · `MaskFitType`(regular/oversized/cropped) · `num_inference_steps`(10~50, 기본 30) · `guidance_scale`(1.0~10.0, 기본 2.5) · 업로드 정책(jpeg/png/webp, 10MB) · 해상도 768×1024 |
| 버림 | `TryOnStatus` · `TryOnRequestAccepted` · `TryOnResult` — 게이트웨이 `JobStatus`/`{job_id}`/`JobResult`와 중복 |

`router.py`·`service.py`는 만들지 않았습니다. 비동기 전환 때 함께 만드는 게 맞다고 봤습니다.

---

## 2. 워커 CatVTON 경로가 바뀌었습니다

`AI/test/` → `AI/validation/` 이름 변경 때문입니다. **제가 이미 수정했지만**, 로컬에서
`CATVTON_CODE_PATH`를 직접 export 해서 쓰고 계셨다면 그 값도 바꾸셔야 합니다.

```bash
# 기존
export CATVTON_CODE_PATH=/path/to/AI/test/AI_tryon/catvton
# 변경 후
export CATVTON_CODE_PATH=/path/to/AI/validation/AI_tryon/catvton
```

수정한 곳: `worker/tryon_worker_example.py:18` 기본값, `worker/README.md` 3곳,
`AI/docs/tryon-advancement-strategy.md` 1곳. import 대상 3개
(`model/pipeline.py`·`model/cloth_masker.py`·`utils.py`)가 새 경로에 존재하는 것까지
확인했습니다. 단 **워커 실제 실행은 GPU 노트북에서만 가능해 검증하지 못했습니다.**

---

## 3. 워커 설정에 남은 것 — 커밋 누락으로 보입니다

리포에 없는데 있어야 하는 파일 2개입니다. 둘 다 gitignore 대상이 **아닙니다**.

| 파일 | 상황 |
| --- | --- |
| `worker/storage_utils.py` | `tryon_worker_example.py`가 `from storage_utils import download_image, upload_image` 합니다. **이 파일 없이는 워커가 기동조차 하지 않습니다.** `worker/README.md` 파일 구성표와 인프라 문서 §7에도 있어야 할 파일로 적혀 있습니다 |
| `worker/.env.example` | README 표에 있으나 실제로는 없습니다. `GATEWAY_URL`·`WORKER_API_KEY`·`CATVTON_CODE_PATH` 예시가 들어가면 될 것으로 보입니다 |

**제가 만들지 않았습니다** — 로컬에 이미 있으실 가능성이 높고, 제가 새로 쓰면 충돌합니다.
커밋해 주시면 됩니다. 그때까지 `worker/README.md` 표에는 부재 사실만 명시해 뒀습니다.

추가로 `worker/requirements.txt`가 README에는 `requests`, `Pillow`로 적혀 있었으나 실제로는
`requests`만 있습니다. 일단 **서술을 실제에 맞췄는데**, `Pillow`가 필요한 게 맞다면
`requirements.txt` 쪽을 고치는 게 맞습니다(워커가 `PIL.Image`를 씁니다).

---

## 4. ⚠️ 품질 검수 쪽은 건드리지 말아 주세요

**요청자(구조 마이그레이션 담당)가 이어서 직접 진행합니다.** 아래는 이번 MR에서 의도적으로
손대지 않은 상태이며, 다른 분이 정리하면 작업이 충돌합니다.

- `AI/app/quality/` — 전체. 프롬프트·임계치·하자 항목화·점수·오버레이가 구현돼 있습니다.
  `ClipSegSegmenter`가 `app/` 안에 남아 있는 건 **알고 있는 아키텍처 위반**입니다.
  후처리(1038줄)를 목업 동기 API와 공유하고 있어서, 워커 이관과 비동기 전환을 함께 해야
  정리됩니다. 컨테이너에 torch가 없어 실행되지 않는 코드라 운영상 영향은 없습니다.
- `worker/quality_check_worker_example.py` — `run_inference()`가 `NotImplementedError`
  스텁인 채로 둡니다. 위 이관과 함께 채웁니다.
- 품질 검수 테스트 — 작성·통과 확인이 끝난 6개 파일을 별도 보관 중입니다. 코드 위치가
  확정된 뒤 `AI/test/quality/`에 올립니다.

---

## 관련 자료

- 구조 규정: `AI/docs/infra-architecture.md` §2(워커는 Redis 직접 접속 금지) /
  §3.2(게이트웨이는 추론하지 않음) / §6(기능별 처리 방식) / §7(디렉터리 구조)
- 변경된 규율: `AI/CLAUDE.md` — 디렉터리 구조, 테스트 배치 규칙(basename 유일성 등)
- 시착 고도화 방향: `AI/docs/tryon-advancement-strategy.md`
