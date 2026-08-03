package com.ssafy.backend.live.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Future;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 예약 라이브 개설(LIVE-001) 요청.
 *
 * <p>방송 예정 시각은 미래여야 한다. 요청 검증 단계에서 {@code @Future}로 거르므로
 * 서비스는 "과거 시각으로 예약된 방"을 만나지 않는다.
 */
public record LiveScheduleRequest(

        @Schema(description = "방송명", example = "빈티지 데님 라이브", maxLength = 200)
        @NotBlank
        @Size(max = 200)
        String title,

        @Schema(description = "썸네일 URL", example = "https://cdn.example.com/live/1.jpg", maxLength = 500)
        @Size(max = 500)
        String thumbnailUrl,

        @Schema(
                description = "방송 설명. **선택**이며 없으면 null",
                example = "90년대 리바이스·랭글러 위주로 소개합니다",
                maxLength = 1000)
        @Size(max = 1000)
        String description,

        @Schema(
                description = "방송 예정 시각. 반드시 미래여야 한다. **오프셋 없는 KST 벽시계로 보낸다** "
                        + "(서버도 KST 로 돌아간다)",
                example = "2026-08-01T20:00:00")
        @NotNull
        @Future
        LocalDateTime scheduledAt,

        @Schema(
                description = "판매할 상품 ID 목록. **개설 시점에 정하며 최소 1개가 필요하다.** "
                        + "미리 등록해 둔 본인 상품 중에서 고른다",
                example = "[2001, 2002]")
        @NotEmpty
        List<Long> productIds
) {
}