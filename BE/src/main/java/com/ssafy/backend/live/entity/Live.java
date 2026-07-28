package com.ssafy.backend.live.entity;

import com.ssafy.backend.global.entity.BaseTimeEntity;
import com.ssafy.backend.member.entity.Member;
import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 라이브 방송 방(Room). 채팅·경매·시착이 모두 이 방에 매달린다.
 *
 * <p>스키마는 {@code docs/db/schema.sql}의 {@code live} 테이블이 단일 기준이다.
 * 예약 개설(LIVE-001)과 즉시 개설(LIVE-002)은 별도 테이블이 아니라 이 엔티티 하나를
 * 상태로 구분한다 — 예약분은 {@code SCHEDULED} + {@code scheduledAt}, 즉시분은
 * {@code LIVE} + {@code startedAt}으로 시작한다.
 */
@Entity
@Table(
        name = "live",
        check =
                @CheckConstraint(
                        name = "ck_live_status",
                        constraint = "status IN ('SCHEDULED', 'LIVE', 'ENDED', 'CANCELED')"))
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Live extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "host_id", nullable = false)
    private Member host;

    @Column(nullable = false, length = 200)
    private String title;

    @Column(name = "thumbnail_url", length = 500)
    private String thumbnailUrl;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private LiveStatus status;

    // 예약 라이브만 값을 갖는다. 즉시 라이브는 null.
    @Column(name = "scheduled_at")
    private LocalDateTime scheduledAt;

    @Column(name = "started_at")
    private LocalDateTime startedAt;

    @Column(name = "ended_at")
    private LocalDateTime endedAt;

    // OpenVidu v3 room name. 방송을 실제로 시작하는 시점에 채워진다(시그널링은 다음 주).
    @Column(name = "openvidu_room", length = 100)
    private String openviduRoom;

    @Column(name = "peak_viewer_count", nullable = false)
    private int peakViewerCount;

    // 개설 경로가 둘(예약/즉시)이고 각각 채워야 할 시각 필드가 다르다. @Builder 로 열어 두면
    // "SCHEDULED 인데 scheduledAt 이 없는" 조합을 만들 수 있어, 생성자는 감추고 정적 팩터리만 연다.
    private Live(
            Member host,
            String title,
            String thumbnailUrl,
            LiveStatus status,
            LocalDateTime scheduledAt,
            LocalDateTime startedAt) {
        this.host = host;
        this.title = title;
        this.thumbnailUrl = thumbnailUrl;
        this.status = status;
        this.scheduledAt = scheduledAt;
        this.startedAt = startedAt;
        this.peakViewerCount = 0;
    }

    /** 예약 개설(LIVE-001). 방송 예정 시각이 미래인지는 서비스에서 검증한다. */
    public static Live schedule(
            Member host, String title, String thumbnailUrl, LocalDateTime scheduledAt) {
        return new Live(host, title, thumbnailUrl, LiveStatus.SCHEDULED, scheduledAt, null);
    }

    /** 즉시 개설(LIVE-002). 예약 없이 곧바로 진행 중 상태로 만들어진다. */
    public static Live openNow(
            Member host, String title, String thumbnailUrl, LocalDateTime startedAt) {
        return new Live(host, title, thumbnailUrl, LiveStatus.LIVE, null, startedAt);
    }

    public boolean isHostedBy(Long memberId) {
        return memberId != null && host.getId().equals(memberId);
    }

    /** 상품 편성을 바꿀 수 있는 상태인지. 종료·취소된 방송은 더 이상 손대지 않는다. */
    public boolean isOpenForEditing() {
        return status == LiveStatus.SCHEDULED || status == LiveStatus.LIVE;
    }
}