package com.ssafy.backend.product.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "product_image")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ProductImage {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "product_id", nullable = false)
    private Product product;

    @Column(name = "image_key", nullable = false, length = 500)
    private String imageKey;

    @Column(name = "sort_order", nullable = false)
    private Short sortOrder;

    @Column(name = "is_primary", nullable = false)
    private boolean primary;

    @Builder
    private ProductImage(Product product, String imageKey, Short sortOrder, boolean primary) {
        this.product = product;
        this.imageKey = imageKey;
        this.sortOrder = sortOrder;
        this.primary = primary;
    }

    public boolean belongsTo(Long productId) {
        return productId != null && product.getId().equals(productId);
    }
}