package com.ssafy.backend.order.config;

import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.order.entity.CourierCode;
import com.ssafy.backend.order.entity.Order;
import com.ssafy.backend.order.entity.OrderShipment;
import com.ssafy.backend.order.repository.OrderRepository;
import com.ssafy.backend.order.repository.OrderShipmentRepository;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.ProductRepository;
import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

// 마이페이지 구매 내역 데모 시드. 상품 시드(ProductSeeder, @Order(2))가 끝난 뒤 살 상품이 있어야
// 하므로 @Order(3)을 둔다. 배송지는 DemoMemberSeeder(@Order(1))가 채운 회원 정보를 그대로 쓴다.
//
// OrderService(PointService 결제 포함)를 거치지 않고 엔티티를 직접 구성한다 — 상품 시드 중
// 가장 싼 3개를 합쳐도 118,500원으로 데모 포인트 기본 지급액(10만)을 넘어, 실제 결제 흐름을
// 태우면 잔액 부족으로 시드가 실패한다. 목적이 마이페이지 주문 목록·배송 상태 화면을 채우는
// 것이라 포인트 잔액과의 정합성보다 그 목적을 우선한다.
@Slf4j
@Component
@RequiredArgsConstructor
@org.springframework.core.annotation.Order(3)
public class DemoOrderSeeder implements ApplicationRunner {

    private final MemberRepository memberRepository;
    private final ProductRepository productRepository;
    private final OrderRepository orderRepository;
    private final OrderShipmentRepository orderShipmentRepository;

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        seedOrders("vintib1@gmail.com", 3, false);
        seedOrders("vintib2@gmail.com", 2, true);
    }

    /** 배송 예정(PAID + 배송지 등록) 또는 배송 완료(DELIVERED) 주문을 부족한 수만큼 채운다(멱등). */
    private void seedOrders(String buyerEmail, int targetCount, boolean delivered) {
        Member buyer = memberRepository.findByEmail(buyerEmail).orElse(null);
        if (buyer == null) {
            log.warn("주문 시드 대상 회원이 없다: {}", buyerEmail);
            return;
        }
        long existing = orderRepository.countByBuyer_Id(buyer.getId());
        int needed = (int) (targetCount - existing);
        if (needed <= 0) {
            return;
        }

        List<Product> candidates = productRepository.findAll().stream()
                .filter(Product::isAvailableForDirectPurchase)
                .filter(product -> !product.isOwnedBy(buyer.getId()))
                .sorted(Comparator.comparing(Product::getId))
                .limit(needed)
                .toList();
        if (candidates.size() < needed) {
            log.warn("주문 시드용 판매 중 상품이 부족하다: {} (필요 {}건, 가용 {}건)",
                    buyerEmail, needed, candidates.size());
        }

        log.info("시드 주문 생성: {} ({}건, {})", buyerEmail, candidates.size(), delivered ? "배송완료" : "배송예정");
        candidates.forEach(product -> seedOrder(buyer, product, delivered));
    }

    private void seedOrder(Member buyer, Product product, boolean delivered) {
        Order order = Order.createDirectSale(buyer, product.getSeller(), product, null, product.getPrice());
        LocalDateTime shippedAt = LocalDateTime.now().minusDays(2);
        LocalDateTime deliveredAt = LocalDateTime.now().minusDays(1);
        if (delivered) {
            order.markShipping();
            order.markDelivered(deliveredAt);
        }
        order = orderRepository.save(order);

        OrderShipment shipment = OrderShipment.builder()
                .order(order)
                .recipientName(buyer.getName())
                .recipientPhone(buyer.getPhoneNumber())
                .zipcode(buyer.getPostalCode())
                .address1(buyer.getAddress())
                .address2(buyer.getDetailAddress())
                .build();
        if (delivered) {
            shipment.registerTracking(CourierCode.CJ, generateTrackingNumber(product), shippedAt);
            shipment.markDelivered(deliveredAt);
        }
        orderShipmentRepository.save(shipment);

        product.markSold();
        productRepository.save(product);
    }

    private String generateTrackingNumber(Product product) {
        return "SEED" + product.getId() + (System.nanoTime() % 1_000_000);
    }
}
