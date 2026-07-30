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
    password_hash     VARCHAR(255),                    -- SSO 전용 계정은 NULL
    nickname          VARCHAR(30)  NOT NULL UNIQUE,    -- 경매 최고 입찰자 표시에 사용(AUCT-011)
    name              VARCHAR(50),
    phone             VARCHAR(20),
    member_type       VARCHAR(20)  NOT NULL DEFAULT 'GENERAL',
    status            VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE',
    profile_image_url VARCHAR(500),
    onboarding_done   BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ,
    CONSTRAINT ck_member_type   CHECK (member_type IN ('GENERAL', 'BUSINESS')),
    CONSTRAINT ck_member_status CHECK (status IN ('ACTIVE', 'SUSPENDED', 'WITHDRAWN'))
);

-- 싸피어스 SSO 등 외부 계정 연결 (AUTH-003, AUTH-004)
CREATE TABLE member_social_account (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    member_id        BIGINT       NOT NULL REFERENCES member (id),
    provider         VARCHAR(30)  NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT ck_social_provider CHECK (provider IN ('SSAFY')),
    CONSTRAINT uq_social_provider_user UNIQUE (provider, provider_user_id)
);

-- 전신 사진·신체 정보 (ONBOARD-003, TRYON-001~002)
CREATE TABLE member_body_profile (
    member_id      BIGINT PRIMARY KEY REFERENCES member (id),
    body_photo_url VARCHAR(500),
    height_cm      SMALLINT,
    weight_kg      SMALLINT,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 사업자 정보 (BIZ-001)
CREATE TABLE business_info (
    member_id            BIGINT PRIMARY KEY REFERENCES member (id),
    business_number      VARCHAR(20)  NOT NULL,
    certificate_url      VARCHAR(500) NOT NULL,
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
    depth     SMALLINT     NOT NULL DEFAULT 1
);

-- 온보딩 관심 정보 (ONBOARD-002) — 추천(REC-001) 입력으로 사용
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
-- 3. 상품 [서윤] — 라이브·경매가 FK 로 물리는 축
-- =============================================================================

CREATE TABLE product (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    seller_id       BIGINT       NOT NULL REFERENCES member (id),
    -- 카테고리는 필수다. 상품이 어느 카테고리에도 속하지 않으면 검색·필터는 물론
    -- 라이브 카테고리(편성 상품에서 유도)에서도 통째로 누락된다.
    category_id     BIGINT       NOT NULL REFERENCES category (id),
    brand_id        BIGINT       REFERENCES brand (id),
    title           VARCHAR(200) NOT NULL,
    description     TEXT,
    condition_grade VARCHAR(20),                     -- 중고 상태 등급 (체계 미확정)
    size_label      VARCHAR(50),
    sale_type       VARCHAR(20),                     -- 상시 판매 / 경매. 기본 정보 저장 시점에는 NULL,
                                                       -- 판매 채널을 정하는 API(판매 가격 설정/경매 조건 설정)
                                                       -- 호출 시 확정된다
    sale_status     VARCHAR(30)  NOT NULL DEFAULT 'DRAFT',
    price           BIGINT,                          -- 상시 판매가. 경매 예정 상품은 NULL
    view_count      INTEGER      NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,
    CONSTRAINT ck_product_sale_type CHECK (sale_type IN ('DIRECT_SALE', 'AUCTION')),
    CONSTRAINT ck_product_sale_status CHECK (sale_status IN (
        'DRAFT',              -- 등록 중(미공개)
        'ON_SALE',            -- 상시 판매 중
        'AUCTION_SCHEDULED',  -- 경매 예정
        'AUCTION_IN_PROGRESS',-- 경매 진행 중 (상시 구매 즉시 중단, LIVE-006)
        'SOLD',               -- 판매 완료(낙찰 포함)
        'PRIVATE'             -- 비공개
    )),
    -- 상시 판매 상품은 가격이 반드시 있어야 한다.
    -- 경매 상품의 가격은 강제하지 않는다 — 미낙찰 후 상시 판매로 전환(PROD-005)하는
    -- 과도기에 sale_type 과 price 갱신 순서를 애플리케이션이 자유롭게 잡을 수 있어야 한다.
    CONSTRAINT ck_product_price_by_type CHECK (
        sale_type <> 'DIRECT_SALE' OR price IS NOT NULL
    )
);

CREATE TABLE product_image (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id BIGINT       NOT NULL REFERENCES product (id),
    image_key  VARCHAR(500) NOT NULL,
    sort_order SMALLINT     NOT NULL DEFAULT 0,
    is_primary BOOLEAN      NOT NULL DEFAULT FALSE
);

-- 찜 (MY-009)
CREATE TABLE wish (
    member_id  BIGINT      NOT NULL REFERENCES member (id),
    product_id BIGINT      NOT NULL REFERENCES product (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (member_id, product_id)
);

-- 팔로우 (FOLLOW-001) — HOME-002 팔로잉 콘텐츠 조회의 기준
CREATE TABLE follow (
    follower_id  BIGINT      NOT NULL REFERENCES member (id),
    following_id BIGINT      NOT NULL REFERENCES member (id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (follower_id, following_id),
    CONSTRAINT ck_follow_not_self CHECK (follower_id <> following_id)
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
    status            VARCHAR(20)  NOT NULL DEFAULT 'SCHEDULED',
    scheduled_at      TIMESTAMPTZ,                    -- 예약 라이브만. 즉시 라이브는 NULL
    started_at        TIMESTAMPTZ,
    ended_at          TIMESTAMPTZ,
    openvidu_room     VARCHAR(100),                   -- OpenVidu v3 room name
    peak_viewer_count INTEGER      NOT NULL DEFAULT 0,
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


-- =============================================================================
-- 5. 경매·입찰 [정윤] — 프로젝트 최대 난관 구간
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
-- Redis 분산락이 1차 방어이고, 이 제약은 락이 실패했을 때의 안전망이다.
CREATE UNIQUE INDEX ux_bid_auction_price ON bid (auction_id, bid_price);

CREATE INDEX ix_bid_auction_created ON bid (auction_id, created_at DESC);
CREATE INDEX ix_bid_bidder          ON bid (bidder_id, created_at DESC);


-- =============================================================================
-- 6. 포인트 [서윤] — 입찰 트랜잭션의 핵심 의존
-- =============================================================================

-- 잔액 집계 테이블. 매번 원장을 합산하지 않기 위해 버킷별 잔액을 들고 있는다.
-- 기능정의서 §4.9 포인트 상태 6종을 '상태 컬럼'이 아니라 '잔액 버킷'으로 구현한 것이다.
CREATE TABLE point_account (
    member_id       BIGINT PRIMARY KEY REFERENCES member (id),
    available       BIGINT      NOT NULL DEFAULT 0,  -- 사용 가능
    bid_held        BIGINT      NOT NULL DEFAULT 0,  -- 입찰 보류 (AUCT-007)
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
        'CHARGE',        -- 충전 (POINT-001)
        'BID_HOLD',      -- 입찰 보류 (AUCT-007)
        'BID_RELEASE',   -- 보류 해제 (AUCT-008)
        'PAYMENT',       -- 낙찰·구매 결제 → 거래 보관
        'SETTLEMENT',    -- 판매자 정산
        'REFUND',        -- 환불
        'WITHDRAW'       -- 출금
    ))
);

CREATE INDEX ix_point_tx_member ON point_transaction (member_id, created_at DESC);

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
        'RELEASED',  -- 상위 입찰 발생으로 해제 (AUCT-008)
        'CONVERTED'  -- 낙찰되어 거래 대금으로 전환 (AUCT-012)
    ))
);

