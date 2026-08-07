package com.ssafy.backend.chat.service;

import com.ssafy.backend.chat.dto.response.ChatMessageBlockedNotice;
import com.ssafy.backend.chat.dto.response.ChatMessageResponse;
import com.ssafy.backend.chat.dto.response.ChatSendOutcome;
import com.ssafy.backend.chat.entity.ChatMessage;
import com.ssafy.backend.chat.entity.SenderType;
import com.ssafy.backend.chat.repository.ChatMessageRepository;
import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.client.dto.ChatAnswer;
import com.ssafy.backend.global.client.dto.ModerateChatResponse;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.CursorPageResponse;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestClientException;

/**
 * 라이브 채팅(CHAT-001) + AI 욕설/스팸 판정(CHAT-004)·반복질문 감지(CHAT-002 트리거).
 * 반복질문 답변 자체는 {@code ChatAnswerPollingScheduler}가 비동기로 채워 넣는다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ChatMessageService {

    private final ChatMessageRepository chatMessageRepository;
    private final LiveRepository liveRepository;
    private final MemberRepository memberRepository;
    private final AiClient aiClient;

    /**
     * 회원 발언을 저장한다. AI 판정에서 HIDE/BLOCK/TIMED_OUT을 권고하면 메시지는 저장은
     * 되지만(관리용 흔적) 발신자 전용 알림만 돌려준다 — 호출부(STOMP 컨트롤러)는 이때
     * 브로드캐스트를 생략한다.
     *
     * @param senderId STOMP principal에서 꺼낸 회원 ID. <b>{@code null}이면 비회원이다.</b>
     */
    @Transactional
    public ChatSendOutcome send(Long senderId, Long liveId, String content, String clientMessageId) {
        // 비회원은 읽기만 가능하다. DB 의 ck_chat_user_has_member 가 최후 방어선이지만, 거기까지
        // 가면 500 이 되므로 여기서 401 로 돌려준다.
        if (senderId == null) {
            throw new CustomException(ErrorCode.CHAT_GUEST_NOT_ALLOWED);
        }
        if (!ChatMessage.isValidContent(content)) {
            throw new CustomException(ErrorCode.CHAT_CONTENT_INVALID);
        }

        Live live = findLive(liveId);
        // 끝난 방송에는 쓸 수 없다. 읽기는 계속 허용한다 — 다시보기로 대화를 볼 수 있어야 한다.
        if (live.isClosed()) {
            throw new CustomException(ErrorCode.INVALID_LIVE_STATE);
        }

        Member sender = memberRepository.findById(senderId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

        LocalDateTime sentAt = LocalDateTime.now();
        String trimmed = content.strip();
        ChatMessage saved = chatMessageRepository.save(
                ChatMessage.userMessage(live, sender, trimmed, sentAt));

        ModerationOutcome moderation = moderateAndBlockIfNeeded(saved, senderId, trimmed, sentAt);
        if (moderation.blocked()) {
            ChatMessageBlockedNotice notice = moderation.muteRemainingSeconds() != null
                    ? ChatMessageBlockedNotice.muted(clientMessageId, moderation.muteRemainingSeconds())
                    : ChatMessageBlockedNotice.blocked(clientMessageId);
            return ChatSendOutcome.blocked(notice);
        }

        return ChatSendOutcome.broadcast(ChatMessageResponse.of(saved, clientMessageId));
    }

    /**
     * AI 게이트웨이에 동기 판정을 요청한다(-571). 실패해도(타임아웃 등) 판정 없이 통과시킨다 —
     * 채팅은 AI 장애와 무관하게 동작해야 하는 핵심 기능이라 보조 기능 실패로 막으면 안 된다.
     */
    private ModerationOutcome moderateAndBlockIfNeeded(
            ChatMessage message, Long userId, String content, LocalDateTime sentAt) {
        try {
            ModerateChatResponse moderation = aiClient.moderateChatMessage(
                    message.getLive().getId(), message.getId(), userId, content, sentAt);
            if (moderation.isBlocked()) {
                message.block();
                log.info("채팅 메시지 차단(messageId={}, reason={})", message.getId(), moderation.reason());
                return ModerationOutcome.blocked(moderation.muteRemainingSeconds());
            }
            return ModerationOutcome.passed();
        } catch (RestClientException e) {
            log.warn("채팅 AI 판정 실패, 판정 없이 통과시킴(messageId={}): {}", message.getId(), e.getMessage());
            return ModerationOutcome.passed();
        }
    }

    /** AI 판정 결과 중 컨트롤러가 알 필요가 있는 것만 추린 내부 표현. */
    private record ModerationOutcome(boolean blocked, Double muteRemainingSeconds) {
        static ModerationOutcome passed() {
            return new ModerationOutcome(false, null);
        }

        static ModerationOutcome blocked(Double muteRemainingSeconds) {
            return new ModerationOutcome(true, muteRemainingSeconds);
        }
    }

    /**
     * 과거 메시지 조회. <b>비회원도 가능하다.</b> 중간에 입장한 시청자가 이전 대화를 볼 수 있어야
     * 하고, WebSocket 은 접속 이후 메시지만 주기 때문에 이력은 REST 로 받는다.
     *
     * <p>방향이 둘이다. <b>위로 스크롤</b>은 {@code cursor}(더 오래된 것, 최신순), <b>재접속 후
     * 끊긴 구간 메우기</b>는 {@code after}(더 새로운 것, 오래된 순)를 쓴다.
     *
     * @param cursor 이 ID보다 오래된 메시지. 첫 페이지는 {@code null}
     * @param after  이 ID보다 새로운 메시지. {@code cursor}와 함께 줄 수 없다
     */
    public CursorPageResponse<ChatMessageResponse> getMessages(
            Long liveId, Long cursor, Long after, int size) {
        // 두 방향을 동시에 요청하면 어느 쪽을 의도한 것인지 알 수 없다. 임의로 하나를 고르면
        // FE 는 왜 예상과 다른 결과가 오는지 알 수 없으므로 400 으로 돌려준다.
        if (cursor != null && after != null) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
        if (!liveRepository.existsById(liveId)) {
            throw new CustomException(ErrorCode.LIVE_NOT_FOUND);
        }

        // 다음 페이지 유무를 판정하려고 1건 더 가져온다. COUNT 쿼리를 한 번 더 쏘지 않는다.
        PageRequest pageRequest = PageRequest.of(0, size + 1);
        List<ChatMessage> found = after != null
                ? chatMessageRepository.findPageAfterByLiveId(liveId, after, pageRequest)
                : chatMessageRepository.findPageByLiveId(liveId, cursor, pageRequest);

        return CursorPageResponse.of(found, size, ChatMessageResponse::from, ChatMessage::getId);
    }

    private Live findLive(Long liveId) {
        return liveRepository.findById(liveId)
                .orElseThrow(() -> new CustomException(ErrorCode.LIVE_NOT_FOUND));
    }

    /**
     * 반복질문 자동답변 폴링(-571)이 AI에 물어볼 {@code since} 커서. 아직 이 방송에 AI 메시지가
     * 하나도 없으면 방송 시작 시각부터 조회한다.
     */
    public LocalDateTime lastAiAnswerCursor(Long liveId) {
        return chatMessageRepository
                .findTopByLive_IdAndSenderTypeOrderByCreatedAtDesc(liveId, SenderType.AI)
                .map(ChatMessage::getCreatedAt)
                .orElseGet(() -> findLive(liveId).getStartedAt());
    }

    /**
     * AI가 생성한 반복질문 답변들을 {@code sender_type=AI} 메시지로 저장한다. AI 게이트웨이
     * 호출(네트워크 I/O)은 호출부(스케줄러)가 트랜잭션 밖에서 먼저 끝내고, 여기는 순수 DB
     * 쓰기만 한다.
     */
    @Transactional
    public List<ChatMessageResponse> saveAiAnswers(Long liveId, List<ChatAnswer> answers) {
        Live live = findLive(liveId);
        return answers.stream()
                .map(answer -> chatMessageRepository.save(ChatMessage.aiMessage(
                        live,
                        answer.answer(),
                        // Instant(절대 시각) -> 이 서버 타임존(KST) 벽시계로 변환한다. 나머지
                        // chat_message.created_at이 전부 KST LocalDateTime.now()라, 여기만
                        // 다른 기준으로 저장하면 다음 폴링 커서(lastAiAnswerCursor)가 어긋난다.
                        LocalDateTime.ofInstant(answer.createdAt(), ZoneId.systemDefault()))))
                .map(ChatMessageResponse::from)
                .toList();
    }
}