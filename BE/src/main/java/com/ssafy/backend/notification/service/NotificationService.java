package com.ssafy.backend.notification.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.notification.dto.response.NotificationItemResponse;
import com.ssafy.backend.notification.dto.response.NotificationResponse;
import com.ssafy.backend.notification.entity.Notification;
import com.ssafy.backend.notification.repository.NotificationRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class NotificationService {

    private final NotificationRepository notificationRepository;

    // 이미 읽은 알림을 다시 읽음 처리해도 에러 없이 멱등하게 처리한다.
    @Transactional
    public NotificationResponse markAsRead(Long memberId, Long notificationId) {
        Notification notification = notificationRepository.findById(notificationId)
                .filter(n -> n.getMember().getId().equals(memberId))
                .orElseThrow(() -> new CustomException(ErrorCode.NOTIFICATION_NOT_FOUND));

        notification.markAsRead();
        return NotificationResponse.of(notification);
    }

    public PageResponse<NotificationItemResponse> getNotifications(Long memberId, boolean unreadOnly, Pageable pageable) {
        // 알림함은 '안 읽은 것 먼저'가 기본 조회다(schema.sql ix_notification_member 인덱스 주석 근거).
        // 클라이언트가 다른 sort를 보내도 무시한다 — ProductService.getProductList와 동일한 정책.
        Pageable sorted = PageRequest.of(
                pageable.getPageNumber(),
                pageable.getPageSize(),
                Sort.by(Sort.Order.asc("read"), Sort.Order.desc("createdAt")));

        Page<Notification> notifications = unreadOnly
                ? notificationRepository.findByMember_IdAndReadFalse(memberId, sorted)
                : notificationRepository.findByMember_Id(memberId, sorted);

        return PageResponse.from(notifications.map(NotificationItemResponse::of));
    }
}