package com.ssafy.backend.notification.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

public record NotificationUnreadCountResponse(@Schema(example = "4") long unreadCount) {
}
