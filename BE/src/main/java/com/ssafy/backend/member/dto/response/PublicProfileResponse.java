package com.ssafy.backend.member.dto.response;

import com.ssafy.backend.member.entity.Member;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 공개 회원/판매자 프로필(011 §3.3) — 다른 사용자가 상품 상세 판매자, 검색 회원, 라이브 호스트
 * 정보를 볼 때 쓴다. 비회원도 조회 가능하며, 본인 전용 조회(MY-001, {@code GET /users/{id}})와
 * 달리 전화번호 등 민감정보는 담지 않는다.
 */
public record PublicProfileResponse(
        @Schema(example = "10") Long id,
        @Schema(example = "seller") String nickname,
        String profileImageUrl,
        @Schema(description = "소개글", example = "빈티지 셀러입니다.") String description,
        @Schema(description = "커버 이미지 URL") String coverImageUrl,
        @Schema(example = "124") long followerCount,
        @Schema(example = "20") long followingCount,
        @Schema(example = "8") long productCount,
        @Schema(example = "3") long liveCount,
        @Schema(description = "조회자 기준 팔로우 여부. 비회원이면 항상 false", example = "false") boolean isFollowing,
        @Schema(description = "사업자 인증 승인 여부", example = "true") boolean businessVerified) {

    public static PublicProfileResponse of(
            Member member,
            long followerCount,
            long followingCount,
            long productCount,
            long liveCount,
            boolean isFollowing,
            boolean businessVerified) {
        return new PublicProfileResponse(
                member.getId(),
                member.getNickname(),
                member.getProfileImageUrl(),
                member.getDescription(),
                member.getCoverImageUrl(),
                followerCount,
                followingCount,
                productCount,
                liveCount,
                isFollowing,
                businessVerified);
    }
}
