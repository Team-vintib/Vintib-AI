package com.ssafy.backend.auction.service;

import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.service.LiveCleanupHook;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 방송이 끝나면 아직 진행 중인 경매를 강제로 마감한다(AUCT-014).
 *
 * <p>이게 없으면 방송이 끝난 뒤에도 경매가 {@code RUNNING}으로 남는다. 그러면 낙찰자의 포인트가
 * 계속 보류돼 있고, {@code ux_auction_live_running} 때문에 그 방송에는 다시 경매를 걸 수도 없다.
 *
 * <p><b>방송 상태 전이와 같은 트랜잭션에서 돈다</b>({@link LiveCleanupHook} 계약). 경매 마감이
 * 실패하면 방송 종료도 함께 롤백되는 편이 맞다 — "방송은 끝났는데 경매는 살아 있는" 어긋난
 * 상태를 만드는 것보다 종료를 다시 시도하게 하는 쪽이 낫다.
 *
 * <p><b>여기서는 {@code AUCTION_CLOSED}를 따로 쏘지 않는다.</b> 방송 종료가
 * {@code /topic/lives/{liveId}/status}로 이미 전파되고 FE는 그 이벤트에서 시청 화면을 종료
 * 안내로 바꾼다 — 같은 순간에 경매 종료까지 쏘면 화면 전환이 두 번 겹친다. 낙찰 결과는
 * 방송 종료 대시보드(Phase 8-b)와 {@code GET /api/auctions/{auctionId}/winner}로 확인한다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AuctionLiveCleanupHook implements LiveCleanupHook {

    private final AuctionCloseService auctionCloseService;

    @Override
    public void onLiveEnded(Live live) {
        auctionCloseService.closeRunningAuctionsOfLive(live.getId()).forEach(closed ->
                log.info("방송 종료로 경매 강제 마감 - liveId={}, auctionId={}, status={}",
                        live.getId(), closed.auctionId(), closed.status()));
    }
}
