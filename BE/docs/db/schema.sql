-- =============================================================================
-- 빈티지·세컨핸드 의류 라이브 경매 플랫폼 — 전체 스키마 (S15P11A108-296)
-- PostgreSQL 18
--
-- 설계 원칙
--   * enum 은 네이티브 ENUM 타입 대신 VARCHAR + CHECK 로 표현한다.
--     JPA @Enumerated(EnumType.STRING) 과 그대로 맞물리고, 값 추가 시
--     ALTER TYPE 없이 CHECK 만 교체하면 되어 마이그레이션이 가볍다.
--   * 금액은 전부 BIGINT(원 단위 정수). KRW 는 소수점이 없어 NUMERIC 이 불필요하다.
--   * 시각은 전부 TIMESTAMPTZ. 경매 종료 판정이 서버 시각 기준이라 타임존 모호성을 남기면 안 된다.
--   * 삭제는 물리 삭제 대신 상태 컬럼 또는 deleted_at 으로 처리한다.
--
-- 담당 경계: [서윤] 회원·상품·포인트·주문·알림 / [정윤] 라이브·경매·입찰·채팅
-- =============================================================================


-- =============================================================================
-- 1. 회원 [서윤]
-- =============================================================================

CREATE TABLE member (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email             VARCHAR(255) NOT NULL UNIQUE,
    password          VARCHAR(255),                    -- SSO 전용 계정은 NULL.
    google_id         VARCHAR(100) UNIQUE,              -- 구글 로그인 연동. 미연동 회원은 NULL.
    -- 온보딩 완료 전에는 NULL이고, 온보딩 완료 시 애플리케이션에서 필수로 검증한다(UNIQUE만 DB가 보장).
    nickname          VARCHAR(30)  UNIQUE,              -- 경매 최고 입찰자 표시에 사용.
    name              VARCHAR(50),
    phone_number      VARCHAR(20),
    -- 온보딩에서 채워지는 정보. 가입 시점에는 전부 NULL.
    address           VARCHAR(200),
    detail_address    VARCHAR(100),
    postal_code       VARCHAR(10),                     -- 주소 검색을 안 쓰고 직접 입력하면 NULL 허용.
    gender            VARCHAR(10),
    member_type       VARCHAR(20)  NOT NULL DEFAULT 'GENERAL',
    status            VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE',
    profile_image_url VARCHAR(500),
    description       VARCHAR(500),                    -- 소개글
    cover_image_url   VARCHAR(500),                     -- 커버 이미지 URL
    onboarding_done   BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ,
    CONSTRAINT ck_member_type   CHECK (member_type IN ('GENERAL', 'BUSINESS')),
    CONSTRAINT ck_member_status CHECK (status IN ('ACTIVE', 'SUSPENDED', 'WITHDRAWN')),
    CONSTRAINT ck_member_gender CHECK (gender IN ('MALE', 'FEMALE'))
);

