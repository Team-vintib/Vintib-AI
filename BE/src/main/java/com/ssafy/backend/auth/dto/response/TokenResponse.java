package com.ssafy.backend.auth.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

public record TokenResponse(

        @Schema(example = "eyJhbGciOiJIUzI1NiJ9...")
        String accessToken,

        @Schema(example = "eyJhbGciOiJIUzI1NiJ9...")
        String refreshToken,

        @Schema(description = "로그인한 회원 id. FE가 JWT를 직접 디코딩하지 않고 "
                + "GET /api/users/{id}를 바로 호출할 수 있게 함께 내려준다.", example = "1")
        Long id
) {
}