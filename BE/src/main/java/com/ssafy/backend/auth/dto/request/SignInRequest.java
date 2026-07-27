package com.ssafy.backend.auth.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;

public record SignInRequest(

        @Schema(example = "user@example.com")
        @NotBlank
        @Email
        String email,

        @Schema(example = "password12!")
        @NotBlank
        String password
) {
}