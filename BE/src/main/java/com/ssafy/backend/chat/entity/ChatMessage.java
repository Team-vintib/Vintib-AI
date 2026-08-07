package com.ssafy.backend.chat.entity;

import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.member.entity.Member;
import jakarta.persistence.CheckConstraint;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
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
 * 라이브 채팅 메시지(CHAT-001).
 *
 * <p><b>{@code @Builder}를 두지 않고 정적 팩토리만 노출한다.</b> 빌더를 열면
 * "{@code senderType=USER}인데 작성자가 없는" 메시지를 만들 수 있는데, 그건 DB 제약
 * {@code ck_chat_user_has_member}가 거부하는 조합이다. 잘못된 조합을 애초에 만들 수 없게
 * 하는 편이 500을 받아 원인을 추적하는 것보다 낫다.
 *
 * <p><b>{@code BaseTimeEntity}를 상속하지 않는다.</b> 채팅 메시지는 수정되지 않으므로
 * {@code updated_at}이 필요 없고, 상속하면 스키마에 없는 컬럼이 생겨
 * {@code docs/db/schema.sql}과 어긋난다({@code LiveProduct}와 같은 이유).
 *
 * <p>{@code isBlocked}는 금칙어·도배 차단(CHAT-004)용 자리다. AI 게이트웨이(`POST
 * /chat/moderate`)의 HIDE/BLOCK 권고를 받으면 {@link #block()}으로 세운다 — 조회에서
 * 제외하는 규칙은 이미 걸려 있다.
 */
@Entity
@Table(
        name = "chat_message",
        check = {
                @CheckConstraint(
                        name = "ck_chat_sender_type",
                        constraint = "sender_type IN ('USER', 'SYSTEM', 'AI')"),
                // 회원 발언은 작성자가 반드시 있어야 한다. 애플리케이션 검증이 뚫려도 여기서 막힌다.
                @CheckConstraint(
                        name = "ck_chat_user_has_member",
                        constraint = "sender_type <> 'USER' OR member_id IS NOT NULL")
        })
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ChatMessage {

    private static final int MAX_CONTENT_LENGTH = 500;

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "live_id", nullable = false)
    private Live live;

    /** 시스템·AI 메시지는 {@code null}이다. */
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "member_id")
    private Member sender;

    @Enumerated(EnumType.STRING)
    @Column(name = "sender_type", nullable = false, length = 20)
    private SenderType senderType;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String content;

    @Column(name = "is_blocked", nullable = false)
    private boolean blocked;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    private ChatMessage(Live live, Member sender, SenderType senderType, String content, LocalDateTime createdAt) {
        this.live = live;
        this.sender = sender;
        this.senderType = senderType;
        this.content = content;
        this.blocked = false;
        this.createdAt = createdAt;
    }

    /** 회원 발언. 작성자가 없으면 만들 수 없다. */
    public static ChatMessage userMessage(Live live, Member sender, String content, LocalDateTime sentAt) {
        if (sender == null) {
            throw new IllegalArgumentException("회원 발언에는 작성자가 필요합니다.");
        }
        return new ChatMessage(live, sender, SenderType.USER, content, sentAt);
    }

    /** 입장·퇴장·경매 안내 등 서버가 만드는 메시지. 작성자가 없다. */
    public static ChatMessage systemMessage(Live live, String content, LocalDateTime sentAt) {
        return new ChatMessage(live, null, SenderType.SYSTEM, content, sentAt);
    }

    /** 반복질문 자동답변(CHAT-002). 특정 발신자를 지칭하지 않으므로 작성자가 없다. */
    public static ChatMessage aiMessage(Live live, String content, LocalDateTime sentAt) {
        return new ChatMessage(live, null, SenderType.AI, content, sentAt);
    }

    /**
     * 욕설·스팸 판정(CHAT-004)에서 AI 게이트웨이가 HIDE/BLOCK을 권고했을 때 호출한다.
     * 집행 주체는 BE다 — AI는 판정만 한다.
     */
    public void block() {
        this.blocked = true;
    }

    public static boolean isValidContent(String content) {
        if (content == null) {
            return false;
        }
        String trimmed = content.strip();
        return !trimmed.isEmpty() && trimmed.length() <= MAX_CONTENT_LENGTH;
    }

    /**
     * 표시할 작성자명. 온보딩을 완료해야 채팅 등 다른 기능을 쓸 수 있고(SY019 게이트),
     * 온보딩 완료는 닉네임이 있어야만 가능하므로(SY019 순서 보장) 여기 도달한 회원은
     * 항상 닉네임이 채워져 있다.
     */
    public String senderDisplayName() {
        return sender == null ? null : sender.getNickname();
    }
}