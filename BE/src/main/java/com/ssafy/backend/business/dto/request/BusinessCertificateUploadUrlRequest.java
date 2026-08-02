package com.ssafy.backend.business.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

public record BusinessCertificateUploadUrlRequest(

        @Schema(example = "image/jpeg")
        @NotBlank
        String contentType) {
}
