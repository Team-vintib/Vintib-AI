-- =============================================================================
-- 데이터 사전의 '설명' 원천 (S15P11A108-52)
--
-- 설명을 마크다운 문서에만 적으면 스키마가 바뀔 때 조용히 어긋난다.
-- DB 에 COMMENT 로 심어두면 data-dictionary.md 를 언제든 재생성할 수 있고,
-- psql \d+ · DataGrip · DBeaver 에서도 그대로 보인다.
--
-- 적용 순서: schema.sql → comments.sql → gen-data-dictionary.sql
-- =============================================================================


-- ---------- 회원 ----------
COMMENT ON TABLE member IS '서비스 회원. 판매자·구매자 구분 없이 한 테이블을 쓴다.';
COMMENT ON COLUMN member.email             IS '로그인 ID 겸 연락 수단. 경매 화면에는 노출하지 않는다.';
COMMENT ON COLUMN member.password          IS '자체 로그인용 해시. SSO 전용 계정은 NULL.';
COMMENT ON COLUMN member.nickname          IS '공개 표시명. 최고 입찰자·낙찰자 표시에 쓰는 유일한 신원 정보 (AUCT-011).';
COMMENT ON COLUMN member.name              IS '실명. 배송·정산용이며 외부 노출 금지.';
COMMENT ON COLUMN member.member_type       IS 'GENERAL(일반) | BUSINESS(사업자)';
COMMENT ON COLUMN member.status            IS 'ACTIVE | SUSPENDED(정지) | WITHDRAWN(탈퇴)';
COMMENT ON COLUMN member.onboarding_done   IS '온보딩(관심 브랜드·카테고리·신체 정보) 완료 여부.';
COMMENT ON COLUMN member.deleted_at        IS '탈퇴 시각. 입찰·주문 이력이 FK 로 남아 물리 삭제하지 않는다.';
COMMENT ON COLUMN member.address           IS '기본 주소(도로명/지번). 온보딩(ONBOARD-001)에서 입력.';
COMMENT ON COLUMN member.detail_address    IS '상세 주소(동/호수 등).';
COMMENT ON COLUMN member.postal_code       IS '우편번호. 주소 검색을 안 쓰고 직접 입력하면 NULL 허용.';
COMMENT ON COLUMN member.gender            IS 'MALE | FEMALE';

COMMENT ON TABLE member_social_account IS '외부 계정 연결 (AUTH-003, AUTH-004). 한 회원이 여러 provider 를 가질 수 있다.';
COMMENT ON COLUMN member_social_account.provider         IS 'SSO 공급자. 현재 SSAFY 만 허용.';
COMMENT ON COLUMN member_social_account.provider_user_id IS '공급자 측 고유 ID. provider 와 묶어 유일하다.';

COMMENT ON TABLE member_body_profile IS '전신 사진·신체 정보 (ONBOARD-003, TRYON-001~002). 가상 시착 입력값.';
COMMENT ON COLUMN member_body_profile.body_photo_key IS '전신 사진 S3 key(비공개 버킷). 미등록이면 시착 불가.';
COMMENT ON COLUMN member_body_profile.height_cm      IS '키(cm).';
COMMENT ON COLUMN member_body_profile.weight_kg      IS '몸무게(kg).';
COMMENT ON COLUMN member_body_profile.chest_cm       IS '가슴둘레(cm).';
COMMENT ON COLUMN member_body_profile.waist_cm       IS '허리둘레(cm).';
COMMENT ON COLUMN member_body_profile.hip_cm         IS '엉덩이둘레(cm).';

COMMENT ON TABLE business_info IS '사업자 인증 정보 (BIZ-001).';
COMMENT ON COLUMN business_info.business_number     IS '사업자등록번호.';
COMMENT ON COLUMN business_info.business_name       IS '상호명.';
COMMENT ON COLUMN business_info.representative_name IS '대표자명.';
COMMENT ON COLUMN business_info.certificate_key     IS '사업자등록증 사본 S3 key(비공개 버킷).';
COMMENT ON COLUMN business_info.verification_status IS 'PENDING | APPROVED | REJECTED';


