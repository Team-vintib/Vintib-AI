package com.ssafy.backend.notification.repository;

import com.ssafy.backend.notification.entity.Notification;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface NotificationRepository extends JpaRepository<Notification, Long> {

    Page<Notification> findByMember_Id(Long memberId, Pageable pageable);

    Page<Notification> findByMember_IdAndReadFalse(Long memberId, Pageable pageable);

    /** 마이페이지 요약(에픽 S15P11A108-207 보너스) — 안 읽은 알림 수. */
    long countByMember_IdAndReadFalse(Long memberId);

    @Modifying(clearAutomatically = true)
    @Query("UPDATE Notification n SET n.read = true WHERE n.member.id = :memberId AND n.read = false")
    int markAllAsReadByMemberId(@Param("memberId") Long memberId);
}