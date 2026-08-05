-- 카테고리/브랜드 마스터 시드 (SY007).
-- CategoryBrandSeeder(ApplicationRunner)가 category 테이블이 비어 있을 때만 실행한다.
-- 재실행 안전성은 애플리케이션 쪽 count() == 0 가드가 책임진다 — 이 스크립트 자체는
-- 멱등하지 않으니 psql 등으로 직접 재실행할 경우 중복 삽입에 주의한다.

-- ---------- 카테고리: 성별 3개 (depth = 1) ----------
-- SY032: 카테고리 v2(SY022의 3-depth 구조는 유지, 소분류 내용 개편 + 영문 코드 컬럼 추가).
-- ID는 삽입 순서에 의존하며 docs/db/category-taxonomy.md 의 ID 매핑표(1~126)와 정확히 일치해야 한다.
INSERT INTO category (name, name_en, depth) VALUES
    ('남성', 'MEN', 1),
    ('여성', 'WOMEN', 1),
    ('공용', 'UNISEX', 1);

-- ---------- 카테고리: 대분류 20개 (depth = 2, 남성 6 + 여성 7 + 공용 7) ----------
-- "원피스 및 점프슈트"는 여성·공용에만 있다 — 남성은 6개, 여성·공용은 7개로 성별마다 개수가 다르다.
INSERT INTO category (name, name_en, depth, parent_id) VALUES
    -- 남성 (id 4~9)
    ('아우터',   'OUTER',            2, (SELECT id FROM category WHERE name = '남성' AND depth = 1)),
    ('상의',     'TOP',              2, (SELECT id FROM category WHERE name = '남성' AND depth = 1)),
    ('하의',     'BOTTOM',           2, (SELECT id FROM category WHERE name = '남성' AND depth = 1)),
    ('신발',     'SHOES',            2, (SELECT id FROM category WHERE name = '남성' AND depth = 1)),
    ('가방',     'BAG',              2, (SELECT id FROM category WHERE name = '남성' AND depth = 1)),
    ('액세서리', 'ACCESSORY',        2, (SELECT id FROM category WHERE name = '남성' AND depth = 1)),

    -- 여성 (id 10~16)
    ('아우터',   'OUTER',            2, (SELECT id FROM category WHERE name = '여성' AND depth = 1)),
    ('상의',     'TOP',              2, (SELECT id FROM category WHERE name = '여성' AND depth = 1)),
    ('하의',     'BOTTOM',           2, (SELECT id FROM category WHERE name = '여성' AND depth = 1)),
    ('신발',     'SHOES',            2, (SELECT id FROM category WHERE name = '여성' AND depth = 1)),
    ('가방',     'BAG',              2, (SELECT id FROM category WHERE name = '여성' AND depth = 1)),
    ('액세서리', 'ACCESSORY',        2, (SELECT id FROM category WHERE name = '여성' AND depth = 1)),
    ('원피스 및 점프슈트', 'DRESS_JUMPSUIT', 2, (SELECT id FROM category WHERE name = '여성' AND depth = 1)),

    -- 공용 (id 17~23)
    ('아우터',   'OUTER',            2, (SELECT id FROM category WHERE name = '공용' AND depth = 1)),
    ('상의',     'TOP',              2, (SELECT id FROM category WHERE name = '공용' AND depth = 1)),
    ('하의',     'BOTTOM',           2, (SELECT id FROM category WHERE name = '공용' AND depth = 1)),
    ('신발',     'SHOES',            2, (SELECT id FROM category WHERE name = '공용' AND depth = 1)),
    ('가방',     'BAG',              2, (SELECT id FROM category WHERE name = '공용' AND depth = 1)),
    ('액세서리', 'ACCESSORY',        2, (SELECT id FROM category WHERE name = '공용' AND depth = 1)),
    ('원피스 및 점프슈트', 'DRESS_JUMPSUIT', 2, (SELECT id FROM category WHERE name = '공용' AND depth = 1));