-- ---------- 마스터 ----------
COMMENT ON TABLE brand    IS '브랜드 마스터. 상품 등록·검색 필터의 기준.';
COMMENT ON TABLE category IS '카테고리 마스터. parent_id 로 계층을 이룬다.';
COMMENT ON COLUMN category.parent_id IS '상위 카테고리. 최상위는 NULL.';
COMMENT ON COLUMN category.depth     IS '계층 깊이. 최상위가 1.';

COMMENT ON TABLE member_interest_brand    IS '온보딩 관심 브랜드 (ONBOARD-002). 추천(REC-001) 입력.';
COMMENT ON TABLE member_interest_category IS '온보딩 관심 카테고리 (ONBOARD-002). 추천(REC-001) 입력.';


-- ---------- 상품 ----------
COMMENT ON TABLE product IS '판매 상품. 라이브·경매·주문이 모두 이 테이블을 FK 로 문다.';
COMMENT ON COLUMN product.seller_id       IS '판매자.';
COMMENT ON COLUMN product.condition_grade IS '중고 상태 등급. ⚠️ 등급 체계 미확정이라 자유 문자열.';
COMMENT ON COLUMN product.size_label      IS '사이즈 표기(S/M/L, 95/100 등). 브랜드마다 달라 문자열로 둔다.';
COMMENT ON COLUMN product.color           IS '색상(자유 문자열).';
COMMENT ON COLUMN product.material        IS '소재(자유 문자열).';
COMMENT ON COLUMN product.measurements    IS '실측 치수(cm). 항목(총장/어깨너비 등)이 상품마다 달라 JSONB로 저장.';
COMMENT ON COLUMN product.sale_type       IS 'DIRECT_SALE(상시 판매) | AUCTION(경매)';
COMMENT ON COLUMN product.sale_status     IS 'DRAFT | ON_SALE | AUCTION_SCHEDULED | AUCTION_IN_PROGRESS | SOLD';
COMMENT ON COLUMN product.price           IS '상시 판매가(원). 경매 예정 상품은 NULL — 가격대 필터에서 별도 처리한다 (SEARCH-002).';
COMMENT ON COLUMN product.view_count      IS '누적 조회수(집계값). ⚠️ 회원별 조회 이력은 남지 않는다 — REC-001 착수 시 재검토 필요.';
COMMENT ON COLUMN product.deleted_at      IS '삭제 시각. 주문 이력 보존을 위해 물리 삭제하지 않는다.';

COMMENT ON TABLE product_image IS '상품 이미지. 시착(TRYON-003) 입력으로도 쓰인다.';
COMMENT ON COLUMN product_image.sort_order IS '노출 순서.';
COMMENT ON COLUMN product_image.is_primary IS '대표 이미지 여부. 목록·썸네일에 쓴다.';

COMMENT ON TABLE product_defect IS '판매자가 직접 입력한 하자 목록 (PROD-001).';
COMMENT ON COLUMN product_defect.content    IS '하자 내용(자유 문자열).';
COMMENT ON COLUMN product_defect.sort_order IS '노출 순서.';

COMMENT ON TABLE wish   IS '찜 (MY-009). 추천(REC-001) 입력.';


-- ---------- 라이브 ----------
COMMENT ON TABLE live IS '라이브 방송. 경매·채팅이 열리는 "방"이다.';
COMMENT ON COLUMN live.host_id           IS '방송 진행자(판매자).';
COMMENT ON COLUMN live.status            IS 'SCHEDULED(예정) | LIVE(진행 중) | ENDED(종료) | CANCELED(방송 전 취소)';
COMMENT ON COLUMN live.scheduled_at      IS '예약 방송 시작 예정 시각 (LIVE-001). 즉시 개설(LIVE-002)은 NULL.';
COMMENT ON COLUMN live.openvidu_room     IS 'OpenVidu v3 room name. WebRTC 세션·토큰 발급 시 사용.';
COMMENT ON COLUMN live.peak_viewer_count IS '최고 동시 시청자 수. 통계·발표용.';

