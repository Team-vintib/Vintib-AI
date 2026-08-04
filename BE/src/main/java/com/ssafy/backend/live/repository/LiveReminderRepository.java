package com.ssafy.backend.live.repository;

import com.ssafy.backend.live.entity.LiveReminder;
import com.ssafy.backend.live.entity.LiveStatus;
import java.time.LocalDateTime;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface LiveReminderRepository extends JpaRepository<LiveReminder, Long> {

    Optional<LiveReminder> findByLive_IdAndMember_Id(Long liveId, Long memberId);

    boolean existsByLive_IdAndMember_Id(Long liveId, Long memberId);

    /**
     * 지금 보내야 할 알림 신청.
     *
     * <p>대상은 두 가지다 — <b>예정 시각이 코앞으로 온 방송</b>과 <b>호스트가 이미 시작해 버린
     * 방송</b>. 예정 시각만 보면 호스트가 일찍 시작했을 때 알림이 늦고, 상태만 보면 "시작 전에
     * 미리 알려 달라"는 요구를 못 채운다.
     *
     * <p>{@code notifiedAt IS NULL}이 중복 발송을 막는다. 종료·취소된 방송은 대상이 아니다 —
     * 이미 끝난 방송을 "곧 시작합니다"로 알릴 수는 없다.
     *
     * <p>{@code live}·{@code member}를 함께 당겨 온다. 알림 본문에 방송명이, 수신자로 회원이
     * 필요해 지연 로딩으로 두면 신청 수만큼 질의가 나간다.
     */
    @EntityGraph(attributePaths = {"live", "member"})
    @Query("""
            SELECT r FROM LiveReminder r
            WHERE r.notifiedAt IS NULL
              AND r.live.status IN :statuses
              AND (r.live.status = com.ssafy.backend.live.entity.LiveStatus.LIVE
                   OR r.live.scheduledAt <= :threshold)
            ORDER BY r.id ASC
            """)
    List<LiveReminder> findDue(
            @Param("statuses") Collection<LiveStatus> statuses,
            @Param("threshold") LocalDateTime threshold,
            Pageable pageable);
}
