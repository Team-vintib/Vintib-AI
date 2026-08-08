package com.ssafy.backend.product.entity;

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
import java.util.Map;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/**
 * AI 품질 검수에서 사용자가 확정(인정)한 하자 1건(SY043). {@code ProductDefect}(판매자가 직접
 * 입력한 하자)와 별개다 — 이건 등록 시 {@code POST /products}의 {@code aiQualityFindings}로
 * 받은, AI가 탐지하고 사용자가 "하자로 인정"한 항목만 저장한다
 * (042-product-registration-ai-pipeline.md §3).
 *
 * <p>AI 원본 스키마(041-quality-inspection-integration.md §2)는 {@code key}/{@code defect_type}/
 * {@code label}/{@code confidence} 등 훨씬 많은 필드를 갖지만, 등록 시점에 FE가 실제로 넘기는
 * 값은 {@code photoRole}/{@code description}/{@code box}뿐이라(042 §3) 그 세 개만 저장한다 —
 * 나머지는 BE가 받지도 않는 값이라 채울 수 없다.
 */
@Entity
@Table(name = "product_quality_finding")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ProductQualityFinding {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "product_id", nullable = false)
    private Product product;

    // FRONT/BACK만 의미가 있다 — ADDITIONAL 사진은 품질 검수 대상이 아니다.
    @Enumerated(EnumType.STRING)
    @Column(name = "photo_role", nullable = false, length = 20)
    private ProductImageRole photoRole;

    @Column(columnDefinition = "TEXT", nullable = false)
    private String description;

    // 검수 이미지 위 탐지 위치, 프레임 기준 % 좌표 {x, y, width, height}. 없으면 null
    // (사용자가 위치 없이 텍스트만 인정한 경우).
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private Map<String, Integer> box;

    @Column(name = "sort_order", nullable = false)
    private Short sortOrder;

    @Builder
    private ProductQualityFinding(
            Product product,
            ProductImageRole photoRole,
            String description,
            Map<String, Integer> box,
            Short sortOrder) {
        this.product = product;
        this.photoRole = photoRole;
        this.description = description;
        this.box = box;
        this.sortOrder = sortOrder;
    }
}
