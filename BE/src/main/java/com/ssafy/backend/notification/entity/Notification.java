package com.ssafy.backend.notification.entity;

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
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "notification")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Notification {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "member_id", nullable = false)
    private Member member;

    @Column(nullable = false, length = 40)
    private String type;

    @Column(nullable = false, length = 200)
    private String title;

    @Column(length = 500)
    private String body;

    // LIVE / AUCTION / ORDER ...
    @Column(name = "ref_type", length = 30)
    private String refType;

    @Column(name = "ref_id")
    private Long refId;

    @Column(name = "is_read", nullable = false)
    private boolean read;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Builder
    private Notification(Member member, String type, String title, String body, String refType, Long refId) {
        this.member = member;
        this.type = type;
        this.title = title;
        this.body = body;
        this.refType = refType;
        this.refId = refId;
        this.read = false;
        this.createdAt = LocalDateTime.now();
    }

    public void markAsRead() {
        this.read = true;
    }
}