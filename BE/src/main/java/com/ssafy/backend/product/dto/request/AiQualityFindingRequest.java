package com.ssafy.backend.product.dto.request;

import com.ssafy.backend.product.entity.ProductImageRole;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

/**
 * 등록 시 사용자가 "하자로 인정"하고 확정한 AI 품질 검수 finding 1건
 * (042-product-registration-ai-pipeline.md §3).
 */
public record AiQualityFindingRequest(

        @Schema(description = "이 finding이 속한 사진. FRONT/BACK만 허용", example = "FRONT")
        @NotNull
        ProductImageRole photoRole,

        @Schema(example = "소매 끝단 마모 의심")
        @NotBlank
        String description,

        @Schema(description = "사진 프레임 기준 % 좌표(0~100). 없으면 생략 가능")
        @Valid
        Box box) {

    public record Box(
            @Schema(example = "58") @NotNull Integer x,
            @Schema(example = "18") @NotNull Integer y,
            @Schema(example = "24") @NotNull Integer width,
            @Schema(example = "18") @NotNull Integer height) {
    }
}
