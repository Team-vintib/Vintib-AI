-- 카테고리/브랜드 마스터 시드 (SY007).
-- CategoryBrandSeeder(ApplicationRunner)가 category 테이블이 비어 있을 때만 실행한다.
-- 재실행 안전성은 애플리케이션 쪽 count() == 0 가드가 책임진다 — 이 스크립트 자체는
-- 멱등하지 않으니 psql 등으로 직접 재실행할 경우 중복 삽입에 주의한다.

-- ---------- 카테고리: 성별 3개 (depth = 1) ----------
-- SY022: 카테고리 3-depth 개편(성별 → 대분류 → 소분류). ID는 삽입 순서에 의존하며
-- docs/requests/BE/category_schema.md 의 ID 매핑표(1~111)와 정확히 일치해야 한다.
INSERT INTO category (name, depth) VALUES
    ('남성', 1),
    ('여성', 1),
    ('공용', 1);

-- ---------- 카테고리: 대분류 18개 (depth = 2, 성별당 6개) ----------
INSERT INTO category (name, depth, parent_id) VALUES
    -- 남성 (id 4~9)
    ('아우터',   2, (SELECT id FROM category WHERE name = '남성' AND depth = 1)),
    ('상의',     2, (SELECT id FROM category WHERE name = '남성' AND depth = 1)),
    ('하의',     2, (SELECT id FROM category WHERE name = '남성' AND depth = 1)),
    ('신발',     2, (SELECT id FROM category WHERE name = '남성' AND depth = 1)),
    ('가방',     2, (SELECT id FROM category WHERE name = '남성' AND depth = 1)),
    ('액세서리', 2, (SELECT id FROM category WHERE name = '남성' AND depth = 1)),

    -- 여성 (id 10~15)
    ('아우터',   2, (SELECT id FROM category WHERE name = '여성' AND depth = 1)),
    ('상의',     2, (SELECT id FROM category WHERE name = '여성' AND depth = 1)),
    ('하의',     2, (SELECT id FROM category WHERE name = '여성' AND depth = 1)),
    ('신발',     2, (SELECT id FROM category WHERE name = '여성' AND depth = 1)),
    ('가방',     2, (SELECT id FROM category WHERE name = '여성' AND depth = 1)),
    ('액세서리', 2, (SELECT id FROM category WHERE name = '여성' AND depth = 1)),

    -- 공용 (id 16~21)
    ('아우터',   2, (SELECT id FROM category WHERE name = '공용' AND depth = 1)),
    ('상의',     2, (SELECT id FROM category WHERE name = '공용' AND depth = 1)),
    ('하의',     2, (SELECT id FROM category WHERE name = '공용' AND depth = 1)),
    ('신발',     2, (SELECT id FROM category WHERE name = '공용' AND depth = 1)),
    ('가방',     2, (SELECT id FROM category WHERE name = '공용' AND depth = 1)),
    ('액세서리', 2, (SELECT id FROM category WHERE name = '공용' AND depth = 1));

-- ---------- 카테고리: 소분류 90개 (depth = 3, 성별당 30개) ----------
-- 대분류 이름(아우터 등)이 성별마다 중복되므로, parent_id 서브쿼리는 대분류 이름뿐 아니라
-- 그 대분류의 parent_id(=성별 id)까지 같이 조건에 걸어 정확한 부모를 가리킨다.
INSERT INTO category (name, depth, parent_id) VALUES
    -- 남성 > 아우터 (id 22~26)
    ('자켓',    3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('코트',    3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('가디건',  3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('베스트',  3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('후드집업', 3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),

    -- 남성 > 상의 (id 27~31)
    ('티셔츠',   3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('셔츠',     3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('니트',     3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('후드티',   3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('스웨트셔츠', 3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),

    -- 남성 > 하의 (id 32~36)
    ('데님',     3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('슬랙스',   3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('카고팬츠', 3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('스커트',   3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('쇼츠',     3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),

    -- 남성 > 신발 (id 37~40)
    ('스니커즈', 3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('부츠',     3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('로퍼',     3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('샌들',     3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),

    -- 남성 > 가방 (id 41~45)
    ('백팩',    3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('숄더백',  3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('토트백',  3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('크로스백', 3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('파우치',  3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),

    -- 남성 > 액세서리 (id 46~51)
    ('모자',   3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('벨트',   3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('스카프', 3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('주얼리', 3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('시계',   3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),
    ('선글라스', 3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '남성' AND depth = 1))),

    -- 여성 > 아우터 (id 52~56)
    ('자켓',    3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('코트',    3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('가디건',  3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('베스트',  3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('후드집업', 3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),

    -- 여성 > 상의 (id 57~61)
    ('티셔츠',   3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('셔츠',     3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('니트',     3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('후드티',   3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('스웨트셔츠', 3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),

    -- 여성 > 하의 (id 62~66)
    ('데님',     3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('슬랙스',   3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('카고팬츠', 3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('스커트',   3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('쇼츠',     3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),

    -- 여성 > 신발 (id 67~70)
    ('스니커즈', 3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('부츠',     3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('로퍼',     3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('샌들',     3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),

    -- 여성 > 가방 (id 71~75)
    ('백팩',    3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('숄더백',  3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('토트백',  3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('크로스백', 3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('파우치',  3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),

    -- 여성 > 액세서리 (id 76~81)
    ('모자',   3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('벨트',   3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('스카프', 3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('주얼리', 3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('시계',   3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),
    ('선글라스', 3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '여성' AND depth = 1))),

    -- 공용 > 아우터 (id 82~86)
    ('자켓',    3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('코트',    3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('가디건',  3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('베스트',  3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('후드집업', 3, (SELECT id FROM category WHERE name = '아우터' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),

    -- 공용 > 상의 (id 87~91)
    ('티셔츠',   3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('셔츠',     3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('니트',     3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('후드티',   3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('스웨트셔츠', 3, (SELECT id FROM category WHERE name = '상의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),

    -- 공용 > 하의 (id 92~96)
    ('데님',     3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('슬랙스',   3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('카고팬츠', 3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('스커트',   3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('쇼츠',     3, (SELECT id FROM category WHERE name = '하의' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),

    -- 공용 > 신발 (id 97~100)
    ('스니커즈', 3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('부츠',     3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('로퍼',     3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('샌들',     3, (SELECT id FROM category WHERE name = '신발' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),

    -- 공용 > 가방 (id 101~105)
    ('백팩',    3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('숄더백',  3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('토트백',  3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('크로스백', 3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('파우치',  3, (SELECT id FROM category WHERE name = '가방' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),

    -- 공용 > 액세서리 (id 106~111)
    ('모자',   3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('벨트',   3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('스카프', 3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('주얼리', 3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('시계',   3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1))),
    ('선글라스', 3, (SELECT id FROM category WHERE name = '액세서리' AND depth = 2 AND parent_id = (SELECT id FROM category WHERE name = '공용' AND depth = 1)));

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