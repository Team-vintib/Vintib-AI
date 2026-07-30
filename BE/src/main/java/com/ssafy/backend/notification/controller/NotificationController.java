package com.ssafy.backend.notification.controller;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.notification.dto.response.NotificationItemResponse;
import com.ssafy.backend.notification.dto.response.NotificationReadAllResponse;
import com.ssafy.backend.notification.dto.response.NotificationResponse;
import com.ssafy.backend.notification.service.NotificationService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

// 경로는 APIs.md "알림(Notifications)" 섹션의 `/users/{id}/alerts`, `/users/{userId}/alerts/read-all`,
// `/users/{userId}/alerts/{id}` 스펙을 그대로 따른다.
@Tag(name = "알림(Notifications)", description = "알림함 조회/읽음 처리 API")
@RestController
@RequestMapping("/api/users/{userId}/alerts")
@RequiredArgsConstructor
public class NotificationController {

    private final NotificationService notificationService;

    @Operation(
            summary = "알림 목록 조회",
            description = "알림함을 조회한다. 정렬은 항상 '읽지 않음 우선 → 최신순'으로 고정되며, "
                    + "sort 파라미터를 보내도 무시된다. unreadOnly=true면 읽지 않은 알림만 조회한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 알림함을 조회하려 함")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<NotificationItemResponse>>> getNotifications(
            Authentication authentication,
            @PathVariable Long userId,
            @RequestParam(defaultValue = "false") boolean unreadOnly,
            @PageableDefault(size = 20) Pageable pageable) {
        requireSelf(authentication, userId);
        PageResponse<NotificationItemResponse> response =
                notificationService.getNotifications(userId, unreadOnly, pageable);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(
            summary = "알림 전체 읽음 처리",
            description = "본인의 읽지 않은 알림을 모두 읽음 처리한다. 대상이 없어도 에러 없이 처리된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "읽음 처리 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 알림함을 처리하려 함")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PatchMapping("/read-all")
    public ResponseEntity<ApiResponse<NotificationReadAllResponse>> markAllAsRead(
            Authentication authentication, @PathVariable Long userId) {
        requireSelf(authentication, userId);
        NotificationReadAllResponse response = notificationService.markAllAsRead(userId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(summary = "알림 읽음 처리", description = "알림 한 건을 읽음 처리한다. 이미 읽은 알림도 에러 없이 처리된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "읽음 처리 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 알림을 처리하려 함"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않거나 본인 소유가 아닌 알림임")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PatchMapping("/{id}")
    public ResponseEntity<ApiResponse<NotificationResponse>> markAsRead(
            Authentication authentication, @PathVariable Long userId, @PathVariable Long id) {
        requireSelf(authentication, userId);
        NotificationResponse response = notificationService.markAsRead(userId, id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    // path의 userId가 인증된 본인이 아니면 존재 자체를 드러내지 않고 403으로 막는다(IDOR 방지) — WishController와 동일한 패턴.
    private void requireSelf(Authentication authentication, Long userId) {
        Long memberId = (Long) authentication.getPrincipal();
        if (!memberId.equals(userId)) {
            throw new CustomException(ErrorCode.NOTIFICATION_FORBIDDEN);
        }
    }
}