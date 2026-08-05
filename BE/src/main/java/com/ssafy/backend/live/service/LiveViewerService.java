package com.ssafy.backend.live.service;

import com.ssafy.backend.live.dto.response.ViewerCountResponse;
import com.ssafy.backend.live.repository.LiveRepository;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.data.redis.core.Cursor;
import org.springframework.data.redis.core.ScanOptions;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

/**
 * 현재 동시 시청자 수 집계(LIVE-005 / -450). 구독·해지·연결 종료를 세어 Redis 에 들고 있는다.
 *
 * <p><b>왜 Redis 인가.</b> 값이 초 단위로 바뀌고 프로세스가 죽으면 의미가 사라지는 휘발성
 * 데이터다. DB 에 넣으면 시청자가 들고 날 때마다 write 가 발생한다. 반대로 <b>최고 시청자 수</b>는
 * 방송이 끝난 뒤에도 남아야 하므로 {@code live.peak_viewer_count} 에 저장한다 — 다만 최고치를
 * 넘어설 때만 DB 를 때린다.
 *
 * <p><b>왜 INCR 카운터가 아니라 세션 ID 집합인가.</b> FE 한 명이 같은 방송의 여러 토픽
 * (채팅·시청자수·경매·상품)을 구독한다. 구독마다 카운터를 올리면 한 사람이 네 명으로 잡힌다.
 * 세션 ID 를 {@code Set} 에 넣으면 몇 번 구독해도 {@code SCARD} 는 사람 수를 준다.
 *
 * <p><b>호스트는 세지 않는다.</b> 판매자가 자기 방송 화면을 열어 둔 것은 시청이 아니다 —
 * 넣으면 아무도 안 보는 방송이 늘 "1명"으로 보이고, 판매자가 "몇 명이 보고 있나"를 판단할 때
 * 자기 자신을 빼서 읽어야 한다. 최고 시청자 수({@code peak_viewer_count})도 같은 기준을 따른다.
 *
 * <p><b>세션 → 방송 역방향 매핑이 필요한 이유.</b> UNSUBSCRIBE·DISCONNECT 프레임에는 destination 이
 * 없다. 어느 방송에서 빠져야 하는지 알 수 없으므로 구독 시점에 {@code sessionId + subscriptionId →
 * liveId} 를 남겨 둔다. 한 세션이 같은 방송을 여러 번 구독했다면 <b>마지막 구독이 사라질 때만</b>
 * 시청자에서 제외한다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class LiveViewerService {

    private static final String VIEWERS_KEY_PREFIX = "live:viewers:";
    private static final String SESSION_KEY_PREFIX = "live:session:";
    private static final int SCAN_BATCH_SIZE = 500;

    private final StringRedisTemplate redisTemplate;
    private final LiveRepository liveRepository;
    private final SimpMessagingTemplate messagingTemplate;

    /**
     * 세션이 방송을 구독했다. 시청자로 세고 갱신된 수를 브로드캐스트한다.
     *
     * <p><b>구독 직후 자기 자신이 이 브로드캐스트를 받는지는 보장하지 않는다.</b>
     * {@code SessionSubscribeEvent} 발행과 SUBSCRIBE 프레임의 브로커 등록은 경합할 수 있다.
     * 그래서 FE 는 <b>초기값을 라이브 상세 API 의 {@code currentViewerCount} 로 받고</b> 이후
     * 변화만 토픽으로 받는다.
     *
     * <p>이미 시청자로 잡혀 있는 세션이면 아무 일도 하지 않는다 — 같은 방송의 두 번째, 세 번째
     * 구독마다 같은 값을 브로드캐스트할 이유가 없다.
     *
     * @param memberId 구독한 회원 ID. <b>비회원이면 null</b>. 호스트를 시청자에서 빼기 위해 받는다
     */
    public void enter(String sessionId, String subscriptionId, Long liveId, Long memberId) {
        // 호스트 세션도 매핑은 남긴다 — 정리 경로(UNSUBSCRIBE·DISCONNECT)를 한 갈래로 유지한다.
        // 시청자 집합에 없으므로 나갈 때 SREM 이 0을 돌려주고 브로드캐스트도 일어나지 않는다.
        redisTemplate.opsForHash().put(sessionKey(sessionId), subscriptionId, String.valueOf(liveId));

        // 판매자는 자기 방송의 시청자가 아니다 — 혼자 있는 방송은 0명으로 보여야 한다.
        if (isHost(liveId, memberId)) {
            return;
        }

        Long added = redisTemplate.opsForSet().add(viewersKey(liveId), sessionId);
        if (added == null || added == 0) {
            return;
        }

        int count = getViewerCount(liveId);
        // 최고치를 넘어설 때만 UPDATE 가 실제로 행을 건드린다(조건이 SQL 안에 있다).
        liveRepository.raisePeakViewerCount(liveId, count);
        broadcast(liveId, count);
    }

    /**
     * 구독 하나가 해지됐다. SPA 에서 <b>연결은 유지한 채 다른 화면으로 이동하면</b> DISCONNECT 없이
     * UNSUBSCRIBE 만 온다.
     *
     * <p>같은 세션이 이 방송의 다른 토픽을 여전히 구독 중이면 시청자에서 빼지 않는다.
     */
    public void leaveSubscription(String sessionId, String subscriptionId) {
        String sessionKey = sessionKey(sessionId);
        Object stored = redisTemplate.opsForHash().get(sessionKey, subscriptionId);
        if (stored == null) {
            // 라이브 토픽이 아닌 구독(예: /user/queue/errors)이었다.
            return;
        }

        redisTemplate.opsForHash().delete(sessionKey, subscriptionId);

        Long liveId = Long.valueOf(stored.toString());
        if (stillSubscribed(sessionKey, liveId)) {
            return;
        }
        removeViewer(sessionId, liveId);
    }

    /** 연결이 끊겼다. 이 세션이 구독하던 모든 방송에서 제외한다. */
    public void leaveSession(String sessionId) {
        String sessionKey = sessionKey(sessionId);
        Set<Long> liveIds = redisTemplate.opsForHash().values(sessionKey).stream()
                .map(value -> Long.valueOf(value.toString()))
                .collect(Collectors.toSet());

        redisTemplate.delete(sessionKey);
        liveIds.forEach(liveId -> removeViewer(sessionId, liveId));
    }

    /** 현재 동시 시청자 수. 아무도 없거나 키가 없으면 0. */
    public int getViewerCount(Long liveId) {
        Long size = redisTemplate.opsForSet().size(viewersKey(liveId));
        return size == null ? 0 : size.intValue();
    }

    /**
     * 여러 방송의 시청자 수. 목록 한 페이지(기본 12건)마다 그만큼 {@code SCARD} 를 보낸다 —
     * Redis 가 같은 호스트에 있어 왕복 비용이 무의미하고, 파이프라인으로 묶으면 키 접두어를
     * 바이트로 직접 다뤄야 해서 읽기가 나빠진다. 목록 크기 상한이 100 이라 그 이상 커지지 않는다.
     */
    public Map<Long, Integer> getViewerCounts(Collection<Long> liveIds) {
        return liveIds.stream()
                .distinct()
                .collect(Collectors.toMap(Function.identity(), this::getViewerCount));
    }

    /** 방송이 끝나면 시청자 집합을 버린다 — 종료된 방송에 시청자 수가 남아 있을 이유가 없다. */
    public void clear(Long liveId) {
        redisTemplate.delete(viewersKey(liveId));
    }

    /**
     * 기동 시 남아 있는 시청자 키를 지운다.
     *
     * <p><b>없으면 유령 시청자가 영구히 남는다.</b> 프로세스가 죽으면 WebSocket 세션은 모두
     * 끊기지만 DISCONNECT 를 처리할 주체가 없어 Redis 값만 살아남는다. 재기동 후 "아무도 없는
     * 방송에 300명"이 표시된다.
     *
     * <p>{@code KEYS} 대신 {@code SCAN} 을 쓴다 — {@code KEYS} 는 키 전체를 훑는 동안 Redis 를
     * 멈춰 세운다. 단일 인스턴스라 "다른 서버가 살아 있는데 내가 키를 지운다"는 상황은 없다.
     */
    @EventListener(ApplicationReadyEvent.class)
    public void clearStaleKeysOnStartup() {
        int deleted = deleteByPattern(VIEWERS_KEY_PREFIX + "*") + deleteByPattern(SESSION_KEY_PREFIX + "*");
        if (deleted > 0) {
            log.info("기동 시 잔여 시청자 키 정리 - {}개", deleted);
        }
    }

    private void removeViewer(String sessionId, Long liveId) {
        Long removed = redisTemplate.opsForSet().remove(viewersKey(liveId), sessionId);
        if (removed == null || removed == 0) {
            return;
        }
        broadcast(liveId, getViewerCount(liveId));
    }

    /**
     * 이 회원이 그 방송의 호스트인지.
     *
     * <p><b>비회원은 조회 없이 바로 false다</b> — 토큰 없이 붙은 세션은 호스트일 수 없다.
     * 회원이면 인덱스를 타는 {@code exists} 한 방으로 확인한다(방송을 통째로 읽어 올 이유가 없다).
     */
    private boolean isHost(Long liveId, Long memberId) {
        return memberId != null && liveRepository.existsByIdAndHost_Id(liveId, memberId);
    }

    /** 이 세션이 해당 방송의 다른 구독을 아직 갖고 있는지. */
    private boolean stillSubscribed(String sessionKey, Long liveId) {
        String target = String.valueOf(liveId);
        return redisTemplate.opsForHash().values(sessionKey).stream()
                .anyMatch(value -> target.equals(value.toString()));
    }

    private void broadcast(Long liveId, int count) {
        messagingTemplate.convertAndSend(
                "/topic/lives/" + liveId + "/viewers", ViewerCountResponse.of(liveId, count));
    }

    private int deleteByPattern(String pattern) {
        List<String> keys = new ArrayList<>();
        try (Cursor<String> cursor = redisTemplate.scan(
                ScanOptions.scanOptions().match(pattern).count(SCAN_BATCH_SIZE).build())) {
            cursor.forEachRemaining(keys::add);
        }
        if (keys.isEmpty()) {
            return 0;
        }
        Long deleted = redisTemplate.delete(new HashSet<>(keys));
        return deleted == null ? 0 : deleted.intValue();
    }

    private String viewersKey(Long liveId) {
        return VIEWERS_KEY_PREFIX + liveId;
    }

    private String sessionKey(String sessionId) {
        return SESSION_KEY_PREFIX + sessionId;
    }
}
