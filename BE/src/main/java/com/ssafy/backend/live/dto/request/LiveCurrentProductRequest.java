package com.ssafy.backend.live.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 지금 소개 중인 상품 변경(LIVE-004).
 *
 * <p><b>{@code productId}에 {@code @NotNull}을 걸지 않는다.</b> {@code null}이 "해제"라는 뜻을
 * 갖기 때문이다 — 호스트가 잡담 구간으로 넘어가면 어떤 상품도 소개하지 않는 상태가 된다.
 * 필수로 막으면 한번 지정한 뒤에는 되돌릴 방법이 없어진다.
 */
public record LiveCurrentProductRequest(

        @Schema(
                description = "소개할 상품 ID. **이 방송에 편성된 상품이어야 한다.** "
                        + "null이면 소개 중인 상품을 해제한다",
                example = "2001")
        Long productId) {
}
