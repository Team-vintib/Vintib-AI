package com.ssafy.backend.auction.service;

import com.ssafy.backend.auction.dto.response.LiveBroadcastSummaryResponse;
import com.ssafy.backend.auction.dto.response.LiveUnsoldProductResponse;
import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.auction.entity.AuctionStatus;
import com.ssafy.backend.auction.repository.AuctionRepository;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveProduct;
import com.ssafy.backend.live.port.ProductQueryPort;
import com.ssafy.backend.live.port.ProductQueryPort.ProductCard;
import com.ssafy.backend.live.repository.LiveProductRepository;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.order.repository.OrderRepository;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 방송 종료 요약(FE 요청 018)과 방송별 유찰 상품 목록(LIVE-006) 조회 — Phase 8-b.
 *
 * <p><b>왜 {@code live}가 아니라 {@code auction} 패키지인가.</b> 두 조회 모두 편성 상품과 경매
 * 결과를 함께 봐야 한다. 그런데 패키지 의존은 {@code auction → live} 단방향으로만 나 있고
 * ({@code Auction}이 {@code Live}를 참조한다) 반대 방향은 한 곳도 없다. 라이브 서비스가 경매
 * 리포지토리를 잡으면 그 단방향이 깨진다. 경로가 {@code /api/lives/...}인 것은 문제가 아니다 —
 * {@code AuctionController}도 {@code /api/lives/{liveId}/auctions}를 매핑한다.
 *
 * <h2>"이 방송의 결과"를 상품 상태가 아니라 방송 연결로 찾는 이유</h2>
 *
 * 유찰 상품은 판매 상태가 {@code AUCTION_SCHEDULED}로 돌아간다(JY008 설계 판단 10 정정). 그래서
 * <b>상품 상태만 보면 다른 방송에서 유찰됐거나 아직 한 번도 경매에 안 걸린 상품까지 섞인다.</b>
 * "이 방송의 결과"는 {@code auction.live_id}와 {@code orders.live_id}에만 있다.
 *
 * <p><b>같은 상품에 재경매를 걸 수 있으므로 상품별로 마지막 경매만 본다.</b> 유찰 뒤 다시 걸어
 * 낙찰됐다면 그 상품은 팔린 것이고, 유찰 목록에 남아 있으면 안 된다.
 *
 * <h2>판매는 두 경로다</h2>
 *
 * 요약은 <b>경매 실적이 아니라 방송 실적</b>이라 방송 중 정찰가로 팔린 것도 센다. 즉시구매는
 * 경매를 거치지 않아 {@code orders.live_id}로만 방송과 이어진다 — FE 가 라이브 구매 요청에
 * {@code liveId}를 실어야 잡힌다. 유찰 목록(§{@link #getUnsoldProducts})은 이름 그대로 경매
 * 결과만 보므로 이 구분과 무관하다.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class LiveBroadcastResultService {

    /** 끝난 경매만 결과 집계 대상이다 — 준비 중·진행 중은 아직 결과가 없다. */
    private static final List<AuctionStatus> FINISHED =
            List.of(AuctionStatus.SUCCESS, AuctionStatus.FAILED);

    private final AuctionRepository auctionRepository;
    private final OrderRepository orderRepository;
    private final LiveRepository liveRepository;
    private final LiveProductRepository liveProductRepository;
    private final ProductQueryPort productQueryPort;

    /**
     * 방송 종료 요약(FE 요청 018). <b>호스트 본인만.</b>
     *
     * <p>편성 상품 전체를 편성 순서대로 훑으며 각 상품의 마지막 경매 결과를 붙인다.
     */
    public LiveBroadcastSummaryResponse getSummary(Long liveId, Long requesterId) {
        requireHost(liveId, requesterId);

        List<Long> productIds = linkedProductIds(liveId);
        Map<Long, Auction> lastAuctionByProductId = lastFinishedAuctionByProductId(liveId);
        Map<Long, Long> directSalePriceByProductId = directSalePriceByProductId(liveId);
        Map<Long, ProductCard> cards = productQueryPort.findCards(productIds);

        List<LiveBroadcastSummaryResponse.Result> results = productIds.stream()
                .map(productId -> toResult(
                        productId,
                        cards.get(productId),
                        lastAuctionByProductId.get(productId),
                        directSalePriceByProductId.get(productId)))
                .toList();

        int soldCount = (int) results.stream().filter(LiveBroadcastSummaryResponse.Result::isSold).count();
        long totalSales = results.stream()
                .filter(LiveBroadcastSummaryResponse.Result::isSold)
                .mapToLong(LiveBroadcastSummaryResponse.Result::finalPrice)
                .sum();

        return new LiveBroadcastSummaryResponse(
                soldCount, results.size() - soldCount, totalSales, results);
    }

    /**
     * 이 방송의 유찰 상품 목록(LIVE-006). <b>호스트 본인만.</b>
     *
     * <p>마지막 경매가 유찰인 상품만 나온다 — 유찰 뒤 재경매로 팔렸다면 빠진다.
     */
    public List<LiveUnsoldProductResponse> getUnsoldProducts(Long liveId, Long requesterId) {
        requireHost(liveId, requesterId);

        Map<Long, Auction> lastAuctionByProductId = lastFinishedAuctionByProductId(liveId);
        List<Long> unsoldProductIds = linkedProductIds(liveId).stream()
                .filter(productId -> isFailed(lastAuctionByProductId.get(productId)))
                .toList();

        Map<Long, ProductCard> cards = productQueryPort.findCards(unsoldProductIds);

        return unsoldProductIds.stream()
                .map(productId -> {
                    ProductCard card = cards.get(productId);
                    return new LiveUnsoldProductResponse(
                            productId,
                            card == null ? null : card.title(),
                            card == null ? null : card.thumbnailUrl(),
                            lastAuctionByProductId.get(productId).getStartPrice());
                })
                .toList();
    }

    /** 편성 상품 ID를 편성 순서대로. 제외된 연결은 빠진다. */
    private List<Long> linkedProductIds(Long liveId) {
        return liveProductRepository.findByLiveIdAndRemovedAtIsNullOrderBySortOrderAsc(liveId).stream()
                .map(LiveProduct::getProductId)
                .toList();
    }

    /**
     * 상품별 <b>마지막</b> 종료 경매. 질의가 오래된 순으로 주므로 뒤에 오는 것이 앞을 덮어쓴다.
     */
    private Map<Long, Auction> lastFinishedAuctionByProductId(Long liveId) {
        Map<Long, Auction> byProductId = new LinkedHashMap<>();
        auctionRepository.findByLiveIdAndStatusInOrderByIdAsc(liveId, FINISHED)
                .forEach(auction -> byProductId.put(auction.getProductId(), auction));
        return byProductId;
    }

    /**
     * 이 방송에서 정찰가로 팔린 상품 → 주문 금액. 경매를 거친 주문은 빠진다.
     *
     * <p>같은 상품이 여러 번 팔릴 수는 없지만(팔리면 {@code SOLD}가 된다) 방어적으로 첫 건을 쓴다.
     */
    private Map<Long, Long> directSalePriceByProductId(Long liveId) {
        Map<Long, Long> byProductId = new LinkedHashMap<>();
        orderRepository.findLiveDirectSaleOrders(liveId)
                .forEach(order -> byProductId.putIfAbsent(order.getProduct().getId(), order.getOrderPrice()));
        return byProductId;
    }

    /**
     * 상품 하나의 결과. <b>낙찰이 즉시구매보다 우선한다</b> — 둘 다 잡히는 경우는 없어야 하지만,
     * 있다면 경매 쪽이 더 확실한 근거({@code auction.live_id})라 그쪽을 믿는다.
     */
    private LiveBroadcastSummaryResponse.Result toResult(
            Long productId, ProductCard card, Auction auction, Long directSalePrice) {
        String title = card == null ? null : card.title();
        String thumbnailUrl = card == null ? null : card.thumbnailUrl();
        // 편성 시점 상품의 판매 방식·등록가(045) — soldVia/finalPrice(팔린 경로·가격)와는 다른
        // 축이라, 안 팔린 상품에도 채워야 대시보드가 "정찰제인데 안 팔림"을 구분할 수 있다.
        String saleType = card == null ? null : card.saleType();
        Long registeredPrice = card == null ? null : card.price();

        if (auction != null && auction.getStatus() == AuctionStatus.SUCCESS) {
            return LiveBroadcastSummaryResponse.Result.wonAtAuction(
                    productId, title, thumbnailUrl, auction.getFinalPrice(), saleType, registeredPrice);
        }
        if (directSalePrice != null) {
            return LiveBroadcastSummaryResponse.Result.soldDirectly(
                    productId, title, thumbnailUrl, directSalePrice, saleType, registeredPrice);
        }
        // 유찰됐거나, 경매를 아예 걸지 않았거나, 걸었지만 아직 안 끝났다.
        // 셋 다 "이 방송에서 안 팔렸다"이므로 UNSOLD 다 — 대시보드는 방송 전체를 보여 줘야 한다.
        return LiveBroadcastSummaryResponse.Result.unsold(productId, title, thumbnailUrl, saleType, registeredPrice);
    }

    private boolean isFailed(Auction auction) {
        return auction != null && auction.getStatus() == AuctionStatus.FAILED;
    }

    /**
     * 방송 결과는 판매자 본인만 본다 — 판매 실적이라 시청자에게 공개할 정보가 아니다.
     */
    private void requireHost(Long liveId, Long requesterId) {
        Live live = liveRepository.findById(liveId)
                .orElseThrow(() -> new CustomException(ErrorCode.LIVE_NOT_FOUND));
        if (!live.isHostedBy(requesterId)) {
            throw new CustomException(ErrorCode.NOT_LIVE_HOST);
        }
    }
}