COMMENT ON TABLE live_product IS '라이브 ↔ 상품 연결 (LIVE-003). 방송 전·중 모두 추가·제외 가능하며 개수 제한이 없다.';
COMMENT ON COLUMN live_product.sort_order IS '방송 중 소개 순서.';
COMMENT ON COLUMN live_product.removed_at IS '연결 해제 시각. 물리 삭제하지 않는 이유는 "그 시점에 연결돼 있었다"는 사실이 다시보기 타임라인(LIVE-008)의 근거이기 때문.';


-- ---------- 경매·입찰 ----------
COMMENT ON TABLE auction IS '상품 1건에 대한 경매. 한 라이브에서 동시에 RUNNING 인 경매는 항상 1개다 (LIVE-004).';
COMMENT ON COLUMN auction.start_price      IS '시작가(원) (AUCT-001).';
COMMENT ON COLUMN auction.bid_unit         IS '증액 단위(원). 다음 입찰가 = 현재가 + 이 값 (AUCT-003).';
COMMENT ON COLUMN auction.duration_seconds IS '경매 진행 시간(초) (AUCT-001).';
COMMENT ON COLUMN auction.status           IS 'READY(설정 완료) | RUNNING(진행 중) | SUCCESS(낙찰) | FAILED(미낙찰) | CANCELED';
COMMENT ON COLUMN auction.current_price    IS '현재가(원). bid 집계 대신 비정규화해 들고 있다 — AUCT-011 실시간 표시가 초당 수십 회 조회된다.';
COMMENT ON COLUMN auction.top_bidder_id    IS '현재 최고 입찰자. 닉네임만 공개한다 (AUCT-011).';
COMMENT ON COLUMN auction.scheduled_end_at IS '종료 예정 시각. 종료 3초 이하에 입찰이 들어오면 5초 연장되며 갱신된다 (AUCT-010).';
COMMENT ON COLUMN auction.extension_count  IS '연장 횟수. 제한은 없으나 이상 동작 검증·통계용으로 센다.';
COMMENT ON COLUMN auction.winner_id        IS '낙찰자 (AUCT-012). status=SUCCESS 면 반드시 존재한다.';
COMMENT ON COLUMN auction.final_price      IS '낙찰가(원). status=SUCCESS 면 반드시 존재한다.';

COMMENT ON TABLE bid IS '입찰 내역. 낙찰 판정과 포인트 보류의 근거가 되는 원장.';
COMMENT ON COLUMN bid.bid_price  IS '입찰가(원). 같은 경매에서 동일 가격은 단 한 번만 성립한다.';
COMMENT ON COLUMN bid.status     IS 'ACTIVE(현재 최고) | OUTBID(상위 입찰에 밀림) | WON(낙찰) | LOST(종료 시점 최고가 아님)';
COMMENT ON COLUMN bid.created_at IS '⭐ 서버 수신 시각. 선착순 판정의 유일한 기준이며 클라이언트 클릭 시각은 쓰지 않는다 (AUCT-005).';


-- ---------- 포인트 ----------
COMMENT ON TABLE point_account IS '회원별 포인트 잔액. 기능정의서 §4.9 포인트 상태 6종을 "상태 컬럼"이 아니라 "잔액 버킷"으로 구현했다. 금액이 버킷 사이를 이동한다.';
COMMENT ON COLUMN point_account.available    IS '[사용 가능] 충전·보류 해제·환불로 들어온다. 입찰 가능액의 기준.';
COMMENT ON COLUMN point_account.bid_held     IS '[입찰 보류] 최고 입찰자가 되면 available 에서 옮겨진다 (AUCT-007).';
COMMENT ON COLUMN point_account.trade_escrow IS '[거래 보관] 낙찰·구매 후 구매 확정 전까지 묶여 있는 대금.';
COMMENT ON COLUMN point_account.settling     IS '[판매자 정산] 구매 확정 후 판매자에게 넘어갈 몫.';
COMMENT ON COLUMN point_account.withdrawing  IS '[출금 처리] 출금 요청 후 처리 중인 금액.';

