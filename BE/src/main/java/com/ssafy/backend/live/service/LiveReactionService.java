package com.ssafy.backend.live.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.live.dto.response.ReactionResponse;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.ReactionType;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.time.Duration;
import java.time.LocalDateTime;
import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 라이브 반응 이모지. <b>저장하지 않고 그대로 중계한다</b>(사용자 결정 2026-07-30).
 *
 * <p>DB 를 쓰지 않으므로 남는 방어선이 없다. 그래서 <b>rate limit 이 이 기능의 유일한 보호
 * 장치다</b> — 한 사람이 초당 수백 건을 쏘면 모든 시청자의 브라우저가 그 애니메이션을 그리느라
 * 멈춘다. 서버가 아니라 <b>다른 시청자의 화면을 보호하는 제한</b>이라는 점이 중요하다.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class LiveReactionService {

    /** 고정 창(fixed window) 방식. 창 안에서 허용 횟수를 넘으면 창이 끝날 때까지 거부한다. */
    private static final Duration RATE_LIMIT_WINDOW = Duration.ofSeconds(1);

    /**
     * 창당 허용 횟수. 하트를 연타하는 UX 를 막지 않을 만큼 넉넉하고, 화면을 마비시킬 만큼
     * 크지는 않은 값으로 잡았다.
     */
    private static final int MAX_REACTIONS_PER_WINDOW = 5;

    private static final String RATE_LIMIT_KEY_PREFIX = "live:reaction:";

    private final LiveRepository liveRepository;
    private final MemberRepository memberRepository;
    private final StringRedisTemplate redisTemplate;

    /**
     * 반응 하나를 검증하고 브로드캐스트할 payload 를 만든다.
     *
     * @param senderId STOMP principal 에서 꺼낸 회원 ID. <b>{@code null} 이면 비회원이다</b>
     */
    public ReactionResponse react(Long senderId, Long liveId, ReactionType type) {
        // 비회원 차단을 채팅과 다른 코드로 돌려준다 — FE 가 "로그인하면 채팅할 수 있다"와
        // "로그인하면 반응할 수 있다"를 각각 안내할 수 있어야 한다.
        if (senderId == null) {
            throw new CustomException(ErrorCode.REACTION_GUEST_NOT_ALLOWED);
        }
        // enum 에 없는 값은 역직렬화 단계에서 null 이 된다. 여기서 걸러야 NPE 가 아니라 400 이 된다.
        if (type == null) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }

        Live live = liveRepository.findById(liveId)
                .orElseThrow(() -> new CustomException(ErrorCode.LIVE_NOT_FOUND));
        // 끝난 방송에는 반응할 수 없다. 채팅과 같은 규칙이다 — 다만 반응은 이력이 없어 읽기도 없다.
        if (live.isClosed()) {
            throw new CustomException(ErrorCode.INVALID_LIVE_STATE);
        }

        checkRateLimit(liveId, senderId);

        Member sender = memberRepository.findById(senderId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

        return ReactionResponse.of(liveId, type, sender.getId(), sender.getNickname(), LocalDateTime.now());
    }

    /**
     * 방송·회원 단위로 센다. 방송을 키에 넣는 이유는 <b>여러 방송을 동시에 보는 사용자가 한 방송의
     * 연타 때문에 다른 방송에서 막히지 않게</b> 하기 위해서다.
     */
    private void checkRateLimit(Long liveId, Long senderId) {
        String key = RATE_LIMIT_KEY_PREFIX + liveId + ":" + senderId;

        Long count = redisTemplate.opsForValue().increment(key);
        if (count == null) {
            // Redis 응답을 못 받았다면 제한을 걸 근거가 없다. 반응 하나를 막는 것보다 통과가 낫다.
            return;
        }
        if (count == 1L) {
            // 창의 시작점이다. TTL 을 여기서만 걸어야 매 반응마다 창이 뒤로 밀리지 않는다.
            redisTemplate.expire(key, RATE_LIMIT_WINDOW);
        }
        if (count > MAX_REACTIONS_PER_WINDOW) {
            throw new CustomException(ErrorCode.REACTION_TOO_FREQUENT);
        }
    }
}
