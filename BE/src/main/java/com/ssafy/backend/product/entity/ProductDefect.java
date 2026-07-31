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
@Table(name = "product_defect")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ProductDefect {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "product_id", nullable = false)
    private Product product;

    @Column(columnDefinition = "TEXT", nullable = false)
    private String content;

    @Column(name = "sort_order", nullable = false)
    private Short sortOrder;

    @Builder
    private ProductDefect(Product product, String content, Short sortOrder) {
        this.product = product;
        this.content = content;
        this.sortOrder = sortOrder;
    }
}
