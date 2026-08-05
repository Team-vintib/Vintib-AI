-- 상품 데모 시드 40건 (DemoMemberSeeder @Order(1) 이후 실행).
-- seller는 시드 계정 4명에게 배분
-- 브랜드 마스터에 없는 경우 brand_id = NULL, ai_model_enabled 기본값 false.

INSERT INTO product (
    seller_id, category_id, brand_id, title, description,
    condition_grade, size_label, color, material,
    sale_type, sale_status, price, ai_model_enabled, ai_model_gender,
    created_at, updated_at
) VALUES
    -- 1. Brunello Cucinelli BC 로고 반팔 티셔츠
    (
        (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        'Brunello Cucinelli BC 로고 반팔 티셔츠', '구매 후 1년 반, 한 번도 미착용. 택 없는 새상품급. 슬림핏 / Made in Italy.',
        'S', 'M', 'PURPLE', 'Cotton 100%',
        'DIRECT_SALE', 'ON_SALE', 330000, false, NULL,
        NOW() - INTERVAL '19 days', NOW() - INTERVAL '19 days'
    ),
    -- 2. Maison Kitsuné 더블 모노크롬 폭스 헤드 패치 클래식 티셔츠
    (
        (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        'Maison Kitsuné 더블 모노크롬 폭스 헤드 패치 클래식 티셔츠 블랙', '시착 0회. 더블 폭스 헤드 자수 패치. Maison Kitsuné Paris 정품.',
        'S', 'S', 'BLACK', 'Cotton 100%',
        'DIRECT_SALE', 'ON_SALE', 85000, false, NULL,
        NOW() - INTERVAL '18 days', NOW() - INTERVAL '18 days'
    ),
    -- 3. Maison Kitsuné 더블 폭스 헤드 패치 폴로 반팔 셔츠
    (
        (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'SHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        '메종 키츠네 더블 폭스 헤드 패치 폴로 반팔 셔츠 블랙', '워싱 물 빠짐·사용감 존재. 실측: 어깨 40 / 가슴 44 / 총기장 64 (cm). 택배비 포함 가격.',
        'B', 'S', 'BLACK', 'Cotton 100%',
        'DIRECT_SALE', 'ON_SALE', 65000, false, NULL,
        NOW() - INTERVAL '1 days', NOW() - INTERVAL '1 days'
    ),
    -- 4. Maison Margiela 18FW PVC 패치 데님팬츠
    (
        (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        (SELECT id FROM brand WHERE name_en = 'Maison Margiela'),
        'Maison Margiela 18FW PVC 패치 데님팬츠', '18FW 라인 10 남성. 뒷허리 PVC 밴딩·패치 디테일. 중청 워싱, 레귤러 핏. 밑단 수선(자연스럽게 작업됨). 오른다리 미세 오염 있음. Made in Italy.',
        'B', '31', 'MEDIUM_BLUE', 'Cotton 100%',
        'DIRECT_SALE', 'ON_SALE', 320000, false, NULL,
        NOW() - INTERVAL '16 days', NOW() - INTERVAL '16 days'
    ),
    -- 5. Diesel Safado 딥 인디고 데님팬츠
    (
        (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        'Diesel Safado 딥 인디고 데님팬츠', '슬림 스트레이트 시그니처 모델. 딥 인디고 생지 컬러. 레귤러 슬림 스트레이트 핏. 사용감 외 큰 하자 없음. W29 L32.',
        'B', 'W29 L32', 'DARK_BLUE', 'Cotton 98%, Elastane 2%',
        'DIRECT_SALE', 'ON_SALE', 78000, false, NULL,
        NOW() - INTERVAL '15 days', NOW() - INTERVAL '15 days'
    ),
    -- 6. 90’s 히스테릭 글래머 아카이브 패치워크
    (
        (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        '90’s 히스테릭 글래머 아카이브 패치워크', '사고 싶은게 생겨서 판매합니다. 안전결제 전에 채팅 부탁드립니다. 거래 불가 상태일 수 있기 때문입니다. 계좌 거래로 진행합니다. 디스 디테일, 패치워크, 자연스러운 페이딩과 워싱이 들어간 슬림 스트레이트 핏 데님입니다. 스터드 디테일이 있는 히스테릭 글래머의 대표적인 상품입니다. 상태는 하자 없이 매우 좋습니다. 하늘색 스트라이프 패치워크는 제가 덧댄 것으로, 바지 자체 디테일은 아니지만 탈착이 가능하며 제품 상태에 영향을 주지 않습니다.',
        'A', 'M', 'LIGHT_BLUE', 'Cotton 100%',
        'DIRECT_SALE', 'ON_SALE', 195000, false, NULL,
        NOW() - INTERVAL '14 days', NOW() - INTERVAL '14 days'
    ),
    -- 7. guess X hysteric glamour 청반바지 26
    (
        (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        'guess X hysteric glamour 청반바지 26', '히스테릭 글래머와 게스 콜라보레이션 청반바지입니다. 특별한 오염이나 하자가 없으며 바로 착용 가능한 양호한 상태입니다. 빈티지/중고 상품 특성상 자연스러운 사용감이나 미세한 오염이 있을 수 있으니 신중한 구매 부탁드립니다. 실측 사이즈를 반드시 확인해 주세요. (교환 및 환불 불가)',
        'A', '26', 'BLUE', 'Cotton 100%',
        'DIRECT_SALE', 'ON_SALE', 200000, false, NULL,
        NOW() - INTERVAL '13 days', NOW() - INTERVAL '13 days'
    ),
    -- 8. 준야와타나베 카프리 기장 팬츠
    (
        (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        '준야와타나베 카프리 기장 팬츠', '뉴욕 도버 스트릿 마켓에서 구매된 제품을 매물로 구했습니다. 안감 디테일과 밴딩에 들어간 카모 프린트가 매력적인 팬츠입니다. 턱이 잡힌 원단과 핏이 매우 예쁩니다. 제품 착용샷은 아니지만 참고용 사진과 유사한 핏이 나옵니다.',
        'A', 'M', 'KHAKI', 'Cotton 100%',
        'DIRECT_SALE', 'ON_SALE', 250000, false, NULL,
        NOW() - INTERVAL '12 days', NOW() - INTERVAL '12 days'
    ),
    -- 9. XS) 준야와타나베 빈티지 레이어드 데님팬츠
    (
        (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        'XS) 준야와타나베 빈티지 레이어드 데님팬츠', '실측 사이즈: 허리 40 / 허벅지 29 / 밑단 21 / 밑위 32 / 총장 93 (표기 사이즈 XS). 문의 언제든지 환영합니다. 아이폰 자동 색보정으로 인해 제품의 사진과 실물 간의 색상 차이가 존재할 수 있습니다 (실제 색상은 착용샷과 가장 유사합니다).',
        'A', 'XS', 'BLUE', 'Cotton 100%',
        'DIRECT_SALE', 'ON_SALE', 180000, false, NULL,
        NOW() - INTERVAL '11 days', NOW() - INTERVAL '11 days'
    ),
    -- 10. 앤더슨벨 패치워크 와이드 데님 팬츠
    (
        (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        '앤더슨벨 패치워크 와이드 데님 팬츠', '앤더슨벨 팬츠입니다. 상태가 매우 좋으며 하자 없이 잘 관리되었습니다.',
        'A', '32', 'BLUE', 'Cotton 100%',
        'DIRECT_SALE', 'ON_SALE', 120000, false, NULL,
        NOW() - INTERVAL '10 days', NOW() - INTERVAL '10 days'
    ),
    -- 11. 리메이크 Levi's 데님
    (
        (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        (SELECT id FROM brand WHERE name_en = 'Levi''s'),
        '리메이크 Levi''s 데님', '리메이크 된 리바이스 데님입니다. 일본 빈티지샵 ''matakiso''에서 구매하였습니다. 손이 잘 가지 않아 판매합니다. 실착은 1회이고, 정확한 사이즈는 문의 부탁드립니다. 편하게 문의 주세요.',
        'S', 'FREE', 'BLUE', 'Cotton 100%',
        'DIRECT_SALE', 'ON_SALE', 80000, false, NULL,
        NOW() - INTERVAL '9 days', NOW() - INTERVAL '9 days'
    ),
    -- 12. 에비수 새상품 진청 빅 다이콕 데님 팬츠 청바지 30
    (
        (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        '에비수 새상품 진청 빅 다이콕 데님 팬츠 청바지 30', 'Whose Pants - Serial No.3720. 새상품입니다. 실측 사이즈: 허리단면 38 / 밑위 25 / 허벅지단면 26 / 밑단 18 / 총장 110 (단위: cm).',
        'S', '30', 'DARK_BLUE', 'Cotton 100%',
        'DIRECT_SALE', 'ON_SALE', 180000, false, NULL,
        NOW() - INTERVAL '8 days', NOW() - INTERVAL '8 days'
    ),
    -- 13. BBC 아이스크림 개바지
    (
        (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        'BBC 아이스크림 개바지', '3년 전 포르투갈 리스본의 sun of gon 편집샵에서 구매했습니다. 5번 내외로 착용하여 사용감이 매우 적으며, 프린팅 상태도 최상급입니다. 택도 보유 중입니다.',
        'A', '32', 'BLUE', 'Cotton 100%',
        'DIRECT_SALE', 'ON_SALE', 320000, false, NULL,
        NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days'
    ),
    -- 14. 실리크롬 목걸이 급처 정품
    (
        (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'JEWELRY' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        '실리크롬 목걸이 급처 정품', '실리크롬 목걸이입니다. 100% 정품이고 색상은 블랙입니다. 급처라 계좌 거래만 받습니다.',
        'A', 'FREE', 'BLACK', 'Silicone',
        'DIRECT_SALE', 'ON_SALE', 250000, false, NULL,
        NOW() - INTERVAL '6 days', NOW() - INTERVAL '6 days'
    ),
    -- 15. [US8] 크롬하츠 키퍼링 실버
    (
        (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'JEWELRY' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        '[US8] 크롬하츠 키퍼링 실버', '크롬하츠 키퍼 링 실버입니다. 매장에서 구매한 새상품이며, 개인정보 제거 후 인보이스를 같이 드립니다. 모든 상품은 정품이며 가품 시 1000% 환불해 드립니다. 중고 상품 특성상 가품 외 교환 및 환불은 불가합니다.',
        'S', 'US 8', 'GRAY', 'Silver 925',
        'DIRECT_SALE', 'ON_SALE', 3700000, false, NULL,
        NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days'
    ),
    -- 16. 나이키 슈프림 14k 골드 링 반지 박효신
    (
        (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'JEWELRY' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        (SELECT id FROM brand WHERE name_en = 'Nike'),
        '나이키 슈프림 14k 골드 링 반지 박효신', '박효신님도 애착하셨던 19시즌 나이키 슈프림 14k 링입니다! 매물 없는 희귀한 제품이며, 사진보다 실물이 더 깔끔하고 예쁩니다. 주머니(파우치)와 함께 보내드립니다.',
        'A', '13호(KR)', 'YELLOW', '14k Gold',
        'DIRECT_SALE', 'ON_SALE', 800000, false, NULL,
        NOW() - INTERVAL '4 days', NOW() - INTERVAL '4 days'
    ),
    -- 17. Distressed grunge t-shirts
    (
        (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        'Distressed grunge t-shirts', '새상품 싱글스티치 반팔티에 직접 디스 작업을 진행했습니다. "Torn, repaired, and reborn." 찢어지고, 꿰매지고, 다시 태어난 한 벌의 티셔츠입니다. 데일리로 입기 좋고 레이어드용으로도 예쁩니다. 수수료는 판매자가 부담합니다.',
        'S', 'FREE', 'GRAY', 'Cotton 100%',
        'DIRECT_SALE', 'ON_SALE', 55000, false, NULL,
        NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'
    ),
    -- 18. 90's mood grunge distressed tees (긴팔 포함)
    (
        (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        '90''s mood grunge distressed tees (긴팔 포함)', '새상품에 데저트 컬러 무드로 디스트레스드 및 워싱 작업을 진행했습니다. 빈티지 무드가 좋아 데일리로 입기 좋고, 반팔 단품이나 FW 시즌 긴팔 레이어드용으로 모두 예쁩니다. 핏이 예쁘게 떨어지며, 긴팔 티셔츠 하나를 같이 보내드립니다! 수수료는 판매자가 부담합니다.',
        'S', 'L', 'BEIGE', 'Cotton 100%',
        'DIRECT_SALE', 'ON_SALE', 93000, false, NULL,
        NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days'
    ),
    -- 19. Harley Davidson Cap
    (
        (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'HAT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        (SELECT id FROM brand WHERE name_en = 'Harley Davidson'),
        'Harley Davidson Cap', '할리데이비슨(Harley Davidson) 캡 모자입니다.',
        'A', 'FREE', 'BLACK', 'Cotton 100%',
        'DIRECT_SALE', 'ON_SALE', 80100, false, NULL,
        NOW() - INTERVAL '1 days', NOW() - INTERVAL '1 days'
    ),
    -- 20. 국내 유일 y2k 야후 빈티지 볼캡 모자 & 보스톤백 더플백
    (
        (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'HAT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        '국내 유일 y2k 야후 빈티지 볼캡 모자 & 보스톤백 더플백', '일괄로만 판매하며 낱개 판매 불가합니다. 추억의 야후 자수로고 볼캡 모자(네이비, Free)와 보스턴백(대략 가로 45cm x 세로 38cm) 세트입니다. 두 제품 모두 큰 오염이나 데미지는 없으나 약간의 사용감이 있는 상태(8.5/10)입니다. 교환 및 환불은 불가합니다.',
        'A', 'FREE', 'NAVY', 'Cotton / Poly',
        'DIRECT_SALE', 'ON_SALE', 87000, false, NULL,
        NOW(), NOW()
    ),
    -- 21. 메종키츠네 아이보리 여성가디건 55~55반
    (
        (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'CARDIGAN' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'OUTER' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
        NULL,
        '메종키츠네 아이보리 여성가디건 55~55반', '백화점에서 구입하여 백화점 AS 가능합니다. 구입가는 55만 원대였으며, 몇 번 입지 않아 상태가 최상입니다.',
        'S', '55~55반', NULL, NULL,
        'DIRECT_SALE', 'ON_SALE', 245500, false, NULL,
        NOW(), NOW()
    ),
    -- 22. 톰브라운 밀라노스티치 가디건 4사이즈
    (
        (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'CARDIGAN' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'OUTER' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
        NULL,
        '톰브라운 밀라노스티치 가디건 4사이즈', '톰브라운 밀라노스티치 가디건 4사이즈입니다. 상태 좋고 단품입니다.',
        'A', '4', 'NAVY', 'Cotton 100%',
        'DIRECT_SALE', 'ON_SALE', 600000, false, NULL,
        NOW(), NOW()
    ),
    -- 23. AMI 아미 빅하트 로고 가디건 베이지(L)
    (
        (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'CARDIGAN' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'OUTER' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
        NULL,
        'AMI 아미 빅하트 로고 가디건 베이지(L)', '개인 판매자입니다. 크림(KREAM)에서 구매한 100% 정품이며, 2회 착용하여 상태가 매우 좋습니다.',
        'S', 'L', 'BEIGE', 'Wool 100%',
        'DIRECT_SALE', 'ON_SALE', 350000, false, NULL,
        NOW(), NOW()
    ),
    -- 24. Thom Browne 톰브라운 히든삼선 타탄체크 셔츠 1
    (
        (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'SHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
        NULL,
        'Thom Browne 톰브라운 히든삼선 타탄체크 셔츠 1', '톰브라운의 시그니처 컬러(레드/블루/화이트) 체크 패턴에 히든 삼선 테이핑 디테일이 더해진 FW 코튼 셔츠입니다. 인기 시즌 제품으로, 몇 번 착용 후 세탁하여 보관만 해둔 상태이며 이염 및 데미지 없는 좋은 컨디션을 유지하고 있습니다.',
        'A', '1', 'MIXED', 'Cotton 100%',
        'DIRECT_SALE', 'ON_SALE', 250000, false, NULL,
        NOW(), NOW()
    ),
    -- 25. [M] 폴로랄프로렌 릴렉스 플리스 라인 트러커 자켓 새상품
    (
        (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'JACKET' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'OUTER' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
        (SELECT id FROM brand WHERE name_en = 'Polo Ralph Lauren'),
        '[M] 폴로랄프로렌 릴렉스 플리스 라인 트러커 자켓 새상품', '택 달린 새상품입니다. 실측 사이즈: 가슴 56 / 총장 62 / 어깨 17 / 소매 64 (단위: cm).',
        'S', 'M', NULL, NULL,
        'DIRECT_SALE', 'ON_SALE', 250000, false, NULL,
        NOW(), NOW()
    ),
    -- 26. 미군 장교 트렌치코트 L-XL
    (
        (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'COAT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'OUTER' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
        NULL,
        '미군 장교 트렌치코트 L-XL', '옷장 정리로 판매합니다. 빈티지샵에서 구매한 제품으로, 미국의 미군 제복 및 관련 의류 제조업체인 Old Master Products, Inc. 산하의 Garrison Collection 제품입니다. L~XL 사이즈 입으시는 분들께 추천합니다. (내피 O, 허리벨트 O)',
        'B', 'L-XL', 'BEIGE', 'Cotton / Poly',
        'DIRECT_SALE', 'ON_SALE', 88000, false, NULL,
        NOW(), NOW()
    ),
    -- 27. 쇼트 블레이저 xl
    (
        (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'JACKET' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'OUTER' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
        NULL,
        '쇼트 블레이저 xl', '쇼트(Schott) 브랜드의 블레이저 자켓입니다. 무난한 블랙 색상으로 다양하게 활용하기 좋습니다.',
        'A', 'XL', 'BLACK', 'Wool / Poly',
        'DIRECT_SALE', 'ON_SALE', 130000, false, NULL,
        NOW(), NOW()
    ),
    -- 28. 아비렉스 빅 로고 스펠아웃 밀리터리 캠프 봄버 자켓
    (
        (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'JACKET' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'OUTER' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
        NULL,
        '아비렉스 빅 로고 스펠아웃 밀리터리 캠프 봄버 자켓', '밀리터리 브랜드를 대표하는 아비렉스의 밀리터리 캠프 드랍존 모디파이 헤일로 자켓입니다. High Altitude Low Opening에서 영감을 받아 제작되었으며, 보온성과 탄성이 뛰어난 고기능성 F/W 전용 제품입니다. 블랙 & 실버 조합으로 택티컬한 무드 연출이 가능하며, 리플렉티브 포인트, 벨크로 패치, 하이넥 유틸리티 버클 등의 디테일이 특징입니다. 사용감이 적어 좋은 컨디션을 유지하고 있습니다.',
        'A', NULL, 'BLACK', NULL,
        'DIRECT_SALE', 'ON_SALE', 300000, false, NULL,
        NOW(), NOW()
    ),
    -- 29. 잔스포츠백팩
    (
        (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'BACKPACK' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BAG' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        '잔스포츠백팩', '잔스포츠 백팩입니다. 흔하게 볼 수 없는 구하기 힘든 유니크한 디자인의 제품입니다.',
        'A', 'FREE', 'BLACK', 'Nylon / Poly',
        'DIRECT_SALE', 'ON_SALE', 150000, false, NULL,
        NOW(), NOW()
    ),
    -- 30. 밀라숀 넥타이 리폼 스카프
    (
        (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'SCARF' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        '밀라숀 넥타이 리폼 스카프', '밀라숀(Mila Schon)의 넥타이를 스카프로 리폼한 제품입니다. 키치한 패턴이 귀엽고 상태 정말 좋습니다.',
        'A', 'FREE', 'MIXED', 'Silk 100%',
        'DIRECT_SALE', 'ON_SALE', 80000, false, NULL,
        NOW(), NOW()
    ),
    -- 31. 나비 타이
    (
        (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'SCARF' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        '나비 타이', '일본 브랜드 나비 타이입니다. 미사용 새제품입니다. (교환 및 환불 불가)',
        'S', 'FREE', 'NAVY', 'Silk 100%',
        'DIRECT_SALE', 'ON_SALE', 35000, false, NULL,
        NOW(), NOW()
    ),
    -- 32. 크롬하츠 blueher 블랙&블루
    (
        (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'SUNGLASSES' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        '크롬하츠 blueher 블랙&블루', '크롬하츠(Chrome Hearts) blueher 블랙&블루 안경테 제품입니다.',
        'A', 'FREE', NULL, NULL,
        'DIRECT_SALE', 'ON_SALE', 3000000, false, NULL,
        NOW(), NOW()
    ),
    -- 33. [280] 아디다스 x 스포티 앤 리치 삼바 버건디
    (
        (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'SNEAKERS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'SHOES' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        (SELECT id FROM brand WHERE name_en = 'Adidas'),
        '[280] 아디다스 x 스포티 앤 리치 삼바 버건디', '아디다스 x 스포티 앤 리치 삼바 OG 클라우드 화이트 컬리지에이트 버건디 280 사이즈입니다. 실착 2번 하여 상태 깨끗하고 좋습니다. 배송비는 판매자가 부담합니다.',
        'A', '280', 'RED', 'Leather / Suede',
        'DIRECT_SALE', 'ON_SALE', 98000, false, NULL,
        NOW(), NOW()
    ),
    -- 34. 나이키 x 슈프림 에어포스 1 로우 블랙
    (
        (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'SNEAKERS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'SHOES' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        (SELECT id FROM brand WHERE name_en = 'Nike'),
        '나이키 x 슈프림 에어포스 1 로우 블랙', '나이키 에어포스 1 로우 블랙 슈프림 콜라보 제품입니다. 전체적으로 사용감은 있지만 눈에 띄는 큰 흠집이나 오염 없이 상태 양호합니다. 박스 포함 풀 구성이며, 판매하는 상품은 모두 정품입니다. 실측 사이즈 및 착용샷 문의는 받지 않습니다.',
        'B', '270', 'BLACK', 'Leather',
        'DIRECT_SALE', 'ON_SALE', 130000, false, NULL,
        NOW(), NOW()
    ),
    -- 35. aa 나이키 에어조던 와이낫제로5 농구화 285
    (
        (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'SNEAKERS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'SHOES' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        (SELECT id FROM brand WHERE name_en = 'Nike'),
        'aa 나이키 에어조던 와이낫제로5 농구화 285', '약간의 사용감이 있지만 상태가 좋습니다. 관심 있으신 분은 자세히 보시고 구매 부탁드립니다. (제주/도서산간 추가 배송비 있습니다) ※ 묶음배송 할인: 2개 구매 시 배송비 무료, 4개 구매 시 20% 할인 + 배송비 무료',
        'A', '285', 'MIXED', 'Synthetic / Mesh',
        'DIRECT_SALE', 'ON_SALE', 28500, false, NULL,
        NOW(), NOW()
    ),
    -- 36. 290.컨버스 x 스투시 척70 하이 플루메리아 핑크
    (
        (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'SNEAKERS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'SHOES' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        (SELECT id FROM brand WHERE name_en = 'Converse'),
        '290.컨버스 x 스투시 척70 하이 플루메리아 핑크', '컨버스 x 스투시 척70 핑크 (품번: A02052C) 제품입니다. 290 사이즈, 미시착 새상품입니다.',
        'S', '290', 'PINK', 'Canvas',
        'DIRECT_SALE', 'ON_SALE', 175000, false, NULL,
        NOW(), NOW()
    ),
    -- 37. 아디다스 베이프 포럼84 로우 그린 카모
    (
        (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'SNEAKERS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'SHOES' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        (SELECT id FROM brand WHERE name_en = 'Adidas'),
        '아디다스 베이프 포럼84 로우 그린 카모', '크림(KREAM)에서 구매 후 2~3회 착용했습니다. 신발 소재 특성상 뒤쪽에 보풀이 있으니 참고 부탁드립니다. (구성품: 박스, 더스트백, 신발끈)',
        'A', '245', 'GREEN', 'Leather / Suede',
        'DIRECT_SALE', 'ON_SALE', 150000, false, NULL,
        NOW(), NOW()
    ),
    -- 38. 생로랑 SL 816 Black
    (
        (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'SUNGLASSES' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        '생로랑 SL 816 Black', '6월에 구매한 생로랑(Saint Laurent) SL 816 Black 모델 새상품입니다. (케이스 포함) 저에게 어울리지 않아 판매하며, 문자 2통 이내 쿨거래 시 택배비 포함으로 드립니다. (구매 문의 외 다른 문의는 받지 않습니다.)',
        'S', 'FREE', 'BLACK', 'Acetate',
        'DIRECT_SALE', 'ON_SALE', 380000, false, NULL,
        NOW(), NOW()
    ),
    -- 39. YSL 생로랑 반지갑
    (
        (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'POUCH' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BAG' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
        NULL,
        'YSL 생로랑 반지갑', '구매 후 한동안 사용하다 판매합니다. 연식 대비 가죽 상태 양호합니다. YSL 로고 부분에 도색 벗겨짐이 살짝 있으나 셀프 도색으로 보완 가능합니다. 구매 시 받은 정품 박스도 동봉해 드립니다.',
        'B', NULL, NULL, 'Leather',
        'DIRECT_SALE', 'ON_SALE', 105000, false, NULL,
        NOW(), NOW()
    ),
    -- 40. 메종키츠네 골프 폭스헤드 pk XXL(105~110) 새상품
    (
        (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
        (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
        NULL,
        '메종키츠네 골프 폭스헤드 pk XXL(105~110) 새상품', '선물 받은 후 입지 않아 판매합니다. 택만 제거된 새상품이며, 23 SS 시즌 이월 상품입니다.',
        'S', 'XXL', 'WHITE', 'Cotton 100%',
        'DIRECT_SALE', 'ON_SALE', 150000, false, NULL,
        NOW(), NOW()
    );