package com.ssafy.backend.business.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

public record BusinessInfoSubmitRequest(

        @Schema(example = "1234567890")
        @NotBlank
        @Pattern(regexp = "\\d{10}", message = "사업자등록번호는 숫자 10자리여야 합니다.")
        String businessNumber,

        @Schema(example = "빈티브 상회")
        @NotBlank
        String businessName,

        @Schema(example = "홍길동")
        @NotBlank
        String representativeName,

        @Schema(example = "business-certificates/1/abc123.jpg")
        @NotBlank
        String certificateKey) {
}
