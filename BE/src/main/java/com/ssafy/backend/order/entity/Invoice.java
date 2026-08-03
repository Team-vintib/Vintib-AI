package com.ssafy.backend.order.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * 세금계산서(BIZ-002). 법적 문서라 발행 시점 판매자 사업자 정보를 스냅샷으로 저장한다 —
 * 이후 판매자가 {@code business_info}를 바꿔도 이미 발행된 계산서는 바뀌지 않는다.
 * 주문당 1건만 허용한다({@code uq_invoice_order}) — 취소/재발행은 범위 밖.
 */
@Entity
@Table(name = "invoice")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Invoice {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "order_id", nullable = false, unique = true)
    private Order order;

    @Column(name = "business_number", nullable = false, length = 20)
    private String businessNumber;

    @Column(name = "business_name", nullable = false, length = 100)
    private String businessName;

    @Column(name = "representative_name", nullable = false, length = 50)
    private String representativeName;

    @Column(name = "supply_amount", nullable = false)
    private Long supplyAmount;

    @Column(name = "tax_amount", nullable = false)
    private Long taxAmount;

    @Column(name = "total_amount", nullable = false)
    private Long totalAmount;

    @Column(name = "issued_at", nullable = false)
    private LocalDateTime issuedAt;

    @Builder
    private Invoice(
            Order order, String businessNumber, String businessName, String representativeName,
            Long supplyAmount, Long taxAmount, Long totalAmount) {
        this.order = order;
        this.businessNumber = businessNumber;
        this.businessName = businessName;
        this.representativeName = representativeName;
        this.supplyAmount = supplyAmount;
        this.taxAmount = taxAmount;
        this.totalAmount = totalAmount;
        this.issuedAt = LocalDateTime.now();
    }

    /** 주문 금액을 기준으로 부가세 10%를 역산해 발행한다(공급가액 = 주문금액 / 1.1, 원단위 반올림). */
    public static Invoice issue(Order order, String businessNumber, String businessName, String representativeName) {
        long orderPrice = order.getOrderPrice();
        long supplyAmount = Math.round(orderPrice / 1.1);
        long taxAmount = orderPrice - supplyAmount;
        return Invoice.builder()
                .order(order)
                .businessNumber(businessNumber)
                .businessName(businessName)
                .representativeName(representativeName)
                .supplyAmount(supplyAmount)
                .taxAmount(taxAmount)
                .totalAmount(orderPrice)
                .build();
    }
}
