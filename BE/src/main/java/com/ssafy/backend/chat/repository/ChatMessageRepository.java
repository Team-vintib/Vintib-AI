package com.ssafy.backend.chat.repository;

import com.ssafy.backend.chat.entity.ChatMessage;
import com.ssafy.backend.chat.entity.SenderType;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ChatMessageRepository extends JpaRepository<ChatMessage, Long> {

    /**
     * 반복질문 자동답변 폴링(-571)의 {@code since} 커서용 — 이 방송에 마지막으로 저장한 AI
     * 메시지 1건. 없으면(아직 AI 답변이 하나도 없으면) 호출부가 방송 시작 시각을 대신 쓴다.
     */
    Optional<ChatMessage> findTopByLive_IdAndSenderTypeOrderByCreatedAtDesc(
            Long liveId, SenderType senderType);

    /**
     * 최신순 커서 페이징. {@code cursor}는 "이 ID보다 이전(더 오래된) 메시지"를 뜻하며
     * 첫 페이지는 {@code null}로 호출한다.
     *
     * <p><b>커서를 {@code createdAt}이 아니라 {@code id}로 잡는다.</b> 채팅은 조회 중에도 계속
     * 쌓이므로 offset 방식이면 경계에서 메시지가 밀리거나 중복된다. {@code createdAt}은 같은
     * 밀리초에 두 건이 들어오면 동률이 생겨 같은 문제가 남는다 — {@code id}는 IDENTITY 증가라
     * 서버 수신 순서와 정확히 일치한다.
     *
     * <p>차단된 메시지({@code is_blocked})는 <b>응답에서 제외한다.</b> 숨김 판단을 FE에 맡기면
     * 클라이언트마다 다르게 보인다.
     */
    @Query("""
            select c
            from ChatMessage c
            join fetch c.live
            left join fetch c.sender
            where c.live.id = :liveId
              and c.blocked = false
              and (:cursor is null or c.id < :cursor)
            order by c.id desc
            """)
    List<ChatMessage> findPageByLiveId(
            @Param("liveId") Long liveId, @Param("cursor") Long cursor, Pageable pageable);

    /**
     * 지정한 ID <b>이후(더 새로운)</b> 메시지를 오래된 순으로 가져온다. 재접속 후 끊긴 구간을
     * 메우는 용도다.
     *
     * <p><b>정렬이 위와 반대인 것은 의도다.</b> 앞으로 채우는 조회에서 최신순으로 자르면
     * "가장 새로운 30건"이 와서 끊긴 지점과 그 사이에 구멍이 남는다. 오래된 순으로 자르면
     * 마지막으로 본 메시지 바로 다음부터 이어지므로 구멍이 생기지 않는다.
     */
    @Query("""
            select c
            from ChatMessage c
            join fetch c.live
            left join fetch c.sender
            where c.live.id = :liveId
              and c.blocked = false
              and c.id > :after
            order by c.id asc
            """)
    List<ChatMessage> findPageAfterByLiveId(
            @Param("liveId") Long liveId, @Param("after") Long after, Pageable pageable);
}