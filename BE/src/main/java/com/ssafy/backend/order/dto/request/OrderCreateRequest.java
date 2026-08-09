package com.ssafy.backend.order.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

public record OrderCreateRequest(

        @Schema(description = "구매할 상품 ID(정찰제/ON_SALE 상태만 가능)", example = "10")
        @NotNull
        Long productId,

        @Schema(
                description = "라이브 시청 화면에서 구매한 경우 그 방송 ID. **라이브 밖에서 사면 생략한다.** "
                        + "이 값을 보내야 방송 종료 요약(`GET /api/lives/{liveId}/summary`)의 판매 실적에 "
                        + "잡힌다 — 주문만 봐서는 어느 방송에서 팔렸는지 알 수 없다",
                example = "101")
        Long liveId) {
}