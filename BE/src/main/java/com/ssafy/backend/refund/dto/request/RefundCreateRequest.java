package com.ssafy.backend.refund.dto.request;

import com.ssafy.backend.refund.entity.RefundReason;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record RefundCreateRequest(

        @Schema(example = "UNDISCLOSED_DEFECT") @NotNull RefundReason reason,
        @Schema(example = "소매 부분에 미고지된 얼룩이 있습니다.") @NotBlank String detailReason) {
}