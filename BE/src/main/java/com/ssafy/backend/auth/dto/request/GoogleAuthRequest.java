package com.ssafy.backend.auth.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

public record GoogleAuthRequest(

        @Schema(example = "4/0AY0e-g7...")
        @NotBlank
        String code,

        @Schema(example = "https://i15a108.p.ssafy.io/auth/google/callback")
        @NotBlank
        String redirectUri
) {
}