COMMENT ON TABLE point_transaction IS '포인트 원장. 모든 증감을 append-only 로 남긴다. 잔액 이상 발생 시 대조 근거.';
COMMENT ON COLUMN point_transaction.type          IS 'CHARGE | BID_HOLD | BID_RELEASE | PAYMENT | SETTLEMENT | REFUND | WITHDRAW';
COMMENT ON COLUMN point_transaction.amount        IS '증감액(원). 부호 있음.';
COMMENT ON COLUMN point_transaction.balance_after IS '기록 시점의 available 잔액. 원장 재계산 없이 시점 잔액을 알 수 있다.';
COMMENT ON COLUMN point_transaction.ref_type      IS '연결 대상 종류 (AUCTION / ORDER / BID ...).';
COMMENT ON COLUMN point_transaction.ref_id        IS '연결 대상 ID. FK 를 걸지 않아 무결성은 애플리케이션 책임.';

COMMENT ON TABLE point_hold IS '입찰 보류 건. 입찰 내역 ↔ 포인트 잔액을 잇는 테이블이며 경매 동시성 제어의 핵심.';
COMMENT ON COLUMN point_hold.amount      IS '보류 금액(원). 해당 입찰가와 같다.';
COMMENT ON COLUMN point_hold.status      IS 'HELD(보류 중 = 최고 입찰자) | RELEASED(상위 입찰로 해제, AUCT-008) | CONVERTED(낙찰되어 거래 대금 전환, AUCT-012)';
COMMENT ON COLUMN point_hold.released_at IS '보류 해제 시각.';


-- ---------- 주문·배송 ----------
COMMENT ON TABLE orders IS '주문. 낙찰(AUCT-012) 또는 상시 구매로 생성된다. order 가 SQL 예약어라 테이블명이 orders 다.';
COMMENT ON COLUMN orders.auction_id      IS '낙찰로 생성된 주문의 경매. 상시 판매 주문은 NULL.';
COMMENT ON COLUMN orders.order_price     IS '결제 금액(원).';
COMMENT ON COLUMN orders.status          IS 'PAID → SHIPPING → DELIVERED → CONFIRMED → SETTLED (+ REFUNDED / CANCELED)';
COMMENT ON COLUMN orders.auto_confirm_at IS '자동 구매 확정 예정 시각(배송 완료 + 7일). 배송 완료 시점에 채워 넣고 스케줄러가 이 컬럼으로 대상을 찾는다.';

COMMENT ON TABLE order_shipment IS '배송지·송장 정보 (SHIP-*). 주문 1건당 1행.';
COMMENT ON COLUMN order_shipment.courier         IS '택배사. 송장 등록 전에는 NULL.';
COMMENT ON COLUMN order_shipment.tracking_number IS '운송장 번호. 판매자가 등록한다.';

COMMENT ON TABLE invoice IS '세금계산서 (BIZ-002). 주문당 1건, 발행 시점 사업자 정보를 스냅샷으로 저장.';
COMMENT ON COLUMN invoice.business_number      IS '발행 시점 판매자 사업자등록번호(스냅샷).';
COMMENT ON COLUMN invoice.business_name        IS '발행 시점 판매자 상호명(스냅샷).';
COMMENT ON COLUMN invoice.representative_name  IS '발행 시점 판매자 대표자명(스냅샷).';
COMMENT ON COLUMN invoice.supply_amount        IS '공급가액. round(orders.order_price / 1.1).';
COMMENT ON COLUMN invoice.tax_amount           IS '부가세. orders.order_price - supply_amount.';
COMMENT ON COLUMN invoice.total_amount         IS '합계금액. orders.order_price와 동일.';
COMMENT ON COLUMN order_shipment.delivered_at    IS '배송 완료 시각. orders.auto_confirm_at 계산 기준.';


