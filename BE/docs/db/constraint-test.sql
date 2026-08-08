-- 제약 검증: 정책 위반 INSERT 가 실제로 DB 에서 거부되는지 확인한다.
--
-- 실행 (컨테이너가 떠 있는 상태에서 레포 루트 기준):
--   docker exec -i vintib-postgres psql -U postgres -c "DROP DATABASE IF EXISTS schema_check;" -c "CREATE DATABASE schema_check;"
--   docker exec -i vintib-postgres psql -U postgres -d schema_check -v ON_ERROR_STOP=1 -f - < BE/docs/db/schema.sql
--   docker exec -i vintib-postgres psql -U postgres -d schema_check -f - < BE/docs/db/constraint-test.sql
--
-- 기대 결과: 통과 11 / 실패 0
\set QUIET on
SET client_min_messages TO NOTICE;

-- ---------- 시드 ----------
INSERT INTO member (email, nickname) VALUES
    ('seller@t.com', '판매자'), ('bidder1@t.com', '입찰자1'), ('bidder2@t.com', '입찰자2');

INSERT INTO category (name, name_en) VALUES ('아우터', 'OUTER');

INSERT INTO product (seller_id, category_id, title, sale_type, sale_status, price)
VALUES (1, 1, '빈티지 데님 자켓', 'AUCTION', 'AUCTION_SCHEDULED', NULL),
       (1, 1, '울 코트',        'AUCTION', 'AUCTION_SCHEDULED', NULL);

INSERT INTO live (host_id, title, status) VALUES (1, '주말 빈티지 마켓', 'LIVE');

INSERT INTO auction (live_id, product_id, start_price, bid_unit, duration_seconds, status)
VALUES (1, 1, 10000, 1000, 120, 'RUNNING'),
       (1, 2, 20000, 1000, 120, 'READY');

INSERT INTO bid (auction_id, bidder_id, bid_price) VALUES (1, 2, 11000);
INSERT INTO point_account (member_id, available) VALUES (2, 500000), (3, 500000);
INSERT INTO point_hold (member_id, auction_id, bid_id, amount, status)
VALUES (2, 1, 1, 11000, 'HELD');

\echo ''
\echo '========== 제약 검증 =========='

DO $$
DECLARE
    passed INT := 0;
    failed INT := 0;
