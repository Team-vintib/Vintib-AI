package com.ssafy.backend.live.port;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.tuple;

import com.ssafy.backend.live.port.ProductQueryPort.CategorySummary;
import com.ssafy.backend.live.port.ProductQueryPort.ProductCard;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

/**
 * 라이브 카테고리 유도 규칙 테스트.
 *
 * <p>카테고리 계층(대분류-소분류)을 실제로 타야 검증되는 로직이라 시드된 카테고리 마스터를
 * 그대로 쓰는 통합 테스트로 둔다.
 */
@SpringBootTest
class ProductQueryAdapterTest {

    @Autowired
    private ProductQueryPort productQueryPort;

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private CategoryRepository categoryRepository;

    @Autowired
    private MemberRepository memberRepository;

    private Member seller;

    @BeforeEach
    void setUp() {
        seller = memberRepository.save(Member.builder()
                .email("cat-seller-" + UUID.randomUUID() + "@example.com")
                .password("encoded")
                .name("판매자")
                .build());
    }

    private Category 소분류(String name) {
        return categoryRepository.findAll().stream()
                .filter(category -> category.getName().equals(name) && category.getParentId() != null)
                .findFirst()
                .orElseThrow(() -> new IllegalStateException("시드에 없는 소분류: " + name));
    }

    private Long 상품_등록(Category category) {
        return productRepository.save(Product.builder()
                        .seller(seller)
                        .categoryId(category.getId())
                        .title("빈티지 " + category.getName())
                        .build())
                .getId();
    }

    @Test
    void 소분류_상품은_대분류로_올라간다() {
        // 자켓(소분류) → 아우터(대분류)
        Long 자켓_상품 = 상품_등록(소분류("자켓"));

        List<CategorySummary> categories = productQueryPort.findRootCategories(List.of(자켓_상품));

        assertThat(categories).extracting(CategorySummary::name).containsExactly("아우터");
    }

    @Test
    void 같은_대분류_상품이_여럿이면_하나로_합쳐진다() {
        // 자켓·코트 둘 다 아우터 소속이므로 배지는 아우터 하나만 나와야 한다.
        Long 자켓 = 상품_등록(소분류("자켓"));
        Long 코트 = 상품_등록(소분류("코트"));

        List<CategorySummary> categories = productQueryPort.findRootCategories(List.of(자켓, 코트));

        assertThat(categories).extracting(CategorySummary::name).containsExactly("아우터");
    }

    @Test
    void 여러_대분류_상품을_걸면_카테고리도_여러_개가_된다() {
        // 아우터·하의·액세서리를 함께 파는 방송은 세 카테고리 모두에서 검색돼야 한다.
        Long 자켓 = 상품_등록(소분류("자켓"));
        Long 데님 = 상품_등록(소분류("데님"));
        Long 스카프 = 상품_등록(소분류("스카프"));

        List<CategorySummary> categories = productQueryPort.findRootCategories(List.of(자켓, 데님, 스카프));

        assertThat(categories)
                .extracting(CategorySummary::name)
                .containsExactlyInAnyOrder("아우터", "하의", "액세서리");
    }

    @Test
    void 편성_상품이_없으면_카테고리도_비어_있다() {
        assertThat(productQueryPort.findRootCategories(List.of())).isEmpty();
    }

    @Test
    void 카테고리_ID는_마스터의_ID와_같다() {
        // 목록 화면의 카테고리 필터가 이 ID 를 그대로 쓴다.
        Category 자켓 = 소분류("자켓");
        Long 상품 = 상품_등록(자켓);

        List<CategorySummary> categories = productQueryPort.findRootCategories(List.of(상품));

        assertThat(categories)
                .extracting(CategorySummary::id, CategorySummary::name)
                .containsExactly(tuple(자켓.getParentId(), "아우터"));
    }

    // ---------- 카드 조회 — 소재/치수/하자 요약 (FE 요청 003 §3.5) ----------

    @Test
    void 소재와_실측_치수가_카드에_담긴다() {
        Category 자켓 = 소분류("자켓");
        Product product = productRepository.save(Product.builder()
                .seller(seller)
                .categoryId(자켓.getId())
                .title("빈티지 자켓")
                .material("코튼 100%")
                .measurements(Map.of("어깨너비", 45, "총장", 70))
                .build());

        ProductCard card = productQueryPort.findCards(List.of(product.getId())).get(product.getId());

        assertThat(card.material()).isEqualTo("코튼 100%");
        assertThat(card.measurements()).containsEntry("어깨너비", 45).containsEntry("총장", 70);
    }

    @Test
    void 하자_목록은_쉼표로_이어붙인_한_줄_요약으로_담긴다() {
        Category 자켓 = 소분류("자켓");
        Product product = productRepository.save(Product.builder()
                .seller(seller)
                .categoryId(자켓.getId())
                .title("빈티지 자켓")
                .defects(List.of("밑단 오염", "우측 소매 실밥 풀림"))
                .build());

        ProductCard card = productQueryPort.findCards(List.of(product.getId())).get(product.getId());

        assertThat(card.defectSummary()).isEqualTo("밑단 오염, 우측 소매 실밥 풀림");
    }

    @Test
    void 소재와_하자가_없으면_null이다() {
        Category 자켓 = 소분류("자켓");
        Product product = productRepository.save(
                Product.builder().seller(seller).categoryId(자켓.getId()).title("빈티지 자켓").build());

        ProductCard card = productQueryPort.findCards(List.of(product.getId())).get(product.getId());

        assertThat(card.material()).isNull();
        assertThat(card.measurements()).isNull();
        assertThat(card.defectSummary()).isNull();
    }

    /**
     * 판매 상태는 판매 방식과 별개 축이다. 경매 예정 상품도 {@code saleType} 은 {@code AUCTION},
     * {@code saleStatus} 는 {@code AUCTION_SCHEDULED} 로 따로 내려가야 FE 가 "경매 예정" 과
     * "판매 완료" 를 구분할 수 있다.
     */
    @Test
    void 판매_상태가_판매_방식과_따로_카드에_담긴다() {
        Category 자켓 = 소분류("자켓");
        Product 등록전 = productRepository.save(
                Product.builder().seller(seller).categoryId(자켓.getId()).title("초안 자켓").build());
        Product 경매예정 = productRepository.save(
                Product.builder().seller(seller).categoryId(자켓.getId()).title("경매 자켓").build());
        경매예정.scheduleAuction();
        productRepository.save(경매예정);

        Map<Long, ProductCard> cards =
                productQueryPort.findCards(List.of(등록전.getId(), 경매예정.getId()));

        assertThat(cards.get(등록전.getId()).saleStatus()).isEqualTo("DRAFT");
        assertThat(cards.get(등록전.getId()).saleType()).isNull();
        assertThat(cards.get(경매예정.getId()).saleStatus()).isEqualTo("AUCTION_SCHEDULED");
        assertThat(cards.get(경매예정.getId()).saleType()).isEqualTo("AUCTION");
    }
}