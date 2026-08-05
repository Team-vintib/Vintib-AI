package com.ssafy.backend.social.entity;

import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.product.entity.Product;
import jakarta.persistence.Column;
import jakarta.persistence.EmbeddedId;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.MapsId;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "wish")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Wish {

    @EmbeddedId
    private WishId id;

    @MapsId("memberId")
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "member_id", nullable = false)
    private Member member;

    @MapsId("productId")
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "product_id", nullable = false)
    private Product product;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Builder
    private Wish(Member member, Product product) {
        this.member = member;
        this.product = product;
        this.id = new WishId(member.getId(), product.getId());
        this.createdAt = LocalDateTime.now();
    }
}
