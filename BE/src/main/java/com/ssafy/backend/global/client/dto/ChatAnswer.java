package com.ssafy.backend.global.client.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;

/**
 * 반복질문 자동답변 한 건 — AI/app/chat/schemas.py의 {@code FaqAnswer}. 근거 없는(ungrounded)
 * 답변은 애초에 목록에 안 실려 오므로 BE가 따로 걸러낼 필요는 없다(036 요청 문서).
 *
 * <p>{@code createdAt}은 {@code LocalDateTime}이 아니라 {@code Instant}다. AI가 보내는
 * {@code created_at}은 오프셋이 있는 UTC 문자열인데("...Z"), Jackson의 {@code
 * LocalDateTimeDeserializer}는 오프셋 있는 문자열을 받으면 변환 없이 오프셋만 버리고 숫자를
 * 그대로 읽어버린다 — 그 결과로 저장된 시각이 실제보다 9시간 이른 값이 되고, 그 값이 다음
 * 폴링의 {@code since} 커서로 다시 쓰이면서 같은 답변이 계속 "새 답변"으로 재조회돼 채팅에
 * 중복 저장되는 문제가 있었다(실측으로 발견, S15P11A108-571 후속). {@code Instant}는 오프셋
 * 있는 문자열을 절대 시각으로 정확히 파싱하므로, 이 문제 자체가 생기지 않는다. KST
 * {@code LocalDateTime}으로의 변환은 이 값을 실제로 쓰는 지점({@code ChatMessageService})
 * 에서 한다.
 */
public record ChatAnswer(
        String ticket,
        String question,
        String answer,
        @JsonProperty("created_at") Instant createdAt) {
}
