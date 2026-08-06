package com.ssafy.backend.order.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

public record OrderShipmentAddressRequest(

        @Schema(example = "홍길동") @NotBlank String recipientName,
        @Schema(example = "010-1234-5678") @NotBlank String recipientPhone,
        @Schema(example = "06134") @NotBlank String zipcode,
        @Schema(example = "서울특별시 강남구 테헤란로 1") @NotBlank String address1,
        @Schema(example = "101동 1001호") String address2) {
}