# 상품 등록 — AI 모델 착용컷 생성 (S15P11A108-568)

에픽 `S15P11A108-211` 소속.

## 배경

FE 상품 등록 화면(`ProductRegistrationPage.vue`)에 "AI 착용컷 설정" 섹션이 이미 있다 —
사용 여부(사용함/사용 안 함) + 성별(여성/남성) 2단계 토글이다. 하지만 **완전히
미완성**이다: 선택값이 draft 상태에 잡히기만 하고 제출 시 API 요청에서 빠지며,
호출할 백엔드 API 자체가 없고, 결과 이미지 개념(URL, 상태 등)도 타입에 없다.

"여성"/"남성"이라는 이름 자체는 FE 화면 문구고, "희동이"/"도우너"는 AI 쪽에서 붙인
내부 검증 페르소나 이름이다(`AI/docs/tryon-advancement-strategy.md` §9~§10) — 매핑은
자연스럽게 남성→희동이, 여성→도우너가 된다(그 검증에 실제로 쓴 페르소나이기도 하다).

**AI 쪽 파이프라인은 이미 프로덕션에 있다.** `S15P11A108-504`로 승격한
`worker/tryon_worker_example.py`(VLM 캡션 → FLUX worn-reference → CatVTON 합성)가
정확히 이 용도로 쓸 수 있다 — 고정 인물 사진을 `user_image_url` 자리에, 판매자가
등록 중 올린 상품 사진을 `product_image_url` 자리에 넣으면 끝이다. 새로운 추론
로직이 필요 없다(희동이/도우너 사진 자체가 그 파이프라인 검증에 실제로 썼던 것과
동일 파일이다).

## 접근 방식

### 1. 페르소나 참조 이미지 — AI가 자체 호스팅 (완료, 방향 수정)

처음엔 "BE가 자체 버킷에 업로드해서 URL을 만들어달라"고 요청할 계획이었으나,
**job 호출·페르소나 관리 같은 AI 관련 인프라는 AI 팀이 직접 맡기로 한 기존 결정**과
어긋나서 방향을 바꿨다. 페르소나 이미지 2장(`heedongi.png`/`dooner.png`)은
`AI/app/static/personas/`에 두고 `AI/app/main.py`가 `/personas`로 정적 서빙한다 —
BE는 이 URL을 몰라도 되고, 업로드·관리도 필요 없다.
(`worker/models/catvton/assets/personas/`에도 같은 파일이 있다 — 그건 워커 코드가
참조하는 원본 자산 위치이고, `AI/app/static/personas/`는 게이트웨이 컨테이너가
실제로 배포·서빙하는 사본이다. `AI/Dockerfile`이 `AI/` 안만 `COPY`하므로 워커 쪽
파일을 게이트웨이 이미지에서 직접 참조할 수 없어 사본이 필요했다.)

### 2. 새 AI 추론 로직 — 없음, 대신 얇은 트리거 엔드포인트 하나 추가

추론 자체는 기존 `type="tryon"` job 계약(`worker/tryon_worker_example.py`)을
**그대로** 쓴다. 다만 "job 호출은 AI가 한다"는 방향에 맞춰, BE가 범용
`POST /ai/{feature}`의 job payload 스키마(`user_image_url`/`mask_type`/`fit_type`
조합)를 직접 몰라도 되도록 전용 엔드포인트를 새로 만들었다:

- `POST /ai/tryon/registration-model-cut` (`AI/app/tryon/router.py`, 신규) — BE가
  상품 사진 URL과 성별만 넘기면, AI가 내부에서 페르소나 URL을 골라 기존 `tryon`
  큐(`queue:tryon`)에 그대로 job을 넣는다. 응답은 `{"job_id": ...}` 접수증뿐이다.
- 결과 조회는 새 엔드포인트를 만들지 않았다 — 일반 시착 job과 완전히 같은 결과
  계약이라 기존 게이트웨이 공통 경로 `GET /ai/jobs/{job_id}`를 그대로 쓴다.
- `mask_type`(상의/하의)은 여전히 BE가 상품 카테고리 기준으로 정해 보내야 한다
  (`docs/requests/BE/035-tryon-product-category.md`가 풀리기 전까지). `fit_type`은
  `regular`로 고정한다.

### 3. BE 요청 — 크게 축소됨

이제 BE는 AI의 job 큐 내부 스키마를 몰라도 된다. 필요한 건:
- 상품 등록 시 `aiModelEnabled=true`면 `POST /ai/tryon/registration-model-cut`
  (상품 사진 URL + 성별 + mask_type)을 호출해 `job_id`를 받는다.
- `GET /ai/jobs/{job_id}`로 폴링해 완료 시 결과 이미지를 상품의 보조 이미지로
  저장한다(어떤 테이블/필드로 둘지는 BE 판단).
- FE에는 이 결과(생성 상태 + 이미지 URL)를 조회할 수 있는 응답 필드가 필요하다.

### 4. FE 요청 — 실제 연동

지금 있는 토글(`aiModelEnabled`/`aiModelGender`)을 실제로 제출 payload에 포함하고,
결과(생성 중/완료/실패, 이미지 URL)를 받아서 보여주는 UI가 필요하다. BE·FE가
주고받을 정확한 필드는 요청 문서(`docs/requests/BE/039-*`,
`docs/requests/FE/035-*`)에 API 명세로 정리했다.

## 범위 밖

- 페르소나 확장(현재 성별 2종 외 체형 등 추가 옵션) — 지금 FE 토글이 성별 2종뿐이라
  맞춘다.
- AI 쪽 새 추론 로직 — 기존 tryon job 계약 재사용으로 충분.
- 실시간 진행률 표시 등 UX 디테일 — BE/FE 소관.

## 커밋 계획

브랜치 `feat/211-registration-ai-model-tryon`, 커밋 키 `[S15P11A108-568]`:
1. `chore:` 페르소나 참조 이미지를 `worker/models/catvton/assets/personas/`로 정리
2. `docs:` 계획 문서(이 문서)
3. `docs:` BE 전체 연동 요청 문서
4. `docs:` FE 실제 연동 요청 문서
5. `feat:` `POST /ai/tryon/registration-model-cut` 트리거 엔드포인트 + 페르소나
   정적 서빙(`AI/app/static/personas/`, `AI/app/main.py`), 테스트
6. `docs:` 방향 수정 반영(페르소나 호스팅·job 호출은 AI 소관) — 계획 문서 + BE/FE
   요청 문서에 API 명세 추가
