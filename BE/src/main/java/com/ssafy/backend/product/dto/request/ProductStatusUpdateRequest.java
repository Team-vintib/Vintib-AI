package com.ssafy.backend.product.dto.request;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

public record ProductStatusUpdateRequest(
        @NotNull @Positive Long price) {
}