package com.ssafy.backend.auction.service;

import com.ssafy.backend.auction.dto.request.AuctionConfigRequest;
import com.ssafy.backend.auction.dto.response.AuctionResponse;
import com.ssafy.backend.auction.dto.response.AuctionSnapshotResponse;
import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.auction.entity.AuctionStatus;
import com.ssafy.backend.auction.port.ProductCommandPort;
import com.ssafy.backend.auction.repository.AuctionRepository;
import com.ssafy.backend.auction.repository.BidRepository;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.port.ProductQueryPort;
import com.ssafy.backend.live.repository.LiveProductRepository;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.time.LocalDateTime;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 경매 조건 설정(AUCT-001)과 현황 조회·시작(AUCT-002).
 *
 * <p><b>여기에는 아직 락이 없다.</b> 조건 설정·시작은 호스트 한 사람만 하는 동작이라 경합이
 * 생기지 않는다. 입찰 경합(AUCT-003~006)은 다음 단계에서 비관적 락과 함께 다룬다.
 *
 * <p>라이브 조회는 포트를 거치지 않고 리포지토리를 직접 쓴다. 상품 도메인과 달리 라이브는
 * 같은 담당자의 안정된 도메인이라 격리 이득이 없다. 반대로 <b>상품은 서윤 영역이라</b>
 * 조회는 {@link ProductQueryPort}, 상태 변경은 {@link ProductCommandPort}로만 건드린다.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class AuctionService {

    /** 아직 끝나지 않은 경매. 이 상태의 경매가 있으면 같은 상품에 조건을 다시 걸 수 없다. */
    private static final List<AuctionStatus> UNFINISHED =
            List.of(AuctionStatus.READY, AuctionStatus.RUNNING);

    private final AuctionRepository auctionRepository;
    private final BidRepository bidRepository;
    private final LiveRepository liveRepository;
    private final LiveProductRepository liveProductRepository;
    private final MemberRepository memberRepository;
    private final ProductQueryPort productQueryPort;
    private final ProductCommandPort productCommandPort;

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
        Auction saved = auctionRepository.save(auction);

        // 상품도 "경매 예정"이 돼야 한다. 이게 빠져 있어서 조건을 걸어도 상품은 DRAFT·ON_SALE에
        // 머물렀고, 홈·상품 목록에 상시 판매처럼 보였다(-394 보완).
        productCommandPort.markAuctionScheduled(request.productId());

        return AuctionResponse.from(saved);
    }

    /**
     * 라이브 경매 패널 초기화용 현황 조회(AUCT-002).
     *
     * <p><b>경매가 없으면 예외가 아니라 {@code null}이다.</b> 아직 경매를 걸지 않은 방송이
     * 정상이고, 시청자가 들어올 때마다 404를 받는 것은 오류가 아니라 "아직 없음"이다.
     *
     * @return 진행 중 경매 우선, 없으면 준비 중 경매. 둘 다 없으면 {@code null}
     */
    public AuctionSnapshotResponse getCurrentSnapshot(Long liveId) {
        if (!liveRepository.existsById(liveId)) {
            throw new CustomException(ErrorCode.LIVE_NOT_FOUND);
        }
        return auctionRepository.findPanelCandidates(liveId, PageRequest.of(0, 1)).stream()
                .findFirst()
                .map(this::toSnapshot)
                .orElse(null);
    }

    /**
     * 경매를 시작한다(AUCT-002). {@code READY → RUNNING}이며 종료 예정 시각이 이때 확정된다.
     *
     * <p><b>한 라이브에서 진행 중인 경매는 하나뿐이다</b>(LIVE-004). 둘이 동시에 돌면 시청자가
     * 어느 쪽에 입찰하는지 알 수 없고 화면도 하나뿐이다. 여기서 먼저 막고, 최후 방어선은
     * 부분 UNIQUE 인덱스 {@code ux_auction_live_running}이다.
     *
     * <p>상품도 함께 {@code AUCTION_IN_PROGRESS}로 옮긴다 — 경매 상태와 상품 판매 상태는 짝이다.
     */
    @Transactional
    public AuctionSnapshotResponse startAuction(Long hostId, Long auctionId) {
        Auction auction = auctionRepository.findWithLiveById(auctionId)
                .orElseThrow(() -> new CustomException(ErrorCode.AUCTION_NOT_FOUND));
        Live live = auction.getLive();

        if (!live.isHostedBy(hostId)) {
            throw new CustomException(ErrorCode.NOT_LIVE_HOST);
        }
        if (live.isClosed()) {
            throw new CustomException(ErrorCode.INVALID_LIVE_STATE);
        }
        if (!auction.isReady()) {
            // 이미 진행 중이거나 끝난 경매다. 다시 시작하면 종료 시각이 밀려 입찰 기회가 뒤집힌다.
            throw new CustomException(ErrorCode.AUCTION_NOT_STARTABLE);
        }
        if (auctionRepository.existsByLiveIdAndStatus(live.getId(), AuctionStatus.RUNNING)) {
            throw new CustomException(ErrorCode.AUCTION_ALREADY_RUNNING);
        }

        auction.start(LocalDateTime.now());
        productCommandPort.markAuctionInProgress(auction.getProductId());

        return toSnapshot(auction);
    }

    /** 상품명·입찰자 닉네임·입찰 수를 붙여 현황 한 장으로 만든다. */
    private AuctionSnapshotResponse toSnapshot(Auction auction) {
        String productTitle = productQueryPort.findById(auction.getProductId())
                .map(ProductQueryPort.ProductSummary::title)
                .orElse(null);
        String bidderNickname = auction.getTopBidderId() == null
                ? null
                : memberRepository.findById(auction.getTopBidderId())
                        .map(Member::getNickname)
                        .orElse(null);

        return AuctionSnapshotResponse.of(
                auction,
                productTitle,
                bidderNickname,
                bidRepository.countByAuction_Id(auction.getId()),
                LocalDateTime.now());
    }
}