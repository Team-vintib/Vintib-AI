# SY026 — 사업자 정보 제출(BIZ-001) + 세금계산서 발행(BIZ-002)

## 배경/목표

`APIs.md` "사업자(Businesses)" 섹션의 `POST /users/{id}/business`(BIZ-001), `POST/GET /orders/{id}/invoices`(BIZ-002)가 전부 미구현이다. 이번 범위는 **BIZ-001의 제출/조회/재제출**과 **BIZ-002(세금계산서 발행/조회)**로 한정한다 — 관리자 승인/거절, `PATCH`(MY-008 정보 수정)는 이번 범위 밖(이 프로젝트에 관리자 권한 체계 자체가 없음: `MemberType`은 `GENERAL`/`BUSINESS`뿐, `ADMIN` 없음).

`orders`는 스키마만 있고 엔티티/서비스/컨트롤러가 전혀 없다(0%, `docs/requests/BE/010-commerce-wallet-contract.md` 확인). 세금계산서가 주문을 FK로 참조해야 하므로, 이번에 **Order는 엔티티+레포지토리(FK 대상용, `findById`만)**, **Invoice는 신규 테이블+엔티티+서비스+컨트롤러까지 온전히** 구현한다(사용자 승인 사항). **주문 생성 API가 없으므로, 테스트·시연 시 `orders` 행은 직접 SQL로 심어야 한다.**

FE 요청 문서(`docs/requests/BE/003-business-contract.md`)가 요청한 `POST /api/business-verifications`(multipart), `GET /api/business-verifications/me`는 이 프로젝트의 반복된 전례(온보딩류는 항상 `/api/users/{id}/X`로 확정)와 확립된 업로드 컨벤션(presigned 2단계, 최근 SY025 시착 프로필과 동일)에 따라 다르게 확정한다. BIZ-002는 FE 요청 문서 자체가 없으므로 이번에 BE 주도로 신규 계약 문서를 만든다.

Jira: BIZ-001 = `S15P11A108-298`, BIZ-002 = `S15P11A108-231`(둘 다 에픽 `S15P11A108-205 [BIZ] 사업자` 하위). 커밋도 이 두 이슈 키로 나눠서 진행한다.

## 작업 내용

### 1) DB 스키마 (`BE/docs/db/schema.sql`, `comments.sql`)

`business_info`(어느 환경에도 아직 생성된 적 없음 — 엔티티가 없어 `ddl-auto:update`가 만든 적이 없다)를 교체:

```sql
-- 사업자 정보 (BIZ-001)
CREATE TABLE business_info (
    member_id            BIGINT PRIMARY KEY REFERENCES member (id),
    business_number      VARCHAR(20)  NOT NULL,
    business_name        VARCHAR(100) NOT NULL,
    representative_name  VARCHAR(50)  NOT NULL,
    -- 비공개(private) 버킷 S3 key. presigned GET으로만 열림 — member_body_profile.body_photo_key와 동일한 이유.
    certificate_key      VARCHAR(500) NOT NULL,
    verification_status  VARCHAR(20)  NOT NULL DEFAULT 'PENDING',
    submitted_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    verified_at          TIMESTAMPTZ,
    CONSTRAINT ck_business_verification
        CHECK (verification_status IN ('PENDING', 'APPROVED', 'REJECTED'))
);
```

`orders`(392행~)는 변경 없음. 신규 `invoice` 테이블을 "7. 주문·배송" 섹션에 추가:

