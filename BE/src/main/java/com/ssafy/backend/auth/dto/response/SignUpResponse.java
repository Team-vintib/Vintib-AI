package com.ssafy.backend.auth.dto.response;

import com.ssafy.backend.member.entity.Member;
import io.swagger.v3.oas.annotations.media.Schema;

public record SignUpResponse(

        @Schema(example = "1")
        Long id,

        @Schema(example = "user@example.com")
        String email,

        @Schema(example = "홍길동")
        String name,

        @Schema(example = "false")
        boolean onboardingCompleted
) {

    public static SignUpResponse from(Member member) {
        return new SignUpResponse(member.getId(), member.getEmail(), member.getName(), member.isOnboardingCompleted());
    }
}