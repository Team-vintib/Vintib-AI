package com.ssafy.backend.order.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

public record OrderShipmentRegisterRequest(

        @Schema(example = "CJ대한통운") @NotBlank String courier,
        @Schema(example = "123456789012") @NotBlank String trackingNumber) {
}
