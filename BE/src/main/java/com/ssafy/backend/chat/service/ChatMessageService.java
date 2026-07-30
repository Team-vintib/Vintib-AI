package com.ssafy.backend.chat.service;

import com.ssafy.backend.chat.dto.response.ChatMessageResponse;
import com.ssafy.backend.chat.entity.ChatMessage;
import com.ssafy.backend.chat.repository.ChatMessageRepository;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.CursorPageResponse;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.time.LocalDateTime;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 라이브 채팅(CHAT-001). 사람 간 채팅만 다룬다 — AI 채팅 매니저(CHAT-002/003/004)는 보류다.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ChatMessageService {

    private final ChatMessageRepository chatMessageRepository;
    private final LiveRepository liveRepository;
    private final MemberRepository memberRepository;

    /**
     * 회원 발언을 저장한다.
     *
     * @param senderId STOMP principal에서 꺼낸 회원 ID. <b>{@code null}이면 비회원이다.</b>
     */
    @Transactional
    public ChatMessageResponse send(Long senderId, Long liveId, String content, String clientMessageId) {
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

        ChatMessage saved = chatMessageRepository.save(
                ChatMessage.userMessage(live, sender, content.strip(), LocalDateTime.now()));

        return ChatMessageResponse.of(saved, clientMessageId);
    }

    /**
     * 과거 메시지 조회. <b>비회원도 가능하다.</b> 중간에 입장한 시청자가 이전 대화를 볼 수 있어야
     * 하고, WebSocket 은 접속 이후 메시지만 주기 때문에 이력은 REST 로 받는다.
     *
     * @param cursor 이 ID보다 오래된 메시지를 가져온다. 첫 페이지는 {@code null}
     */
    public CursorPageResponse<ChatMessageResponse> getMessages(Long liveId, Long cursor, int size) {
        if (!liveRepository.existsById(liveId)) {
            throw new CustomException(ErrorCode.LIVE_NOT_FOUND);
        }

        // 다음 페이지 유무를 판정하려고 1건 더 가져온다. COUNT 쿼리를 한 번 더 쏘지 않는다.
        List<ChatMessage> found =
                chatMessageRepository.findPageByLiveId(liveId, cursor, PageRequest.of(0, size + 1));

        return CursorPageResponse.of(found, size, ChatMessageResponse::from, ChatMessage::getId);
    }

    private Live findLive(Long liveId) {
        return liveRepository.findById(liveId)
                .orElseThrow(() -> new CustomException(ErrorCode.LIVE_NOT_FOUND));
    }
}