```sql
-- 세금계산서 (BIZ-002). 법적 문서라 발행 시점 사업자 정보를 스냅샷으로 저장한다 —
-- 이후 판매자가 business_info를 바꿔도 이미 발행된 계산서는 안 바뀐다.
-- 주문당 1건만 허용(uq_invoice_order) — 취소/재발행은 이번 범위 밖.
CREATE TABLE invoice (
    id                   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id             BIGINT      NOT NULL REFERENCES orders (id),
    business_number      VARCHAR(20)  NOT NULL,
    business_name        VARCHAR(100) NOT NULL,
    representative_name  VARCHAR(50)  NOT NULL,
    supply_amount        BIGINT      NOT NULL,  -- 공급가액 = round(order_price / 1.1)
    tax_amount           BIGINT      NOT NULL,  -- 부가세 = order_price - supply_amount
    total_amount         BIGINT      NOT NULL,  -- = order_price
    issued_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_invoice_order UNIQUE (order_id)
);
```

`comments.sql`: `business_info` 코멘트를 새 컬럼명(`certificate_key`)에 맞게 고치고 `business_name`/`representative_name` 코멘트 추가. "주문·배송" 구역에 `invoice` 코멘트 추가. 구현 후 `bash docs/db/regen.sh`로 `data-dictionary.md` 재생성(`erd.md`는 SY025와 동일 판단으로 재실행 불필요).

### 2) 엔티티

- **`business/entity/BusinessVerificationStatus.java`** — `PENDING`/`APPROVED`/`REJECTED`(NONE은 DB enum에 없음, row 없음을 서비스 레벨 문자열 `"NONE"`으로 표현).
- **`business/entity/BusinessInfo.java`** — `MemberBodyProfile`과 동일한 공유 PK 1:1(`@Id`+`@MapsId @OneToOne`). 필드: `businessNumber`/`businessName`/`representativeName`/`certificateKey`/`verificationStatus`/`submittedAt`/`verifiedAt`. `@Builder private BusinessInfo(Member, businessNumber, businessName, representativeName, certificateKey)` — 생성 시 `PENDING`+`submittedAt=now()`. `public void resubmit(businessNumber, businessName, representativeName, certificateKey)` — REJECTED 상태에서만 서비스가 호출, `PENDING` 리셋 + `submittedAt` 갱신 + `verifiedAt=null`.
- **`order/entity/OrderStatus.java`** — `PAID/SHIPPING/DELIVERED/CONFIRMED/SETTLED/REFUNDED/CANCELED`.
- **`order/entity/Order.java`** — `orders` 그대로 매핑(`buyer`/`seller`→`Member`, `product`→`Product`, `auction`→`Auction` nullable, `orderPrice`, `status`, `autoConfirmAt`, `BaseTimeEntity` 상속). **`@Builder(access = AccessLevel.PACKAGE)`** — 서비스/컨트롤러가 없어 외부 생성 경로 자체를 막는다(테스트 시딩은 SQL 직접 삽입 또는 같은 패키지 테스트에서만 빌더 사용). 헬퍼: `public boolean isPartyOf(Long memberId) { return memberId != null && (buyer.getId().equals(memberId) || seller.getId().equals(memberId)); }`
- **`order/entity/Invoice.java`** — `order`(`@ManyToOne LAZY`, `order_id` unique), `businessNumber`/`businessName`/`representativeName`(스냅샷), `supplyAmount`/`taxAmount`/`totalAmount`, `issuedAt`. 정적 팩토리 `Invoice.issue(Order order, String businessNumber, String businessName, String representativeName)`가 `orderPrice`로 부가세 10% 계산(`supplyAmount = Math.round(orderPrice / 1.1)`, `taxAmount = orderPrice - supplyAmount`, `totalAmount = orderPrice`) 후 빌드.

### 3) 레포지토리

- `business/repository/BusinessInfoRepository.java` — `JpaRepository<BusinessInfo, Long>`(PK=`memberId`).
- `order/repository/OrderRepository.java` — `JpaRepository<Order, Long>`(`findById`만 사용).
- `order/repository/InvoiceRepository.java` — `existsByOrder_Id(Long)`, `findByOrder_Id(Long)` 추가.

### 4) DTO

