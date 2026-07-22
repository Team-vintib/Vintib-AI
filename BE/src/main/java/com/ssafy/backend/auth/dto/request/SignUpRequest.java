package com.ssafy.backend.auth.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record SignUpRequest(

        @Schema(example = "user@example.com")
        @NotBlank
        @Email
        String email,

        @Schema(example = "password12!")
        @NotBlank
        @Pattern(
                regexp = "^(?=.*[A-Za-z])(?=.*\\d)[A-Za-z\\d!@#$%^&*()_+=-]{8,20}$",
                message = "비밀번호는 영문과 숫자를 포함해 8~20자로 입력해주세요."
        )
        String password,

        @Schema(example = "홍길동")
        @NotBlank
        @Size(max = 30)
        String name,

        @Schema(example = "3fa85f64-5717-4562-b3fc-2c963f66afa6")
        @NotBlank
        String verificationToken
) {
}