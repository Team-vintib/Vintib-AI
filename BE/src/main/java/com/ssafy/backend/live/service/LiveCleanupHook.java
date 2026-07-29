package com.ssafy.backend.live.service;

import com.ssafy.backend.live.entity.Live;

/**
 * 방송이 종료될 때 딸린 리소스를 정리하는 훅.
 *
 * <p><b>왜 인터페이스인가</b> — 종료 시 정리해야 할 것들(진행 중 경매 마감, 채팅방 닫기,
 * OpenVidu room 해제)이 아직 다 만들어지지 않았다. 정리 대상이 생길 때마다 종료 로직을 다시 열어
 * 고치는 대신, 구현체를 하나 추가해 등록만 하면 되게 한다.
 *
 * <p>구현체는 스프링 빈으로 등록하면 {@link LiveService}가 자동으로 모아 호출한다.
 * 등록 순서에 의존하지 않도록 각 구현체는 서로 독립적이어야 한다.
 */
public interface LiveCleanupHook {

    /**
     * 방송이 {@code ENDED}로 전이된 직후 호출된다. 상태 전이와 같은 트랜잭션 안에서 실행된다.
     */
    void onLiveEnded(Live live);
}