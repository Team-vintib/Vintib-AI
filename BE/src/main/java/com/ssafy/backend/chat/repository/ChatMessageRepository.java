package com.ssafy.backend.chat.repository;

import com.ssafy.backend.chat.entity.ChatMessage;
import java.util.List;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ChatMessageRepository extends JpaRepository<ChatMessage, Long> {

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
}