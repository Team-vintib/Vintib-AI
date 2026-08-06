package com.ssafy.backend.auth.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record GoogleLinkRequest(

        @Schema(example = "3f29b1e2-...")
        @NotBlank
        String linkToken,

        @Schema(example = "true")
        @NotNull
        Boolean confirm
) {
}
