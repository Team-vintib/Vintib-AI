package com.ssafy.backend.social.dto.response;

import com.ssafy.backend.member.entity.Member;
import io.swagger.v3.oas.annotations.media.Schema;

public record FollowUserResponse(
        @Schema(example = "10") Long id,
        @Schema(example = "seller") String nickname,
        @Schema(example = "https://cdn.example.com/profile/10.jpg") String profileImageUrl,
        @Schema(example = "124") long followerCount,
        @Schema(example = "8") long productCount,
        @Schema(description = "조회자 기준 팔로우 여부. 비회원 조회면 false", example = "true") boolean isFollowing) {

    public static FollowUserResponse of(
            Member member, long followerCount, long productCount, boolean isFollowing) {
        return new FollowUserResponse(
                member.getId(),
                member.getNickname(),
                member.getProfileImageUrl(),
                followerCount,
                productCount,
                isFollowing);
    }
}
