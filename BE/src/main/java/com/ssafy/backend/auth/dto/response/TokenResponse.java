package com.ssafy.backend.auth.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

public record TokenResponse(

        @Schema(example = "eyJhbGciOiJIUzI1NiJ9...")
        String accessToken,

        @Schema(example = "eyJhbGciOiJIUzI1NiJ9...")
        String refreshToken
) {
}