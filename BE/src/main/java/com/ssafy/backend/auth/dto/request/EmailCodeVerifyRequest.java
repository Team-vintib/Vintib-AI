package com.ssafy.backend.auth.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

public record EmailCodeVerifyRequest(

        @Schema(example = "user@example.com")
        @NotBlank
        @Email
        String email,

        @Schema(example = "123456")
        @NotBlank
        @Pattern(regexp = "^\\d{6}$", message = "인증 코드는 숫자 6자리입니다.")
        String code
) {
}