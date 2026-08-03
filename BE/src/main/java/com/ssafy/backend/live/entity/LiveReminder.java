package com.ssafy.backend.live.entity;

import com.ssafy.backend.member.entity.Member;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * 예약 라이브 시작 알림 신청(FE 요청 008 §3.2.1).
 *
 * <p>사용자가 "이 방송 시작하면 알려 줘"를 누르면 한 행이 생긴다. 방송 하나에 회원 하나 —
 * <b>같은 방송에 두 번 신청할 수 없다</b>(unique 제약). 취소는 행을 지운다.
 *
 * <p><b>{@code notifiedAt}이 중복 발송을 막는 유일한 근거다.</b> 스케줄러는 여러 번 돌고
 * 서버가 재기동될 수도 있는데, 이 컬럼이 비어 있는 신청만 대상으로 삼고 발송 직후 채워
 * 같은 트랜잭션에서 커밋한다. 신청 행을 지우는 방식을 쓰지 않는 이유는, 발송 이력이 사라지면
 * 사용자가 알림을 받았는지 확인할 방법이 없어지기 때문이다.
 */
@Entity
@Table(
        name = "live_reminder",
        uniqueConstraints =
                @jakarta.persistence.UniqueConstraint(
                        name = "ux_live_reminder",
                        columnNames = {"live_id", "member_id"}))
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class LiveReminder {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "live_id", nullable = false)
    private Live live;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "member_id", nullable = false)
    private Member member;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    /** 알림을 실제로 만든 시각. null이면 아직 보내지 않았다는 뜻이다. */
    @Column(name = "notified_at")
    private LocalDateTime notifiedAt;

    private LiveReminder(Live live, Member member, LocalDateTime createdAt) {
        this.live = live;
        this.member = member;
        this.createdAt = createdAt;
    }

    public static LiveReminder of(Live live, Member member, LocalDateTime at) {
        return new LiveReminder(live, member, at);
    }

    public void markNotified(LocalDateTime at) {
        this.notifiedAt = at;
    }
}
