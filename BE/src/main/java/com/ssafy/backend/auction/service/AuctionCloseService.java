package com.ssafy.backend.auction.service;

import com.ssafy.backend.auction.dto.response.AuctionSnapshotResponse;
import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.auction.entity.AuctionStatus;
import com.ssafy.backend.auction.entity.Bid;
import com.ssafy.backend.auction.entity.BidStatus;
import com.ssafy.backend.auction.port.OrderCommandPort;
import com.ssafy.backend.auction.port.PointCommandPort;
import com.ssafy.backend.auction.port.ProductCommandPort;
import com.ssafy.backend.auction.repository.AuctionRepository;
import com.ssafy.backend.auction.repository.BidRepository;
import com.ssafy.backend.live.port.NotificationCommandPort;
import com.ssafy.backend.live.port.ProductQueryPort;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.time.LocalDateTime;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 경매 마감 — 낙찰(AUCT-012)·유찰(AUCT-014)(Phase 8).
 *
 * <p><b>{@link AuctionService}와 나눈 이유.</b> 저쪽은 사람이 부르는 동작(조건 설정·시작·입찰)이고
 * 이쪽은 스케줄러와 방송 종료 훅이 부르는 동작이다. 트랜잭션 경계와 실패 처리 방식이 달라
 * (여기는 한 건이 실패해도 나머지를 계속 처리해야 한다) 한 클래스에 두면 서로의 규칙이 섞인다.
 *
 * <h2>마감 순서가 고정된 이유</h2>
 *
 * 상품 상태 변경({@link ProductCommandPort})이 <b>반드시 마지막</b>이다. 그 구현이 벌크 UPDATE라
 * {@code clearAutomatically = true}로 영속성 컨텍스트를 통째로 비운다 — 그 뒤에 엔티티를 더
 * 건드리면 변경이 반영되지 않고, 지연 로딩도 끊긴다. 그래서 응답 snapshot 도 그 전에 만든다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AuctionCloseService {

    /**
     * 한 주기에 마감하는 경매 수 상한. 밀린 경매가 쌓여 있어도 한 번에 전부 처리하지 않는다 —
     * 남는 것은 다음 주기(1초 뒤)에 이어서 마감된다.
     */
    private static final int MAX_CLOSE_BATCH_SIZE = 100;

    private final AuctionRepository auctionRepository;
    private final BidRepository bidRepository;
    private final MemberRepository memberRepository;
    private final ProductQueryPort productQueryPort;
    private final ProductCommandPort productCommandPort;
    private final PointCommandPort pointCommandPort;
    private final OrderCommandPort orderCommandPort;
    private final NotificationCommandPort notificationCommandPort;

    /**
     * 마감할 때가 된 경매 ID들. {@link AuctionCloseScheduler}가 이 목록을 받아
     * {@link #closeIfDue}를 하나씩 부른다.
     *
     * <p><b>루프를 여기 두지 않고 스케줄러에 맡기는 이유.</b> 경매마다 트랜잭션을 따로 열어야
     * 하는데(한 건이 터져도 나머지는 마감돼야 한다), 같은 클래스 안에서 {@code closeIfDue}를
     * 부르면 스프링 프록시를 거치지 않아 {@code @Transactional}이 통째로 무시된다.
     */
    @Transactional(readOnly = true)
    public List<Long> findDueAuctionIds() {
        return auctionRepository.findByStatusAndScheduledEndAtLessThanEqual(
                        AuctionStatus.RUNNING, LocalDateTime.now(), PageRequest.of(0, MAX_CLOSE_BATCH_SIZE))
                .stream()
                .map(Auction::getId)
                .toList();
    }

    /**
     * 종료 시각이 지났으면 마감한다. 아직 시간이 남았으면 아무 일도 하지 않는다.
     *
     * <p><b>후보를 고른 뒤 다시 확인하는 이유.</b> 그 사이 마감 직전 입찰이 들어와 종료 시각이
     * 밀렸을 수 있다(AUCT-010). 잠근 뒤 확인해야 "연장됐는데 마감된" 경매가 생기지 않는다.
     *
     * @return 마감했으면 그 현황, 마감할 때가 아니었으면 {@code null}
     */
    @Transactional
    public AuctionSnapshotResponse closeIfDue(Long auctionId) {
        Auction auction = auctionRepository.findByIdForUpdate(auctionId).orElse(null);
        if (auction == null || !auction.isDue(LocalDateTime.now())) {
            return null;
        }
        return close(auction);
    }

    /**
     * 방송이 끝날 때 아직 진행 중인 경매를 강제로 마감한다(AUCT-014).
     * {@code AuctionLiveCleanupHook}이 방송 상태 전이와 <b>같은 트랜잭션에서</b> 부른다.
     *
     * <p>여기서는 종료 시각을 보지 않는다 — 방송이 끝났으면 남은 시간과 무관하게 끝내야 한다.
     * 입찰이 있었으면 그 시점의 최고가로 낙찰시킨다(시간을 다 못 채웠다고 무효로 하면 이미
     * 보류된 포인트를 어떻게 할지가 더 복잡해진다).
     */
    @Transactional
    public List<AuctionSnapshotResponse> closeRunningAuctionsOfLive(Long liveId) {
        return auctionRepository.findByLiveIdAndStatus(liveId, AuctionStatus.RUNNING).stream()
                .map(this::close)
                .toList();
    }

    /** 낙찰/유찰 판정과 뒤처리. 호출부가 이미 상태와 잠금을 확인했다고 가정한다. */
    private AuctionSnapshotResponse close(Auction auction) {
        LocalDateTime now = LocalDateTime.now();

        // 입찰이 하나도 없으면 유찰이다 — 낙찰자도 낼 돈도 없어 뒤처리가 상품 상태 원복뿐이다.
        if (!auction.hasBid()) {
            auction.closeAsFailed(now);
            AuctionSnapshotResponse snapshot = toSnapshot(auction, now);
            // 시작할 때 AUCTION_IN_PROGRESS 로 옮겨 둔 것을 되돌린다. 그대로 두면 다음 라이브에서
            // 다시 경매에 걸 수 없고, 홈에서도 "경매 중"으로 계속 보인다.
            productCommandPort.markAuctionScheduled(auction.getProductId());
            return snapshot;
        }

        auction.closeAsSuccess(now);
        Member winner = settleBids(auction);

        // 주문을 먼저 만들어야 포인트 원장이 가리킬 주문 ID가 생긴다.
        Long orderId = orderCommandPort.createAuctionWinOrder(auction);
        pointCommandPort.convertHoldToPayment(auction.getId(), orderId);

        if (winner != null) {
            notificationCommandPort.notify(
                    winner,
                    "AUCTION_WON",
                    "낙찰되었습니다",
                    "%s원에 낙찰되었어요.".formatted(auction.getFinalPrice()),
                    "AUCTION",
                    auction.getId());
        }

        AuctionSnapshotResponse snapshot = toSnapshot(auction, now);
        // 반드시 마지막 — 이 호출이 영속성 컨텍스트를 비운다(클래스 주석 참고).
        productCommandPort.markSold(auction.getProductId());
        return snapshot;
    }

    /**
     * 입찰 결과를 확정한다 — 살아 있던 최고 입찰이 {@code WON}, 이미 밀린 입찰들이 {@code LOST}.
     *
     * @return 낙찰자. 활성 입찰을 찾지 못하면 {@code null}(정상 경로에서는 생기지 않는다)
     */
    private Member settleBids(Auction auction) {
        Member winner = null;
        for (Bid bid : bidRepository.findAllByAuction_Id(auction.getId())) {
            if (bid.getStatus() == BidStatus.ACTIVE) {
                bid.win();
                winner = bid.getBidder();
            } else {
                bid.lose();
            }
        }
        return winner;
    }

    /** {@link AuctionService#toSnapshot}과 같은 조립. 마감 시점에는 낙찰자 닉네임이 함께 실린다. */
    private AuctionSnapshotResponse toSnapshot(Auction auction, LocalDateTime now) {
        String productTitle = productQueryPort.findById(auction.getProductId())
                .map(ProductQueryPort.ProductSummary::title)
                .orElse(null);
        String bidderNickname = auction.getTopBidderId() == null
                ? null
                : memberRepository.findById(auction.getTopBidderId())
                        .map(Member::getNickname)
                        .orElse(null);

        return AuctionSnapshotResponse.of(
                auction, productTitle, bidderNickname, bidRepository.countByAuction_Id(auction.getId()), now);
    }
}
