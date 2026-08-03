package com.ssafy.backend.live.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.data.redis.core.StringRedisTemplate;

/**
 * 시청자 수 집계 테스트(-450).
 *
 * <p><b>Redis 를 실제로 붙여 검증한다.</b> 집계의 핵심이 "같은 사람을 두 번 세지 않는다"인데,
 * 그 성질은 {@code SADD} 의 멱등성에서 나온다. 모킹하면 검증하려는 것이 사라진다.
 */
@SpringBootTest
class LiveViewerServiceTest {

    @Autowired
    private LiveViewerService liveViewerService;

    @Autowired
    private LiveRepository liveRepository;

    @Autowired
    private MemberRepository memberRepository;

    @Autowired
    private StringRedisTemplate redisTemplate;

    private Member host;
    private Long liveId;

    @BeforeEach
    void setUp() {
        host = memberRepository.save(Member.builder()
                .email("viewer-" + UUID.randomUUID() + "@example.com")
                .password("encoded")
                .name("호스트")
                .build());
        liveId = liveRepository.save(Live.openNow(host, "빈티지 데님 라이브", null, null, LocalDateTime.now())).getId();

        // 테스트마다 같은 sessionId 문자열을 재사용한다. 앞선 테스트가 남긴 세션 매핑이 있으면
        // 엉뚱한 방송에서 시청자를 빼게 되므로 시청자·세션 키를 모두 비우고 시작한다.
        liveViewerService.clearStaleKeysOnStartup();
    }

    @Test
    void 구독하면_시청자로_잡힌다() {
        liveViewerService.enter("session-a", "sub-0", liveId);

        assertThat(liveViewerService.getViewerCount(liveId)).isEqualTo(1);
    }

    @Test
    void 한_세션이_같은_방송의_여러_토픽을_구독해도_한_명이다() {
        // FE 는 채팅·시청자수·경매·상품 토픽을 함께 구독한다. 구독마다 세면 한 명이 네 명이 된다.
        liveViewerService.enter("session-a", "sub-0", liveId);
        liveViewerService.enter("session-a", "sub-1", liveId);
        liveViewerService.enter("session-a", "sub-2", liveId);

        assertThat(liveViewerService.getViewerCount(liveId)).isEqualTo(1);
    }

    @Test
    void 서로_다른_세션은_각각_센다() {
        liveViewerService.enter("session-a", "sub-0", liveId);
        liveViewerService.enter("session-b", "sub-0", liveId);

        assertThat(liveViewerService.getViewerCount(liveId)).isEqualTo(2);
    }

    @Test
    void 구독이_남아_있으면_해지해도_시청자에서_빠지지_않는다() {
        liveViewerService.enter("session-a", "sub-0", liveId);
        liveViewerService.enter("session-a", "sub-1", liveId);

        liveViewerService.leaveSubscription("session-a", "sub-0");

        // 채팅 구독은 끊었지만 아직 이 방송의 다른 토픽을 보고 있다.
        assertThat(liveViewerService.getViewerCount(liveId)).isEqualTo(1);
    }

    @Test
    void 마지막_구독을_해지하면_시청자에서_빠진다() {
        liveViewerService.enter("session-a", "sub-0", liveId);
        liveViewerService.enter("session-a", "sub-1", liveId);

        liveViewerService.leaveSubscription("session-a", "sub-0");
        liveViewerService.leaveSubscription("session-a", "sub-1");

        assertThat(liveViewerService.getViewerCount(liveId)).isZero();
    }

    @Test
    void 라이브_토픽이_아닌_구독_해지는_아무_영향이_없다() {
        liveViewerService.enter("session-a", "sub-0", liveId);

        // /user/queue/errors 처럼 방송과 무관한 구독의 해지다.
        liveViewerService.leaveSubscription("session-a", "sub-error");

        assertThat(liveViewerService.getViewerCount(liveId)).isEqualTo(1);
    }

    @Test
    void 연결이_끊기면_구독하던_모든_방송에서_빠진다() {
        Long otherLiveId = liveRepository.save(
                        Live.openNow(host, "다른 방송", null, null, LocalDateTime.now()))
                .getId();

        liveViewerService.enter("session-a", "sub-0", liveId);
        liveViewerService.enter("session-a", "sub-1", otherLiveId);

        liveViewerService.leaveSession("session-a");

        assertThat(liveViewerService.getViewerCount(liveId)).isZero();
        assertThat(liveViewerService.getViewerCount(otherLiveId)).isZero();
    }

    @Test
    void 여러_방송의_시청자_수를_한_번에_조회한다() {
        liveViewerService.enter("session-a", "sub-0", liveId);
        liveViewerService.enter("session-b", "sub-0", liveId);

        Map<Long, Integer> counts = liveViewerService.getViewerCounts(List.of(liveId, 999_999L));

        assertThat(counts).containsEntry(liveId, 2);
        // 아무도 본 적 없는 방송은 키가 없다 — null 이 아니라 0 이어야 FE 가 분기하지 않는다.
        assertThat(counts).containsEntry(999_999L, 0);
    }

    @Test
    void 최고_시청자_수는_넘어설_때만_갱신된다() {
        liveViewerService.enter("session-a", "sub-0", liveId);
        liveViewerService.enter("session-b", "sub-0", liveId);
        assertThat(peakOf(liveId)).isEqualTo(2);

        // 한 명이 나가고 다시 들어와도 최고치는 2 그대로다. 1 로 내려가면 기록이 아니다.
        liveViewerService.leaveSession("session-b");
        liveViewerService.enter("session-c", "sub-0", liveId);

        assertThat(liveViewerService.getViewerCount(liveId)).isEqualTo(2);
        assertThat(peakOf(liveId)).isEqualTo(2);
    }

    @Test
    void 방송이_종료되면_시청자_집합이_비워진다() {
        liveViewerService.enter("session-a", "sub-0", liveId);

        Live live = liveRepository.findById(liveId).orElseThrow();
        live.transitionTo(LiveStatus.ENDED, LocalDateTime.now());
        new ViewerCountCleanupHook(liveViewerService).onLiveEnded(live);

        assertThat(liveViewerService.getViewerCount(liveId)).isZero();
    }

    @Test
    void 기동_시_잔여_시청자_키를_정리한다() {
        redisTemplate.opsForSet().add("live:viewers:" + liveId, "죽은-세션");
        redisTemplate.opsForHash().put("live:session:죽은-세션", "sub-0", String.valueOf(liveId));

        liveViewerService.clearStaleKeysOnStartup();

        // 프로세스가 죽으면 세션은 끊기는데 Redis 값만 남아 "아무도 없는 방송에 300명"이 된다.
        assertThat(liveViewerService.getViewerCount(liveId)).isZero();
        assertThat(redisTemplate.hasKey("live:session:죽은-세션")).isFalse();
    }

    private int peakOf(Long id) {
        return liveRepository.findById(id).orElseThrow().getPeakViewerCount();
    }
}
