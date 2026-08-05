package com.ssafy.backend.order.dto.request;

import com.ssafy.backend.order.entity.CourierCode;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record OrderShipmentRegisterRequest(

        @Schema(example = "CJ", description = "deliveryapi.co.kr이 지원하는 국내 택배사 코드") @NotNull CourierCode courierCode,
        @Schema(example = "123456789012") @NotBlank String trackingNumber) {
}