- `business/dto/request`: `BusinessCertificateUploadUrlRequest(@NotBlank String contentType)`, `BusinessInfoSubmitRequest(@NotBlank @Pattern(regexp="\\d{10}") String businessNumber, @NotBlank String businessName, @NotBlank String representativeName, @NotBlank String certificateKey)`
- `business/dto/response`: `BusinessCertificateUploadUrlResponse(String key, String uploadUrl, long expiresInSeconds)`, `BusinessInfoResponse(String status, String businessNumber, String businessName, String representativeName, String certificateUrl, LocalDateTime submittedAt, LocalDateTime verifiedAt)` — `status`는 `"NONE"|"PENDING"|"APPROVED"|"REJECTED"` 문자열.
- `order/dto/response`: `InvoiceResponse(Long id, Long orderId, String businessNumber, String businessName, String representativeName, Long supplyAmount, Long taxAmount, Long totalAmount, LocalDateTime issuedAt)`

### 5) 서비스

**`business/service/BusinessInfoService.java`**(`TryOnProfileService`와 동일 스타일):
- `createUploadUrl`: content-type 검증(jpeg/png/webp, 실패 시 `INVALID_IMAGE_TYPE` 재사용) → key `business-certificates/{memberId}/{uuid}.{ext}` → private 버킷 presigned PUT.
- `submit`(upsert 겸 재제출):
  - row 없음 → `verifyUploaded` 통과 후 신규 생성(`PENDING`).
  - row 있고 `REJECTED` → `verifyUploaded` 통과 후, 인증서 key가 바뀌면 기존 S3 객체 삭제 → `resubmit(...)`.
  - row 있고 `PENDING`/`APPROVED` → `BUSINESS_INFO_ALREADY_SUBMITTED`(409), DB 변경 없음.
  - `verifyUploaded`: key prefix 확인 + `headObject`(`NoSuchKeyException`→`B001`) + 10MB 초과 시 삭제 후 `B001`(`TryOnProfileService`와 동일 로직·상한).
- `getStatus`: row 없으면 `status="NONE"`+나머지 null(예외 아님, 200 정상 흐름). row 있으면 실제 값 + 조회 시점 presigned GET URL.

**`order/service/InvoiceService.java`**(`business` 패키지의 `BusinessInfoRepository`를 직접 참조 — `WishService`가 `ProductRepository`를 직접 참조하는 것과 동일한 "상위 도메인이 하위 도메인 직접 참조" 컨벤션, 포트 불필요):
- `issueInvoice(orderId, memberId)`: 주문 없으면 `ORDER_NOT_FOUND`(O002/404) → `!isPartyOf(memberId)`면 `INVOICE_FORBIDDEN`(I004/403) → 이미 발행됐으면 `INVOICE_ALREADY_ISSUED`(I001/409) → 판매자 `businessInfo`가 없거나 `APPROVED` 아니면 `INVOICE_ISSUER_NOT_APPROVED_BUSINESS`(I003/400) → `Invoice.issue(...)` 저장.
- `getInvoice(orderId, memberId)`: 주문/당사자 확인 동일 → 인보이스 없으면 `INVOICE_NOT_FOUND`(I002/404) → 매핑 반환.

### 6) 컨트롤러

- **`business/controller/BusinessInfoController.java`** — `@RequestMapping("/api/users/{userId}/business")`, `TryOnProfileController`와 동일한 `requireSelf`(불일치 시 `B002`). `POST /upload-url`(200) / `POST`(제출·재제출 겸용 — 신규 생성이어도 201 대신 **200으로 통일**, 같은 엔드포인트가 생성/갱신을 모두 처리해 상태코드 분기가 오히려 혼란스러움) / `GET`(200, row 없어도 `"NONE"`). `@Tag(name = "사업자(Businesses)")`.
- **`order/controller/InvoiceController.java`** — `@RequestMapping("/api/orders/{orderId}/invoices")`. 경로에 `{userId}`가 없어 `requireSelf` 패턴 대신 서비스 내부 `order.isPartyOf(principal)`에 권한 확인을 위임. `POST`(순수 생성이라 **201**) / `GET`(200). `@Tag(name = "세금계산서(Invoices)")`.

