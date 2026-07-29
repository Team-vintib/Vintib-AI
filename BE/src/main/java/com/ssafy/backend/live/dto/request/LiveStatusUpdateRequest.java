package com.ssafy.backend.live.dto.request;

import com.ssafy.backend.live.entity.LiveStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

/**
 * 방송 상태 전이 요청.
 *
 * <p>전이할 목표 상태만 받는다. 허용되는 전이는 예정→진행, 예정→취소, 진행→종료 세 가지이며
 * 판정은 {@link LiveStatus#canTransitionTo}가 한다.
 */
public record LiveStatusUpdateRequest(

        @Schema(
                description = "전이할 방송 상태",
                example = "LIVE",
                allowableValues = {"LIVE", "ENDED", "CANCELED"})
        @NotNull
        LiveStatus status
) {
}