package com.ssafy.backend.notification.repository;

import com.ssafy.backend.notification.entity.Notification;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface NotificationRepository extends JpaRepository<Notification, Long> {

    Page<Notification> findByMember_Id(Long memberId, Pageable pageable);

    Page<Notification> findByMember_IdAndReadFalse(Long memberId, Pageable pageable);
}