두 컨트롤러 모두 `@Operation`/`@ApiResponses`/`@SecurityRequirement(name="bearerAuth")` 기존 컨벤션대로.

### 7) `ErrorCode` 추가

```java
// [지갑/주문] 구역 O001 다음
ORDER_NOT_FOUND(HttpStatus.NOT_FOUND, "O002", "존재하지 않는 주문입니다."),

// 신규 [사업자]
BUSINESS_CERTIFICATE_UPLOAD_NOT_CONFIRMED(HttpStatus.BAD_REQUEST, "B001", "업로드가 확인되지 않았습니다. 먼저 사업자등록증을 업로드해주세요."),
BUSINESS_INFO_FORBIDDEN(HttpStatus.FORBIDDEN, "B002", "본인의 사업자 정보만 처리할 수 있습니다."),
BUSINESS_INFO_ALREADY_SUBMITTED(HttpStatus.CONFLICT, "B003", "이미 제출했거나 승인된 사업자 정보입니다."),

// 신규 [세금계산서]
INVOICE_ALREADY_ISSUED(HttpStatus.CONFLICT, "I001", "이미 발행된 세금계산서입니다."),
INVOICE_NOT_FOUND(HttpStatus.NOT_FOUND, "I002", "발행된 세금계산서가 없습니다."),
INVOICE_ISSUER_NOT_APPROVED_BUSINESS(HttpStatus.BAD_REQUEST, "I003", "판매자가 사업자 인증을 완료해야 세금계산서를 발행할 수 있습니다."),
INVOICE_FORBIDDEN(HttpStatus.FORBIDDEN, "I004", "본인이 거래 당사자인 주문만 처리할 수 있습니다."),
```

### 8) 온보딩 화이트리스트 — 변경 없음

사업자 인증 제출은 온보딩 완료(`PATCH /users/{id}/member-type`) 이후에만 의미 있는 별도 플로우라 기본 차단 동작이 그대로 맞는 정책이다. (참고: `/api/users/*`는 세그먼트 1개만 매칭해 `/api/users/{id}/business`엔 애초에 안 걸림.)

### 9) FE 문서

- `docs/requests/BE/003-business-contract.md` §3.1/§3.2를 "구현 완료, 계약은 다르게 확정됨"(SY025가 이미 쓴 톤)으로 갱신: 경로·업로드 방식·응답 필드 차이 명시, 관리자 승인/`PATCH`는 범위 밖임을 명시.
- 신규 `docs/requests/FE/017-business-invoice-contract.md`(`002-product-image-presigned-upload.md` 형식): BIZ-001 확정 계약 + BIZ-002는 "FE 요청 없었던 BE 주도 신규 API 안내"로 스펙 전달, 주문 생성 API가 없어 실제 호출 가능한 주문이 아직 없다는 제약 명시. 에러코드 표(`B001~B003`/`O002`/`I001~I004`) 포함.
- `docs/requests/BE/006-be-request-index.md` 003번 행 갱신.

### 10) 테스트

**`BusinessInfoServiceTest`**(Mockito, 9건): 업로드URL발급 / 지원안하는이미지타입 / 최초제출성공 / 업로드미확인시B001 / REJECTED재제출성공(필드갱신+PENDING리셋+기존S3삭제) / PENDING상태재제출시도시B003 / APPROVED상태재제출시도시B003 / 조회시row없으면NONE / 조회시실제상태+presignedURL.

**`InvoiceServiceTest`**(Mockito, `Order`/`BusinessInfo`는 `@Mock`으로 스텁 — package-private 빌더 회피, 7건): 발행성공+금액계산검증(orderPrice=110000→supply=100000/tax=10000/total=110000) / 중복발행시I001 / 주문없음시O002 / 당사자아님시I004 / 미승인사업자상태에서발행시도시I003 / 조회성공 / 조회시인보이스없으면I002.

