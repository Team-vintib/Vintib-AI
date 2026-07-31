package com.ssafy.backend.member.entity;

import com.ssafy.backend.product.entity.Brand;
import jakarta.persistence.EmbeddedId;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.MapsId;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "member_interest_brand")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class MemberInterestBrand {

    @EmbeddedId
    private MemberInterestBrandId id;

    @MapsId("memberId")
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "member_id", nullable = false)
    private Member member;

    @MapsId("brandId")
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "brand_id", nullable = false)
    private Brand brand;

    @Builder
    private MemberInterestBrand(Member member, Brand brand) {
        this.member = member;
        this.brand = brand;
        this.id = new MemberInterestBrandId(member.getId(), brand.getId());
    }
}
