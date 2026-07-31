package com.ssafy.backend.member.entity;

import com.ssafy.backend.product.entity.Category;
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
@Table(name = "member_interest_category")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class MemberInterestCategory {

    @EmbeddedId
    private MemberInterestCategoryId id;

    @MapsId("memberId")
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "member_id", nullable = false)
    private Member member;

    @MapsId("categoryId")
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "category_id", nullable = false)
    private Category category;

    @Builder
    private MemberInterestCategory(Member member, Category category) {
        this.member = member;
        this.category = category;
        this.id = new MemberInterestCategoryId(member.getId(), category.getId());
    }
}