-- 한 회원은 동시에 하나의 HELD 보류만 가질 수 있다. 정책 두 개를 동시에 구현한다.
--   * AUCT-009 최고 입찰자인 동안 타 경매 입찰 차단
--     — 상시 판매 구매는 보류를 만들지 않으므로 이 제약에 걸리지 않는다.
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
    auction_id      BIGINT      REFERENCES auction (id),  -- 상시 판매 주문은 NULL
    order_price     BIGINT      NOT NULL,
    status          VARCHAR(30) NOT NULL DEFAULT 'PAID',
    -- 배송 완료 후 7일 경과 시 자동 구매 확정. 스케줄러가 이 컬럼으로 대상을 찾는다.
    -- 배송 완료 시점(delivered_at)에 계산해 채운다.
    auto_confirm_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_order_status CHECK (status IN (
        'PAID',        -- 결제 완료, 거래 대금 보관 중
        'SHIPPING',    -- 송장 등록·배송 중 (SHIP-*)
        'DELIVERED',   -- 배송 완료
        'CONFIRMED',   -- 구매 확정 (수동 또는 7일 자동)
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

CREATE TABLE order_shipment (
    order_id        BIGINT PRIMARY KEY REFERENCES orders (id),
    recipient_name  VARCHAR(50)  NOT NULL,
    recipient_phone VARCHAR(20)  NOT NULL,
    zipcode         VARCHAR(10)  NOT NULL,
    address1        VARCHAR(255) NOT NULL,
    address2        VARCHAR(255),
    courier         VARCHAR(50),
    tracking_number VARCHAR(50),
    shipped_at      TIMESTAMPTZ,
    delivered_at    TIMESTAMPTZ
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
-- 9. 알림 [서윤] — 트리거 이벤트는 정윤 도메인(라이브·경매)에서 발행
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

-- HOME-001: 상시 판매 / 경매 예정 상품 목록
CREATE INDEX ix_product_status_created
    ON product (sale_status, created_at DESC) WHERE deleted_at IS NULL;

-- HOME-002: 팔로잉 회원의 상품·라이브
CREATE INDEX ix_product_seller ON product (seller_id, created_at DESC);
CREATE INDEX ix_live_host      ON live (host_id, created_at DESC);

-- SEARCH-002: 카테고리·브랜드·가격대 필터
CREATE INDEX ix_product_category ON product (category_id, sale_status);
CREATE INDEX ix_product_brand    ON product (brand_id, sale_status);
CREATE INDEX ix_product_price    ON product (price) WHERE price IS NOT NULL;

-- SEARCH-001: 상품명·닉네임·방송명 부분 일치.
-- LIKE '%키워드%' 는 B-Tree 인덱스를 타지 못한다. 3주 일정에서 Elasticsearch 는
-- 인프라 부담(단일 EC2)이 커서, 추가 인프라 없이 부분 일치를 인덱싱하는 pg_trgm 으로 간다.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX ix_product_title_trgm   ON product USING gin (title gin_trgm_ops);
CREATE INDEX ix_member_nickname_trgm ON member  USING gin (nickname gin_trgm_ops);
CREATE INDEX ix_live_title_trgm      ON live    USING gin (title gin_trgm_ops);