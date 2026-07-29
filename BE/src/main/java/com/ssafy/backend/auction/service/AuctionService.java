package com.ssafy.backend.auction.service;

import com.ssafy.backend.auction.dto.request.AuctionConfigRequest;
import com.ssafy.backend.auction.dto.response.AuctionResponse;
import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.auction.entity.AuctionStatus;
import com.ssafy.backend.auction.repository.AuctionRepository;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.repository.LiveProductRepository;
import com.ssafy.backend.live.repository.LiveRepository;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 경매 조건 설정(AUCT-001).
 *
 * <p>이번 단계는 <b>단순 HTTP</b>다 — 조건을 DB에 적어두기만 하고 경매를 시작하지 않는다.
 * 동시성(입찰 경합·분산 락)은 경매 진행(AUCT-002 이후)에서 다루므로 여기에는 락이 없다.
 *
 * <p>라이브 조회는 포트를 거치지 않고 리포지토리를 직접 쓴다. 상품 도메인과 달리 라이브는
 * 같은 담당자의 안정된 도메인이라 격리 이득이 없다.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class AuctionService {

    /** 아직 끝나지 않은 경매. 이 상태의 경매가 있으면 같은 상품에 조건을 다시 걸 수 없다. */
    private static final List<AuctionStatus> UNFINISHED =
            List.of(AuctionStatus.READY, AuctionStatus.RUNNING);

    private final AuctionRepository auctionRepository;
    private final LiveRepository liveRepository;
    private final LiveProductRepository liveProductRepository;

    /**
     * 경매 조건을 설정한다. 결과는 {@code READY} 상태이며 시작은 별도 API(AUCT-002)가 한다.
     *
     * <p><b>미등록 상품에는 경매를 걸 수 없다</b> — 라이브에 연결(LIVE-003)되지 않은 상품은 방송에
     * 노출되지 않으므로 시청자가 입찰할 방법이 없다. 연결 여부는 제외되지 않은 연결만 인정한다.
     */
    @Transactional
    public AuctionResponse configureAuction(Long hostId, Long liveId, AuctionConfigRequest request) {
        Live live = liveRepository.findById(liveId)
                .orElseThrow(() -> new CustomException(ErrorCode.LIVE_NOT_FOUND));

        if (!live.isHostedBy(hostId)) {
            throw new CustomException(ErrorCode.NOT_LIVE_HOST);
        }
        // 편성 변경(isOpenForEditing)과 다른 기준을 쓴다 — 경매 조건 설정은 방송 중에도 해야 한다.
        // 실제 라이브 커머스에서 경매는 방송을 진행하면서 건다.
        if (live.isClosed()) {
            throw new CustomException(ErrorCode.INVALID_LIVE_STATE);
        }
        if (!liveProductRepository.existsByLiveIdAndProductIdAndRemovedAtIsNull(liveId, request.productId())) {
            throw new CustomException(ErrorCode.LIVE_PRODUCT_NOT_FOUND);
        }
        if (auctionRepository.existsByLiveIdAndProductIdAndStatusIn(liveId, request.productId(), UNFINISHED)) {
            throw new CustomException(ErrorCode.AUCTION_ALREADY_CONFIGURED);
        }

        Auction auction = Auction.configure(
                live, request.productId(), request.startPrice(), request.bidUnit(), request.durationSeconds());

        return AuctionResponse.from(auctionRepository.save(auction));
    }
}