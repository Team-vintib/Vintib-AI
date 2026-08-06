package com.ssafy.backend.auction.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.ssafy.backend.auction.dto.request.AuctionConfigRequest;
import com.ssafy.backend.auction.dto.request.BidRequest;
import com.ssafy.backend.auction.dto.response.AuctionResponse;
import com.ssafy.backend.auction.entity.AuctionStatus;
import com.ssafy.backend.auction.repository.AuctionRepository;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveProduct;
import com.ssafy.backend.live.repository.LiveProductRepository;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.order.entity.Order;
import com.ssafy.backend.order.repository.OrderRepository;
import com.ssafy.backend.point.service.PointService;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.data.domain.PageRequest;
import org.springframework.transaction.annotation.Transactional;

/**
 * 낙찰 → 상품 {@code SOLD} 종단 검증(AUCT-012).
 *
 * <p><b>{@link AuctionCloseServiceTest}가 있는데도 이걸 두는 이유.</b> 저쪽은 포트를 목으로 두어
 * "{@code markSold()}를 불렀다"까지만 확인한다 — 실제로 DB 의 {@code sale_status}가 바뀌는지,
 * 그 앞의 주문 생성·포인트 전환이 제약에 걸려 트랜잭션째 롤백되지는 않는지는 검증되지 않는다.
 * FE 에서 "낙찰돼도 상태가 안 바뀐다"는 보고가 올라와, 조건 설정 → 시작 → 입찰 → 마감까지
 * 실제 DB 로 한 번에 태워 확인한다.
 */
@SpringBootTest
@Transactional
class AuctionWinToSoldIntegrationTest {

    private static final long START_PRICE = 10_000L;
    private static final long BID_UNIT = 1_000L;
    private static final int DURATION_SECONDS = 60;

    @Autowired
    private AuctionService auctionService;

    @Autowired
    private AuctionCloseService auctionCloseService;

    @Autowired
    private AuctionRepository auctionRepository;

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private CategoryRepository categoryRepository;

    @Autowired
    private MemberRepository memberRepository;

    @Autowired
    private LiveRepository liveRepository;

    @Autowired
    private LiveProductRepository liveProductRepository;

    @Autowired
    private OrderRepository orderRepository;

    @Autowired
    private PointService pointService;

    private Member seller;
    private Member bidder;
    private Live live;
    private Product product;

    @BeforeEach
    void setUp() {
        seller = 회원_생성("판매자");
        bidder = 회원_생성("입찰자");

        Long categoryId = categoryRepository.findAll().stream()
                .filter(category -> category.getParentId() != null)
                .map(Category::getId)
                .findFirst()
                .orElseThrow(() -> new IllegalStateException("시드된 소분류 카테고리가 없다"));

        product = productRepository.save(Product.builder()
                .seller(seller)
                .categoryId(categoryId)
                .title("낙찰 검증용 빈티지 자켓")
                .build());

        live = liveRepository.save(
                Live.openNow(seller, "낙찰 검증 방송", null, null, LocalDateTime.now()));
        liveProductRepository.save(LiveProduct.link(live, product.getId(), (short) 0, LocalDateTime.now()));

        // 입찰하려면 보류할 포인트가 있어야 한다. 없으면 holdForBid 에서 막혀 입찰 자체가 안 된다.
        pointService.charge(bidder.getId(), 100_000L, null);
    }

    private Member 회원_생성(String name) {
        return memberRepository.save(Member.builder()
                .email("auction-sold-" + UUID.randomUUID() + "@example.com")
                .password("encoded")
                .name(name)
                .build());
    }

    private Long 경매_걸고_시작한다() {
        AuctionResponse configured = auctionService.configureAuction(
                seller.getId(),
                live.getId(),
                new AuctionConfigRequest(product.getId(), START_PRICE, BID_UNIT, DURATION_SECONDS));
        auctionService.startAuction(seller.getId(), configured.id());
        return configured.id();
    }

    private SaleStatus 상품_상태() {
        return productRepository.findById(product.getId()).orElseThrow().getSaleStatus();
    }

    @Test
    void 낙찰되면_상품이_SOLD가_되고_낙찰_주문이_생긴다() {
        Long auctionId = 경매_걸고_시작한다();
        assertThat(상품_상태()).isEqualTo(SaleStatus.AUCTION_IN_PROGRESS);

        auctionService.placeBid(bidder.getId(), auctionId, new BidRequest(START_PRICE));

        // 방송 종료 강제 마감(AUCT-014) — 종료 시각을 기다리지 않고 스케줄러와 같은 close() 를 탄다.
        auctionCloseService.closeRunningAuctionsOfLive(live.getId());

        assertThat(auctionRepository.findById(auctionId).orElseThrow().getStatus())
                .isEqualTo(AuctionStatus.SUCCESS);
        assertThat(상품_상태()).isEqualTo(SaleStatus.SOLD);

        List<Order> orders = orderRepository.findByBuyer_IdOrderByCreatedAtDesc(
                        bidder.getId(), PageRequest.of(0, 10))
                .getContent();
        assertThat(orders)
                .singleElement()
                .satisfies(order -> {
                    assertThat(order.getProduct().getId()).isEqualTo(product.getId());
                    assertThat(order.getOrderPrice()).isEqualTo(START_PRICE);
                });
    }

    @Test
    void 낙찰된_상품은_상품_목록에서_빠진다() {
        Long auctionId = 경매_걸고_시작한다();
        auctionService.placeBid(bidder.getId(), auctionId, new BidRequest(START_PRICE));

        assertThat(판매자_상품_목록()).hasSize(1);

        auctionCloseService.closeRunningAuctionsOfLive(live.getId());

        assertThat(판매자_상품_목록()).isEmpty();
    }

    @Test
    void 입찰이_없으면_유찰되고_상품은_경매_예정으로_돌아간다() {
        경매_걸고_시작한다();

        auctionCloseService.closeRunningAuctionsOfLive(live.getId());

        // 유찰은 SOLD 가 아니다 — 상품은 목록에 계속 남고 다음 방송에 다시 걸 수 있다.
        assertThat(상품_상태()).isEqualTo(SaleStatus.AUCTION_SCHEDULED);
        assertThat(판매자_상품_목록()).hasSize(1);
    }

    private List<Product> 판매자_상품_목록() {
        return productRepository.findWithFilter(
                        false, List.of(-1L),
                        false, List.of(""),
                        false, null,
                        false, null,
                        false, null,
                        true, seller.getId(),
                        PageRequest.of(0, 20))
                .getContent();
    }
}
