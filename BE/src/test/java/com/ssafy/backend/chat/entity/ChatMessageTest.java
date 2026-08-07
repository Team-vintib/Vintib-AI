package com.ssafy.backend.chat.entity;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.member.entity.Member;
import java.time.LocalDateTime;
import org.junit.jupiter.api.Test;

/**
 * {@link ChatMessage} 단위 테스트(-451). DB 없이 정적 팩토리의 불변식만 본다.
 */
class ChatMessageTest {

    private static final LocalDateTime NOW = LocalDateTime.of(2026, 7, 30, 14, 0);

    private Live 라이브() {
        return Live.openNow(회원("호스트", "빈티지장인"), "빈티지 데님 라이브", null, null, NOW);
    }

    private Member 회원(String name, String nickname) {
        Member member = Member.builder()
                .email("chat-" + name + "@example.com")
                .password("encoded")
                .name(name)
                .build();
        if (nickname != null) {
            org.springframework.test.util.ReflectionTestUtils.setField(member, "nickname", nickname);
        }
        return member;
    }

    @Test
    void 회원_발언은_USER_타입으로_생성된다() {
        ChatMessage message = ChatMessage.userMessage(라이브(), 회원("시청자", "덕후"), "사이즈 M 맞나요?", NOW);

        assertThat(message.getSenderType()).isEqualTo(SenderType.USER);
        assertThat(message.getSender()).isNotNull();
        assertThat(message.isBlocked()).isFalse();
        assertThat(message.getCreatedAt()).isEqualTo(NOW);
    }

    @Test
    void 작성자_없는_회원_발언은_만들_수_없다() {
        // DB 의 ck_chat_user_has_member 와 같은 규칙을 코드에서도 막는다. 여기서 못 막으면
        // 저장 시점에 제약 위반이 500 으로 새어 나간다.
        assertThatThrownBy(() -> ChatMessage.userMessage(라이브(), null, "내용", NOW))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void 시스템_메시지는_작성자가_없다() {
        ChatMessage message = ChatMessage.systemMessage(라이브(), "경매가 시작되었습니다.", NOW);

        assertThat(message.getSenderType()).isEqualTo(SenderType.SYSTEM);
        assertThat(message.getSender()).isNull();
        assertThat(message.senderDisplayName()).isNull();
    }

    @Test
    void 닉네임이_없으면_표시명도_없다() {
        // SY019: 온보딩(닉네임 저장 포함)을 완료해야 채팅 자체를 쓸 수 있는 게이트가 있어
        // 실제로는 도달하지 않는 상태지만, 엔티티 메서드 자체는 있는 그대로 null을 돌려준다
        // (이름으로 대체하던 우회는 게이트 도입으로 제거함).
        ChatMessage message = ChatMessage.userMessage(라이브(), 회원("김정윤", null), "내용", NOW);

        assertThat(message.senderDisplayName()).isNull();
    }

    @Test
    void 닉네임이_있으면_닉네임으로_표시한다() {
        ChatMessage message = ChatMessage.userMessage(라이브(), 회원("김정윤", "빈티지장인"), "내용", NOW);

        assertThat(message.senderDisplayName()).isEqualTo("빈티지장인");
    }

    @Test
    void AI_메시지는_작성자가_없다() {
        ChatMessage message = ChatMessage.aiMessage(라이브(), "네, 프리사이즈이며 신축성이 좋습니다.", NOW);

        assertThat(message.getSenderType()).isEqualTo(SenderType.AI);
        assertThat(message.getSender()).isNull();
        assertThat(message.isBlocked()).isFalse();
    }

    @Test
    void block_호출하면_차단_상태가_된다() {
        ChatMessage message = ChatMessage.userMessage(라이브(), 회원("시청자", "덕후"), "욕설성 발언", NOW);

        message.block();

        assertThat(message.isBlocked()).isTrue();
    }

    @Test
    void 빈_내용과_공백만_있는_내용은_거부된다() {
        assertThat(ChatMessage.isValidContent(null)).isFalse();
        assertThat(ChatMessage.isValidContent("")).isFalse();
        assertThat(ChatMessage.isValidContent("   ")).isFalse();
    }

    @Test
    void 최대_길이_경계를_지킨다() {
        assertThat(ChatMessage.isValidContent("가".repeat(500))).isTrue();
        assertThat(ChatMessage.isValidContent("가".repeat(501))).isFalse();
        // 앞뒤 공백은 길이 계산에서 빠진다 — 공백으로 한도를 넘기려는 입력을 막지 않기 위함이 아니라,
        // 저장 시에도 strip 한 값이 들어가므로 판정 기준을 같게 맞추는 것이다.
        assertThat(ChatMessage.isValidContent("  " + "가".repeat(500) + "  ")).isTrue();
    }
}