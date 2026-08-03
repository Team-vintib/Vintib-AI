package com.ssafy.backend.live.port;

import com.ssafy.backend.member.entity.Member;

/**
 * 라이브 도메인이 알림을 만드는 유일한 창구.
 *
 * <p>{@code ProductQueryPort}와 같은 이유로 둔다 — 라이브가 알림 도메인의 엔티티 구조를 직접
 * 다루면, 알림 쪽이 바뀔 때 라이브 코드가 함께 깨진다. 어댑터 한 곳만 고치면 되게 좁혀 둔다.
 */
public interface NotificationCommandPort {

    /**
     * 알림 한 건을 만든다.
     *
     * @param type    알림 종류(FE 요청 008 §3.2.1 기준 {@code LIVE_REMINDER} 등)
     * @param refType 클릭 시 이동할 대상 종류. {@code LIVE}면 FE 가 {@code /lives/{refId}}로 보낸다
     */
    void notify(Member member, String type, String title, String body, String refType, Long refId);
}
