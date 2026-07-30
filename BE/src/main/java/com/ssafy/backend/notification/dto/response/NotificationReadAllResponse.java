package com.ssafy.backend.notification.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

public record NotificationReadAllResponse(@Schema(example = "3") long updatedCount) {
}