### 11) `BE/README.md`

디렉터리 구조에 신규 패키지 반영:
```
├── business/                    # 사업자 인증 정보 제출/조회 (BIZ-001) — 서윤
│   ├── controller/
│   ├── service/
│   ├── entity/                  # BusinessInfo, BusinessVerificationStatus
│   ├── repository/
│   └── dto/
├── order/                        # 주문 FK 대상 엔티티(CRUD 없음) + 세금계산서 (BIZ-002) — 서윤
│   ├── controller/                # InvoiceController
│   ├── service/                   # InvoiceService
│   ├── entity/                    # Order, OrderStatus, Invoice
│   ├── repository/                # OrderRepository(findById만), InvoiceRepository
│   └── dto/response/
```
담당 분배 목록은 이미 `order`가 있어 텍스트 변경 불필요.

## 구현 목록

- [ ] `schema.sql`(+`comments.sql`) — `business_info` 컬럼 추가/변경, 신규 `invoice` 테이블
- [ ] `regen.sh` 재실행
- [ ] `business/entity/BusinessVerificationStatus.java`, `BusinessInfo.java`
- [ ] `order/entity/OrderStatus.java`, `Order.java`, `Invoice.java`
- [ ] `business/repository/BusinessInfoRepository.java`
- [ ] `order/repository/OrderRepository.java`, `InvoiceRepository.java`
- [ ] `business/dto/*`(request 2, response 2)
- [ ] `order/dto/response/InvoiceResponse.java`
- [ ] `business/service/BusinessInfoService.java`
- [ ] `order/service/InvoiceService.java`
- [ ] `business/controller/BusinessInfoController.java`(Swagger)
- [ ] `order/controller/InvoiceController.java`(Swagger)
- [ ] `ErrorCode`에 `O002`, `B001~B003`, `I001~I004` 추가
- [ ] `docs/requests/BE/003-business-contract.md` 갱신
- [ ] `docs/requests/FE/017-business-invoice-contract.md` 신규
- [ ] `docs/requests/BE/006-be-request-index.md` 갱신
- [ ] `BusinessInfoServiceTest`(9건), `InvoiceServiceTest`(7건)
- [ ] `BE/README.md` 갱신
- [ ] `.claude/skills/BE:verify` 기준 `./gradlew build` 통과 확인

## 확인 필요한 미결정 사항

- 사업자등록증 업로드 용량 상한을 시착 프로필과 동일하게 10MB로 통일함 — 스캔본이라 더 낮은 상한(예: 5MB)이 필요하면 조정 가능.
- 세금계산서 발행 요청을 buyer/seller 누구나 호출 가능하게 설계함(실제로는 "구매자 요청 → 시스템/판매자 확정"이 더 자연스러울 수 있으나 이번 범위에서는 단일 엔드포인트로 단순화) — 필요시 추후 FE 피드백 받아 조정.
- 부가세 계산은 통상적 원단위 반올림만 적용, 세무 법적 정확성 검증은 범위 밖.

## 검증 방법

1. `.claude/skills/BE:verify` 기준 `./gradlew build` 통과 확인(신규 테스트 16건 포함 전체 green).
2. 로컬 Postgres/MinIO로 실제 API 호출 검증: 사업자 인증서 업로드 URL 발급 → MinIO PUT → 제출(PENDING) → 조회 → 같은 상태에서 재제출 시도 시 409 확인 → (DB에서 직접 status를 REJECTED로 바꾼 뒤) 재제출 성공 확인.
3. 세금계산서: DB에 직접 `orders` 행(seller의 business_info를 APPROVED로 미리 세팅) 삽입 → `POST /orders/{id}/invoices` 발행 성공 + 금액 계산 확인 → 중복 발행 409 확인 → 다른 회원 토큰으로 접근 시 403 확인.
4. `BusinessInfoServiceTest`/`InvoiceServiceTest` 전체 통과 확인.