-- ---------- 채팅 ----------
COMMENT ON TABLE chat_message IS '라이브 채팅 (CHAT-001). 비회원은 시청만 가능하고 발언할 수 없다.';
COMMENT ON COLUMN chat_message.member_id   IS '작성자. SYSTEM·AI 메시지는 NULL.';
COMMENT ON COLUMN chat_message.sender_type IS 'USER(회원 발언) | SYSTEM(입장·퇴장·경매 안내) | AI(자동 답변, CHAT-002)';
COMMENT ON COLUMN chat_message.is_blocked  IS '금칙어·도배로 차단된 메시지 (CHAT-004). 삭제 대신 플래그로 남긴다.';


-- ---------- 알림 ----------
COMMENT ON TABLE notification IS '회원 알림 (NOTI-*). 라이브·경매 트리거는 정윤 도메인에서 이벤트로 발행하고 생성은 서윤 담당.';
COMMENT ON COLUMN notification.type     IS '알림 종류 (NOTI-002 방송, NOTI-003 경매 등).';
COMMENT ON COLUMN notification.ref_type IS '연결 대상 종류 (LIVE / AUCTION / ORDER ...). 클릭 시 이동 대상.';
COMMENT ON COLUMN notification.ref_id   IS '연결 대상 ID.';
COMMENT ON COLUMN notification.is_read  IS '읽음 여부. 알림함 기본 조회가 "안 읽은 것 먼저"라 인덱스 선두에 있다.';


-- ---------- 나머지 컬럼 ----------
COMMENT ON COLUMN member.phone_number      IS '연락처. 배송·정산 확인용이며 외부 노출 금지.';
COMMENT ON COLUMN member.profile_image_url IS '프로필 이미지 URL.';
COMMENT ON COLUMN member.description       IS '소개글. 공개 프로필에 노출된다.';
COMMENT ON COLUMN member.cover_image_url   IS '커버 이미지 URL. 공개 프로필에 노출된다.';

COMMENT ON COLUMN brand.name    IS '브랜드명. 중복 불가.';
COMMENT ON COLUMN brand.name_en IS '브랜드 영문명. 없는 브랜드는 NULL.';
COMMENT ON COLUMN category.name IS '카테고리명.';

COMMENT ON COLUMN business_info.submitted_at IS '인증 서류 제출 시각.';
COMMENT ON COLUMN business_info.verified_at  IS '인증 승인·거절 처리 시각.';

COMMENT ON COLUMN product.title       IS '상품명. 통합 검색 대상이며 pg_trgm GIN 인덱스가 걸려 있다 (SEARCH-001).';
COMMENT ON COLUMN product.description IS '상품 상세 설명.';
COMMENT ON COLUMN product_image.image_key IS 'S3 오브젝트 key(전체 URL 아님). public 버킷에 저장하며 응답 시점에 고정 URL로 조립한다.';

COMMENT ON TABLE tryon_result IS 'AI 가상 시착 합성 결과물. 생성(POST) 자체는 AI 계약 확정 전이라 저장/조회/삭제만 다룬다.';
COMMENT ON COLUMN tryon_result.member_id  IS '결과물 소유자. 본인만 조회 가능 (presigned GET URL).';
COMMENT ON COLUMN tryon_result.product_id IS '합성에 사용된 상품.';
COMMENT ON COLUMN tryon_result.image_key  IS 'S3 오브젝트 key(전체 URL 아님). private 버킷에 저장하며 조회 시 presigned GET URL을 매번 새로 발급한다.';
COMMENT ON COLUMN tryon_result.deleted_at IS '사용자가 수동 삭제한 시각. 자동 만료 정책은 없다.';

