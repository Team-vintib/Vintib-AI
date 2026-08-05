package com.ssafy.backend.live.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;
import java.util.List;

/**
 * 즉시 라이브 개설(LIVE-002) 요청.
 *
 * <p>예약과 달리 방송 시각을 받지 않는다 — 개설 즉시 시작이므로 시작 시각은 서버가 정한다.
 * 판매할 상품은 예약과 마찬가지로 개설 시점에 함께 정한다.
 */
public record LiveInstantRequest(

        @Schema(description = "방송명", example = "지금 바로 여는 빈티지 라이브", maxLength = 200)
        @NotBlank
        @Size(max = 200)
        String title,

        @Schema(description = "썸네일 URL", example = "https://cdn.example.com/live/2.jpg", maxLength = 500)
        @Size(max = 500)
        String thumbnailUrl,

        @Schema(
                description = "방송 설명. **선택**이며 없으면 null",
                example = "지금 막 들어온 물건들 바로 보여드립니다",
                maxLength = 1000)
        @Size(max = 1000)
        String description,

        @Schema(
                description = "판매할 상품 ID 목록. **개설 시점에 정하며 최소 1개가 필요하다.** "
                        + "즉시 개설은 곧바로 방송이 시작돼 이후 편성을 바꿀 수 없다",
                example = "[2001, 2002]")
        @NotEmpty
        List<Long> productIds
) {
}