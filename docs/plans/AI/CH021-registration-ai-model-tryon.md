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

### 1. 페르소나 참조 이미지를 프로덕션 위치로 정리 (완료)

`worker/models/catvton/assets/personas/{heedongi,dooner}.png` — 검증 폴더
(`AI/validation/`)가 아니라 워커가 실제로 참조할 위치로 복사했다. 지금은 워커가
이 파일을 직접 읽지 않는다(아래 3번 참고) — BE가 한 번 자체 스토리지에 업로드해서
안정적인 URL을 만드는 게 목적이다.

### 2. 새 AI 추론 로직 — 없음

기존 `POST /ai/tryon` job 계약(`AI/app/tryon/schemas.py`, `worker/
tryon_worker_example.py`)을 **그대로** 쓴다. `mask_type`(상의/하의는 상품 카테고리에
따라 BE가 정하거나, `docs/requests/BE/035-tryon-product-category.md`가 풀리기
전까지는 요청 시 값을 지정), `fit_type`은 기본값(regular)이면 충분하다 — 판매자가
등록 중에 상세 사이즈까지 고르게 하는 건 범위 밖으로 본다(이미 등록 흐름이 복잡하다).

### 3. BE 요청 — 전체 연동 필요 (범위가 크다)

BE 쪽엔 지금 아무것도 없어서(값도 안 보냄, API도 없음), 요청 문서에 전체 흐름을
정리해서 전달한다:
- 페르소나 이미지 2장(`worker/models/catvton/assets/personas/*.png`)을 BE 자체
  퍼블릭 버킷에 한 번 업로드하고, 그 URL을 저장(설정값 또는 상수)
- 상품 등록 시 `aiModelEnabled=true`면, 업로드된 상품 사진 + 위 URL로 `POST /ai/tryon`
  job을 생성
- job 완료 후 결과 이미지를 상품의 보조 이미지로 저장(어떤 테이블/필드로 둘지는 BE
  판단 — 새 컬럼이 될 수도, 기존 상품 이미지 테이블에 "AI 생성" 플래그를 추가하는
  것일 수도 있다)
- FE에는 이 결과(생성 상태 + 이미지 URL)를 조회할 수 있는 응답 필드가 필요하다

### 4. FE 요청 — 실제 연동

지금 있는 토글(`aiModelEnabled`/`aiModelGender`)을 실제로 제출 payload에 포함하고,
결과(생성 중/완료/실패, 이미지 URL)를 받아서 보여주는 UI가 필요하다. BE 계약이
먼저 확정돼야 하므로, 이번엔 "이런 필드가 올 것이다" 정도만 미리 공유한다.

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
