package com.ssafy.backend.auction.service;

import com.ssafy.backend.auction.dto.response.AuctionEventResponse;
import com.ssafy.backend.auction.dto.response.AuctionSnapshotResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 경매 마감 스캐너(AUCT-012, JY008 설계 판단 3).
 *
 * <p><b>왜 1초인가.</b> 경매는 초 단위 카운트다운을 보여 주는 화면이라, 0이 된 뒤 몇 초씩
 * 결과가 안 나오면 시청자는 화면이 멈춘 것으로 본다. 자동 연장 임계값이 3초라 그보다 촘촘해야
 * 한다는 제약도 있다. 조회는 인덱스를 탄 좁은 질의 하나뿐이라 이 주기를 감당한다.
 *
 * <p>{@code fixedDelay}를 쓰는 이유는 {@code LiveReminderScheduler}와 같다 — 한 주기가 늦어져도
 * 다음 실행이 겹쳐 들어와 같은 경매를 두 번 집지 않는다.
 *
 * <p><b>루프가 서비스가 아니라 여기 있는 이유.</b> 경매마다 트랜잭션을 따로 열어야 하는데,
 * 서비스가 자기 메서드를 직접 부르면 스프링 프록시를 안 거쳐 {@code @Transactional}이 무시된다.
 * 그래서 후보 조회와 개별 마감을 나눠 받아 여기서 돈다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AuctionCloseScheduler {

    private static final long INTERVAL_MS = 1_000;

    private final AuctionCloseService auctionCloseService;
    private final SimpMessagingTemplate messagingTemplate;

    @Scheduled(fixedDelay = INTERVAL_MS, initialDelay = INTERVAL_MS)
    public void closeDueAuctions() {
        try {
            for (Long auctionId : auctionCloseService.findDueAuctionIds()) {
                closeOne(auctionId);
            }
        } catch (Exception e) {
            // 여기서 예외가 새어 나가면 스케줄러가 통째로 멈춘다. 다음 주기에 다시 시도한다.
            log.error("경매 마감 스캔 실패 - 다음 주기에 재시도한다", e);
        }
    }

    /**
     * 한 경매를 마감하고 결과를 전파한다. <b>커밋이 끝난 뒤에 쏜다</b> — 컨트롤러들이 상태
     * 전파를 커밋 이후로 미루는 것과 같은 이유로, 롤백되면 시청자 화면에서만 경매가 끝난 채
     * 남는다.
     */
    private void closeOne(Long auctionId) {
        try {
            AuctionSnapshotResponse snapshot = auctionCloseService.closeIfDue(auctionId);
            if (snapshot == null) {
                // 마감 직전 입찰로 연장됐다(AUCT-010). 다음 주기에 다시 본다.
                return;
            }
            messagingTemplate.convertAndSend(
                    "/topic/lives/" + snapshot.liveId() + "/auctions",
                    AuctionEventResponse.closed(snapshot));
        } catch (RuntimeException e) {
            // 한 경매가 실패해도 나머지는 마감돼야 한다.
            log.error("경매 마감 실패 - auctionId={}, 다음 주기에 재시도한다", auctionId, e);
        }
    }
}