COMMENT ON COLUMN live.title         IS '방송명. 통합 검색 대상 (SEARCH-001).';
COMMENT ON COLUMN live.thumbnail_url IS '방송 썸네일 URL. 홈 목록에 노출된다.';
COMMENT ON COLUMN live.started_at    IS '실제 방송 시작 시각. 예정 시각(scheduled_at)과 다를 수 있다.';
COMMENT ON COLUMN live.ended_at      IS '방송 종료 시각.';
COMMENT ON COLUMN live_product.added_at IS '상품 연결 시각.';

COMMENT ON COLUMN auction.started_at IS '경매 시작 시각 (AUCT-002 이벤트 발행 시점).';
COMMENT ON COLUMN auction.ended_at   IS '경매 종료 시각. 연장이 반영된 실제 종료 시점.';
COMMENT ON COLUMN bid.bidder_id      IS '입찰자.';

COMMENT ON COLUMN orders.buyer_id  IS '구매자. 낙찰 주문이면 auction.winner_id 와 같다.';
COMMENT ON COLUMN orders.seller_id IS '판매자. 상품 등록자와 같다.';

COMMENT ON COLUMN order_shipment.recipient_name  IS '수령인 이름.';
COMMENT ON COLUMN order_shipment.recipient_phone IS '수령인 연락처.';
COMMENT ON COLUMN order_shipment.zipcode         IS '우편번호.';
COMMENT ON COLUMN order_shipment.address1        IS '기본 주소.';
COMMENT ON COLUMN order_shipment.address2        IS '상세 주소.';
COMMENT ON COLUMN order_shipment.shipped_at      IS '발송 시각. 송장 등록 시점.';

COMMENT ON COLUMN chat_message.content IS '메시지 본문. 차단되어도 내용은 남긴다 (is_blocked 참고).';
COMMENT ON COLUMN notification.title   IS '알림 제목.';
COMMENT ON COLUMN notification.body    IS '알림 본문.';

COMMENT ON TABLE  follow              IS '회원 간 팔로우 (FOLLOW-001).';
COMMENT ON COLUMN follow.follower_id  IS '팔로우를 하는 회원 (구독자).';
COMMENT ON COLUMN follow.following_id IS '팔로우 대상 회원 (판매자/크리에이터).';

-- ---------- 공통 컬럼 ----------
-- id·created_at 같은 상용구를 테이블마다 반복해 적으면 정작 중요한 설명이 묻힌다.
-- 아직 설명이 없는 것만 골라 일괄로 채운다 (위에서 개별 지정한 것은 덮어쓰지 않는다).
DO $$
DECLARE
    r RECORD;
    txt TEXT;
BEGIN
    FOR r IN
        SELECT c.oid AS reloid, c.relname, a.attnum, a.attname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_attribute a ON a.attrelid = c.oid
        WHERE n.nspname = 'public'
          AND c.relkind = 'r'
          AND a.attnum > 0
          AND NOT a.attisdropped
          AND col_description(c.oid, a.attnum) IS NULL
          AND a.attname IN ('id', 'created_at', 'updated_at', 'deleted_at',
                            'member_id', 'product_id', 'live_id', 'auction_id',
                            'bid_id', 'order_id', 'brand_id', 'category_id')
    LOOP
        txt := CASE r.attname
            WHEN 'id'          THEN 'PK. IDENTITY 자동 채번.'
            WHEN 'created_at'  THEN '생성 시각.'
            WHEN 'updated_at'  THEN '최종 수정 시각.'
            WHEN 'deleted_at'  THEN '삭제 시각. NULL 이면 유효한 행.'
            WHEN 'member_id'   THEN '대상 회원.'
            WHEN 'product_id'  THEN '대상 상품.'
            WHEN 'live_id'     THEN '대상 라이브.'
            WHEN 'auction_id'  THEN '대상 경매.'
            WHEN 'bid_id'      THEN '근거 입찰.'
            WHEN 'order_id'    THEN '대상 주문.'
            WHEN 'brand_id'    THEN '브랜드.'
            WHEN 'category_id' THEN '카테고리.'
        END;

        EXECUTE format('COMMENT ON COLUMN %I.%I IS %L', r.relname, r.attname, txt);
    END LOOP;
END $$;
