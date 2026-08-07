package com.ssafy.backend.auction.service;

import com.ssafy.backend.auction.dto.request.AuctionConfigRequest;
import com.ssafy.backend.auction.dto.request.BidRequest;
import com.ssafy.backend.auction.dto.response.AuctionResponse;
import com.ssafy.backend.auction.dto.response.AuctionSnapshotResponse;
import com.ssafy.backend.auction.dto.response.AuctionWinnerResponse;
import com.ssafy.backend.auction.dto.response.BidResponse;
import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.auction.entity.AuctionStatus;
import com.ssafy.backend.auction.entity.Bid;
import com.ssafy.backend.auction.entity.BidStatus;
import com.ssafy.backend.auction.port.PointCommandPort;
import com.ssafy.backend.auction.port.ProductCommandPort;
import com.ssafy.backend.auction.repository.AuctionRepository;
import com.ssafy.backend.auction.repository.BidRepository;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.CursorPageResponse;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.notification.port.NotificationCommandPort;
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
 * 경매 조건 설정(AUCT-001)부터 현황 조회·시작·입찰(AUCT-002~006)까지.
 *
 * <p><b>입찰 동시성의 1차 방어는 {@code AuctionRepository.findByIdForUpdate}의 행 잠금이다.</b>
 * 같은 경매에 대한 입찰은 이 잠금으로 직렬화되므로 "락은 풀렸는데 커밋은 안 된" 창이 원리적으로
 * 없다. Redis 분산락·MQ는 검토 후 채택하지 않았다 — 계획 문서(JY008) 설계 판단 1 참고.
 * 조건 설정·시작은 호스트 한 사람만 하는 동작이라 잠글 필요가 없다.
 *
 * <p>라이브 조회는 포트를 거치지 않고 리포지토리를 직접 쓴다. 상품 도메인과 달리 라이브는
 * 같은 담당자의 안정된 도메인이라 격리 이득이 없다. 반대로 <b>상품·포인트는 서윤 영역이라</b>
 * {@link ProductQueryPort}/{@link ProductCommandPort}/{@link PointCommandPort}로만 건드린다.
 * {@link NotificationCommandPort}는 {@code live} 패키지 소유를 그대로 재사용한다 — 둘 다 정윤
 * 담당 도메인이라 새로 만들 이유가 없다.
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
    private final PointCommandPort pointCommandPort;
    private final NotificationCommandPort notificationCommandPort;

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

    /**
     * 입찰한다(AUCT-003~006). <b>이 메서드가 이 계획의 핵심이자 가장 위험한 구간이다.</b>
     *
     * <p>한 트랜잭션에서 — 경매 행 잠금 → 유효성 검증 → (상위 입찰이면) 직전 최고 입찰자
     * 보류 해제 → 새 입찰 저장 → 포인트 보류 → 현재가·최고 입찰자 갱신·자동 연장 순으로
     * 처리한다. 어느 한 단계라도 실패하면 전부 롤백된다 — "포인트는 빠졌는데 입찰은 안 된"
     * 상태가 생길 수 없다.
     *
     * <p><b>포인트 보류가 입찰 저장 다음인 이유.</b> {@code point_hold.bid_id}가 특정 입찰
     * 행을 가리켜야 하는데, 그 ID는 {@code Bid}를 저장해야만 나온다.
     */
    @Transactional
    public AuctionSnapshotResponse placeBid(Long bidderId, Long auctionId, BidRequest request) {
        Auction auction = auctionRepository.findByIdForUpdate(auctionId)
                .orElseThrow(() -> new CustomException(ErrorCode.AUCTION_NOT_FOUND));

        LocalDateTime now = LocalDateTime.now();
        if (!auction.isOpenForBidding(now)) {
            throw new CustomException(ErrorCode.AUCTION_NOT_ACTIVE);
        }
        // AUCT-006 — 직전 최고 입찰자 본인은 연속으로 입찰할 수 없다. 포인트 보류 쪽이
        // "최고 입찰자는 이미 HELD를 쥐고 있다"를 전제하므로 여기서 먼저 막아야 한다.
        if (!auction.isBiddableBy(bidderId)) {
            throw new CustomException(ErrorCode.CONSECUTIVE_BID_NOT_ALLOWED);
        }

        long nextBidPrice = auction.nextBidPrice();
        if (request.amount() < nextBidPrice) {
            throw new CustomException(ErrorCode.BID_LOWER_THAN_CURRENT);
        }
        if (request.amount() > nextBidPrice) {
            // 화면에 보이던 nextBidPrice 가 그 사이 바뀌었다는 뜻이다 — 최신 값으로 다시 시도해야 한다.
            throw new CustomException(ErrorCode.BID_PRICE_MISMATCH);
        }

        Member bidder = memberRepository.findById(bidderId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

        // 상위 입찰이 들어왔다 — 직전 최고 입찰자의 보류를 풀고, 그의 입찰을 OUTBID로 내리고, 밀렸다는
        // 사실을 알린다. 첫 입찰(hasBid() == false)에는 풀어 줄 대상도 알릴 대상도 없다.
        if (auction.hasBid()) {
            pointCommandPort.releaseHoldForAuction(auction.getId());
            bidRepository.findByAuction_IdAndStatus(auction.getId(), BidStatus.ACTIVE)
                    .ifPresent(previousBid -> {
                        previousBid.outbid();
                        notificationCommandPort.notify(
                                previousBid.getBidder(),
                                "AUCTION_OUTBID",
                                "상위 입찰이 발생했어요",
                                "다른 사용자가 더 높은 금액으로 입찰했습니다.",
                                "AUCTION",
                                auction.getId());
                    });
        }

        Bid bid;
        try {
            // IDENTITY 전략이라 save() 시점에 즉시 INSERT 된다 — ux_bid_auction_price 위반이
            // 있다면 여기서 바로 터진다. 행 잠금이 같은 경매의 입찰을 이미 직렬화하고 가격도
            // 서버가 매번 다시 계산하므로 정상 경로에서는 사실상 발동하지 않는다. 그래도
            // 이 안전망이 실제로 뚫렸다는 뜻이라 명확한 에러로 바꿔 둔다.
            bid = bidRepository.save(Bid.place(auction, bidder, request.amount(), now));
        } catch (org.springframework.dao.DataIntegrityViolationException duplicatePrice) {
            throw new CustomException(ErrorCode.DUPLICATE_BID_PRICE);
        }

        // 여기서 실패(잔액 부족·다른 경매 보류 중)하면 위에서 만든 입찰·해제까지 전부 롤백된다.
        pointCommandPort.holdForBid(bidderId, auction.getId(), bid.getId(), request.amount());

        auction.applyBid(bidderId, request.amount(), now);

        return toSnapshot(auction);
    }

    /**
     * 입찰 내역 커서 페이징(AUCT-003). <b>비회원도 조회할 수 있다</b> — 시청자가 지금 얼마까지
     * 붙었는지 보는 것은 경매 참여가 아니라 관전이다.
     *
     * @param viewerId 조회한 회원 ID. 비회원이면 {@code null}이며 이때 {@code isMine}은 항상 false
     */
    public CursorPageResponse<BidResponse> getBidHistory(Long auctionId, Long cursor, int size, Long viewerId) {
        if (!auctionRepository.existsById(auctionId)) {
            throw new CustomException(ErrorCode.AUCTION_NOT_FOUND);
        }
        List<Bid> found =
                bidRepository.findPageByAuctionId(auctionId, cursor, PageRequest.of(0, size + 1));
        return CursorPageResponse.of(found, size, bid -> BidResponse.of(bid, viewerId), Bid::getId);
    }

    /**
     * 경매 결과 조회(AUCT-012). <b>비회원도 조회할 수 있다</b> — 입찰 내역과 같은 이유로
     * 누가 얼마에 가져갔는지는 관전 정보다.
     *
     * <p>아직 끝나지 않은 경매도 그대로 돌려준다 — 종료 여부 판단은 {@code status}로 한다.
     */
    public AuctionWinnerResponse getWinner(Long auctionId) {
        Auction auction = auctionRepository.findWithLiveById(auctionId)
                .orElseThrow(() -> new CustomException(ErrorCode.AUCTION_NOT_FOUND));

        String winnerNickname = auction.getWinnerId() == null
                ? null
                : memberRepository.findById(auction.getWinnerId())
                        .map(Member::getNickname)
                        .orElse(null);

        return AuctionWinnerResponse.of(
                auction, winnerNickname, bidRepository.countByAuction_Id(auctionId));
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