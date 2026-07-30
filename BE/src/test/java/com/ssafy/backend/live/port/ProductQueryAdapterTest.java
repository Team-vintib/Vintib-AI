package com.ssafy.backend.live.port;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.tuple;

import com.ssafy.backend.live.port.ProductQueryPort.CategorySummary;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import java.util.List;
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
}