BEGIN
    -- 1. LIVE-004 : 한 라이브에 RUNNING 경매는 1개
    BEGIN
        INSERT INTO auction (live_id, product_id, start_price, bid_unit, duration_seconds, status)
        VALUES (1, 2, 20000, 1000, 120, 'RUNNING');
        RAISE NOTICE '[FAIL] LIVE-004  동시 RUNNING 경매 2개가 허용됨';
        failed := failed + 1;
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE '[PASS] LIVE-004  동시 RUNNING 경매 2개 거부';
        passed := passed + 1;
    END;

    -- 2. AUCT-004/005 : 같은 경매의 동일 가격 중복 입찰
    BEGIN
        INSERT INTO bid (auction_id, bidder_id, bid_price) VALUES (1, 3, 11000);
        RAISE NOTICE '[FAIL] AUCT-004  동일 가격 중복 입찰이 허용됨';
        failed := failed + 1;
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE '[PASS] AUCT-004  동일 가격 중복 입찰 거부';
        passed := passed + 1;
    END;

    -- 3. AUCT-009 : 최고 입찰자인 동안 타 경매 보류 불가
    BEGIN
        INSERT INTO bid (auction_id, bidder_id, bid_price) VALUES (2, 2, 21000);
        INSERT INTO point_hold (member_id, auction_id, bid_id, amount, status)
        VALUES (2, 2, currval(pg_get_serial_sequence('bid','id')), 21000, 'HELD');
        RAISE NOTICE '[FAIL] AUCT-009  타 경매 동시 보류가 허용됨';
        failed := failed + 1;
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE '[PASS] AUCT-009  타 경매 동시 보류 거부';
        passed := passed + 1;
    END;

    -- 4. AUCT-006 : 최고 입찰자의 연속 입찰(같은 경매 재보류) 불가
    BEGIN
        INSERT INTO point_hold (member_id, auction_id, bid_id, amount, status)
        VALUES (2, 1, 1, 12000, 'HELD');
        RAISE NOTICE '[FAIL] AUCT-006  최고 입찰자 연속 보류가 허용됨';
        failed := failed + 1;
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE '[PASS] AUCT-006  최고 입찰자 연속 보류 거부';
        passed := passed + 1;
    END;

    -- 5. AUCT-008 : 보류 해제 후에는 재보류 가능해야 한다 (부분 인덱스 동작 확인)
    BEGIN
        UPDATE point_hold SET status = 'RELEASED', released_at = now() WHERE id = 1;
        INSERT INTO bid (auction_id, bidder_id, bid_price) VALUES (2, 2, 22000);
        INSERT INTO point_hold (member_id, auction_id, bid_id, amount, status)
        VALUES (2, 2, currval(pg_get_serial_sequence('bid','id')), 22000, 'HELD');
        RAISE NOTICE '[PASS] AUCT-008  보류 해제 후 재보류 성공';
        passed := passed + 1;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE '[FAIL] AUCT-008  해제 후 재보류가 거부됨: %', SQLERRM;
        failed := failed + 1;
    END;

    -- 6. 낙찰 상태인데 낙찰자·낙찰가 누락
    BEGIN
        UPDATE auction SET status = 'SUCCESS' WHERE id = 1;
        RAISE NOTICE '[FAIL] AUCT-012  낙찰자 없는 SUCCESS 가 허용됨';
        failed := failed + 1;
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE '[PASS] AUCT-012  낙찰자 없는 SUCCESS 거부';
        passed := passed + 1;
    END;

    -- 7. 포인트 잔액 음수
    BEGIN
        UPDATE point_account SET available = -1 WHERE member_id = 2;
        RAISE NOTICE '[FAIL] POINT    잔액 음수가 허용됨';
        failed := failed + 1;
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE '[PASS] POINT    잔액 음수 거부';
        passed := passed + 1;
    END;

    -- 8. 정찰제인데 가격 없음
    BEGIN
        INSERT INTO product (seller_id, category_id, title, sale_type, sale_status, price)
        VALUES (1, 1, '가격없는 정찰제', 'DIRECT_SALE', 'ON_SALE', NULL);
        RAISE NOTICE '[FAIL] PROD     가격 없는 정찰제가 허용됨';
        failed := failed + 1;
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE '[PASS] PROD     가격 없는 정찰제 거부';
        passed := passed + 1;
    END;

    -- 9. 자기 자신에게 주문
    BEGIN
        INSERT INTO orders (buyer_id, seller_id, product_id, order_price)
        VALUES (1, 1, 1, 10000);
        RAISE NOTICE '[FAIL] ORDER    자기 자신에게 주문이 허용됨';
        failed := failed + 1;
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE '[PASS] ORDER    자기 자신에게 주문 거부';
        passed := passed + 1;
    END;

    -- 10. 회원 발언인데 작성자 없음
    BEGIN
        INSERT INTO chat_message (live_id, member_id, sender_type, content)
        VALUES (1, NULL, 'USER', '작성자 없는 회원 발언');
        RAISE NOTICE '[FAIL] CHAT-001 작성자 없는 USER 발언이 허용됨';
        failed := failed + 1;
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE '[PASS] CHAT-001 작성자 없는 USER 발언 거부';
        passed := passed + 1;
    END;

    -- 11. 자기 자신 팔로우
    BEGIN
        INSERT INTO follow (follower_id, following_id) VALUES (1, 1);
        RAISE NOTICE '[FAIL] FOLLOW   자기 자신 팔로우가 허용됨';
        failed := failed + 1;
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE '[PASS] FOLLOW   자기 자신 팔로우 거부';
        passed := passed + 1;
    END;

    RAISE NOTICE '';
    RAISE NOTICE '===== 통과 % / 실패 % =====', passed, failed;
END $$;
