-- 상품 데모 시드 101건 (DemoMemberSeeder @Order(1) 이후 실행).
-- seller는 시드 계정 6명에게 배분
-- brand는 브랜드 마스터 FK가 아니라 자유 텍스트다(BE 결정) — 브랜드가 없으면 NULL,
-- ai_model_enabled 기본값 false.

INSERT INTO product (
    seller_id, category_id, brand, title, description,
    condition_grade, size_label, color, material,
    sale_type, sale_status, price, ai_model_enabled, ai_model_gender,
    created_at, updated_at
) VALUES
      -- Brunello Cucinelli BC 로고 반팔 티셔츠
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          'Brunello Cucinelli BC 로고 반팔 티셔츠', '구매 후 1년 반, 한 번도 미착용. 택 없는 새상품급. 슬림핏 / Made in Italy.',
          'S', 'M', 'PURPLE', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 330000, false, NULL,
          NOW() - INTERVAL '62 days', NOW() - INTERVAL '62 days'
      ),
      -- 2. Maison Kitsuné 더블 모노크롬 폭스 헤드 패치 클래식 티셔츠
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          'Maison Kitsuné 더블 모노크롬 폭스 헤드 패치 클래식 티셔츠 블랙', '시착 0회. 더블 폭스 헤드 자수 패치. Maison Kitsuné Paris 정품.',
          'S', 'S', 'BLACK', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 85000, false, NULL,
          NOW(), NOW()
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
          'Maison Margiela',
          'Maison Margiela 18FW PVC 패치 데님팬츠', '18FW 라인 10 남성. 뒷허리 PVC 밴딩·패치 디테일. 중청 워싱, 레귤러 핏. 밑단 수선(자연스럽게 작업됨). 오른다리 미세 오염 있음. Made in Italy.',
          'B', 'M', 'BLUE', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 320000, false, NULL,
          NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days'
      ),
      -- Diesel Safado 딥 인디고 데님팬츠
      (
          (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          'Diesel Safado 딥 인디고 데님팬츠', '슬림 스트레이트 시그니처 모델. 딥 인디고 생지 컬러. 레귤러 슬림 스트레이트 핏. 사용감 외 큰 하자 없음. W29 L32.',
          'B', 'S', 'BLUE', '면 98%, 스판덱스 2%',
          'DIRECT_SALE', 'ON_SALE', 78000, false, NULL,
          NOW() - INTERVAL '63 days', NOW() - INTERVAL '63 days'
      ),
      -- 90’s 히스테릭 글래머 아카이브 패치워크
      (
          (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '90’s 히스테릭 글래머 아카이브 패치워크', '사고 싶은게 생겨서 판매합니다. 안전결제 전에 채팅 부탁드립니다. 거래 불가 상태일 수 있기 때문입니다. 계좌 거래로 진행합니다. 디스 디테일, 패치워크, 자연스러운 페이딩과 워싱이 들어간 슬림 스트레이트 핏 데님입니다. 스터드 디테일이 있는 히스테릭 글래머의 대표적인 상품입니다. 상태는 하자 없이 매우 좋습니다. 하늘색 스트라이프 패치워크는 제가 덧댄 것으로, 바지 자체 디테일은 아니지만 탈착이 가능하며 제품 상태에 영향을 주지 않습니다.',
          'A', 'M', 'BLUE', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 195000, false, NULL,
          NOW() - INTERVAL '64 days', NOW() - INTERVAL '64 days'
      ),
      -- 7. guess X hysteric glamour 청반바지 26
      (
          (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          'guess X hysteric glamour 청반바지 26', '히스테릭 글래머와 게스 콜라보레이션 청반바지입니다. 특별한 오염이나 하자가 없으며 바로 착용 가능한 양호한 상태입니다. 빈티지/중고 상품 특성상 자연스러운 사용감이나 미세한 오염이 있을 수 있으니 신중한 구매 부탁드립니다. 실측 사이즈를 반드시 확인해 주세요. (교환 및 환불 불가)',
          'A', 'XS', 'BLUE', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 200000, false, NULL,
          NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'
      ),
      -- 준야와타나베 카프리 기장 팬츠
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '준야와타나베 카프리 기장 팬츠', '뉴욕 도버 스트릿 마켓에서 구매된 제품을 매물로 구했습니다. 안감 디테일과 밴딩에 들어간 카모 프린트가 매력적인 팬츠입니다. 턱이 잡힌 원단과 핏이 매우 예쁩니다. 제품 착용샷은 아니지만 참고용 사진과 유사한 핏이 나옵니다.',
          'A', 'M', 'KHAKI', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 250000, false, NULL,
          NOW() - INTERVAL '65 days', NOW() - INTERVAL '65 days'
      ),
      -- XS) 준야와타나베 빈티지 레이어드 데님팬츠
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          'XS) 준야와타나베 빈티지 레이어드 데님팬츠', '실측 사이즈: 허리 40 / 허벅지 29 / 밑단 21 / 밑위 32 / 총장 93 (표기 사이즈 XS). 문의 언제든지 환영합니다. 아이폰 자동 색보정으로 인해 제품의 사진과 실물 간의 색상 차이가 존재할 수 있습니다 (실제 색상은 착용샷과 가장 유사합니다).',
          'A', 'XS', 'BLUE', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 180000, false, NULL,
          NOW() - INTERVAL '66 days', NOW() - INTERVAL '66 days'
      ),
      -- 앤더슨벨 패치워크 와이드 데님 팬츠
      (
          (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '앤더슨벨 패치워크 와이드 데님 팬츠', '앤더슨벨 팬츠입니다. 상태가 매우 좋으며 하자 없이 잘 관리되었습니다.',
          'A', 'M', 'BLUE', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 120000, false, NULL,
          NOW() - INTERVAL '67 days', NOW() - INTERVAL '67 days'
      ),
      -- 11. 리메이크 Levi's 데님
      (
          (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          'Levi''s',
          '리메이크 Levi''s 데님', '리메이크 된 리바이스 데님입니다. 일본 빈티지샵 ''matakiso''에서 구매하였습니다. 손이 잘 가지 않아 판매합니다. 실착은 1회이고, 정확한 사이즈는 문의 부탁드립니다. 편하게 문의 주세요.',
          'S', 'FREE', 'BLUE', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 80000, false, NULL,
          NOW() - INTERVAL '4 days', NOW() - INTERVAL '4 days'
      ),
      -- 12. 에비수 새상품 진청 빅 다이콕 데님 팬츠 청바지 30
      (
          (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '에비수 새상품 진청 빅 다이콕 데님 팬츠 청바지 30', 'Whose Pants - Serial No.3720. 새상품입니다. 실측 사이즈: 허리단면 38 / 밑위 25 / 허벅지단면 26 / 밑단 18 / 총장 110 (단위: cm).',
          'S', 'S', 'BLUE', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 180000, false, NULL,
          NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days'
      ),
      -- BBC 아이스크림 개바지
      (
          (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          'BBC 아이스크림 개바지', '3년 전 포르투갈 리스본의 sun of gon 편집샵에서 구매했습니다. 5번 내외로 착용하여 사용감이 매우 적으며, 프린팅 상태도 최상급입니다. 택도 보유 중입니다.',
          'A', 'M', 'BLUE', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 320000, false, NULL,
          NOW() - INTERVAL '68 days', NOW() - INTERVAL '68 days'
      ),
      -- 14. 실리크롬 목걸이 급처 정품
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'JEWELRY' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '실리크롬 목걸이 급처 정품', '실리크롬 목걸이입니다. 100% 정품이고 색상은 블랙입니다. 급처라 계좌 거래만 받습니다.',
          'A', 'FREE', 'BLACK', '실리콘',
          'DIRECT_SALE', 'ON_SALE', 250000, false, NULL,
          NOW() - INTERVAL '6 days', NOW() - INTERVAL '6 days'
      ),
      -- 15. [US8] 크롬하츠 키퍼링 실버
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'JEWELRY' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '[US8] 크롬하츠 키퍼링 실버', '크롬하츠 키퍼 링 실버입니다. 매장에서 구매한 새상품이며, 개인정보 제거 후 인보이스를 같이 드립니다. 모든 상품은 정품이며 가품 시 1000% 환불해 드립니다. 중고 상품 특성상 가품 외 교환 및 환불은 불가합니다.',
          'S', 'FREE', 'GRAY', '실버 925',
          'DIRECT_SALE', 'ON_SALE', 3700000, false, NULL,
          NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days'
      ),
      -- 16. 나이키 슈프림 14k 골드 링 반지 박효신
      (
          (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'JEWELRY' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          'Nike',
          '나이키 슈프림 14k 골드 링 반지 박효신', '박효신님도 애착하셨던 19시즌 나이키 슈프림 14k 링입니다! 매물 없는 희귀한 제품이며, 사진보다 실물이 더 깔끔하고 예쁩니다. 주머니(파우치)와 함께 보내드립니다.',
          'A', 'FREE', 'YELLOW', '14k 금',
          'DIRECT_SALE', 'ON_SALE', 800000, false, NULL,
          NOW() - INTERVAL '8 days', NOW() - INTERVAL '8 days'
      ),
      -- 17. Distressed grunge t-shirts
      (
          (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          'Distressed grunge t-shirts', '새상품 싱글스티치 반팔티에 직접 디스 작업을 진행했습니다. "Torn, repaired, and reborn." 찢어지고, 꿰매지고, 다시 태어난 한 벌의 티셔츠입니다. 데일리로 입기 좋고 레이어드용으로도 예쁩니다. 수수료는 판매자가 부담합니다.',
          'S', 'FREE', 'GRAY', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 55000, false, NULL,
          NOW() - INTERVAL '9 days', NOW() - INTERVAL '9 days'
      ),
      -- 90's mood grunge distressed tees (긴팔 포함)
      (
          (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '90''s mood grunge distressed tees (긴팔 포함)', '새상품에 데저트 컬러 무드로 디스트레스드 및 워싱 작업을 진행했습니다. 빈티지 무드가 좋아 데일리로 입기 좋고, 반팔 단품이나 FW 시즌 긴팔 레이어드용으로 모두 예쁩니다. 핏이 예쁘게 떨어지며, 긴팔 티셔츠 하나를 같이 보내드립니다! 수수료는 판매자가 부담합니다.',
          'S', 'L', 'BEIGE', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 93000, false, NULL,
          NOW() - INTERVAL '69 days', NOW() - INTERVAL '69 days'
      ),
      -- 19. Harley Davidson Cap
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'HAT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          'Harley Davidson',
          'Harley Davidson Cap', '할리데이비슨(Harley Davidson) 캡 모자입니다.',
          'A', 'FREE', 'BLACK', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 80100, false, NULL,
          NOW() - INTERVAL '10 days', NOW() - INTERVAL '10 days'
      ),
      -- 20. 국내 유일 y2k 야후 보스톤백 더플백
      (
          (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'CROSS_BAG' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BAG' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '국내 유일 y2k 야후 보스톤백 더플백', '보스턴백(대략 가로 45cm x 세로 38cm) 입니다. 큰 오염이나 데미지는 없으나 약간의 사용감이 있는 상태(8.5/10)입니다. 교환 및 환불은 불가합니다.',
          'A', 'FREE', 'NAVY', 'Cotton / Poly',
          'DIRECT_SALE', 'ON_SALE', 87000, false, NULL,
          NOW() - INTERVAL '11 days', NOW() - INTERVAL '11 days'
      ),
      -- 메종키츠네 아이보리 여성가디건 55~55반
      (
          (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'CARDIGAN' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'OUTER' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
          NULL,
          '메종키츠네 아이보리 여성가디건 55~55반', '백화점에서 구입하여 백화점 AS 가능합니다. 구입가는 55만 원대였으며, 몇 번 입지 않아 상태가 최상입니다.',
          'S', 'S', 'IVORY', NULL,
          'DIRECT_SALE', 'ON_SALE', 245500, false, NULL,
          NOW() - INTERVAL '70 days', NOW() - INTERVAL '70 days'
      ),
      -- 톰브라운 밀라노스티치 가디건 4사이즈
      (
          (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'CARDIGAN' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'OUTER' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
          NULL,
          '톰브라운 밀라노스티치 가디건 4사이즈', '톰브라운 밀라노스티치 가디건 4사이즈입니다. 상태 좋고 단품입니다.',
          'A', 'XL', 'NAVY', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 600000, false, NULL,
          NOW() - INTERVAL '71 days', NOW() - INTERVAL '71 days'
      ),
      -- AMI 아미 빅하트 로고 가디건 베이지(L)
      (
          (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'CARDIGAN' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'OUTER' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
          NULL,
          'AMI 아미 빅하트 로고 가디건 베이지(L)', '개인 판매자입니다. 크림(KREAM)에서 구매한 100% 정품이며, 2회 착용하여 상태가 매우 좋습니다.',
          'S', 'L', 'BEIGE', 'Wool 100%',
          'DIRECT_SALE', 'ON_SALE', 350000, false, NULL,
          NOW() - INTERVAL '72 days', NOW() - INTERVAL '72 days'
      ),
      -- Thom Browne 톰브라운 히든삼선 타탄체크 셔츠 1
      (
          (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
          NULL,
          'Thom Browne 톰브라운 히든삼선 타탄체크 셔츠 1', '톰브라운의 시그니처 컬러(레드/블루/화이트) 체크 패턴에 히든 삼선 테이핑 디테일이 더해진 FW 코튼 셔츠입니다. 인기 시즌 제품으로, 몇 번 착용 후 세탁하여 보관만 해둔 상태이며 이염 및 데미지 없는 좋은 컨디션을 유지하고 있습니다.',
          'A', 'S', 'MIXED', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 250000, false, NULL,
          NOW() - INTERVAL '73 days', NOW() - INTERVAL '73 days'
      ),
      -- [M] 폴로랄프로렌 릴렉스 플리스 라인 트러커 자켓 새상품
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'JACKET' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'OUTER' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
          'Polo Ralph Lauren',
          '[M] 폴로랄프로렌 릴렉스 플리스 라인 트러커 자켓 새상품', '택 달린 새상품입니다. 실측 사이즈: 가슴 56 / 총장 62 / 어깨 17 / 소매 64 (단위: cm).',
          'S', 'M', NULL, NULL,
          'DIRECT_SALE', 'ON_SALE', 250000, false, NULL,
          NOW() - INTERVAL '74 days', NOW() - INTERVAL '74 days'
      ),
      -- 26. 미군 장교 트렌치코트 L-XL
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'COAT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'OUTER' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
          NULL,
          '미군 장교 트렌치코트 L-XL', '옷장 정리로 판매합니다. 빈티지샵에서 구매한 제품으로, 미국의 미군 제복 및 관련 의류 제조업체인 Old Master Products, Inc. 산하의 Garrison Collection 제품입니다. L~XL 사이즈 입으시는 분들께 추천합니다. (내피 O, 허리벨트 O)',
          'B', 'L', 'BEIGE', '면 혼방',
          'DIRECT_SALE', 'ON_SALE', 88000, false, NULL,
          NOW() - INTERVAL '12 days', NOW() - INTERVAL '12 days'
      ),
      -- 27. 쇼트 블레이저 xl
      (
          (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'JACKET' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'OUTER' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
          NULL,
          '쇼트 블레이저 xl', '쇼트(Schott) 브랜드의 블레이저 자켓입니다. 무난한 블랙 색상으로 다양하게 활용하기 좋습니다.',
          'A', 'XL', 'BLACK', '울 혼방',
          'DIRECT_SALE', 'ON_SALE', 130000, false, NULL,
          NOW() - INTERVAL '13 days', NOW() - INTERVAL '13 days'
      ),
      -- 아비렉스 빅 로고 스펠아웃 밀리터리 캠프 봄버 자켓
      (
          (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'JACKET' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'OUTER' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
          NULL,
          '아비렉스 빅 로고 스펠아웃 밀리터리 캠프 봄버 자켓', '밀리터리 브랜드를 대표하는 아비렉스의 밀리터리 캠프 드랍존 모디파이 헤일로 자켓입니다. High Altitude Low Opening에서 영감을 받아 제작되었으며, 보온성과 탄성이 뛰어난 고기능성 F/W 전용 제품입니다. 블랙 & 실버 조합으로 택티컬한 무드 연출이 가능하며, 리플렉티브 포인트, 벨크로 패치, 하이넥 유틸리티 버클 등의 디테일이 특징입니다. 사용감이 적어 좋은 컨디션을 유지하고 있습니다.',
          'A', 'FREE', 'BLACK', NULL,
          'DIRECT_SALE', 'ON_SALE', 300000, false, NULL,
          NOW() - INTERVAL '75 days', NOW() - INTERVAL '75 days'
      ),
      -- 29. 잔스포츠백팩
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'BACKPACK' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BAG' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '잔스포츠백팩', '잔스포츠 백팩입니다. 흔하게 볼 수 없는 구하기 힘든 유니크한 디자인의 제품입니다.',
          'A', 'FREE', 'BLACK', '나일론 혼방',
          'DIRECT_SALE', 'ON_SALE', 150000, false, NULL,
          NOW() - INTERVAL '14 days', NOW() - INTERVAL '14 days'
      ),
      -- 30. 밀라숀 넥타이 리폼 스카프
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SCARF' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '밀라숀 넥타이 리폼 스카프', '밀라숀(Mila Schon)의 넥타이를 스카프로 리폼한 제품입니다. 키치한 패턴이 귀엽고 상태 정말 좋습니다.',
          'A', 'FREE', 'MIXED', '실크 100%',
          'DIRECT_SALE', 'ON_SALE', 80000, false, NULL,
          NOW() - INTERVAL '15 days', NOW() - INTERVAL '15 days'
      ),
      -- 31. 나비 타이
      (
          (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SCARF' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '나비 타이', '일본 브랜드 나비 타이입니다. 미사용 새제품입니다. (교환 및 환불 불가)',
          'S', 'FREE', 'NAVY', 'Silk 100%',
          'DIRECT_SALE', 'ON_SALE', 35000, false, NULL,
          NOW() - INTERVAL '16 days', NOW() - INTERVAL '16 days'
      ),
      -- 32. 크롬하츠 blueher 블랙&블루
      (
          (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SUNGLASSES' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '크롬하츠 blueher 블랙&블루', '크롬하츠(Chrome Hearts) blueher 블랙&블루 안경테 제품입니다.',
          'A', 'FREE', 'MIXED', NULL,
          'DIRECT_SALE', 'ON_SALE', 3000000, false, NULL,
          NOW() - INTERVAL '17 days', NOW() - INTERVAL '17 days'
      ),
      -- 33. [280] 아디다스 x 스포티 앤 리치 삼바 버건디
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SNEAKERS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'SHOES' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          'Adidas',
          '[280] 아디다스 x 스포티 앤 리치 삼바 버건디', '아디다스 x 스포티 앤 리치 삼바 OG 클라우드 화이트 컬리지에이트 버건디 280 사이즈입니다. 실착 2번 하여 상태 깨끗하고 좋습니다. 배송비는 판매자가 부담합니다.',
          'A', 'XL', 'RED', '가죽/스웨이드',
          'DIRECT_SALE', 'ON_SALE', 98000, false, NULL,
          NOW() - INTERVAL '18 days', NOW() - INTERVAL '18 days'
      ),
      -- 34. 나이키 x 슈프림 에어포스 1 로우 블랙
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SNEAKERS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'SHOES' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          'Nike',
          '나이키 x 슈프림 에어포스 1 로우 블랙', '나이키 에어포스 1 로우 블랙 슈프림 콜라보 제품입니다. 전체적으로 사용감은 있지만 눈에 띄는 큰 흠집이나 오염 없이 상태 양호합니다. 박스 포함 풀 구성이며, 판매하는 상품은 모두 정품입니다. 실측 사이즈 및 착용샷 문의는 받지 않습니다.',
          'B', 'L', 'BLACK', 'Leather',
          'DIRECT_SALE', 'ON_SALE', 130000, false, NULL,
          NOW() - INTERVAL '19 days', NOW() - INTERVAL '19 days'
      ),
      -- 35. aa 나이키 에어조던 와이낫제로5 농구화 285
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SNEAKERS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'SHOES' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          'Nike',
          'aa 나이키 에어조던 와이낫제로5 농구화 285', '약간의 사용감이 있지만 상태가 좋습니다. 관심 있으신 분은 자세히 보시고 구매 부탁드립니다. (제주/도서산간 추가 배송비 있습니다) ※ 묶음배송 할인: 2개 구매 시 배송비 무료, 4개 구매 시 20% 할인 + 배송비 무료',
          'A', 'XL', 'MIXED', 'Synthetic / Mesh',
          'DIRECT_SALE', 'ON_SALE', 28500, false, NULL,
          NOW() - INTERVAL '20 days', NOW() - INTERVAL '20 days'
      ),
      -- 36. 290.컨버스 x 스투시 척70 하이 플루메리아 핑크
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SNEAKERS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'SHOES' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          'Converse',
          '290.컨버스 x 스투시 척70 하이 플루메리아 핑크', '컨버스 x 스투시 척70 핑크 (품번: A02052C) 제품입니다. 290 사이즈, 미시착 새상품입니다.',
          'S', 'XL', 'PINK', '캔버스',
          'DIRECT_SALE', 'ON_SALE', 175000, false, NULL,
          NOW() - INTERVAL '21 days', NOW() - INTERVAL '21 days'
      ),
      -- 37. 아디다스 베이프 포럼84 로우 그린 카모
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SNEAKERS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'SHOES' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          'Adidas',
          '아디다스 베이프 포럼84 로우 그린 카모', '크림(KREAM)에서 구매 후 2~3회 착용했습니다. 신발 소재 특성상 뒤쪽에 보풀이 있으니 참고 부탁드립니다. (구성품: 박스, 더스트백, 신발끈)',
          'A', 'S', 'GREEN', 'Leather / Suede',
          'DIRECT_SALE', 'ON_SALE', 150000, false, NULL,
          NOW() - INTERVAL '22 days', NOW() - INTERVAL '22 days'
      ),
      -- 38. 생로랑 SL 816 Black
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SUNGLASSES' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '생로랑 SL 816 Black', '6월에 구매한 생로랑(Saint Laurent) SL 816 Black 모델 새상품입니다. (케이스 포함) 저에게 어울리지 않아 판매하며, 문자 2통 이내 쿨거래 시 택배비 포함으로 드립니다. (구매 문의 외 다른 문의는 받지 않습니다.)',
          'S', 'FREE', 'BLACK', '아세테이트',
          'DIRECT_SALE', 'ON_SALE', 380000, false, NULL,
          NOW() - INTERVAL '23 days', NOW() - INTERVAL '23 days'
      ),
      -- 39. YSL 생로랑 반지갑
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'POUCH' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BAG' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          'YSL 생로랑 반지갑', '구매 후 한동안 사용하다 판매합니다. 연식 대비 가죽 상태 양호합니다. YSL 로고 부분에 도색 벗겨짐이 살짝 있으나 셀프 도색으로 보완 가능합니다. 구매 시 받은 정품 박스도 동봉해 드립니다.',
          'B', 'FREE', NULL, '가죽',
          'DIRECT_SALE', 'ON_SALE', 105000, false, NULL,
          NOW() - INTERVAL '24 days', NOW() - INTERVAL '24 days'
      ),
      -- 40. 메종키츠네 골프 폭스헤드 pk XXL(105~110) 새상품
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
          NULL,
          '메종키츠네 골프 폭스헤드 pk XXL(105~110) 새상품', '선물 받은 후 입지 않아 판매합니다. 택만 제거된 새상품이며, 23 SS 시즌 이월 상품입니다.',
          'S', 'XL', 'WHITE', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 150000, false, NULL,
          NOW() - INTERVAL '25 days', NOW() - INTERVAL '25 days'
      ),
      -- 메종키츠네 더블 모노크롬 폭스XL
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '메종키츠네 더블 모노크롬 폭스XL', '메종 키츠네 더블 모노크롬 폭스 헤드 패치 클래식 티셔츠 화이트 사이즈XL 판매합니다. 실사용 1번 착용했습니다. 별로 입지 않아서 싸게 급처합니다.',
          'A', 'XL', 'WHITE', '면 100%',
          'DIRECT_SALE', 'ON_SALE', 50000, false, NULL,
          NOW() - INTERVAL '76 days', NOW() - INTERVAL '76 days'
      ),
      -- 메종키츠네 더블 폭스 반팔티 그레이
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '메종키츠네 더블 폭스 반팔티 그레이', '앙증맞은 폭스 자수가 포인트인 제품입니다. 오염이나 하자없고 상태 좋아요. 국내백화점 정품입니다.',
          'A', 'FREE', 'GRAY', 'Cotton',
          'DIRECT_SALE', 'ON_SALE', 59000, false, NULL,
          NOW() - INTERVAL '77 days', NOW() - INTERVAL '77 days'
      ),
      -- 43. 메종키츠네 더블폭스 반팔 티셔츠
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '메종키츠네 더블폭스 반팔 티셔츠', '측정 방법에 따라 오차 있을 수 있습니다. 중고제품 특성상 구매 후 교환,환불은 불가합니다. 제주,도서산간 +6500 (미리 말씀해주세요). 네고문의 답변 안합니다. 가슴단면 55cm, 총장 72cm.',
          'B', 'L', 'WHITE', 'Cotton',
          'DIRECT_SALE', 'ON_SALE', 45000, false, NULL,
          NOW() - INTERVAL '26 days', NOW() - INTERVAL '26 days'
      ),
      -- 메종키츠네 반팔
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '메종키츠네 반팔', '메종키츠네 반팔티 판매합니다. 귀여운 폭스 자수가 포인트인 제품입니다. 특별한 하자 없이 상태 좋습니다.',
          'A', 'FREE', 'BLACK', 'Cotton',
          'DIRECT_SALE', 'ON_SALE', 50000, false, NULL,
          NOW() - INTERVAL '78 days', NOW() - INTERVAL '78 days'
      ),
      -- 메종키츠네 폭스 반팔티 블랙 L
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '메종키츠네 폭스 반팔티 블랙 L', '메종키츠네 폭스 반팔티 블랙 L 사이즈 새 상품입니다. 택 달려있고 비닐 포장 그대로입니다. 귀여운 폭스 자수가 포인트인 제품입니다.',
          'S', 'L', 'BLACK', 'Cotton',
          'DIRECT_SALE', 'ON_SALE', 49000, false, NULL,
          NOW() - INTERVAL '79 days', NOW() - INTERVAL '79 days'
      ),
      -- 메종키츠네 OW011CFKJ7026 ANTHRACITE 더블폭스헤드 반팔티셔츠 블랙
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '메종키츠네 OW011CFKJ7026 ANTHRACITE 더블폭스헤드 반팔티셔츠 블랙', '메종키츠네 OW011CFKJ7026 ANTHRACITE 더블폭스헤드 반팔티셔츠 블랙 판매합니다.',
          'A', 'FREE', 'BLACK', 'Cotton',
          'DIRECT_SALE', 'ON_SALE', 80000, false, NULL,
          NOW() - INTERVAL '80 days', NOW() - INTERVAL '80 days'
      ),
      -- 리바이스 517
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '리바이스 517', '33사이즈 입니다. 옴니피플 구매.',
          'B', 'M', 'BLUE', '면 100%',
          'DIRECT_SALE', 'ON_SALE', 85000, false, NULL,
          NOW() - INTERVAL '81 days', NOW() - INTERVAL '81 days'
      ),
      -- 48. 리바이스 517
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '리바이스 517', '레더탭 옆에 때운 자국 있습니다. 사진 참고하세요.',
          'C', 'FREE', 'BLUE', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 83000, false, NULL,
          NOW() - INTERVAL '27 days', NOW() - INTERVAL '27 days'
      ),
      -- 리바이스 517 현행 부츠컷 데님
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '리바이스 517 현행 부츠컷 데님', '리바이스 517 현행 부츠컷 데님. 리바이스 517 현행 새상품 컨디션. 34x32 허리 단면 43 허벅지 31.5 밑단 24 기장 109.',
          'S', 'L', 'BLUE', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 8500, false, NULL,
          NOW() - INTERVAL '82 days', NOW() - INTERVAL '82 days'
      ),
      -- 50. [00's] Levi's 517 Boot cut
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '[00''s] Levi''s 517 Boot cut', '리바이스517 부츠컷. 표기 사이즈 33x30 실측 참고. 100% Cotton. 자연스러운 페이딩. 사이즈 미스로 매물합니다. 이체시 145,000원입니다. 편하게 문의 주세요! *측정 방법에 따라 1~2cm정도 오차가 있을 수 있습니다. *중고 상품 특성상 교환 및 환불이 어려운 점 양해 바랍니다.',
          'B', 'M', 'BLUE', '면 100%',
          'DIRECT_SALE', 'ON_SALE', 145000, false, NULL,
          NOW() - INTERVAL '28 days', NOW() - INTERVAL '28 days'
      ),
      -- 00's Levi's 517 부츠컷 데님
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '00''s Levi''s 517 부츠컷 데님', '00''s Levi''s 517 부츠컷 데님. [구매 전 유의사항] * 사이즈를 재는 사람, 방법, 제작 과정에 따라서 오차가 있을 수 있습니다. * 사용자의 모니터와 조명에 따라 색상의 차이가 있을 수 있습니다. * 빈티지 특성상 사용감 및 미세 오염이 존재할 수 있으며 교환/환불이 불가하오니 신중한 구매 부탁드립니다.',
          'B', 'FREE', 'BLUE', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 120000, false, NULL,
          NOW() - INTERVAL '83 days', NOW() - INTERVAL '83 days'
      ),
      -- 52. 리바이스 517 데님 팬츠
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '리바이스 517 데님 팬츠', 'No.1-1527 #도떼기구매가능. Levis 517 denim pants. 리바이스 517 데님 팬츠 입니다. 사진에서 보시듯이상품 자체가 매우 양호하게 보존되어 있습니다. 사이즈 남성 33 추천드립니다. Color - denim, Size - 36, 총장104 허리43 밑위37 밑단22 허벅지32(cm). 측정위치에 따라 1-3cm 오차가 있을 수 있습니다. 모든 상품 세탁, 고온 스팀이 완료 된 상품입니다. 배송전에 한번 더 스팀 작업 진행합니다. 구매 전 공지사항과 사이즈를 다시 한번 확인 부탁드립니다.',
          'A', 'M', 'BLUE', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 92900, false, NULL,
          NOW() - INTERVAL '29 days', NOW() - INTERVAL '29 days'
      ),
      -- 53. 00s 리바이스 517 (멕시코) w38
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '00s 리바이스 517 (멕시코) w38', '00년대 리바이스 517 부츠컷 청바지입니다. 멕시코 생산 제품이며, 허리 단면 38인치입니다. 빈티지한 워싱과 자연스러운 사용감이 매력적인 제품입니다. 구매 원하시면 바로 안전결제 해주시면 됩니다! 실측단면(cm) 허리단면48.5 엉덩이단면64 밑위32 허벅지단면33 밑단단면26 총장111. 빈티지 의류 특성상 미세한 얼룩이나 흔적이 있을수 있습니다! 구매 후 제품 특성상 교환/환불이 불가능하니 신중하게 구매 부탁드립니다. 배송은 2-3일 정도 소요되며, 주말/연휴 기간에는 더 소요될 수 있습니다. 사이즈 측정하는 방법에 따라 1-3cm 정도 오차가 발생할 수 있습니다.',
          'B', 'XL', 'BLUE', '면 100%',
          'DIRECT_SALE', 'ON_SALE', 141000, false, NULL,
          NOW() - INTERVAL '30 days', NOW() - INTERVAL '30 days'
      ),
      -- 54. 리바이스 517 부츠컷 데님 팬츠
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '리바이스 517 부츠컷 데님 팬츠', '표기사이즈:34 실측:허리:42 허벅지:32 총장:112.',
          'B', 'L', 'BLUE', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 99000, false, NULL,
          NOW() - INTERVAL '31 days', NOW() - INTERVAL '31 days'
      ),
      -- 55. 00s 리바이스 517-03 (재팬) w29
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '00s 리바이스 517-03 (재팬) w29', '00년대 리바이스 517-03 (재팬) 청바지 판매합니다. 사이즈는 W29이며, 빈티지한 워싱과 디테일이 매력적입니다. 밑단은 헤진 느낌으로 자연스럽게 연출되었으며, 편안하게 착용 가능합니다. 구매 원하시면 바로 안전결제 해주시면 됩니다! 실측단면(cm) 허리단면37 엉덩이단면49 밑위24 허벅지단면26 밑단단면23 총장99. 빈티지 의류 특성상 미세한 얼룩이나 흔적이 있을수 있습니다! 구매 후 제품 특성상 교환/환불이 불가능하니 신중하게 구매 부탁드립니다. 배송은 2-3일 정도 소요되며, 주말/연휴 기간에는 더 소요될 수 있습니다. 사이즈 측정하는 방법에 따라 1-3cm 정도 오차가 발생할 수 있습니다.',
          'B', 'S', 'BLUE', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 140000, false, NULL,
          NOW() - INTERVAL '32 days', NOW() - INTERVAL '32 days'
      ),
      -- 미제 올드 리바이스 517 36(실34)
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '미제 올드 리바이스 517 36(실34)', '2000년 7월 미국 554 공장 생산 517. 사이즈 36/30(실 34). 부츠 컷, 기장 미수선, 왼쪽 다리 앞뒤 옅은 스팟 존재(사진 참고). 단면 실측(cm) 허리 44.5 밑위 31 허벅지 29 총장 103 밑단 21.5. ※ 치수를 재는 방식에 따라 ±1~2cm 차이가 있을 수 있습니다.',
          'B', 'L', 'BLUE', '면 100%',
          'DIRECT_SALE', 'ON_SALE', 125000, false, NULL,
          NOW() - INTERVAL '84 days', NOW() - INTERVAL '84 days'
      ),
      -- 57. 리바이스 부츠컷 517 멕시코산
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DENIM' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '리바이스 부츠컷 517 멕시코산', '핏 이쁘게 떨어짐요. 32x34 특히 밑단이 예쁘게 빠짐.',
          'A', 'M', 'BLUE', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 145000, false, NULL,
          NOW() - INTERVAL '33 days', NOW() - INTERVAL '33 days'
      ),
      -- 58. 메종키츠네 더블폭스 s
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '메종키츠네 더블폭스 s', '매장구매 정품. 상태좋아요.',
          'A', 'S', 'BLACK', 'Cotton',
          'DIRECT_SALE', 'ON_SALE', 45000, false, NULL,
          NOW() - INTERVAL '34 days', NOW() - INTERVAL '34 days'
      ),
      -- Maison Kitsune 더블폭스 반팔 블랙 M
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          'Maison Kitsune 더블폭스 반팔 블랙 M', '집에서 시도해보려고 좀 입어보고 나갈 때 딱 한번 입었습니다 그래서 싸게 내놔요 사진 가능합니다 신세계몰에서 구매 쿨거시 에눌 가능!',
          'A', 'M', 'BLACK', '면',
          'DIRECT_SALE', 'ON_SALE', 60000, false, NULL,
          NOW() - INTERVAL '85 days', NOW() - INTERVAL '85 days'
      ),
      -- 60. 메종키츠네 더블폭스헤드 xs
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '메종키츠네 더블폭스헤드 xs', '실착 3회 여성분들한테 잘 맞으실거같아요!! 편하게 연락주세용 반택합니다.',
          'A', 'XS', 'WHITE', 'Cotton',
          'DIRECT_SALE', 'ON_SALE', 60000, false, NULL,
          NOW() - INTERVAL '35 days', NOW() - INTERVAL '35 days'
      ),
      -- 마제스틱 웜업 L
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'JACKET' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'OUTER' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '마제스틱 웜업 L', '신중하게 구매해주세요.',
          'A', 'L', 'BLACK', '폴리에스터 100%',
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '86 days', NOW() - INTERVAL '86 days'
      ),
      -- 62. 마제스틱 자켓 켄터키 와일드캣츠 L
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'JACKET' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'OUTER' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '마제스틱 자켓 켄터키 와일드캣츠 L', '신중히 고민해보시고 구매 부탁드립니다. 빈티지 제품이라 생활감 있습니다!',
          'B', 'L', 'BLUE', NULL,
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '36 days', NOW() - INTERVAL '36 days'
      ),
      -- 63. 마제스틱 세튼홀 파이러츠 NCAA 자켓
      (
          (SELECT id FROM member WHERE email = 'vintib3@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'JACKET' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'OUTER' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '마제스틱 세튼홀 파이러츠 NCAA 자켓', '이베이 구매.',
          'A', 'L', 'BLUE', '면 100%',
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '37 days', NOW() - INTERVAL '37 days'
      ),
      -- 64. 마제스틱 브랜드의 la에인절스 자켓 L
      (
          (SELECT id FROM member WHERE email = 'vintib4@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'JACKET' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'OUTER' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '마제스틱 브랜드의 la에인절스 자켓 L', '마제스틱 브랜드의 la에인절스 자켓입니다. 평소 응원하던 팀이라 구매했는 데 옷이 생각보다 작게 나와서 판매합니다. L로 표기되어 있지만 95 입으시는 분들이 입으면 정말 이쁜 핏이 나올 것 같습니다! 상태 좋습니다 사이즈 체크만 했어요~ 가격제안 ok.',
          'S', 'L', 'RED', NULL,
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '38 days', NOW() - INTERVAL '38 days'
      ),
      -- 65. 네이버후드 퍼블릭에너미 마제스틱 자켓 L size
      (
          (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'JACKET' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'OUTER' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '네이버후드 퍼블릭에너미 마제스틱 자켓 L size', '네이버후드와 퍼블릭에너미 콜라보 자켓 L사이즈입니다. 마제스틱 자켓 디자인, 전면/후면/소매 자수 포인트, 내부 퀼팅 보온성, 네이버 후드 로고 각인 스냅 버튼, ykk 스냅 사용, 드라이 완료. 좋은 상태 유지중입니다. 실측: 총장 71/ 어깨 57.5 / 가슴 68 / 소매 66.5',
          'A', 'L', 'BLACK', '나일론, 폴리에스터',
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '39 days', NOW() - INTERVAL '39 days'
      ),
      -- 66. (S+급/실측 105) 루이비통 슈프림 맨투맨 백화점판 한글택 M사이즈
      (
          (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SWEATSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '(S+급/실측 105) 루이비통 슈프림 맨투맨 백화점판 한글택 M사이즈', '저희 샵은 3호점을 보유한 남성 전문 의류 업체입니다. 루이비통 슈프림 맨투맨 백화점판 한글택. 루이비통 택 동봉. M size (실측 105정도). 상점 팔로잉 해주시면 배송비도 무료입니다!',
          'S', 'M', 'RED', '면 100%',
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '40 days', NOW() - INTERVAL '40 days'
      ),
      -- 슈프림 요지야마모토 맨투맨
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SWEATSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '슈프림 요지야마모토 맨투맨', '라지. 사용감 적어요. 실측: 총장 73 너비 66',
          'A', 'L', 'BLACK', NULL,
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '87 days', NOW() - INTERVAL '87 days'
      ),
      -- 슈프림X언더커버 곰돌이 맨투맨 블랙(L)
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SWEATSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '슈프림X언더커버 곰돌이 맨투맨 블랙(L)', '제품명: 슈프림 언더커버 곰돌이 맨투맨 블랙. 사이즈: L(체감 105). 제품설명: 슈프림과 언더커버 콜라보 곰돌이 맨투맨입니다. 시보리 짱짱하고 눈에 띄는 데미지나 오염 없습니다. ※ 찔러보기, 네고 요청, 실측 요청 응답 안하고 차단 하겠습니다. 구매 원하시는 분만 연락 주세요.',
          'A', 'L', 'BLACK', '면 100%',
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '88 days', NOW() - INTERVAL '88 days'
      ),
      -- 루이비통 슈프림 슈이비통 로고 맨투맨
      (
          (SELECT id FROM member WHERE email = 'vintib3@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SWEATSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '루이비통 슈프림 슈이비통 로고 맨투맨', 'S사이즈. 하자없이 새상품급 입니다. 사진 촬영 후 깨끗히 보관중인 제품입니다. 상점 팔로우 해주실 시 택배비 무료로 해드립니다. 거래 시 택포 . 에눌 가능합니다',
          'S', 'S', 'RED', NULL,
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '89 days', NOW() - INTERVAL '89 days'
      ),
      -- 70. 리바이스 Y2K 빈티지 카고 팬츠
      (
          (SELECT id FROM member WHERE email = 'vintib4@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'CARGO_PANTS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '리바이스 Y2K 빈티지 카고 팬츠', '총장 / 허리단면 / 밑위 / 허벅지단면 / 밑단 : 100 / 41 / 34 / 29 / 26. 택배비 4,000원 (제주도 7,000원). 상품은 스팀및 케어해서 보내드립니다. 빈티지 상품으로 교환 or 환불은 어렵습니다.',
          'B', 'M', 'KHAKI', '면 100%',
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '41 days', NOW() - INTERVAL '41 days'
      ),
      -- 71. 리바이스 화이트탭 505 커뮤터 라이딩 카고팬츠
      (
          (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'CARGO_PANTS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '리바이스 화이트탭 505 커뮤터 라이딩 카고팬츠', '얼룩있습니다! 사진 확인해주세요. 사이즈 (cm 기준) 허리단면 45 / 허벅지 단면 30 / 엉덩이 단면 54 / 총장 110. 안내사항: 측정 방법에 따라 1~3cm 정도 오차가 있을 수 있습니다. 단순 변심으로 인한 환불은 불가합니다. 중고 상품 특성상 사용감이 있습니다.',
          'C', 'L', 'KHAKI', NULL,
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '42 days', NOW() - INTERVAL '42 days'
      ),
      -- 리바이스 조거 카고바지
      (
          (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'JOGGER_PANTS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '리바이스 조거 카고바지', '남성용. 사이즈 L (32인치 전후). 고무밴딩에 끈 있어서 어느정도 사이즈조절 가능, 스판좋음. 하자없이 깨끗합니다. 색상은 브라운이며, 무난하게 코디하기 좋습니다. 편안하게 입을 수 있는 바지입니다.',
          'A', 'L', 'BROWN', '면/스판덱스',
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '90 days', NOW() - INTERVAL '90 days'
      ),
      -- 73. 270 조던1 하이 헤리티지 빈티지 커스텀
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SNEAKERS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'SHOES' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '270 조던1 하이 헤리티지 빈티지 커스텀', '딱 한번신은 상품입니다. 빈티지 커스텀 예쁘게 들어갔고 물에 닿거나 빨아도 지워지지 않는다고 합니다. 커스텀 비용은 20만원 이상 듭니다. 검은 스우시도 안쪽 측면까지 작업되어 있고 신발끈도 빈티지 커스텀에 맞게 염색되었습니다. 실물이 훨씬 예쁩니다.',
          'S', 'L', 'BLACK', NULL,
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '43 days', NOW() - INTERVAL '43 days'
      ),
      -- 74. 나이키 에어조던1 레트로 하이 OG 브레드토 265
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SNEAKERS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'SHOES' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '나이키 에어조던1 레트로 하이 OG 브레드토 265', '나이키 에어조던1 레트로 하이 OG 브레드토 입니다. 한정판 밤새 줄 서서 구매했었고, 몇 번 안 신어서 바닥 상태도 상급입니다. 사이즈는 265mm 이고, 신발 + 박스 구성입니다.',
          'A', 'M', 'RED', '소가죽, 합성피혁',
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '44 days', NOW() - INTERVAL '44 days'
      ),
      -- 75. 270)조던1 레트로 로우 OG 브레드 2015 새상품, 박스X
      (
          (SELECT id FROM member WHERE email = 'vintib3@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SNEAKERS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'SHOES' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '270)조던1 레트로 로우 OG 브레드 2015 새상품, 박스X', '조던1 레트로 로우 OG 브레드 2015입니다. 착용 0회, 신발끈 맨 적 없는 새상품이구 박스는 없습니다... 급처여서 눈물 머금고.. 던집니다.....ㅜㅠ..',
          'S', 'L', 'BLACK', NULL,
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '45 days', NOW() - INTERVAL '45 days'
      ),
      -- 76. 나이키 260 조던1 미드 브레드토 노블레드
      (
          (SELECT id FROM member WHERE email = 'vintib4@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SNEAKERS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'SHOES' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '나이키 260 조던1 미드 브레드토 노블레드', '쿠션감좋고 상태좋아요. 모든상품 조명에따라 차이가있을수있습니다. 교환환불 불가합니다. 신중하게 구매결정하시길 바랍니다. 신발 단품 입니다.',
          'A', 'M', 'RED', '가죽',
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '46 days', NOW() - INTERVAL '46 days'
      ),
      -- 77. [새상품] 어티슈 윙 캡 블랙
      (
          (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'HAT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '[새상품] 어티슈 윙 캡 블랙', '성수 젠틀몬스터 신사옥에서 구매 후 잠깐 착용하고 손이 안 가서 판매합니다.',
          'S', 'FREE', 'BLACK', '면 100%',
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '47 days', NOW() - INTERVAL '47 days'
      ),
      -- 78. eou 페이크 러너 볼캡 블루
      (
          (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'HAT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          'eou 페이크 러너 볼캡 블루', 'eou 페이크 러너 볼캡 블루입니다. 전면 입체 빈티지 폰트 자수와 로프 디테일, 챙 부분 지그재그 자수까지 디테일이 좋은 모자입니다. 시원한 블루 컬러와 메쉬 소재 조합. 뒷부분이 스트링과 스토퍼로 조절하는 방식. 내부 오염 방지 캡 가이드(종이)까지 그대로 보관 중인 컨디션입니다.',
          'S', 'FREE', 'BLUE', NULL,
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '48 days', NOW() - INTERVAL '48 days'
      ),
      -- 79. 빈티지 에스닉 보헤미안 파우치 J03737
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'POUCH' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BAG' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '빈티지 에스닉 보헤미안 파우치 J03737', '가로19cm x 세로14~15cm. Condition: 8.5. 빈티지 특성상 오염이 존재할 수 있습니다. 상태에 예민하신 분은 구매를 피해주시면 감사드리겠습니다. 구매 후 교환 및 환불은 어렵습니다.',
          'A', 'FREE', 'MIXED', '면 혼방',
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '49 days', NOW() - INTERVAL '49 days'
      ),
      -- 80. 은색 오르비 로고 비비안 웨스트우드 빈티지 오르비 플레이트 버클 웹 벨트
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'BELT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '비비안 웨스트우드 빈티지 오르비 플레이트 버클 웹 벨트', '은색 오르비(Orb) 로고 각인이 들어간 비비안 웨스트우드 빈티지 벨트입니다. 연한 블루-그레이 컬러의 패브릭 스트랩에 핑크 컬러 레터링 자수 디테일이 들어간 2000년대(Y2K) 빈티지 희귀템입니다.',
          'A', 'FREE', 'GRAY', NULL,
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '50 days', NOW() - INTERVAL '50 days'
      ),
      -- 81. Wknd project 오버링 빈티지 레더 벨트 엘씨디씨 로우클래식
      (
          (SELECT id FROM member WHERE email = 'vintib3@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'BELT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          'Wknd project 오버링 빈티지 레더 벨트 엘씨디씨 로우클래식', '1회착용 입니다. 스타일 바뀌어 판매합니다.',
          'S', 'FREE', 'BROWN', '천연가죽',
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '51 days', NOW() - INTERVAL '51 days'
      ),
      -- 82. RRL 더블알엘 헤링본 올인원 올리브 점프수트
      (
          (SELECT id FROM member WHERE email = 'vintib4@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'JUMPSUIT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'DRESS_JUMPSUIT' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          'RRL 더블알엘 헤링본 올인원 올리브 점프수트', 'RRL 올리브 헤링본 원단 점프수트입니다. M사이즈 어깨48 품57 허리52. 국내 100정도 사이즈입니다만 실측으로 확인 부탁드립니다. 10회 미만착용으로 사용감있지만 좋은 컨디션입니다.',
          'A', 'M', 'GREEN', NULL,
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '52 days', NOW() - INTERVAL '52 days'
      ),
      -- RRL 더블알엘 헤링본 팬츠 브루스터 그린 32/32
      (
          (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'COTTON_PANTS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          'RRL 더블알엘 헤링본 팬츠 브루스터 그린 32/32', 'RRL 헤링본 팬츠 브루스터 그린 색상이에요. 사이즈는 32/32이며, 택 달린 미시착 새상품입니다. 기장을 잘못보고 사서 빠르게 판매하기위해 1만원 인하해서 판매해요.',
          'S', 'M', 'GREEN', '면 100%',
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '91 days', NOW() - INTERVAL '91 days'
      ),
      -- 더블알엘 헤링본 퍼티그 팬츠 32x30
      (
          (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'CARGO_PANTS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '더블알엘 헤링본 퍼티그 팬츠 32x30', '작년에 구매해서 대략 7~8회 착용, 3회 세탁, 노수선. 실측 허리44.5, 총장102 어드저스트하면 허리 1인치 정도는 줄어듭니다. 원래 빈티지한 부분 외에 하자나 오염 없습니다. 반품 불가 입니다.',
          'A', 'M', 'GREEN', '면 100%',
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '92 days', NOW() - INTERVAL '92 days'
      ),
      -- [32x30 최상] RRL p44 카고 팬츠 올리브 몽키팬츠
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'CARGO_PANTS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '[32x30 최상] RRL p44 카고 팬츠 올리브 몽키팬츠', '더블알엘 p44 카고팬츠 몽키팬츠 올리브 32x30. 실착 5회, 사진 참고해주세요. 네고 답장 안 합니다. 교환 환불 x',
          'S', 'M', 'GREEN', NULL,
          'DIRECT_SALE', 'ON_SALE', 395000, false, NULL,
          NOW() - INTERVAL '93 days', NOW() - INTERVAL '93 days'
      ),
      -- 빈티지 엑시즈팜 세일러 마린 미니 원피스
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DRESS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'DRESS_JUMPSUIT' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'WOMEN' AND depth = 1))),
          NULL,
          '빈티지 엑시즈팜 세일러 마린 미니 원피스', '1회 착용. 여름에 시원한 느낌으로 입을 수 있는 디자인입니다. 잔보풀감, 스카프 어깨부분 미세 올나감 있음. 교환/환불 불가합니다. 신중하게 고민하신 후 구매 부탁드려요!',
          'C', 'FREE', NULL, NULL,
          'DIRECT_SALE', 'ON_SALE', 9000, false, NULL,
          NOW() - INTERVAL '94 days', NOW() - INTERVAL '94 days'
      ),
      -- 87. [36x32] RRL 헤링본 퍼티그 팬츠
      (
          (SELECT id FROM member WHERE email = 'vintib3@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'CARGO_PANTS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BOTTOM' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '[36x32] RRL 헤링본 퍼티그 팬츠', '몇 번 안 입은 상태 좋은 바지입니다. 노수선 노세탁 비흡연자입니다. 중고 물품 특성상 반품 안 됩니다.',
          'A', 'XL', NULL, NULL,
          'DIRECT_SALE', 'ON_SALE', 350000, false, NULL,
          NOW() - INTERVAL '53 days', NOW() - INTERVAL '53 days'
      ),
      -- 88. 프랑스 핸드메이드 빈티지 입체 절개 A라인 울 원피스
      (
          (SELECT id FROM member WHERE email = 'vintib4@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DRESS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'DRESS_JUMPSUIT' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'WOMEN' AND depth = 1))),
          NULL,
          '프랑스 핸드메이드 빈티지 입체 절개 A라인 울 원피스', '프랑스 디자이너의 핸드메이드 제작 제품으로, 섬세한 패턴과 입체적인 절개 라인이 돋보이는 원피스입니다. 깔끔하게 떨어지는 A라인 실루엣과 보트넥 디자인이 단정하면서도 세련된 분위기를 연출해 드리며, 유행에 구애받지 않고 오래도록 즐기실 수 있는 아이템입니다. 울 소재로 보온성을 챙겼으며, 폴라와 매치하셔도 잘 어우러집니다. 가슴단면42~52(신축성) 총장94.',
          'A', 'FREE', NULL, '울',
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '54 days', NOW() - INTERVAL '54 days'
      ),
      -- 모리걸 플라워 반팔 원피스 <일본 빈티지 제품>
      (
          (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DRESS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'DRESS_JUMPSUIT' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'WOMEN' AND depth = 1))),
          NULL,
          '모리걸 플라워 반팔 원피스 일본 빈티지', '일본 빈티지 제품. 총장:75 어깨단면:40 가슴단면:44 소매길이:26 암홀단면:20 밑단단면:59. 신축성 있음. 신중한 구매 부탁드려요.',
          'A', 'FREE', NULL, NULL,
          'DIRECT_SALE', 'ON_SALE', 15000, false, NULL,
          NOW() - INTERVAL '95 days', NOW() - INTERVAL '95 days'
      ),
      -- 90. 입생로랑(Yves Saint Laurent) 빈티지 원피스 M
      (
          (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DRESS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'DRESS_JUMPSUIT' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'WOMEN' AND depth = 1))),
          NULL,
          '입생로랑(Yves Saint Laurent) 빈티지 원피스 M', '입생로랑 빈티지 원피스 M. 안쪽에 오염이 있으나 전반적으로 상태 양호합니다. 총장: 113.5 어깨: 33 가단: 42. 가격제안 얼마든지 주세요. 교환/환불 안됩니다.',
          'B', 'M', NULL, NULL,
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '55 days', NOW() - INTERVAL '55 days'
      ),
      -- 빈티지 코지, 모리, 히피 롱원피스
      (
          (SELECT id FROM member WHERE email = 'vintib1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'DRESS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'DRESS_JUMPSUIT' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'WOMEN' AND depth = 1))),
          NULL,
          '빈티지 코지, 모리, 히피 롱원피스', '휴양지느낌이 물씬나는 보헤미안st원피스입니다. 화려한패턴에 금박과 레이스포인트 동남아휴양지룩으로 강추. 어깨끈조절가능 가단29~53cm 어깨끈 제외 총장 91cm.',
          'A', 'FREE', NULL, NULL,
          'DIRECT_SALE', 'ON_SALE', 20000, false, NULL,
          NOW() - INTERVAL '96 days', NOW() - INTERVAL '96 days'
      ),
      -- 92. me ISSEY MIYAKE sleeveless 3
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SLEEVELESS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'WOMEN' AND depth = 1))),
          'Issey Miyake',
          'me ISSEY MIYAKE sleeveless 3', 'me Issey Miyake sleeveless 3. Size F 총장 57.5 어깨 27 가슴 30.5 (cm). Product Note: 45% Nylon 45% Polyester 10% Polyurethane',
          'A', 'FREE', 'PURPLE', '45% Nylon 45% Polyester 10% Polyurethane',
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '56 days', NOW() - INTERVAL '56 days'
      ),
      -- me ISSEY MIYAKE sleeveless
      (
          (SELECT id FROM member WHERE email = 'vintib3@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SLEEVELESS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'WOMEN' AND depth = 1))),
          'Issey Miyake',
          'me ISSEY MIYAKE sleeveless', 'me Issey Miyake sleeveless. Size F 총장 57.5 어깨 27 가슴 30.5 (cm). Product Note: 45% Nylon 45% Polyester 10% Polyurethane',
          'A', 'FREE', 'PINK', '45% Nylon 45% Polyester 10% Polyurethane',
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '97 days', NOW() - INTERVAL '97 days'
      ),
      -- me ISSEY MIYAKE 슬리브
      (
          (SELECT id FROM member WHERE email = 'vintib4@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SLEEVELESS' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'WOMEN' AND depth = 1))),
          'Issey Miyake',
          'me ISSEY MIYAKE 슬리브', 'me Issey Miyake 슬리브. Size F 총장 57.5 어깨 27 가슴 30.5 (cm). Product Note: 45% Nylon 45% Polyester 10% Polyurethane',
          'A', 'FREE', 'GREEN', '45% Nylon 45% Polyester 10% Polyurethane',
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '98 days', NOW() - INTERVAL '98 days'
      ),
      -- 95. Odds On Issey Miyake dot shirt 2
      (
          (SELECT id FROM member WHERE email = 'vintib3@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'SHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'WOMEN' AND depth = 1))),
          'Issey Miyake',
          'Odds On Issey Miyake dot shirt 2', 'Odds On Issey Miyake dot shirt 2. Size Free 총장 75 어깨 52 가슴 59 소매 56(cm). Product Note: 100% Cotton',
          'A', 'FREE', NULL, '면 100%',
          'DIRECT_SALE', 'ON_SALE', 170000, false, NULL,
          NOW() - INTERVAL '57 days', NOW() - INTERVAL '57 days'
      ),
      -- 96. Plantation Issey Miyake tote bag
      (
          (SELECT id FROM member WHERE email = 'vintib4@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'TOTE_BAG' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BAG' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'WOMEN' AND depth = 1))),
          'Issey Miyake',
          'Plantation Issey Miyake tote bag', 'Plantation Issey Miyake tote bag. Size OS 30x35(cm).',
          'A', 'FREE', NULL, NULL,
          'DIRECT_SALE', 'ON_SALE', 140000, false, NULL,
          NOW() - INTERVAL '58 days', NOW() - INTERVAL '58 days'
      ),
      -- 97. 토가 아카이브 레더 숄더 파우치
      (
          (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'POUCH' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BAG' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '토가 아카이브 레더 숄더 파우치', '토가 아카이브 숄더 파우치 입니다. 구하기 힘든 모델이고 여름에 툭 하고 다니면 최고입니다. 안에는 휴대폰 하나 넣고 다니기 좋은 사이즈입니다. 남자가 매기에도 좋습니다 줄 조절 굿. 공정상의 문제로 본드자국이 있습니다 확인후 구매부탁드려요. 환불은 어렵습니다.',
          'B', 'FREE', NULL, '가죽',
          'DIRECT_SALE', 'ON_SALE', 140000, false, NULL,
          NOW() - INTERVAL '59 days', NOW() - INTERVAL '59 days'
      ),
      -- 98. [정품] 구찌 미키 클러치백
      (
          (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'POUCH' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'BAG' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '[정품] 구찌 미키 클러치백', '판매하는 상품은 100% 정품 입니다. 상태는 사진과 같이 좋습니다. 구성품은 가품시 전액환불 정품감정 보증서 + 중고명품샵 박스 + 더스트백 + 컨트롤카드 풀셋. 쿨거래시 택배비는 제가 부담하겠습니다. 구매시 당일택배를 원칙으로 하며 특별한 일 없는 이상 우체국 택배를 통해 보내드려 하루면 받으십니다.',
          'A', 'FREE', NULL, NULL,
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '60 days', NOW() - INTERVAL '60 days'
      ),
      -- 스파이더맨 코스튬 세트
      (
          (SELECT id FROM member WHERE email = 'vintibb2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'JUMPSUIT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'DRESS_JUMPSUIT' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '스파이더맨 코스튬 세트', '스파이더맨 코스튬 세트입니다. 마스크 포함 풀세트이며, 특별한 하자 없이 깨끗한 상태입니다. 키165~180 몸무게 60~75추천드리며 하자없습니다. 구성품은 스파이더맨 가면, 몸슈트, 턱 마스크 보호대 입니다. 친절한 이웃 스파이더맨이 되어보세요.',
          'A', 'FREE', 'RED', NULL,
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '99 days', NOW() - INTERVAL '99 days'
      ),
      -- (M-L) 브랜드빈티지 반팔 티셔츠 영화 슈퍼맨 맨오브스틸-H36369
      (
          (SELECT id FROM member WHERE email = 'vintib2@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'TSHIRT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'TOP' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '(M-L) 브랜드빈티지 반팔 티셔츠 영화 슈퍼맨 맨오브스틸-H36369', '영화 슈퍼맨 맨오브스틸 프린팅 반팔 티셔츠. 남녀공용. 실측: 어깨 48, 가슴 46, 소매 19, 총기장 73. 팔로우 하면 무료배송.',
          'A', 'M', NULL, NULL,
          'AUCTION', 'AUCTION_SCHEDULED', NULL, false, NULL,
          NOW() - INTERVAL '100 days', NOW() - INTERVAL '100 days'
      ),
      -- 101. 추억의 야후 자수로고 볼캡 모자(네이비, Free)
      (
          (SELECT id FROM member WHERE email = 'vintibb1@gmail.com'),
          (SELECT id FROM category WHERE name_en = 'HAT' AND depth = 3 AND parent_id = (SELECT id FROM category WHERE name_en = 'ACCESSORY' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name_en = 'UNISEX' AND depth = 1))),
          NULL,
          '추억의 야후 자수로고 볼캡 모자(네이비, Free)', '야후 자수 로고가 들어간 볼캡 모자입니다. 20번 보스톤백과 같은 세트에서 나온 물건입니다. 큰 오염이나 데미지는 없으나 약간의 사용감이 있는 상태(8.5/10)입니다. 교환 및 환불은 불가합니다.',
          'A', 'FREE', 'NAVY', 'Cotton 100%',
          'DIRECT_SALE', 'ON_SALE', 35000, false, NULL,
          NOW() - INTERVAL '61 days', NOW() - INTERVAL '61 days'
      );