-- ---------- 카테고리: 소분류 103개 (depth = 3, 남성 33 + 여성 35 + 공용 35) ----------
-- 대분류 이름(아우터 등)이 성별마다 중복되므로, parent_id 서브쿼리는 대분류 이름뿐 아니라
-- 그 대분류의 parent_id(=성별 id)까지 같이 조건에 걸어 정확한 부모를 가리킨다.
INSERT INTO category (name, name_en, depth, parent_id) VALUES
    -- 남성 > 아우터 (id 24~28)
    ('자켓',    'JACKET',       3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('코트',    'COAT',         3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('가디건',  'CARDIGAN',     3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('패딩',    'PADDED_JACKET', 3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('후드집업', 'HOOD_ZIPUP',  3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),

    -- 남성 > 상의 (id 29~34)
    ('티셔츠',   'TSHIRT',      3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('셔츠',     'SHIRT',       3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('니트',     'KNIT',        3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('후드티',   'HOODIE',      3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('맨투맨',   'SWEATSHIRT',  3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('민소매',   'SLEEVELESS',  3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),

    -- 남성 > 하의 (id 35~41)
    ('데님',       'DENIM',        3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('슬랙스',     'SLACKS',       3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('카고팬츠',   'CARGO_PANTS',  3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('스커트',     'SKIRT',        3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('숏팬츠',     'SHORT_PANTS',  3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('트레이닝/조거', 'JOGGER_PANTS', 3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('코튼팬츠',   'COTTON_PANTS', 3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),

    -- 남성 > 신발 (id 42~45)
    ('스니커즈',   'SNEAKERS',        3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('부츠',       'BOOTS',           3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('구두',       'DRESS_SHOES',     3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('샌들/슬리퍼', 'SANDALS_SLIPPERS', 3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),

    -- 남성 > 가방 (id 46~50)
    ('백팩',    'BACKPACK',    3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('숄더백',  'SHOULDER_BAG', 3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('토트백',  'TOTE_BAG',    3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('크로스백', 'CROSS_BAG',  3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('파우치',  'POUCH',       3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),

    -- 남성 > 액세서리 (id 51~56)
    ('모자',   'HAT',        3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('벨트',   'BELT',       3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('스카프', 'SCARF',      3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('주얼리', 'JEWELRY',    3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('시계',   'WATCH',      3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('선글라스', 'SUNGLASSES', 3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),

    -- 여성 > 아우터 (id 57~61)
    ('자켓',    'JACKET',       3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('코트',    'COAT',         3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('가디건',  'CARDIGAN',     3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('패딩',    'PADDED_JACKET', 3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('후드집업', 'HOOD_ZIPUP',  3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),

    -- 여성 > 상의 (id 62~67)
    ('티셔츠',   'TSHIRT',      3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('셔츠',     'SHIRT',       3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('니트',     'KNIT',        3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('후드티',   'HOODIE',      3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('맨투맨',   'SWEATSHIRT',  3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('민소매',   'SLEEVELESS',  3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),

    -- 여성 > 하의 (id 68~74)
    ('데님',       'DENIM',        3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('슬랙스',     'SLACKS',       3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('카고팬츠',   'CARGO_PANTS',  3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('스커트',     'SKIRT',        3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('숏팬츠',     'SHORT_PANTS',  3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('트레이닝/조거', 'JOGGER_PANTS', 3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('코튼팬츠',   'COTTON_PANTS', 3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),

    -- 여성 > 신발 (id 75~78)
    ('스니커즈',   'SNEAKERS',        3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('부츠',       'BOOTS',           3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('구두',       'DRESS_SHOES',     3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('샌들/슬리퍼', 'SANDALS_SLIPPERS', 3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),

    -- 여성 > 가방 (id 79~83)
    ('백팩',    'BACKPACK',    3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('숄더백',  'SHOULDER_BAG', 3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('토트백',  'TOTE_BAG',    3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('크로스백', 'CROSS_BAG',  3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('파우치',  'POUCH',       3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),

    -- 여성 > 액세서리 (id 84~89)
    ('모자',   'HAT',        3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('벨트',   'BELT',       3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('스카프', 'SCARF',      3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('주얼리', 'JEWELRY',    3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('시계',   'WATCH',      3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('선글라스', 'SUNGLASSES', 3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),

    -- 여성 > 원피스 및 점프슈트 (id 90~91)
    ('원피스',   'DRESS',    3, (SELECT id FROM category WHERE name = '원피스 및 점프슈트' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('점프슈트', 'JUMPSUIT', 3, (SELECT id FROM category WHERE name = '원피스 및 점프슈트' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),

    -- 공용 > 아우터 (id 92~96)
    ('자켓',    'JACKET',       3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('코트',    'COAT',         3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('가디건',  'CARDIGAN',     3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('패딩',    'PADDED_JACKET', 3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('후드집업', 'HOOD_ZIPUP',  3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),

    -- 공용 > 상의 (id 97~102)
    ('티셔츠',   'TSHIRT',      3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('셔츠',     'SHIRT',       3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('니트',     'KNIT',        3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('후드티',   'HOODIE',      3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('맨투맨',   'SWEATSHIRT',  3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('민소매',   'SLEEVELESS',  3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),

    -- 공용 > 하의 (id 103~109)
    ('데님',       'DENIM',        3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('슬랙스',     'SLACKS',       3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('카고팬츠',   'CARGO_PANTS',  3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('스커트',     'SKIRT',        3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('숏팬츠',     'SHORT_PANTS',  3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('트레이닝/조거', 'JOGGER_PANTS', 3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('코튼팬츠',   'COTTON_PANTS', 3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),

    -- 공용 > 신발 (id 110~113)
    ('스니커즈',   'SNEAKERS',        3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('부츠',       'BOOTS',           3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('구두',       'DRESS_SHOES',     3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('샌들/슬리퍼', 'SANDALS_SLIPPERS', 3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),

    -- 공용 > 가방 (id 114~118)
    ('백팩',    'BACKPACK',    3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('숄더백',  'SHOULDER_BAG', 3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('토트백',  'TOTE_BAG',    3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('크로스백', 'CROSS_BAG',  3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('파우치',  'POUCH',       3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),

    -- 공용 > 액세서리 (id 119~124)
    ('모자',   'HAT',        3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('벨트',   'BELT',       3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('스카프', 'SCARF',      3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('주얼리', 'JEWELRY',    3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('시계',   'WATCH',      3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('선글라스', 'SUNGLASSES', 3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),

    -- 공용 > 원피스 및 점프슈트 (id 125~126)
    ('원피스',   'DRESS',    3, (SELECT id FROM category WHERE name = '원피스 및 점프슈트' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('점프슈트', 'JUMPSUIT', 3, (SELECT id FROM category WHERE name = '원피스 및 점프슈트' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1)));

-- ---------- 브랜드 21개 ----------
INSERT INTO brand (name, name_en) VALUES
    -- 하이엔드·디자이너 아카이브
    ('꼼데가르송', 'Comme des Garçons'),
    ('메종 마르지엘라', 'Maison Margiela'),
    ('요지 야마모토', 'Yohji Yamamoto'),
    ('릭 오웬스', 'Rick Owens'),
    ('이세이 미야케', 'Issey Miyake'),
    ('장 폴 고티에', 'Jean Paul Gaultier'),
    ('비비안 웨스트우드', 'Vivienne Westwood'),

    -- 스트릿·서브컬처
    ('베이프', 'A Bathing Ape'),
    ('슈프림', 'Supreme'),
    ('스투시', 'Stussy'),
    ('캐피탈', 'Kapital'),
    ('히스테릭 글래머', 'Hysteric Glamour'),
    ('크롬하츠', 'Chrome Hearts'),

    -- 클래식·아메리칸 캐주얼
    ('폴로 랄프로렌', 'Polo Ralph Lauren'),
    ('리바이스', 'Levi''s'),
    ('칼하트', 'Carhartt'),
    ('버버리', 'Burberry'),

    -- 고프코어·스포티
    ('아크테릭스', 'Arc''teryx'),
    ('나이키', 'Nike'),
    ('아디다스', 'Adidas'),
    ('프라다', 'Prada');