package com.ssafy.backend.member.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

public record MemberImageUploadUrlResponse(
        @Schema(example = "member-profiles/1/abc123.jpg") String key,
        @Schema(example = "https://s3.example.com/member-profiles/1/abc123.jpg?X-Amz-...") String uploadUrl,
        @Schema(example = "300") long expiresInSeconds) {
}
