package com.ssafy.backend.point.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

public record WithdrawalAccountRequest(

        @Schema(example = "국민은행") @NotBlank String bankName,
        @Schema(example = "123456-78-901234") @NotBlank String accountNumber,
        @Schema(example = "홍길동") @NotBlank String accountHolderName) {
}
