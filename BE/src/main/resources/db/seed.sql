-- 카테고리/브랜드 마스터 시드 (SY007).
-- CategoryBrandSeeder(ApplicationRunner)가 category 테이블이 비어 있을 때만 실행한다.
-- 재실행 안전성은 애플리케이션 쪽 count() == 0 가드가 책임진다 — 이 스크립트 자체는
-- 멱등하지 않으니 psql 등으로 직접 재실행할 경우 중복 삽입에 주의한다.

-- ---------- 카테고리: 대분류 6개 (depth = 1) ----------
INSERT INTO category (name, depth) VALUES
    ('아우터', 1),
    ('상의', 1),
    ('하의', 1),
    ('신발', 1),
    ('가방', 1),
    ('액세서리', 1);

-- ---------- 카테고리: 소분류 (depth = 2) ----------
INSERT INTO category (name, depth, parent_id) VALUES
    ('자켓',    2, (SELECT id FROM category WHERE name = '아우터' AND depth = 1)),
    ('코트',    2, (SELECT id FROM category WHERE name = '아우터' AND depth = 1)),
    ('가디건',  2, (SELECT id FROM category WHERE name = '아우터' AND depth = 1)),
    ('베스트',  2, (SELECT id FROM category WHERE name = '아우터' AND depth = 1)),
    ('후드집업', 2, (SELECT id FROM category WHERE name = '아우터' AND depth = 1)),

    ('티셔츠',   2, (SELECT id FROM category WHERE name = '상의' AND depth = 1)),
    ('셔츠',     2, (SELECT id FROM category WHERE name = '상의' AND depth = 1)),
    ('니트',     2, (SELECT id FROM category WHERE name = '상의' AND depth = 1)),
    ('후드티',   2, (SELECT id FROM category WHERE name = '상의' AND depth = 1)),
    ('스웨트셔츠', 2, (SELECT id FROM category WHERE name = '상의' AND depth = 1)),

    ('데님',     2, (SELECT id FROM category WHERE name = '하의' AND depth = 1)),
    ('슬랙스',   2, (SELECT id FROM category WHERE name = '하의' AND depth = 1)),
    ('카고팬츠', 2, (SELECT id FROM category WHERE name = '하의' AND depth = 1)),
    ('스커트',   2, (SELECT id FROM category WHERE name = '하의' AND depth = 1)),
    ('쇼츠',     2, (SELECT id FROM category WHERE name = '하의' AND depth = 1)),

    ('스니커즈', 2, (SELECT id FROM category WHERE name = '신발' AND depth = 1)),
    ('부츠',     2, (SELECT id FROM category WHERE name = '신발' AND depth = 1)),
    ('로퍼',     2, (SELECT id FROM category WHERE name = '신발' AND depth = 1)),
    ('샌들',     2, (SELECT id FROM category WHERE name = '신발' AND depth = 1)),

    ('백팩',    2, (SELECT id FROM category WHERE name = '가방' AND depth = 1)),
    ('숄더백',  2, (SELECT id FROM category WHERE name = '가방' AND depth = 1)),
    ('토트백',  2, (SELECT id FROM category WHERE name = '가방' AND depth = 1)),
    ('크로스백', 2, (SELECT id FROM category WHERE name = '가방' AND depth = 1)),
    ('파우치',  2, (SELECT id FROM category WHERE name = '가방' AND depth = 1)),

    ('모자',   2, (SELECT id FROM category WHERE name = '액세서리' AND depth = 1)),
    ('벨트',   2, (SELECT id FROM category WHERE name = '액세서리' AND depth = 1)),
    ('스카프', 2, (SELECT id FROM category WHERE name = '액세서리' AND depth = 1)),
    ('주얼리', 2, (SELECT id FROM category WHERE name = '액세서리' AND depth = 1)),
    ('시계',   2, (SELECT id FROM category WHERE name = '액세서리' AND depth = 1)),
    ('선글라스', 2, (SELECT id FROM category WHERE name = '액세서리' AND depth = 1));

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