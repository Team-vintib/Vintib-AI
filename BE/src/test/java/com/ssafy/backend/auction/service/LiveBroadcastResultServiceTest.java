package com.ssafy.backend.auction.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyCollection;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

import com.ssafy.backend.auction.dto.response.LiveBroadcastSummaryResponse;
import com.ssafy.backend.auction.dto.response.LiveUnsoldProductResponse;
import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.auction.repository.AuctionRepository;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveProduct;
import com.ssafy.backend.live.port.ProductQueryPort;
import com.ssafy.backend.live.port.ProductQueryPort.ProductCard;
import com.ssafy.backend.live.repository.LiveProductRepository;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.order.entity.Order;
import com.ssafy.backend.order.repository.OrderRepository;
import com.ssafy.backend.product.entity.Product;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class LiveBroadcastResultServiceTest {

    private static final Long HOST_ID = 1L;
    private static final Long OTHER_MEMBER_ID = 2L;
    private static final Long LIVE_ID = 101L;
    private static final Long SOLD_PRODUCT_ID = 2001L;
    private static final Long UNSOLD_PRODUCT_ID = 2002L;
    private static final Long NO_AUCTION_PRODUCT_ID = 2003L;

    @Mock
    private AuctionRepository auctionRepository;

    @Mock
    private LiveRepository liveRepository;

    @Mock
    private LiveProductRepository liveProductRepository;

    @Mock
    private ProductQueryPort productQueryPort;

    @Mock
    private OrderRepository orderRepository;

    @Mock
    private Member host;

    private LiveBroadcastResultService service;

    @BeforeEach
    void setUp() {
        service = new LiveBroadcastResultService(
                auctionRepository, orderRepository, liveRepository, liveProductRepository, productQueryPort);
    }

    /** 이 방송에서 정찰가로 팔린 주문. 유찰 목록 조회에는 필요 없어 요약 테스트에서만 쓴다. */
    private void 즉시구매_주문이_있다(Long productId, long orderPrice) {
        Product product = org.mockito.Mockito.mock(Product.class);
        when(product.getId()).thenReturn(productId);
        Order order = org.mockito.Mockito.mock(Order.class);
        when(order.getProduct()).thenReturn(product);
        when(order.getOrderPrice()).thenReturn(orderPrice);
        when(orderRepository.findLiveDirectSaleOrders(LIVE_ID)).thenReturn(List.of(order));
    }

    private void 즉시구매_주문이_없다() {
        when(orderRepository.findLiveDirectSaleOrders(LIVE_ID)).thenReturn(List.of());
    }

    /** 스터빙을 하지 않는다 — {@code when(...)} 인자 안에서 불려도 안전해야 한다. */
    private Live 라이브() {
        return Live.openNow(host, "빈티지 데님 라이브", null, null, LocalDateTime.now());
    }

    private void 호스트_확인_통과() {
        when(host.getId()).thenReturn(HOST_ID);
        Live live = 라이브();
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live));
    }

    private void 편성_상품이다(Long... productIds) {
        List<LiveProduct> linked = java.util.Arrays.stream(productIds)
                .map(productId -> {
                    LiveProduct liveProduct = org.mockito.Mockito.mock(LiveProduct.class);
                    when(liveProduct.getProductId()).thenReturn(productId);
                    return liveProduct;
                })
                .toList();
        when(liveProductRepository.findByLiveIdAndRemovedAtIsNullOrderBySortOrderAsc(LIVE_ID))
                .thenReturn(linked);
    }

    private Auction 낙찰된_경매(Long productId, long finalPrice) {
        Auction auction = Auction.configure(라이브(), productId, 10_000L, 1_000L, 60);
        auction.start(LocalDateTime.now());
        auction.applyBid(OTHER_MEMBER_ID, finalPrice, LocalDateTime.now());
        auction.closeAsSuccess(LocalDateTime.now());
        return auction;
    }

    private Auction 유찰된_경매(Long productId) {
        Auction auction = Auction.configure(라이브(), productId, 10_000L, 1_000L, 60);
        auction.start(LocalDateTime.now());
        auction.closeAsFailed(LocalDateTime.now());
        return auction;
    }

    private ProductCard 카드(Long productId, String title) {
        return new ProductCard(
                productId, title, null, null, null, null, null, "https://cdn/" + productId + ".jpg",
                null, null, null);
    }

    @Test
    void 요약은_편성_상품_전체를_기준으로_낙찰과_미판매를_집계한다() {
        호스트_확인_통과();
        편성_상품이다(SOLD_PRODUCT_ID, UNSOLD_PRODUCT_ID, NO_AUCTION_PRODUCT_ID);
        when(auctionRepository.findByLiveIdAndStatusInOrderByIdAsc(eq(LIVE_ID), anyCollection()))
                .thenReturn(List.of(낙찰된_경매(SOLD_PRODUCT_ID, 89_000L), 유찰된_경매(UNSOLD_PRODUCT_ID)));
        즉시구매_주문이_없다();
        when(productQueryPort.findCards(any())).thenReturn(Map.of(
                SOLD_PRODUCT_ID, 카드(SOLD_PRODUCT_ID, "리바이스 501"),
                UNSOLD_PRODUCT_ID, 카드(UNSOLD_PRODUCT_ID, "코트"),
                NO_AUCTION_PRODUCT_ID, 카드(NO_AUCTION_PRODUCT_ID, "니트")));

        LiveBroadcastSummaryResponse summary = service.getSummary(LIVE_ID, HOST_ID);

        assertThat(summary.soldCount()).isEqualTo(1);
        // 경매를 아예 걸지 않은 편성 상품도 UNSOLD 로 잡혀야 대시보드가 방송 전체를 보여 준다.
        assertThat(summary.unsoldCount()).isEqualTo(2);
        assertThat(summary.totalSales()).isEqualTo(89_000L);
        assertThat(summary.results()).hasSize(3);
    }

    @Test
    void 낙찰된_상품은_낙찰가와_판매경로가_담긴다() {
        호스트_확인_통과();
        편성_상품이다(SOLD_PRODUCT_ID);
        when(auctionRepository.findByLiveIdAndStatusInOrderByIdAsc(eq(LIVE_ID), anyCollection()))
                .thenReturn(List.of(낙찰된_경매(SOLD_PRODUCT_ID, 89_000L)));
        즉시구매_주문이_없다();
        when(productQueryPort.findCards(any()))
                .thenReturn(Map.of(SOLD_PRODUCT_ID, 카드(SOLD_PRODUCT_ID, "리바이스 501")));

        LiveBroadcastSummaryResponse.Result result = service.getSummary(LIVE_ID, HOST_ID).results().get(0);

        assertThat(result.status()).isEqualTo("SOLD");
        assertThat(result.finalPrice()).isEqualTo(89_000L);
        assertThat(result.soldVia()).isEqualTo("AUCTION");
        assertThat(result.title()).isEqualTo("리바이스 501");
    }

    @Test
    void 방송_중_정찰가로_팔린_상품도_판매로_집계된다() {
        // 요약은 경매 실적이 아니라 방송 실적이다 — 경매를 안 건 상품도 팔렸으면 잡혀야 한다.
        호스트_확인_통과();
        편성_상품이다(NO_AUCTION_PRODUCT_ID);
        when(auctionRepository.findByLiveIdAndStatusInOrderByIdAsc(eq(LIVE_ID), anyCollection()))
                .thenReturn(List.of());
        즉시구매_주문이_있다(NO_AUCTION_PRODUCT_ID, 50_000L);
        when(productQueryPort.findCards(any()))
                .thenReturn(Map.of(NO_AUCTION_PRODUCT_ID, 카드(NO_AUCTION_PRODUCT_ID, "니트")));

        LiveBroadcastSummaryResponse summary = service.getSummary(LIVE_ID, HOST_ID);

        assertThat(summary.soldCount()).isEqualTo(1);
        assertThat(summary.unsoldCount()).isZero();
        assertThat(summary.totalSales()).isEqualTo(50_000L);
        assertThat(summary.results().get(0).soldVia()).isEqualTo("DIRECT_SALE");
        assertThat(summary.results().get(0).finalPrice()).isEqualTo(50_000L);
    }

    @Test
    void 낙찰과_즉시구매가_섞이면_총_판매액에_함께_더해진다() {
        호스트_확인_통과();
        편성_상품이다(SOLD_PRODUCT_ID, NO_AUCTION_PRODUCT_ID);
        when(auctionRepository.findByLiveIdAndStatusInOrderByIdAsc(eq(LIVE_ID), anyCollection()))
                .thenReturn(List.of(낙찰된_경매(SOLD_PRODUCT_ID, 89_000L)));
        즉시구매_주문이_있다(NO_AUCTION_PRODUCT_ID, 50_000L);
        when(productQueryPort.findCards(any())).thenReturn(Map.of());

        LiveBroadcastSummaryResponse summary = service.getSummary(LIVE_ID, HOST_ID);

        assertThat(summary.soldCount()).isEqualTo(2);
        assertThat(summary.totalSales()).isEqualTo(139_000L);
    }

    @Test
    void 유찰_목록은_마지막_경매가_유찰인_상품만_담는다() {
        호스트_확인_통과();
        편성_상품이다(SOLD_PRODUCT_ID, UNSOLD_PRODUCT_ID, NO_AUCTION_PRODUCT_ID);
        when(auctionRepository.findByLiveIdAndStatusInOrderByIdAsc(eq(LIVE_ID), anyCollection()))
                .thenReturn(List.of(낙찰된_경매(SOLD_PRODUCT_ID, 89_000L), 유찰된_경매(UNSOLD_PRODUCT_ID)));
        when(productQueryPort.findCards(any()))
                .thenReturn(Map.of(UNSOLD_PRODUCT_ID, 카드(UNSOLD_PRODUCT_ID, "코트")));

        List<LiveUnsoldProductResponse> unsold = service.getUnsoldProducts(LIVE_ID, HOST_ID);

        // 낙찰된 상품도, 경매를 안 건 상품도 유찰이 아니다.
        assertThat(unsold).hasSize(1);
        assertThat(unsold.get(0).productId()).isEqualTo(UNSOLD_PRODUCT_ID);
        assertThat(unsold.get(0).startPrice()).isEqualTo(10_000L);
    }

    @Test
    void 유찰_뒤_재경매로_낙찰됐으면_유찰_목록에서_빠진다() {
        호스트_확인_통과();
        편성_상품이다(SOLD_PRODUCT_ID);
        // 같은 상품에 유찰 → 재경매 낙찰. 질의가 오래된 순이라 뒤엣것이 마지막 결과다.
        when(auctionRepository.findByLiveIdAndStatusInOrderByIdAsc(eq(LIVE_ID), anyCollection()))
                .thenReturn(List.of(유찰된_경매(SOLD_PRODUCT_ID), 낙찰된_경매(SOLD_PRODUCT_ID, 89_000L)));
        when(productQueryPort.findCards(any())).thenReturn(Map.of());

        assertThat(service.getUnsoldProducts(LIVE_ID, HOST_ID)).isEmpty();
    }

    @Test
    void 호스트가_아니면_요약을_볼_수_없다() {
        호스트_확인_통과();

        assertThatThrownBy(() -> service.getSummary(LIVE_ID, OTHER_MEMBER_ID))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.NOT_LIVE_HOST);
    }

    @Test
    void 호스트가_아니면_유찰_목록을_볼_수_없다() {
        호스트_확인_통과();

        assertThatThrownBy(() -> service.getUnsoldProducts(LIVE_ID, OTHER_MEMBER_ID))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.NOT_LIVE_HOST);
    }

    @Test
    void 존재하지_않는_라이브는_요약을_볼_수_없다() {
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.getSummary(LIVE_ID, HOST_ID))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.LIVE_NOT_FOUND);
    }

    @Test
    void 편성_상품이_없으면_빈_요약을_준다() {
        호스트_확인_통과();
        편성_상품이다();
        when(auctionRepository.findByLiveIdAndStatusInOrderByIdAsc(eq(LIVE_ID), anyCollection()))
                .thenReturn(List.of());
        즉시구매_주문이_없다();
        when(productQueryPort.findCards(any())).thenReturn(Map.of());

        LiveBroadcastSummaryResponse summary = service.getSummary(LIVE_ID, HOST_ID);

        assertThat(summary.soldCount()).isZero();
        assertThat(summary.unsoldCount()).isZero();
        assertThat(summary.totalSales()).isZero();
        assertThat(summary.results()).isEmpty();
    }
}
