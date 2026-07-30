package com.ssafy.backend.notification.dto.response;

import com.ssafy.backend.notification.entity.Notification;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

public record NotificationItemResponse(
        @Schema(example = "1") Long id,
        @Schema(example = "AUCTION_WON") String type,
        @Schema(example = "낙찰되었습니다") String title,
        @Schema(example = "빈티지 자켓 경매에서 낙찰되었습니다.") String body,
        @Schema(example = "AUCTION") String refType,
        @Schema(example = "10") Long refId,
        @Schema(example = "false") boolean isRead,
        @Schema(example = "2026-07-29T12:00:00") LocalDateTime createdAt) {

    public static NotificationItemResponse of(Notification notification) {
        return new NotificationItemResponse(
                notification.getId(),
                notification.getType(),
                notification.getTitle(),
                notification.getBody(),
                notification.getRefType(),
                notification.getRefId(),
                notification.isRead(),
                notification.getCreatedAt());
    }
}