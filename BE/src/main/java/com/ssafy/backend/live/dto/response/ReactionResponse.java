package com.ssafy.backend.live.dto.response;

import com.ssafy.backend.live.entity.ReactionType;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

/**
 * 반응 브로드캐스트. {@code /topic/lives/{liveId}/reactions} 로 나간다.
 *
 * <p><b>{@code senderId} 를 담는 이유는 두 가지다.</b> 발행자가 낙관적으로 그린 자기 반응을 다시
 * 그리지 않게 걸러내야 하고, 호스트 반응을 다르게 보여줄 여지도 남는다.
 *
 * <p><b>{@code sentAt} 은 서버 시각이다.</b> 클라이언트 시각을 쓰면 기기 시계가 틀어진 사용자의
 * 반응이 미래나 과거에 찍힌다.
 */
public record ReactionResponse(

        @Schema(description = "라이브 ID", example = "101")
        Long liveId,

        @Schema(description = "반응 종류", example = "HEART")
        ReactionType type,

        @Schema(description = "보낸 회원 ID. 비회원은 반응을 보낼 수 없어 항상 값이 있다", example = "42")
        Long senderId,

        @Schema(description = "보낸 회원 닉네임", example = "빈티지러버")
        String senderNickname,

        @Schema(description = "서버가 받은 시각", example = "2026-07-30T21:15:03")
        LocalDateTime sentAt
) {

    public static ReactionResponse of(
            Long liveId, ReactionType type, Long senderId, String senderNickname, LocalDateTime sentAt) {
        return new ReactionResponse(liveId, type, senderId, senderNickname, sentAt);
    }
}
