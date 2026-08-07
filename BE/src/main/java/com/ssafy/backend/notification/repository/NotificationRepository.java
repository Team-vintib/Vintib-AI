package com.ssafy.backend.notification.repository;

import com.ssafy.backend.notification.entity.Notification;
import java.util.Collection;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface NotificationRepository extends JpaRepository<Notification, Long> {

    Page<Notification> findByMember_Id(Long memberId, Pageable pageable);

    Page<Notification> findByMember_IdAndReadFalse(Long memberId, Pageable pageable);

    // category 필터(IN) — NotificationCategory.LIVE/AUCTION/SHIPPING/POINT용.
    Page<Notification> findByMember_IdAndTypeIn(Long memberId, Collection<String> types, Pageable pageable);

    Page<Notification> findByMember_IdAndReadFalseAndTypeIn(
            Long memberId, Collection<String> types, Pageable pageable);

    // category=TRADE(catch-all) 필터(NOT IN) — NotificationCategory.excludedTypesForCatchAll() 참고.
    Page<Notification> findByMember_IdAndTypeNotIn(Long memberId, Collection<String> types, Pageable pageable);

    Page<Notification> findByMember_IdAndReadFalseAndTypeNotIn(
            Long memberId, Collection<String> types, Pageable pageable);

    /** 안 읽은 알림 수. */
    long countByMember_IdAndReadFalse(Long memberId);

    long countByMember_IdAndReadFalseAndTypeIn(Long memberId, Collection<String> types);

    long countByMember_IdAndReadFalseAndTypeNotIn(Long memberId, Collection<String> types);

    @Modifying(clearAutomatically = true)
    @Query("UPDATE Notification n SET n.read = true WHERE n.member.id = :memberId AND n.read = false")
    int markAllAsReadByMemberId(@Param("memberId") Long memberId);

    @Modifying(clearAutomatically = true)
    @Query("UPDATE Notification n SET n.read = true WHERE n.member.id = :memberId AND n.read = false AND n.type IN :types")
    int markAllAsReadByMemberIdAndTypeIn(@Param("memberId") Long memberId, @Param("types") Collection<String> types);

    @Modifying(clearAutomatically = true)
    @Query("UPDATE Notification n SET n.read = true WHERE n.member.id = :memberId AND n.read = false AND n.type NOT IN :types")
    int markAllAsReadByMemberIdAndTypeNotIn(
            @Param("memberId") Long memberId, @Param("types") Collection<String> types);
}