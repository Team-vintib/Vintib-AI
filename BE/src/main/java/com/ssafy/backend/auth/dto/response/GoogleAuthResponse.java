package com.ssafy.backend.auth.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * status에 따라 채워지는 필드가 다르다.
 * - LOGIN: accessToken/refreshToken/onboardingCompleted
 * - LINK_REQUIRED: linkToken/email (이미 가입된 이메일이라 연동 확인이 필요함)
 * - LINK_DECLINED: 연동을 거부했다는 사실만 알려준다(추가 필드 없음)
 */
public record GoogleAuthResponse(

        @Schema(example = "LOGIN")
        String status,

        @Schema(example = "eyJhbGciOiJIUzI1NiJ9...")
        String accessToken,

        @Schema(example = "eyJhbGciOiJIUzI1NiJ9...")
        String refreshToken,

        @Schema(description = "로그인한 회원 id", example = "1")
        Long id,

        @Schema(example = "false")
        Boolean onboardingCompleted,

        @Schema(example = "3f29b1e2-...")
        String linkToken,

        @Schema(example = "vintib1@gmail.com")
        String email
) {

    public static GoogleAuthResponse login(TokenResponse tokens, boolean onboardingCompleted) {
        return new GoogleAuthResponse(
                "LOGIN", tokens.accessToken(), tokens.refreshToken(), tokens.id(), onboardingCompleted, null, null);
    }

    public static GoogleAuthResponse linkRequired(String linkToken, String email) {
        return new GoogleAuthResponse("LINK_REQUIRED", null, null, null, null, linkToken, email);
    }

    public static GoogleAuthResponse linkDeclined() {
        return new GoogleAuthResponse("LINK_DECLINED", null, null, null, null, null, null);
    }
}
