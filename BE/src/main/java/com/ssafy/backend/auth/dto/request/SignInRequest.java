package com.ssafy.backend.auth.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;

public record SignInRequest(

        @Schema(example = "vintib1@gmail.com")
        @NotBlank
        @Email
        String email,

        @Schema(example = "qwer1234")
        @NotBlank
        String password
) {
}