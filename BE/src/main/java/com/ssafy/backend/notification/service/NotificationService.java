package com.ssafy.backend.notification.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.notification.dto.response.NotificationResponse;
import com.ssafy.backend.notification.entity.Notification;
import com.ssafy.backend.notification.repository.NotificationRepository;
import lombok.RequiredArgsConstructor;
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
}