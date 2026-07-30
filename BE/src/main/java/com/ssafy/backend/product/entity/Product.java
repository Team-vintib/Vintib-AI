package com.ssafy.backend.product.entity;

import com.ssafy.backend.global.entity.BaseTimeEntity;
import com.ssafy.backend.member.entity.Member;
import jakarta.persistence.CheckConstraint;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
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
import org.hibernate.annotations.SQLRestriction;

@Entity
@Table(
        name = "product",
        check = {
                @CheckConstraint(
                        name = "ck_product_sale_type",
                        constraint = "sale_type IN ('DIRECT_SALE', 'AUCTION')"),
                @CheckConstraint(
                        name = "ck_product_sale_status",
                        constraint = "sale_status IN ("
                                + "'DRAFT', 'ON_SALE', 'AUCTION_SCHEDULED', 'AUCTION_IN_PROGRESS', "
                                + "'AUCTION_FAILED', 'SOLD', 'PRIVATE')"),
                @CheckConstraint(
                        name = "ck_product_price_by_type",
                        constraint = "sale_type <> 'DIRECT_SALE' OR price IS NOT NULL")
        })
@SQLRestriction("deleted_at IS NULL")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Product extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "seller_id", nullable = false)
    private Member seller;

    // 카테고리는 필수다. 미분류 상품은 검색·필터에서 누락되고, 라이브 카테고리(편성 상품에서
    // 유도)도 만들 수 없다.
    @Column(name = "category_id", nullable = false)
    private Long categoryId;

    @Column(name = "brand_id")
    private Long brandId;

    @Column(nullable = false, length = 200)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String description;

    // 중고 상태 등급 체계 미확정 — 자유 문자열 (docs/db/erd.md 확인 필요 가정 #3)
    @Column(name = "condition_grade", length = 20)
    private String conditionGrade;

    @Column(name = "size_label", length = 50)
    private String sizeLabel;

    // 판매 채널(상시 판매/경매)은 이번 단계에서 정하지 않는다 — 판매 가격 설정 또는
    // 경매 조건 설정 API를 호출하는 시점에 비로소 결정된다.
    @Enumerated(EnumType.STRING)
    @Column(name = "sale_type", length = 20)
    private SaleType saleType;

    @Enumerated(EnumType.STRING)
    @Column(name = "sale_status", nullable = false, length = 30)
    private SaleStatus saleStatus;

    private Long price;

    @Column(name = "deleted_at")
    private LocalDateTime deletedAt;

    @Builder
    private Product(
            Member seller,
            Long categoryId,
            Long brandId,
            String title,
            String description,
            String conditionGrade,
            String sizeLabel) {
        this.seller = seller;
        this.categoryId = categoryId;
        this.brandId = brandId;
        this.title = title;
        this.description = description;
        this.conditionGrade = conditionGrade;
        this.sizeLabel = sizeLabel;
        this.saleStatus = SaleStatus.DRAFT;
    }

    public void registerDirectSale(Long price) {
        this.saleType = SaleType.DIRECT_SALE;
        this.price = price;
        this.saleStatus = SaleStatus.ON_SALE;
    }

    public void update(
            String title,
            String description,
            Long categoryId,
            Long brandId,
            String conditionGrade,
            String sizeLabel) {
        if (title != null) {
            this.title = title;
        }
        if (description != null) {
            this.description = description;
        }
        if (categoryId != null) {
            this.categoryId = categoryId;
        }
        if (brandId != null) {
            this.brandId = brandId;
        }
        if (conditionGrade != null) {
            this.conditionGrade = conditionGrade;
        }
        if (sizeLabel != null) {
            this.sizeLabel = sizeLabel;
        }
    }

    public void softDelete() {
        this.deletedAt = LocalDateTime.now();
    }

    public boolean isOwnedBy(Long memberId) {
        return memberId != null && seller.getId().equals(memberId);
    }

    public boolean isPrivate() {
        return saleStatus == SaleStatus.DRAFT || saleStatus == SaleStatus.PRIVATE;
    }

    public boolean isDeleted() {
        return deletedAt != null;
    }

    public boolean isEditable() {
        return saleStatus == SaleStatus.DRAFT
                || saleStatus == SaleStatus.ON_SALE
                || saleStatus == SaleStatus.PRIVATE;
    }
}