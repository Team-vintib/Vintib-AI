package com.ssafy.backend.order.config;

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
import com.ssafy.backend.product.repository.ProductRepository;
import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
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
 * 화면을 다양한 상태로 채우는 것이라 포인트 원장 정합성보다 그 목적을 우선한다.
 *
 * <p><b>6개 데모 계정이 서로의 상품을 사고팔도록 얽는다.</b> 후보 상품은 항상 "본인 소유 제외 +
 * 판매 중 + 우선순위 상품 먼저 + id순"으로만 뽑아 순서대로 배분한다 — 상품 시드가 판매자를
 * 상품마다 돌아가며 배정해뒀기 때문에, 특정 두 계정끼리만 거래가 몰리지 않고 여섯 명 사이에
 * 자연스럽게 흩어진다(별도 매칭 테이블을 만들 필요가 없다). "우선순위 상품"은
 * {@link com.ssafy.backend.product.config.DemoPriorityProducts} 참고 — product-seed.sql에서
 * 주석 번호가 남아있는(검수 확정된) 상품이다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
@org.springframework.core.annotation.Order(3)
public class DemoOrderSeeder implements ApplicationRunner {

    private static final List<String> BUYER_EMAILS = List.of(
            "vintib1@gmail.com", "vintib2@gmail.com", "vintib3@gmail.com",
            "vintib4@gmail.com", "vintibb1@gmail.com", "vintibb2@gmail.com");

    // 구매자 1명당, 상태 버킷 1개당 이 개수만큼 채운다 — 6명 × 4상태 × 2건 = 최대 48건.
    private static final int ORDERS_PER_STATUS = 2;

    private final MemberRepository memberRepository;
    private final ProductRepository productRepository;
    private final OrderRepository orderRepository;
    private final OrderShipmentRepository orderShipmentRepository;

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        BUYER_EMAILS.forEach(this::seedOrdersForBuyer);
    }

    /**
     * 한 구매자 기준으로 네 상태(배송지 입력 전 / 거래중(배송중) / 배송완료·확정 대기 / 정산 완료)를
     * 각각 {@link #ORDERS_PER_STATUS}건까지 채운다. 상태별 기존 건수만큼은 건너뛴다(멱등) —
     * 다만 배송완료 버킷은 {@code OrderAutoConfirmScheduler}가 3일 뒤 정산 완료로 넘겨버리므로,
     * 오래 켜둔 서버에서는 재기동할 때마다 조금씩 채워질 수 있다. 데모 목적상 문제 삼지 않는다.
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

        // 우선순위 상품(DemoPriorityProducts)을 먼저 소진하고, 모자라면 나머지 상품으로 채운다 —
        // 각 그룹 안에서는 id 오름차순.
        List<Product> candidates = productRepository.findAll().stream()
                .filter(Product::isAvailableForDirectPurchase)
                .filter(product -> !product.isOwnedBy(buyer.getId()))
                .sorted(Comparator.<Product, Boolean>comparing(product -> !DemoPriorityProducts.IDS.contains(product.getId()))
                        .thenComparing(Product::getId))
                .limit(totalNeeded)
                .toList();
        if (candidates.size() < totalNeeded) {
            log.warn("주문 시드용 판매 중 상품이 부족하다: {} (필요 {}건, 가용 {}건)",
                    buyerEmail, totalNeeded, candidates.size());
        }

        int cursor = 0;
        for (DemoOrderStage stage : DemoOrderStage.values()) {
            int needed = neededByStage.get(stage);
            for (int i = 0; i < needed && cursor < candidates.size(); i++, cursor++) {
                seedOrder(buyer, candidates.get(cursor), stage);
            }
        }
        if (cursor > 0) {
            log.info("시드 주문 생성: {} ({}건)", buyerEmail, cursor);
        }
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

    private void seedOrder(Member buyer, Product product, DemoOrderStage stage) {
        Order order = orderRepository.save(
                Order.createDirectSale(buyer, product.getSeller(), product, null, product.getPrice()));

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
