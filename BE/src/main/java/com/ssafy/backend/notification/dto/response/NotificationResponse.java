package com.ssafy.backend.notification.dto.response;

import com.ssafy.backend.notification.entity.Notification;
import io.swagger.v3.oas.annotations.media.Schema;

public record NotificationResponse(
        @Schema(example = "1") Long id,
        @Schema(example = "true") boolean isRead) {

    public static NotificationResponse of(Notification notification) {
        return new NotificationResponse(notification.getId(), notification.isRead());
    }
}