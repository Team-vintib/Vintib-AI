package com.ssafy.backend.product.repository;

import static org.assertj.core.api.Assertions.assertThat;

import com.ssafy.backend.auction.port.ProductCommandPort;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.transaction.annotation.Transactional;

/**
 * 상품 목록 공개 범위 — 판매 완료(SOLD) 제외(FE 요청 022).
 *
 * <p>서비스 단위 테스트는 리포지토리를 목으로 두어 JPQL 자체가 검증되지 않는다. 여기서 걸러야
 * 하는 것이 질의의 WHERE 절이라 실제 DB 를 타는 통합 테스트로 둔다
 * ({@code live/port/ProductQueryAdapterTest}와 같은 방식).
 *
 * <p>시드 상품이 이미 들어 있으므로 판매자 필터로 이 테스트가 만든 상품만 좁혀서 본다.
 *
 * <p>{@code @Transactional}을 거는 이유는 두 가지다 — {@code ProductCommandPort}의 벌크 UPDATE 는
 * 트랜잭션 안에서만 부를 수 있고(포트 자체에는 경계가 없다, 낙찰 마감 서비스가 열어 준다),
 * 테스트가 만든 상품이 다른 테스트의 목록 조회에 섞이지 않게 롤백된다.
 */
@SpringBootTest
@Transactional
class ProductListSoldExclusionTest {

    private static final Pageable FIRST_PAGE = PageRequest.of(0, 20);

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private CategoryRepository categoryRepository;

    @Autowired
    private MemberRepository memberRepository;

    @Autowired
    private ProductCommandPort productCommandPort;

    private Member seller;
    private Long categoryId;

    @BeforeEach
    void setUp() {
        seller = memberRepository.save(Member.builder()
                .email("sold-filter-" + UUID.randomUUID() + "@example.com")
                .password("encoded")
                .name("판매자")
                .build());
        categoryId = categoryRepository.findAll().stream()
                .filter(category -> category.getParentId() != null)
                .map(Category::getId)
                .findFirst()
                .orElseThrow(() -> new IllegalStateException("시드된 소분류 카테고리가 없다"));
    }

    private Product 상품_등록(String title) {
        return productRepository.save(Product.builder()
                .seller(seller)
                .categoryId(categoryId)
                .title(title)
                .build());
    }

    /** 판매자 필터만 건 목록 조회 — 나머지 플래그는 전부 끈다(더미값은 서비스가 넣는 것과 같다). */
    private List<Product> 내_상품_목록() {
        return productRepository.findWithFilter(
                        false, List.of(-1L),
                        false, List.of(""),
                        false, null,
                        false, null,
                        false, null,
                        true, seller.getId(),
                        FIRST_PAGE)
                .getContent();
    }

    @Test
    void 판매_완료된_상품은_목록에서_빠진다() {
        Product 팔린_상품 = 상품_등록("낙찰된 빈티지 자켓");
        팔린_상품.registerDirectSale(50_000L);
        팔린_상품.markSold();
        productRepository.save(팔린_상품);

        assertThat(내_상품_목록()).isEmpty();
    }

    @Test
    void 경매_낙찰로_SOLD가_되면_목록에서_빠진다() {
        // 낙찰 마감은 엔티티가 아니라 ProductCommandPort 의 벌크 UPDATE 로 상태를 바꾼다.
        Product 경매_상품 = 상품_등록("경매에 걸린 코트");
        경매_상품.scheduleAuction();
        productRepository.save(경매_상품);
        productCommandPort.markAuctionInProgress(경매_상품.getId());

        assertThat(내_상품_목록()).hasSize(1);

        productCommandPort.markSold(경매_상품.getId());

        assertThat(내_상품_목록()).isEmpty();
    }

    @Test
    void 판매중_경매예정_경매중_상품은_그대로_노출된다() {
        Product 정찰제 = 상품_등록("정찰제 티셔츠");
        정찰제.registerDirectSale(30_000L);
        productRepository.save(정찰제);

        Product 경매_예정 = 상품_등록("경매 예정 가디건");
        경매_예정.scheduleAuction();
        productRepository.save(경매_예정);

        Product 경매_중 = 상품_등록("경매 중인 셔츠");
        경매_중.scheduleAuction();
        productRepository.save(경매_중);
        productCommandPort.markAuctionInProgress(경매_중.getId());

        assertThat(내_상품_목록())
                .extracting(Product::getSaleStatus)
                .containsExactlyInAnyOrder(
                        SaleStatus.ON_SALE, SaleStatus.AUCTION_SCHEDULED, SaleStatus.AUCTION_IN_PROGRESS);
    }

    @Test
    void 등록_중인_DRAFT_상품은_계속_빠진다() {
        상품_등록("등록 중인 상품");

        assertThat(내_상품_목록()).isEmpty();
    }
}
