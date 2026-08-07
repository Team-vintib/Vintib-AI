package com.ssafy.backend.notification.port;

import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.notification.entity.Notification;
import com.ssafy.backend.notification.repository.NotificationRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

/** {@link NotificationCommandPort}의 유일한 구현. 알림 도메인에 대한 의존을 이 파일 하나로 묶는다. */
@Component
@RequiredArgsConstructor
public class NotificationCommandAdapter implements NotificationCommandPort {

    private final NotificationRepository notificationRepository;

    @Override
    public void notify(
            Member member, String type, String title, String body, String refType, Long refId) {
        notificationRepository.save(Notification.builder()
                .member(member)
                .type(type)
                .title(title)
                .body(body)
                .refType(refType)
                .refId(refId)
                .build());
    }
}