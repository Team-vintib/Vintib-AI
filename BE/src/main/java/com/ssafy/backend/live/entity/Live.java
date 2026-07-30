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

    /**
     * 상품 편성을 바꿀 수 있는 상태인지.
     *
     * <p><b>방송이 시작되면 편성을 바꿀 수 없다</b>(운영 정책) — 시청자가 보고 있는 판매 목록이
     * 도중에 바뀌면 안 되고, 라이브 카테고리도 편성에서 유도하므로 함께 흔들린다.
     * 따라서 예약 상태에서만 허용한다. 즉시 개설 방송은 생성 시점에 이미 진행 중이라
     * 개설 요청에 담아 보낸 편성이 그대로 확정된다.
     */
    public boolean isOpenForEditing() {
        return status == LiveStatus.SCHEDULED;
    }

    /**
     * 방송이 끝났는지(종료 또는 취소). 편성 변경과 달리 <b>경매 조건 설정처럼 방송 중에도
     * 허용해야 하는 작업</b>은 이 판정을 쓴다 — 경매를 거는 것은 편성을 바꾸는 것이 아니다.
     */
    public boolean isClosed() {
        return status == LiveStatus.ENDED || status == LiveStatus.CANCELED;
    }

    public boolean canTransitionTo(LiveStatus target) {
        return status.canTransitionTo(target);
    }

    /**
     * 방송 상태를 전이시킨다. 전이 가능 여부는 {@link #canTransitionTo}로 미리 확인해야 한다
     * — 여기서 다시 막지 않는 이유는 "왜 안 되는지"를 예외 코드로 구분해 돌려주는 책임이
     * 서비스에 있기 때문이다.
     *
     * <p>상태에 따라 함께 박히는 시각이 다르다. 시각은 클라이언트 값이 아니라 서버 시각을 받는다
     * — 경매 종료 판정이 서버 시각 기준이라 시간 축이 둘로 갈리면 안 된다(erd.md §6).
     */
    public void transitionTo(LiveStatus target, LocalDateTime at) {
        this.status = target;
        switch (target) {
            case LIVE -> this.startedAt = at;
            case ENDED -> this.endedAt = at;
            default -> {
                // SCHEDULED·CANCELED 는 별도로 박을 시각이 없다.
            }
        }
    }

    /** 방송을 실제로 시작하는 시점에 OpenVidu room 이름을 채운다(연동은 -449). */
    public void assignOpenviduRoom(String openviduRoom) {
        this.openviduRoom = openviduRoom;
    }
}