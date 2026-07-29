package com.ssafy.backend.wish.dto.request;

import jakarta.validation.constraints.NotNull;

public record WishCreateRequest(@NotNull Long productId) {
}
