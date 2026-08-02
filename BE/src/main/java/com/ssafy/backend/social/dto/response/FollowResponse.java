package com.ssafy.backend.social.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

public record FollowResponse(
        @Schema(example = "10") Long targetUserId,
        @Schema(example = "true") boolean isFollowing,
        @Schema(example = "124") long followerCount) {
}
