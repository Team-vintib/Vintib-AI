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

    @Modifying(clearAutomatically = true)
    @Query("UPDATE Notification n SET n.read = true WHERE n.member.id = :memberId AND n.read = false")
    int markAllAsReadByMemberId(@Param("memberId") Long memberId);
}