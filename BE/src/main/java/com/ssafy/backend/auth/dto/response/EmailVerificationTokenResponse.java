package com.ssafy.backend.auth.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

public record EmailVerificationTokenResponse(

        @Schema(example = "3fa85f64-5717-4562-b3fc-2c963f66afa6")
        String verificationToken
) {
}