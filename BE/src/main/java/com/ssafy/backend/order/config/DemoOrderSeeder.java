package com.ssafy.backend.order.config;

import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.auction.repository.AuctionRepository;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.order.entity.CourierCode;
import com.ssafy.backend.order.entity.Order;
import com.ssafy.backend.order.entity.OrderShipment;
import com.ssafy.backend.order.entity.OrderStatus;
import com.ssafy.backend.order.repository.OrderRepository;
import com.ssafy.backend.order.repository.OrderShipmentRepository;
import com.ssafy.backend.product.config.DemoPriorityProducts;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.entity.SaleType;
import com.ssafy.backend.product.repository.ProductRepository;
import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * 마이페이지 구매/판매 내역 데모 시드. 상품 시드(ProductSeeder, {@code @Order(2)})가 끝난 뒤 살
 * 상품이 있어야 하므로 {@code @Order(3)}을 둔다. 배송지는 DemoMemberSeeder({@code @Order(1)})가
 * 채운 회원 정보를 그대로 쓴다.
 *
 * <p><b>OrderService(PointService 결제 포함)를 거치지 않고 엔티티를 직접 구성한다.</b> 상품
 * 시드에 최대 370만 원대 상품도 있어, 실제 결제 흐름({@code PointService.pay})을 태우면 데모
 * 포인트 지급액(100만)을 넘는 상품에서 잔액 부족으로 시드가 실패한다. 목적이 마이페이지
 * 화면을 다양한 상태로 채우는 것이라 포인트 원장 정합성보다 그 목적을 우선한다. 경매 낙찰
 * 데모도 같은 이유로 AUCT 서비스 계층(입찰·마감 스케줄러)을 거치지 않고, 이미 끝난 라이브·
 * 낙찰 경매를 엔티티로 직접 구성해 붙인다.
 *
 * <p><b>개인 계정만 구매자로 삼는다.</b> 사업자 계정(BUSINESS)은 판매 내역만 갖고 구매 내역은
 * 없어야 한다는 운영 정책 — {@link com.ssafy.backend.member.config.DemoMemberSeeder}의
 * {@code GENERAL} 4명만 {@link #BUYER_EMAILS}에 둔다.
 *
 * <p><b>4개 개인 계정이 서로/사업자 계정의 상품을 사도록 얽는다.</b> 후보 상품은 항상 "본인 소유
 * 제외 + 판매 중(또는 경매 예정) + id순"으로만 뽑아 순서대로 배분한다 — 상품 시드가 판매자를
 * 상품마다 돌아가며 배정해뒀기 때문에, 특정 계정에만 거래가 몰리지 않고 자연스럽게 흩어진다.
 * "우선순위 상품"은 {@link DemoPriorityProducts} 참고 — product-seed.sql에서 주석 번호가
 * 남아있는(검수 확정된) 상품이다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
@org.springframework.core.annotation.Order(3)
public class DemoOrderSeeder implements ApplicationRunner {

    private static final List<String> BUYER_EMAILS = List.of(
            "vintib1@gmail.com", "vintib2@gmail.com", "vintib3@gmail.com", "vintib4@gmail.com");

    // 사업자 데모 계정(DemoMemberSeeder의 BUSINESS_USERS). 판매 내역 화면에 "송장 미등록"
    // 상태를 반드시 보여주기 위해 seedOrdersForBuyer와 별도로 최소 1건씩 보강한다.
    private static final List<String> BUSINESS_SELLER_EMAILS =
            List.of("vintibb1@gmail.com", "vintibb2@gmail.com");

    // 구매자 1명당, 상태 버킷 1개당 이 개수만큼 채운다 — 4명 × 4상태 × 1건 = 최대 16건,
    // 즉 구매자 1인당 최대 4건(정찰제·경매 절반씩 섞는다). "각자 3~4개 정도" 요구에 맞춘 값이다.
    private static final int ORDERS_PER_STATUS = 1;

    // 경매 예정 상품 중 정찰제로 돌려 "판매 중" 목록을 채우는 상품 id. 값을 직접 박아 둬야
    // 멱등하다 — 이미 이 id들이 정찰제로 바뀐 뒤엔 AUCTION_SCHEDULED 필터에 안 걸려 다시
    // 손대지 않는다(동적으로 "아무 경매 예정 상품 N개"를 고르면 재기동마다 다른/더 많은 상품이
    // 전환돼 버린다). 전부 우선순위 상품(DemoPriorityProducts)에서만 골랐다 — 비우선 경매 예정
    // 상품은 {@link #auctionWinCandidates}가 낙찰 데모용으로 그대로 써야 한다.
    //
    // <p>우선순위 경매 예정 상품 21개(62~98 범위, id순)에서 <b>한 칸씩 걸러</b> 골랐다 — 앞에서부터
    // 10개를 그대로 뽑으면 남는 11개가 뒤쪽(76~98)에 몰려, 우선순위 상품 목록을 id순으로 볼 때
    // "앞은 전부 정찰제, 뒤 일부만 경매"로 보인다. 하나씩 번갈아 남겨서 정찰제·경매 예정이
    // 고르게 섞이게 한다(62,64,66,71,74,76,78,80,82,90,98이 경매로 남는다).
    private static final Set<Long> AUCTION_TO_DIRECT_SALE_IDS =
            Set.of(63L, 65L, 70L, 73L, 75L, 77L, 79L, 81L, 88L, 92L);

    private final MemberRepository memberRepository;
    private final ProductRepository productRepository;
    private final OrderRepository orderRepository;
    private final OrderShipmentRepository orderShipmentRepository;
    private final LiveRepository liveRepository;
    private final AuctionRepository auctionRepository;

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        convertPriorityAuctionsToDirectSale();
        BUYER_EMAILS.forEach(this::seedOrdersForBuyer);
        BUSINESS_SELLER_EMAILS.forEach(this::ensureUnshippedOrderForSeller);
    }

    /**
     * {@link #AUCTION_TO_DIRECT_SALE_IDS}가 아직 경매 예정이면 정찰제로 돌린다 — "판매 중"
     * 상품이 최소 70개는 넘어야 상품 목록 데모 화면이 허전하지 않고, 경매 예정 상품만으로는
     * 정찰제 즉시구매 후보가 금방 바닥난다.
     */
    private void convertPriorityAuctionsToDirectSale() {
        List<Product> targets = productRepository.findAllById(AUCTION_TO_DIRECT_SALE_IDS).stream()
                .filter(product -> product.getSaleStatus() == SaleStatus.AUCTION_SCHEDULED)
                .toList();
        if (targets.isEmpty()) {
            return;
        }
        for (Product product : targets) {
            product.registerDirectSale(directSalePrice(product));
        }
        productRepository.saveAll(targets);
        log.info("경매 예정 상품 {}건을 정찰제로 전환했다(판매 중 상품 확보).", targets.size());
    }

    private long directSalePrice(Product product) {
        return 50_000L + (product.getId() % 8) * 20_000L;
    }

    /**
     * 한 구매자 기준으로 네 상태(배송지 입력 전 / 거래중(배송중) / 배송완료·확정 대기 / 정산 완료)를
     * 각각 {@link #ORDERS_PER_STATUS}건까지 채운다. 상태별 기존 건수만큼은 건너뛴다(멱등) —
     * 다만 배송완료 버킷은 {@code OrderAutoConfirmScheduler}가 3일 뒤 정산 완료로 넘겨버리므로,
     * 오래 켜둔 서버에서는 재기동할 때마다 조금씩 채워질 수 있다. 데모 목적상 문제 삼지 않는다.
     *
     * <p>채워야 할 슬롯은 홀/짝으로 번갈아 경매 낙찰/정찰제 즉시구매를 섞는다 — 정찰제 후보나
     * 경매 후보 중 한쪽이 먼저 바닥나면 남은 쪽으로 채운다.
     */
    private void seedOrdersForBuyer(String buyerEmail) {
        Member buyer = memberRepository.findByEmail(buyerEmail).orElse(null);
        if (buyer == null) {
            log.warn("주문 시드 대상 회원이 없다: {}", buyerEmail);
            return;
        }

        Map<DemoOrderStage, Integer> neededByStage = new LinkedHashMap<>();
        for (DemoOrderStage stage : DemoOrderStage.values()) {
            long existing = orderRepository.countByBuyer_IdAndStatus(buyer.getId(), stage.countAsStatus());
            neededByStage.put(stage, (int) Math.max(0, ORDERS_PER_STATUS - existing));
        }
        int totalNeeded = neededByStage.values().stream().mapToInt(Integer::intValue).sum();
        if (totalNeeded == 0) {
            return;
        }

        List<Product> directCandidates = directSaleCandidates(buyer.getId());
        List<Product> auctionCandidates = auctionWinCandidates(buyer.getId());
        int directCursor = 0;
        int auctionCursor = 0;
        int slot = 0;
        int seeded = 0;

        for (DemoOrderStage stage : DemoOrderStage.values()) {
            int needed = neededByStage.get(stage);
            for (int i = 0; i < needed; i++, slot++) {
                boolean preferAuction = slot % 2 == 0;
                if (preferAuction && auctionCursor < auctionCandidates.size()) {
                    seedAuctionWinOrder(buyer, auctionCandidates.get(auctionCursor++), stage);
                    seeded++;
                } else if (directCursor < directCandidates.size()) {
                    seedDirectSaleOrder(buyer, directCandidates.get(directCursor++), stage);
                    seeded++;
                } else if (auctionCursor < auctionCandidates.size()) {
                    seedAuctionWinOrder(buyer, auctionCandidates.get(auctionCursor++), stage);
                    seeded++;
                } else {
                    log.warn("주문 시드용 판매 중 상품이 부족하다: {} (필요 {}건 중 {}건만 채움)",
                            buyerEmail, totalNeeded, seeded);
                }
            }
        }
        if (seeded > 0) {
            log.info("시드 주문 생성: {} ({}건)", buyerEmail, seeded);
        }
    }

    /**
     * 사업자 판매자에게 "송장 미등록"(PAID, {@code OrderShipment} 없음) 주문을 최소 1건 보강한다.
     *
     * <p>{@link #seedOrdersForBuyer}가 만드는 NO_ADDRESS 주문은 구매자 기준으로 후보 상품을
     * 순서대로 배분하다 보니, 어느 판매자에게 배정될지가 우연에 맡겨진다 — 사업자 계정 둘 다에
     * 배정된다는 보장이 없다. 판매 내역 화면에서 이 상태를 확인하려면 특정 판매자를 지정해야 하므로
     * 여기서 별도로, 결정적으로 채운다. 멱등 — 그 판매자에게 이미 PAID 주문이 있으면 건너뛴다.
     */
    private void ensureUnshippedOrderForSeller(String sellerEmail) {
        Member seller = memberRepository.findByEmail(sellerEmail).orElse(null);
        if (seller == null) {
            log.warn("판매자 미배송 주문 보강 시드 대상 회원이 없다: {}", sellerEmail);
            return;
        }
        if (orderRepository.existsBySeller_IdAndStatus(seller.getId(), OrderStatus.PAID)) {
            return;
        }

        Product product = productRepository.findAll().stream()
                .filter(p -> p.isOwnedBy(seller.getId()))
                .filter(Product::isAvailableForDirectPurchase)
                .min(Comparator.comparing(Product::getId))
                .orElse(null);
        if (product == null) {
            log.warn("판매자 미배송 주문 보강 시드용 판매 중 상품이 없다: {}", sellerEmail);
            return;
        }

        Member buyer = memberRepository.findByEmail(BUYER_EMAILS.get(0)).orElse(null);
        if (buyer == null) {
            log.warn("판매자 미배송 주문 보강 시드용 구매자가 없다: {}", BUYER_EMAILS.get(0));
            return;
        }

        Order order = orderRepository.save(
                Order.createDirectSale(buyer, seller, product, null, product.getPrice()));
        product.markSold();
        productRepository.save(product);
        log.info("판매자 미배송(송장 미등록) 주문 보강 시드: {} (orderId={}, productId={})",
                sellerEmail, order.getId(), product.getId());
    }

    /** 정찰제 즉시구매 후보 — 본인 소유 제외 + 판매 중, 우선순위 상품 먼저 + id순. */
    private List<Product> directSaleCandidates(Long buyerId) {
        return productRepository.findAll().stream()
                .filter(Product::isAvailableForDirectPurchase)
                .filter(product -> !product.isOwnedBy(buyerId))
                .sorted(Comparator.<Product, Boolean>comparing(
                                product -> !DemoPriorityProducts.IDS.contains(product.getId()))
                        .thenComparing(Product::getId))
                .toList();
    }

    /**
     * 경매 낙찰 후보 — 본인 소유 제외 + 경매 예정, <b>비우선 상품만</b> 쓴다. 우선순위 상품은
     * {@link com.ssafy.backend.live.config.DemoLiveSeeder}가 방송 편성에 쓰므로, 여기서 먼저
     * SOLD로 채가면(낙찰 처리) 그쪽 편성 후보가 줄어든다 — 두 시더가 서로 건드리지 않도록
     * 후보군을 나눈다.
     */
    private List<Product> auctionWinCandidates(Long buyerId) {
        return productRepository.findAll().stream()
                .filter(product -> product.getSaleType() == SaleType.AUCTION)
                .filter(product -> product.getSaleStatus() == SaleStatus.AUCTION_SCHEDULED)
                .filter(product -> !product.isOwnedBy(buyerId))
                .filter(product -> !DemoPriorityProducts.IDS.contains(product.getId()))
                .sorted(Comparator.comparing(Product::getId))
                .toList();
    }

    /** 이 시더가 만드는 네 가지 데모 상태. {@link OrderStatus}와 1:1은 아니다({@code NO_ADDRESS}는 PAID의 부분집합). */
    private enum DemoOrderStage {
        /** 배송지 입력 전 — PAID, {@code OrderShipment} 자체가 없다. */
        NO_ADDRESS(OrderStatus.PAID),
        /** 거래중 — 배송지 등록 + 송장 등록까지 마쳐 배송 중. */
        SHIPPING(OrderStatus.SHIPPING),
        /** 배송완료, 구매확정 대기 — autoConfirmAt이 아직 안 지난 상태로 만든다. */
        DELIVERED(OrderStatus.DELIVERED),
        /** 정산 완료 — 구매확정까지 마쳤다. */
        SETTLED(OrderStatus.SETTLED);

        private final OrderStatus countAsStatus;

        DemoOrderStage(OrderStatus countAsStatus) {
            this.countAsStatus = countAsStatus;
        }

        OrderStatus countAsStatus() {
            return countAsStatus;
        }
    }

    private void seedDirectSaleOrder(Member buyer, Product product, DemoOrderStage stage) {
        Order order = orderRepository.save(
                Order.createDirectSale(buyer, product.getSeller(), product, null, product.getPrice()));
        progressAndMarkSold(buyer, product, order, stage);
    }

    /**
     * 경매 낙찰 구매 데모. 실제 입찰·마감 흐름 없이, 이미 끝난 라이브 + 낙찰 경매를 곧바로
     * SUCCESS 상태로 구성해 붙인다(클래스 상단 주석 참고). 시작가는 낙찰가의 절반, 증액 단위·
     * 진행 시간은 데모용 고정값이다 — 실제로 진행된 적 없는 경매라 의미 있는 값이 없다.
     */
    private void seedAuctionWinOrder(Member buyer, Product product, DemoOrderStage stage) {
        Member seller = product.getSeller();
        LocalDateTime endedAt = LocalDateTime.now().minusDays(20);
        Live live = liveRepository.save(
                Live.openNow(seller, "경매 라이브 다시보기", null, null, endedAt.minusHours(1)));
        live.transitionTo(LiveStatus.ENDED, endedAt);

        long finalPrice = auctionFinalPrice(product);
        Auction auction = Auction.configure(live, product.getId(), finalPrice / 2, 5_000L, 600);
        auction.start(endedAt.minusMinutes(10));
        auction.applyBid(buyer.getId(), finalPrice, endedAt.minusMinutes(5));
        auction.closeAsSuccess(endedAt);
        auctionRepository.save(auction);

        Order order = orderRepository.save(Order.createAuctionWin(buyer, seller, product, auction, finalPrice));
        progressAndMarkSold(buyer, product, order, stage);
    }

    private long auctionFinalPrice(Product product) {
        return 50_000L + (product.getId() % 10) * 15_000L;
    }

    private void progressAndMarkSold(Member buyer, Product product, Order order, DemoOrderStage stage) {
        if (stage != DemoOrderStage.NO_ADDRESS) {
            OrderShipment shipment = OrderShipment.builder()
                    .order(order)
                    .recipientName(buyer.getName())
                    .recipientPhone(buyer.getPhoneNumber())
                    .zipcode(buyer.getPostalCode())
                    .address1(buyer.getAddress())
                    .address2(buyer.getDetailAddress())
                    .build();

            LocalDateTime shippedAt = switch (stage) {
                case SHIPPING -> LocalDateTime.now().minusDays(1);
                case DELIVERED -> LocalDateTime.now().minusDays(4);
                case SETTLED -> LocalDateTime.now().minusDays(10);
                case NO_ADDRESS -> throw new IllegalStateException("unreachable");
            };
            shipment.registerTracking(CourierCode.CJ, generateTrackingNumber(product), shippedAt);
            // 실제 웹훅 구독 여부와 무관하게 true로 고정 — false로 두면 ShipmentFallbackDeliveryScheduler가
            // shippedAt이 이미 과거로 시딩된 이 건을 곧바로 배송완료 처리해버려, SHIPPING 스테이지로
            // 고정해 보여주려던 데모 데이터의 의도가 깨진다.
            shipment.markWebhookSubscribed(true);
            order.markShipping();

            if (stage == DemoOrderStage.DELIVERED || stage == DemoOrderStage.SETTLED) {
                // DELIVERED는 "확정 대기"를 보여줘야 하므로 autoConfirmAt(배송완료+3일)이 아직
                // 지나지 않아야 한다 — 그래야 OrderAutoConfirmScheduler가 다음 주기에 이 주문을
                // 건드리지 않는다. SETTLED는 이미 확정까지 마쳤다는 설정이라 상관없다.
                LocalDateTime deliveredAt = stage == DemoOrderStage.DELIVERED
                        ? LocalDateTime.now().minusDays(1)
                        : LocalDateTime.now().minusDays(7);
                order.markDelivered(deliveredAt);
                shipment.markDelivered(deliveredAt);
            }
            if (stage == DemoOrderStage.SETTLED) {
                order.confirmAndSettle(LocalDateTime.now().minusDays(6));
            }

            orderShipmentRepository.save(shipment);
        }

        product.markSold();
        productRepository.save(product);
    }

    private String generateTrackingNumber(Product product) {
        return "SEED" + product.getId() + (System.nanoTime() % 1_000_000);
    }
}