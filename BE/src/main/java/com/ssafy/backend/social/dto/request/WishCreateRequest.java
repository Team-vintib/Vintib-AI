package com.ssafy.backend.social.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

public record WishCreateRequest(
        @Schema(example = "1") @NotNull Long productId) {
}
