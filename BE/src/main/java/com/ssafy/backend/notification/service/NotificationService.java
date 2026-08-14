package com.ssafy.backend.notification.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.notification.dto.response.NotificationItemResponse;
import com.ssafy.backend.notification.dto.response.NotificationReadAllResponse;
import com.ssafy.backend.notification.dto.response.NotificationResponse;
import com.ssafy.backend.notification.dto.response.NotificationUnreadCountResponse;
import com.ssafy.backend.notification.entity.Notification;
import com.ssafy.backend.notification.entity.NotificationCategory;
import com.ssafy.backend.notification.repository.NotificationRepository;
import java.util.Set;
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

    public PageResponse<NotificationItemResponse> getNotifications(
            Long memberId, boolean unreadOnly, NotificationCategory category, Pageable pageable) {
        // 알림함은 '안 읽은 것 먼저'가 기본 조회다(schema.sql ix_notification_member 인덱스 주석 근거).
        // 클라이언트가 다른 sort를 보내도 무시한다 — ProductQueryService.getProductList와 동일한 정책.
        Pageable sorted = PageRequest.of(
                pageable.getPageNumber(),
                pageable.getPageSize(),
                Sort.by(Sort.Order.asc("read"), Sort.Order.desc("createdAt")));

        Page<Notification> notifications = findByCategory(memberId, unreadOnly, category, sorted);
        return PageResponse.from(notifications.map(NotificationItemResponse::of));
    }

    // category가 null이면 기존 동작 그대로 전체 조회. TRADE(catch-all)는 NOT IN, 나머지는 IN으로 나뉜다
    private Page<Notification> findByCategory(
            Long memberId, boolean unreadOnly, NotificationCategory category, Pageable sorted) {
        if (category == null) {
            return unreadOnly
                    ? notificationRepository.findByMember_IdAndReadFalse(memberId, sorted)
                    : notificationRepository.findByMember_Id(memberId, sorted);
        }
        if (category.isCatchAll()) {
            Set<String> excluded = NotificationCategory.excludedTypesForCatchAll();
            return unreadOnly
                    ? notificationRepository.findByMember_IdAndReadFalseAndTypeNotIn(memberId, excluded, sorted)
                    : notificationRepository.findByMember_IdAndTypeNotIn(memberId, excluded, sorted);
        }
        Set<String> types = category.types();
        return unreadOnly
                ? notificationRepository.findByMember_IdAndReadFalseAndTypeIn(memberId, types, sorted)
                : notificationRepository.findByMember_IdAndTypeIn(memberId, types, sorted);
    }

    // 대상이 0건이어도 에러 없이 처리한다(빈 알림함에 눌러도 정상 동작).
    @Transactional
    public NotificationReadAllResponse markAllAsRead(Long memberId, NotificationCategory category) {
        int updatedCount;
        if (category == null) {
            updatedCount = notificationRepository.markAllAsReadByMemberId(memberId);
        } else if (category.isCatchAll()) {
            updatedCount = notificationRepository.markAllAsReadByMemberIdAndTypeNotIn(
                    memberId, NotificationCategory.excludedTypesForCatchAll());
        } else {
            updatedCount = notificationRepository.markAllAsReadByMemberIdAndTypeIn(memberId, category.types());
        }
        return new NotificationReadAllResponse(updatedCount);
    }

    public NotificationUnreadCountResponse getUnreadCount(Long memberId, NotificationCategory category) {
        long unreadCount;
        if (category == null) {
            unreadCount = notificationRepository.countByMember_IdAndReadFalse(memberId);
        } else if (category.isCatchAll()) {
            unreadCount = notificationRepository.countByMember_IdAndReadFalseAndTypeNotIn(
                    memberId, NotificationCategory.excludedTypesForCatchAll());
        } else {
            unreadCount = notificationRepository.countByMember_IdAndReadFalseAndTypeIn(memberId, category.types());
        }
        return new NotificationUnreadCountResponse(unreadCount);
    }
}