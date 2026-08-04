# 017 사업자 정보 조회 · 세금계산서 — 남은 FE 항목

- **요청 파트**: BE / **대상 파트**: FE

> 사업자등록증 업로드·제출은 반영 완료되어 덜어냈다. 아래 2건이 남았다.

## 남은 항목

### 1. 사업자 정보 조회 — `GET /api/users/{userId}/business`
- 응답 구조는 제출 결과와 동일. **제출 이력이 없어도 200**(`status: "NONE"`, 나머지 필드 전부 `null` — 에러 아님, 빈 폼 처리).
- `certificateUrl`은 만료 10분 presigned GET — 오래 캐싱 금지.
- 현재 FE엔 사업자 GET 함수가 없고 상태를 `sessionStorage`로만 들고 있다.

### 2. 세금계산서 발행/조회 — `POST`/`GET /api/orders/{orderId}/invoices`
- 발행(POST): 본문 없음, 주문당 1건. 조회(GET): 없으면 404(`I002`).
- 에러: `I001`(중복), `I003`(판매자 인증 `APPROVED` 미완), `I004`(당사자 아님).
- 현재 FE엔 invoice 코드가 없다. (주문 도메인 성격이라 현재 FE 스코프 밖일 수 있음 — 확인 필요)

## 관련 자료
- Swagger `/swagger-ui/index.html` "사업자(Businesses)" 태그 · `BusinessInfoController`, `InvoiceController`