-- 전신 사진·신체 정보.
-- body_photo_key: 비공개(private) 버킷에 저장되는 S3 key. presigned GET으로만 열 수 있어
-- 고정 URL이 아니라 key를 저장한다 — tryon_result.image_key와 동일한 이유.
CREATE TABLE member_body_profile (
    member_id      BIGINT PRIMARY KEY REFERENCES member (id),
    body_photo_key VARCHAR(500),
    height_cm      SMALLINT,
    weight_kg      SMALLINT,
    chest_cm       SMALLINT,
    waist_cm       SMALLINT,
    hip_cm         SMALLINT,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 사업자 정보
-- certificate_key: 비공개(private) 버킷 S3 key. presigned GET으로만 열림 — member_body_profile.body_photo_key와 동일한 이유.
CREATE TABLE business_info (
    member_id            BIGINT PRIMARY KEY REFERENCES member (id),
    business_number      VARCHAR(20)  NOT NULL,
    business_name        VARCHAR(100) NOT NULL,
    representative_name  VARCHAR(50)  NOT NULL,
    certificate_key      VARCHAR(500) NOT NULL,
    verification_status  VARCHAR(20)  NOT NULL DEFAULT 'PENDING',
    submitted_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    verified_at          TIMESTAMPTZ,
    CONSTRAINT ck_business_verification
        CHECK (verification_status IN ('PENDING', 'APPROVED', 'REJECTED'))
);


-- =============================================================================
-- 2. 마스터 — 브랜드·카테고리 [서윤]
-- =============================================================================

CREATE TABLE brand (
    id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name    VARCHAR(100) NOT NULL UNIQUE,
    name_en VARCHAR(100)                     -- 영문명. 없는 브랜드 대비 nullable
);

CREATE TABLE category (
    id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parent_id BIGINT REFERENCES category (id),   -- 상위 카테고리, 최상위는 NULL
    name      VARCHAR(100) NOT NULL,
    name_en   VARCHAR(100) NOT NULL,              -- 영문 코드(예: JACKET) — AI/FE 연동용
    depth     SMALLINT     NOT NULL DEFAULT 1
);

-- 온보딩 관심 정보 — 추천 입력으로 사용
CREATE TABLE member_interest_brand (
    member_id BIGINT NOT NULL REFERENCES member (id),
    brand_id  BIGINT NOT NULL REFERENCES brand (id),
    PRIMARY KEY (member_id, brand_id)
);

CREATE TABLE member_interest_category (
    member_id   BIGINT NOT NULL REFERENCES member (id),
    category_id BIGINT NOT NULL REFERENCES category (id),
    PRIMARY KEY (member_id, category_id)
);


-- =============================================================================
-- 3. 상품 [서윤]
-- =============================================================================

CREATE TABLE product (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    seller_id       BIGINT       NOT NULL REFERENCES member (id),
    -- 카테고리 필수. 상품이 어느 카테고리에도 속하지 않으면 검색·필터,
    -- 라이브 카테고리(편성 상품에서 유도)에서 통째로 누락.
    category_id     BIGINT       NOT NULL REFERENCES category (id),
    -- 브랜드 마스터 FK가 아니라 자유 텍스트다 — FE가 브랜드 마스터에서 고르게 하지 않고
    -- 판매자가 직접 입력한 텍스트를 그대로 받는다(BE 결정).
    brand           VARCHAR(100),
    title           VARCHAR(200) NOT NULL,
    description     TEXT,
    condition_grade VARCHAR(20),                     -- 중고 상태 등급 (체계 미확정)
    size_label      VARCHAR(50),
    color           VARCHAR(50),
    material        VARCHAR(50),
    measurements    JSONB,                           -- 실측 치수(cm). 항목이 상품마다 달라 고정 컬럼 대신 JSONB
    sale_type       VARCHAR(20),                     -- 정찰제 / 경매. 기본 정보 저장 시점에는 NULL,
                                                       -- 판매 채널을 정하는 API(판매 가격 설정/경매 조건 설정)
                                                       -- 호출 시 확정.
    sale_status     VARCHAR(30)  NOT NULL DEFAULT 'DRAFT',
    price           BIGINT,                          -- 정찰제가. 경매 예정 상품은 NULL.
    view_count      INTEGER      NOT NULL DEFAULT 0,
    ai_model_enabled BOOLEAN     NOT NULL DEFAULT FALSE, -- 마네킹 사진 기반 AI 착용컷 사용 여부.
    ai_model_gender VARCHAR(10),                     -- MALE|FEMALE. ai_model_enabled=true면 필수.
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,
    CONSTRAINT ck_product_sale_type CHECK (sale_type IN ('DIRECT_SALE', 'AUCTION')),
    CONSTRAINT ck_product_sale_status CHECK (sale_status IN (
        'DRAFT',              -- 등록 중(미공개)
        'ON_SALE',            -- 정찰제 중
        'AUCTION_SCHEDULED',  -- 경매 예정
        'AUCTION_IN_PROGRESS',-- 경매 진행 중 (상시 구매 즉시 중단, LIVE-006)
        'SOLD'                -- 판매 완료(낙찰 포함)
    )),
    -- 정찰제 상품은 가격이 반드시 있어야 한다.
    -- 경매 상품의 가격은 강제하지 않는다 — 미낙찰 후 정찰제로 전환할 때
    -- sale_type 과 price 갱신 순서를 애플리케이션이 자유롭게 잡을 수 있어야 한다.
    CONSTRAINT ck_product_price_by_type CHECK (
        sale_type <> 'DIRECT_SALE' OR price IS NOT NULL
    ),
    CONSTRAINT ck_product_ai_model_gender CHECK (
        ai_model_enabled = FALSE OR ai_model_gender IS NOT NULL
    )
);

CREATE TABLE product_image (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id BIGINT       NOT NULL REFERENCES product (id),
    image_key  VARCHAR(500) NOT NULL,
    sort_order SMALLINT     NOT NULL DEFAULT 0,
    is_primary BOOLEAN      NOT NULL DEFAULT FALSE
);

-- 판매자가 직접 입력한 하자 목록
CREATE TABLE product_defect (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id BIGINT      NOT NULL REFERENCES product (id),
    content    TEXT        NOT NULL,
    sort_order SMALLINT    NOT NULL DEFAULT 0
);

-- 찜
CREATE TABLE wish (
    member_id  BIGINT      NOT NULL REFERENCES member (id),
    product_id BIGINT      NOT NULL REFERENCES product (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (member_id, product_id)
);

-- AI 가상 시착 결과물. product_id 를 참조하므로 product 다음에 둔다.
-- 다중 아이템 합성("빈티지 코디" 등)은 이번 범위 밖 — 상품 1개 기준 단일 합성 결과만 다룬다.
CREATE TABLE tryon_result (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    member_id  BIGINT       NOT NULL REFERENCES member (id),
    product_id BIGINT       NOT NULL REFERENCES product (id),
    image_key  VARCHAR(500) NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX ix_tryon_result_member ON tryon_result (member_id, created_at DESC) WHERE deleted_at IS NULL;


-- =============================================================================
-- 4. 라이브 [정윤]
-- =============================================================================

CREATE TABLE live (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    host_id           BIGINT       NOT NULL REFERENCES member (id),
    title             VARCHAR(200) NOT NULL,
    thumbnail_url     VARCHAR(500),
    description       VARCHAR(1000),                  -- 방송 설명(선택). 시청 화면 헤더 표시용
    status            VARCHAR(20)  NOT NULL DEFAULT 'SCHEDULED',
    scheduled_at      TIMESTAMPTZ,                    -- 예약 라이브만. 즉시 라이브는 NULL
    started_at        TIMESTAMPTZ,
    ended_at          TIMESTAMPTZ,
    openvidu_room     VARCHAR(100),                   -- OpenVidu v3 room name
    peak_viewer_count INTEGER      NOT NULL DEFAULT 0,
    -- 지금 소개 중인 상품. FE NOW 배지의 원천.
    -- 카테고리는 편성 상품에서 유도하지만 "지금 소개 중"은 호스트의 현재 의도라 파생할 근거가
    -- 없어 컬럼으로 둔다. 편성된 상품인지는 애플리케이션이 live_product 로 검증한다.
    current_product_id BIGINT      REFERENCES product (id),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT ck_live_status CHECK (status IN (
        'SCHEDULED',  -- 예정 (LIVE-001)
        'LIVE',       -- 진행 중 (LIVE-002 / LIVE-004)
        'ENDED',      -- 종료
        'CANCELED'    -- 방송 전 취소
    ))
);

-- 라이브 ↔ 상품 연결 (LIVE-003). 개수 제한은 없으나 최소 1개는 있어야 한다.
-- 편성은 라이브 개설 시점에 정하고, 방송이 시작되면(status='LIVE') 더 이상 바꿀 수 없다 —
-- 시청자가 보고 있는 판매 목록이 도중에 바뀌면 안 되고, 라이브 카테고리를 이 편성에서
-- 유도하므로 함께 흔들린다. 예약(SCHEDULED) 상태에서는 방송 시작 전까지 변경 가능.
-- 제외는 물리 삭제 대신 removed_at 으로 남긴다 — 다시보기 타임라인(LIVE-008)의 근거가 된다.
CREATE TABLE live_product (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    live_id    BIGINT      NOT NULL REFERENCES live (id),
    product_id BIGINT      NOT NULL REFERENCES product (id),
    sort_order SMALLINT    NOT NULL DEFAULT 0,
    added_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    removed_at TIMESTAMPTZ
);

-- 같은 상품을 같은 라이브에 중복 연결하지 못하게 한다(제외된 건은 재연결 허용).
CREATE UNIQUE INDEX ux_live_product_active
    ON live_product (live_id, product_id) WHERE removed_at IS NULL;


-- 예약 라이브 시작 알림 신청
-- notified_at 이 중복 발송을 막는 유일한 근거다 — 스케줄러는 이 값이 비어 있는 신청만 집고,
-- 알림 생성과 같은 트랜잭션에서 채운다. 서버가 재기동돼도 이미 보낸 건은 다시 잡히지 않는다.
CREATE TABLE live_reminder (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    live_id     BIGINT      NOT NULL REFERENCES live (id),
    member_id   BIGINT      NOT NULL REFERENCES member (id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    notified_at TIMESTAMPTZ,                        -- NULL 이면 아직 안 보냄
    CONSTRAINT ux_live_reminder UNIQUE (live_id, member_id)
);

-- 스케줄러가 "아직 안 보낸 것"만 훑는다. 보낸 건이 쌓여도 스캔 대상이 늘지 않게 부분 인덱스로 둔다.
CREATE INDEX ix_live_reminder_pending
    ON live_reminder (live_id) WHERE notified_at IS NULL;


-- =============================================================================
-- 5. 경매·입찰 [정윤]
-- =============================================================================

CREATE TABLE auction (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    live_id           BIGINT      NOT NULL REFERENCES live (id),
    product_id        BIGINT      NOT NULL REFERENCES product (id),
    start_price       BIGINT      NOT NULL,          -- 시작가 (AUCT-001)
    bid_unit          BIGINT      NOT NULL,          -- 증액 단위 (AUCT-001)
    duration_seconds  INTEGER     NOT NULL,          -- 진행 시간 (AUCT-001)
    status            VARCHAR(20) NOT NULL DEFAULT 'READY',
    current_price     BIGINT      NOT NULL DEFAULT 0,-- 현재가. 입찰 없으면 0
    top_bidder_id     BIGINT      REFERENCES member (id),  -- 최고 입찰자 (AUCT-011)
    started_at        TIMESTAMPTZ,
    scheduled_end_at  TIMESTAMPTZ,                   -- 5초 연장 시 갱신됨 (AUCT-010)
    ended_at          TIMESTAMPTZ,
    extension_count   SMALLINT    NOT NULL DEFAULT 0,-- 연장 횟수 제한은 없으나 통계·검증용
    winner_id         BIGINT      REFERENCES member (id),
    final_price       BIGINT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_auction_status CHECK (status IN (
        'READY',      -- 조건 설정 완료, 시작 전 (AUCT-001)
        'RUNNING',    -- 진행 중 (AUCT-002)
        'SUCCESS',    -- 낙찰 (AUCT-012)
        'FAILED',     -- 입찰자 없이 종료 → 미낙찰 (AUCT-014)
        'CANCELED'
    )),
    CONSTRAINT ck_auction_bid_unit    CHECK (bid_unit > 0),
    CONSTRAINT ck_auction_start_price CHECK (start_price >= 0),
    -- 낙찰 상태인데 낙찰자·낙찰가가 비어 있는 레코드를 만들 수 없게 한다.
    -- 낙찰 처리(AUCT-012)는 여러 테이블을 함께 갱신하므로 일부 누락을 DB가 막아준다.
    CONSTRAINT ck_auction_success_fields CHECK (
        status <> 'SUCCESS' OR (winner_id IS NOT NULL AND final_price IS NOT NULL)
    )
);

-- 한 라이브에서 동시에 진행 중인 경매는 항상 1개 (LIVE-004).
-- 애플리케이션 검증에만 맡기지 않고 DB 레벨에서 못 박는다.
CREATE UNIQUE INDEX ux_auction_live_running
    ON auction (live_id) WHERE status = 'RUNNING';

CREATE INDEX ix_auction_live   ON auction (live_id, created_at DESC);
CREATE INDEX ix_auction_status ON auction (status) WHERE status = 'RUNNING';


CREATE TABLE bid (
    id         BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    auction_id BIGINT      NOT NULL REFERENCES auction (id),
    bidder_id  BIGINT      NOT NULL REFERENCES member (id),
    bid_price  BIGINT      NOT NULL,
    status     VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    -- 선착순 판정 기준은 클라이언트 클릭 시각이 아니라 서버 수신 시각이다 (AUCT-005)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_bid_status CHECK (status IN (
        'ACTIVE',  -- 현재 최고 입찰
        'OUTBID',  -- 상위 입찰에 밀림 → 포인트 보류 해제됨 (AUCT-008)
        'WON',     -- 낙찰
        'LOST'     -- 경매 종료 시점에 최고가가 아니었음
    ))
);

-- 같은 경매에서 동일 가격 단계는 단 한 번만 성립한다.
-- 중복 클릭(AUCT-004)과 동시 입찰 경합(AUCT-005)을 DB 레벨에서 차단하는 최후 방어선.
-- 1차 방어는 Redis 분산락이 아니라 DB 비관적 락(AuctionRepository.findByIdForUpdate)이다 —
-- 같은 경매의 입찰은 이 행 잠금으로 직렬화된다. 이 제약은 그 잠금이 실패했을 때의 안전망이다.
CREATE UNIQUE INDEX ux_bid_auction_price ON bid (auction_id, bid_price);

CREATE INDEX ix_bid_auction_created ON bid (auction_id, created_at DESC);
CREATE INDEX ix_bid_bidder          ON bid (bidder_id, created_at DESC);


-- =============================================================================
-- 6. 포인트 [서윤]
-- =============================================================================

-- 잔액 집계 테이블. 매번 원장을 합산하지 않기 위해 버킷별 잔액을 들고 있는다.
-- 기능정의서 포인트 상태 6종을 '상태 컬럼'이 아니라 '잔액 버킷'으로 구현한 것이다.
CREATE TABLE point_account (
    member_id       BIGINT PRIMARY KEY REFERENCES member (id),
    available       BIGINT      NOT NULL DEFAULT 0,  -- 사용 가능
    bid_held        BIGINT      NOT NULL DEFAULT 0,  -- 입찰 보류
    trade_escrow    BIGINT      NOT NULL DEFAULT 0,  -- 거래 대금 보관
    settling        BIGINT      NOT NULL DEFAULT 0,  -- 판매자 정산 대기
    withdrawing     BIGINT      NOT NULL DEFAULT 0,  -- 출금 처리 중
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- 잔액이 음수로 떨어지는 것은 어떤 경로로도 허용하지 않는다.
    -- 포인트는 돈이고, 동시 입찰 상황에서 한 건의 오류도 허용되지 않는다.
    CONSTRAINT ck_point_non_negative CHECK (
        available >= 0 AND bid_held >= 0 AND trade_escrow >= 0
        AND settling >= 0 AND withdrawing >= 0
    )
);

-- 포인트 원장. 모든 증감을 append-only 로 남긴다.
CREATE TABLE point_transaction (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    member_id     BIGINT      NOT NULL REFERENCES member (id),
    type          VARCHAR(30) NOT NULL,
    amount        BIGINT      NOT NULL,              -- 부호 있는 증감액
    balance_after BIGINT      NOT NULL,              -- 기록 시점의 available 잔액
    ref_type      VARCHAR(30),                       -- AUCTION / ORDER / BID ...
    ref_id        BIGINT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_point_tx_type CHECK (type IN (
        'CHARGE',        -- 충전
        'BID_HOLD',      -- 입찰 보류
        'BID_RELEASE',   -- 보류 해제
        'PAYMENT',       -- 낙찰·구매 결제 → 거래 보관
        'SETTLEMENT',    -- 판매자 정산
        'REFUND',        -- 환불
        'WITHDRAW'       -- 출금
    ))
);

CREATE INDEX ix_point_tx_member ON point_transaction (member_id, created_at DESC);

-- 포인트 충전 결제 준비/승인 상태. order_id 는 토스에 넘기는 주문번호(BE 발급, orders 테이블과 무관).
CREATE TABLE point_charge (
    id           BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    member_id    BIGINT      NOT NULL REFERENCES member (id),
    order_id     VARCHAR(64) NOT NULL,
    amount       BIGINT      NOT NULL,
    status       VARCHAR(20) NOT NULL DEFAULT 'READY',
    payment_key  VARCHAR(200),
    approved_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_point_charge_order_id UNIQUE (order_id),
    CONSTRAINT ck_point_charge_status CHECK (status IN ('READY', 'DONE', 'FAILED')),
    CONSTRAINT ck_point_charge_amount_positive CHECK (amount > 0)
);

CREATE INDEX ix_point_charge_member ON point_charge (member_id, created_at DESC);

-- 출금(현금화) 계좌 정보. point_account 와 같은 공유 PK 1:1 — 회원당 한 행만 존재한다.
-- 실제 은행 송금 연동은 범위 밖이라 계좌 정보만 평문으로 남긴다(business_info 와 동일한 전제).
CREATE TABLE withdrawal_account (
    member_id           BIGINT      PRIMARY KEY REFERENCES member (id),
    bank_name           VARCHAR(50) NOT NULL,
    account_number      VARCHAR(30) NOT NULL,
    account_holder_name VARCHAR(50) NOT NULL,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 입찰 보류 상태. 입찰 내역 ↔ 포인트 보류를 잇는 테이블.
CREATE TABLE point_hold (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    member_id   BIGINT      NOT NULL REFERENCES member (id),
    auction_id  BIGINT      NOT NULL REFERENCES auction (id),
    bid_id      BIGINT      NOT NULL REFERENCES bid (id),
    amount      BIGINT      NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'HELD',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    released_at TIMESTAMPTZ,
    CONSTRAINT ck_point_hold_status CHECK (status IN (
        'HELD',      -- 보류 중 (= 이 회원이 해당 경매의 최고 입찰자)
        'RELEASED',  -- 상위 입찰 발생으로 해제
        'CONVERTED'  -- 낙찰되어 거래 대금으로 전환
    ))
);

-- 한 회원은 동시에 하나의 HELD 보류만 가질 수 있다. 정책 두 개를 동시에 구현한다.
--   * AUCT-009 최고 입찰자인 동안 타 경매 입찰 차단
--     — 정찰제 구매는 보류를 만들지 않으므로 이 제약에 걸리지 않는다.
--   * AUCT-006 직전 성공 입찰자는 바로 다음 단계 입찰 불가
--     — 최고 입찰자는 이미 HELD 를 쥐고 있어 두 번째 보류를 만들 수 없다.
--       ⚠️ 따라서 애플리케이션은 '같은 회원의 연속 입찰'에서 기존 보류를 먼저
--          해제해서는 안 된다. 해제해 버리면 이 제약이 무력화된다.
CREATE UNIQUE INDEX ux_point_hold_member_active
    ON point_hold (member_id) WHERE status = 'HELD';

CREATE INDEX ix_point_hold_auction ON point_hold (auction_id, status);


-- =============================================================================
-- 7. 주문·배송 [서윤]
-- =============================================================================

-- order 는 SQL 예약어라 orders 로 둔다.
CREATE TABLE orders (
    id              BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    buyer_id        BIGINT      NOT NULL REFERENCES member (id),
    seller_id       BIGINT      NOT NULL REFERENCES member (id),
    product_id      BIGINT      NOT NULL REFERENCES product (id),
    auction_id      BIGINT      REFERENCES auction (id),  -- 정찰제 주문은 NULL
    -- 이 주문이 발생한 방송(LIVE-006 방송 종료 요약). 라이브 밖에서 산 주문은 NULL.
    -- 낙찰이면 auction_id 로도 방송을 알 수 있지만, 방송 중 즉시구매는 경매를 거치지 않아
    -- 이 컬럼 없이는 방송과 이을 근거가 없다. 두 경로를 한 컬럼으로 묶어 "이 방송에서
    -- 발생한 주문"을 조건 하나로 뽑는다 — 낙찰 주문에도 채운다.
    live_id         BIGINT      REFERENCES live (id),
    order_price     BIGINT      NOT NULL,
    status          VARCHAR(30) NOT NULL DEFAULT 'PAID',
    -- 배송 완료 후 3일 경과 시 자동 구매 확정. 스케줄러가 이 컬럼으로 대상을 찾는다.
    -- 배송 완료 시점(delivered_at)에 계산해 채운다.
    auto_confirm_at   TIMESTAMPTZ,
    -- 정산 완료(SETTLED 전이) 시각. SETTLED가 아닌 주문은 NULL.
    settled_at        TIMESTAMPTZ,
    -- 진행 중인(REQUESTED) 환불 요청이 있는 동안 true. 송장 등록·구매 확정(수동/자동)을 막는 용도로만
    -- 쓴다 — 요청 중에도 status는 바꾸지 않는다.
    refund_requested  BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_order_status CHECK (status IN (
        'PAID',        -- 결제 완료, 거래 대금 보관 중
        'SHIPPING',    -- 송장 등록·배송 중
        'DELIVERED',   -- 배송 완료
        'CONFIRMED',   -- 구매 확정 (수동 또는 3일 자동)
        'SETTLED',     -- 판매자 정산 완료
        'REFUNDED',
        'CANCELED'
    )),
    CONSTRAINT ck_order_not_self CHECK (buyer_id <> seller_id)
);

CREATE INDEX ix_orders_buyer  ON orders (buyer_id, created_at DESC);
CREATE INDEX ix_orders_seller ON orders (seller_id, created_at DESC);

-- 자동 구매 확정 스케줄러 조회용 — DELIVERED 상태만 대상이라 부분 인덱스로 좁힌다.
CREATE INDEX ix_orders_auto_confirm
    ON orders (auto_confirm_at) WHERE status = 'DELIVERED';

-- 방송 종료 요약(LIVE-006) 조회용. 라이브 밖 주문이 대부분이라 부분 인덱스로 좁힌다.
CREATE INDEX ix_orders_live ON orders (live_id) WHERE live_id IS NOT NULL;

CREATE TABLE order_shipment (
    order_id        BIGINT PRIMARY KEY REFERENCES orders (id),
    recipient_name  VARCHAR(50)  NOT NULL,
    recipient_phone VARCHAR(20)  NOT NULL,
    zipcode         VARCHAR(10)  NOT NULL,
    address1        VARCHAR(255) NOT NULL,
    address2        VARCHAR(255),
    -- deliveryapi.co.kr이 지원하는 국내 택배사 10개로 한정한다(SY034) — 자유 문자열 금지.
    courier         VARCHAR(50),
    tracking_number VARCHAR(50),
    shipped_at      TIMESTAMPTZ,
    -- 더 이상 송장 등록 시점에 즉시 채우지 않는다 — deliveryapi.co.kr 웹훅으로 실제 배송완료
    -- 신호를 받았을 때만 채운다(웹훅 구독 실패 시에는 예외적으로 즉시 채우는 폴백을 쓴다).
    delivered_at    TIMESTAMPTZ,
    -- 배송 진행 상태(SY034). 웹훅이 올 때마다(DELIVERED가 아니어도) 갱신 — 송장 등록 직후
    -- 첫 웹훅을 받기 전에는 NULL.
    tracking_status VARCHAR(20),
    CONSTRAINT ck_order_shipment_courier CHECK (courier IN (
        'LOTTE', 'CJ', 'HANJIN', 'POST', 'KYUNGDONG',
        'DAESIN', 'LOGEN', 'HAPDONG', 'COUPANG', 'WOORI'
    )),
    CONSTRAINT ck_order_shipment_tracking_status CHECK (tracking_status IN (
        'PENDING', 'REGISTERED', 'PICKUP_READY', 'PICKED_UP', 'IN_TRANSIT',
        'OUT_FOR_DELIVERY', 'DELIVERED', 'FAILED', 'RETURNED', 'CANCELLED',
        'HOLD', 'UNKNOWN'
    ))
);

-- 환불 요청·승인/거절. 구매자가 요청하고 판매자가 승인/거절.
-- 환불이 승인되면 보관 중이던 대금을 판매자 정산 없이 구매자 포인트로 돌려줌.
-- 같은 주문에 여러 건 가능 (거절 후 재요청 허용).
CREATE TABLE refund_request (
    id               BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id         BIGINT      NOT NULL REFERENCES orders (id),
    reason           VARCHAR(30) NOT NULL,
    detail_reason    TEXT        NOT NULL,
    status           VARCHAR(20) NOT NULL DEFAULT 'REQUESTED',
    rejection_reason TEXT,
    reviewed_at      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_refund_request_reason CHECK (reason IN (
        'NOT_AS_DESCRIBED', 'UNDISCLOSED_DEFECT', 'NOT_SHIPPED', 'DUPLICATE_PAYMENT', 'SYSTEM_ERROR'
    )),
    CONSTRAINT ck_refund_request_status CHECK (status IN ('REQUESTED', 'APPROVED', 'REJECTED'))
);

CREATE INDEX ix_refund_request_order ON refund_request (order_id, created_at DESC);

-- 세금계산서. 법적 문서라 발행 시점 사업자 정보를 스냅샷으로 저장.
-- 이후 판매자가 business_info를 바꿔도 이미 발행된 계산서는 바뀌지 않는다.
-- 주문당 1건만 허용(uq_invoice_order) — 취소/재발행은 범위 밖.
CREATE TABLE invoice (
    id                   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id             BIGINT      NOT NULL REFERENCES orders (id),
    business_number      VARCHAR(20)  NOT NULL,
    business_name        VARCHAR(100) NOT NULL,
    representative_name  VARCHAR(50)  NOT NULL,
    supply_amount        BIGINT      NOT NULL,  -- 공급가액
    tax_amount           BIGINT      NOT NULL,  -- 부가세
    total_amount         BIGINT      NOT NULL,  -- 합계금액 (= order.order_price)
    issued_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_invoice_order UNIQUE (order_id)
);


-- =============================================================================
-- 8. 채팅 [정윤]
-- =============================================================================

CREATE TABLE chat_message (
    id          BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    live_id     BIGINT      NOT NULL REFERENCES live (id),
    member_id   BIGINT      REFERENCES member (id),   -- 시스템·AI 메시지는 NULL
    sender_type VARCHAR(20) NOT NULL DEFAULT 'USER',
    content     TEXT        NOT NULL,
    is_blocked  BOOLEAN     NOT NULL DEFAULT FALSE,   -- 금칙어·도배 차단 (CHAT-004)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_chat_sender_type CHECK (sender_type IN (
        'USER',    -- 로그인 회원 발언 (CHAT-001) — 비회원은 시청만 가능
        'SYSTEM',  -- 입장·퇴장·경매 안내
        'AI'       -- AI 자동 답변 (CHAT-002) — 답변임을 명시해야 함
    )),
    -- 회원 발언은 작성자가 반드시 있어야 한다.
    CONSTRAINT ck_chat_user_has_member CHECK (
        sender_type <> 'USER' OR member_id IS NOT NULL
    )
);

CREATE INDEX ix_chat_live_created ON chat_message (live_id, created_at DESC);


-- =============================================================================
-- 9. 알림 [서윤]
-- =============================================================================

CREATE TABLE notification (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    member_id  BIGINT       NOT NULL REFERENCES member (id),
    type       VARCHAR(40)  NOT NULL,
    title      VARCHAR(200) NOT NULL,
    body       VARCHAR(500),
    ref_type   VARCHAR(30),                          -- LIVE / AUCTION / ORDER ...
    ref_id     BIGINT,
    is_read    BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- 알림함은 '안 읽은 것 먼저'가 기본 조회라 is_read 를 선두에 둔다.
CREATE INDEX ix_notification_member
    ON notification (member_id, is_read, created_at DESC);


-- =============================================================================
-- 10. 조회 패턴 기반 인덱스 (홈·검색)
-- =============================================================================

-- HOME-001: 진행 중/예약 라이브
CREATE INDEX ix_live_status_scheduled ON live (status, scheduled_at DESC);

-- HOME-001: 정찰제 / 경매 예정 상품 목록
CREATE INDEX ix_product_status_created
    ON product (sale_status, created_at DESC) WHERE deleted_at IS NULL;

-- HOME-002: 팔로잉 회원의 상품·라이브
CREATE INDEX ix_product_seller ON product (seller_id, created_at DESC);
CREATE INDEX ix_live_host      ON live (host_id, created_at DESC);

-- SEARCH-002: 카테고리·브랜드·가격대 필터
CREATE INDEX ix_product_category ON product (category_id, sale_status);
CREATE INDEX ix_product_brand    ON product (brand, sale_status);
CREATE INDEX ix_product_price    ON product (price) WHERE price IS NOT NULL;

-- SEARCH-001: 상품명·닉네임·방송명 부분 일치.
-- LIKE '%키워드%' 는 B-Tree 인덱스를 타지 못한다. 3주 일정에서 Elasticsearch 는
-- 인프라 부담(단일 EC2)이 커서, 추가 인프라 없이 부분 일치를 인덱싱하는 pg_trgm 으로 간다.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX ix_product_title_trgm   ON product USING gin (title gin_trgm_ops);
CREATE INDEX ix_member_nickname_trgm ON member  USING gin (nickname gin_trgm_ops);
CREATE INDEX ix_live_title_trgm      ON live    USING gin (title gin_trgm_ops);

-- =============================================================================
-- 11. 소셜 (찜/팔로우)
-- =============================================================================

CREATE TABLE follow (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    follower_id  BIGINT      NOT NULL REFERENCES member (id),
    following_id BIGINT      NOT NULL REFERENCES member (id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ux_follow UNIQUE (follower_id, following_id),
    CONSTRAINT ck_follow_not_self CHECK (follower_id <> following_id)
);