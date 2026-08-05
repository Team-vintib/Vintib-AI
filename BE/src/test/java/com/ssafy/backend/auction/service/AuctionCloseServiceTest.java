package com.ssafy.backend.auction.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

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
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.port.NotificationCommandPort;
import com.ssafy.backend.live.port.ProductQueryPort;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class AuctionCloseServiceTest {

    private static final Long BIDDER_ID = 7L;
    private static final Long LIVE_ID = 101L;
    private static final Long PRODUCT_ID = 2001L;
    private static final Long AUCTION_ID = 301L;
    private static final Long ORDER_ID = 5001L;

    @Mock
    private AuctionRepository auctionRepository;

    @Mock
    private BidRepository bidRepository;

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private ProductQueryPort productQueryPort;

    @Mock
    private ProductCommandPort productCommandPort;

    @Mock
    private PointCommandPort pointCommandPort;

    @Mock
    private OrderCommandPort orderCommandPort;

    @Mock
    private NotificationCommandPort notificationCommandPort;

    @Mock
    private Member host;

    @Mock
    private Member bidder;

    private AuctionCloseService auctionCloseService;

    @BeforeEach
    void setUp() {
        auctionCloseService = new AuctionCloseService(
                auctionRepository,
                bidRepository,
                memberRepository,
                productQueryPort,
                productCommandPort,
                pointCommandPort,
                orderCommandPort,
                notificationCommandPort);
    }

    /** 종료 시각이 이미 지난 진행 중 경매. 시작 후 시계를 되돌릴 수 없어 필드를 직접 당긴다. */
    private Auction 마감할_때가_된_경매() {
        Live live = Live.openNow(host, "빈티지 데님 라이브", null, null, LocalDateTime.now());
        ReflectionTestUtils.setField(live, "id", LIVE_ID);

        Auction auction = Auction.configure(live, PRODUCT_ID, 10_000L, 1_000L, 60);
        ReflectionTestUtils.setField(auction, "id", AUCTION_ID);
        auction.start(LocalDateTime.now());
        ReflectionTestUtils.setField(auction, "scheduledEndAt", LocalDateTime.now().minusSeconds(1));
        return auction;
    }

    private void 입찰이_있다(Auction auction, long amount) {
        auction.applyBid(BIDDER_ID, amount, LocalDateTime.now().minusSeconds(30));
    }

    @Test
    void 입찰이_있으면_낙찰로_마감되고_상품이_SOLD가_된다() {
        Auction auction = 마감할_때가_된_경매();
        입찰이_있다(auction, 45_000L);
        when(auctionRepository.findByIdForUpdate(AUCTION_ID)).thenReturn(Optional.of(auction));
        when(bidRepository.findAllByAuction_Id(AUCTION_ID))
                .thenReturn(List.of(활성_입찰(auction, 45_000L)));
        when(orderCommandPort.createAuctionWinOrder(auction)).thenReturn(ORDER_ID);

        AuctionSnapshotResponse snapshot = auctionCloseService.closeIfDue(AUCTION_ID);

        assertThat(snapshot).isNotNull();
        assertThat(snapshot.status()).isEqualTo(AuctionStatus.SUCCESS);
        assertThat(auction.getWinnerId()).isEqualTo(BIDDER_ID);
        assertThat(auction.getFinalPrice()).isEqualTo(45_000L);
        assertThat(auction.getEndedAt()).isNotNull();
        // 이게 빠지면 같은 물건을 다음 방송에서 또 팔 수 있다.
        verify(productCommandPort).markSold(PRODUCT_ID);
    }

    @Test
    void 낙찰되면_주문이_생기고_보류가_결제로_전환된다() {
        Auction auction = 마감할_때가_된_경매();
        입찰이_있다(auction, 45_000L);
        when(auctionRepository.findByIdForUpdate(AUCTION_ID)).thenReturn(Optional.of(auction));
        when(bidRepository.findAllByAuction_Id(AUCTION_ID))
                .thenReturn(List.of(활성_입찰(auction, 45_000L)));
        when(orderCommandPort.createAuctionWinOrder(auction)).thenReturn(ORDER_ID);

        auctionCloseService.closeIfDue(AUCTION_ID);

        // 보류를 그대로 두면 낙찰자 포인트가 잠기고, 그 회원이 다른 경매에 입찰할 수 없게 된다.
        verify(pointCommandPort).convertHoldToPayment(AUCTION_ID, ORDER_ID);
    }

    @Test
    void 낙찰되면_최고_입찰은_WON_밀린_입찰은_LOST가_된다() {
        Auction auction = 마감할_때가_된_경매();
        입찰이_있다(auction, 45_000L);
        Bid 밀린_입찰 = 활성_입찰(auction, 44_000L);
        밀린_입찰.outbid();
        Bid 최고_입찰 = 활성_입찰(auction, 45_000L);
        when(auctionRepository.findByIdForUpdate(AUCTION_ID)).thenReturn(Optional.of(auction));
        when(bidRepository.findAllByAuction_Id(AUCTION_ID)).thenReturn(List.of(밀린_입찰, 최고_입찰));
        when(orderCommandPort.createAuctionWinOrder(auction)).thenReturn(ORDER_ID);

        auctionCloseService.closeIfDue(AUCTION_ID);

        assertThat(최고_입찰.getStatus()).isEqualTo(BidStatus.WON);
        assertThat(밀린_입찰.getStatus()).isEqualTo(BidStatus.LOST);
    }

    @Test
    void 낙찰되면_낙찰자에게_알림이_간다() {
        Auction auction = 마감할_때가_된_경매();
        입찰이_있다(auction, 45_000L);
        when(auctionRepository.findByIdForUpdate(AUCTION_ID)).thenReturn(Optional.of(auction));
        when(bidRepository.findAllByAuction_Id(AUCTION_ID))
                .thenReturn(List.of(활성_입찰(auction, 45_000L)));
        when(orderCommandPort.createAuctionWinOrder(auction)).thenReturn(ORDER_ID);

        auctionCloseService.closeIfDue(AUCTION_ID);

        verify(notificationCommandPort).notify(
                eq(bidder), eq("AUCTION_WON"), any(), any(), eq("AUCTION"), eq(AUCTION_ID));
    }

    @Test
    void 입찰이_하나도_없으면_유찰되고_상품은_경매_예정으로_돌아간다() {
        Auction auction = 마감할_때가_된_경매();
        when(auctionRepository.findByIdForUpdate(AUCTION_ID)).thenReturn(Optional.of(auction));

        AuctionSnapshotResponse snapshot = auctionCloseService.closeIfDue(AUCTION_ID);

        assertThat(snapshot).isNotNull();
        assertThat(snapshot.status()).isEqualTo(AuctionStatus.FAILED);
        assertThat(auction.getWinnerId()).isNull();
        assertThat(auction.getFinalPrice()).isNull();
        // AUCTION_FAILED 상태는 없어졌다(SY013) — 시작할 때 옮겨 둔 것을 되돌리기만 한다.
        verify(productCommandPort).markAuctionScheduled(PRODUCT_ID);
        verify(productCommandPort, never()).markSold(anyLong());
    }

    @Test
    void 유찰이면_주문도_포인트_전환도_없다() {
        Auction auction = 마감할_때가_된_경매();
        when(auctionRepository.findByIdForUpdate(AUCTION_ID)).thenReturn(Optional.of(auction));

        auctionCloseService.closeIfDue(AUCTION_ID);

        verify(orderCommandPort, never()).createAuctionWinOrder(any());
        verify(pointCommandPort, never()).convertHoldToPayment(anyLong(), anyLong());
    }

    @Test
    void 마감_직전_입찰로_연장됐으면_마감하지_않는다() {
        // 후보를 고른 뒤 잠그기 전에 입찰이 들어와 종료 시각이 밀린 상황(AUCT-010).
        Auction auction = 마감할_때가_된_경매();
        ReflectionTestUtils.setField(auction, "scheduledEndAt", LocalDateTime.now().plusSeconds(5));
        when(auctionRepository.findByIdForUpdate(AUCTION_ID)).thenReturn(Optional.of(auction));

        assertThat(auctionCloseService.closeIfDue(AUCTION_ID)).isNull();
        assertThat(auction.getStatus()).isEqualTo(AuctionStatus.RUNNING);
    }

    @Test
    void 이미_마감된_경매는_다시_마감하지_않는다() {
        Auction auction = 마감할_때가_된_경매();
        auction.closeAsFailed(LocalDateTime.now());
        when(auctionRepository.findByIdForUpdate(AUCTION_ID)).thenReturn(Optional.of(auction));

        assertThat(auctionCloseService.closeIfDue(AUCTION_ID)).isNull();
    }

    @Test
    void 방송이_끝나면_남은_시간과_무관하게_강제로_마감된다() {
        Auction auction = 마감할_때가_된_경매();
        // 아직 한참 남았지만 방송이 끝나면 끝내야 한다.
        ReflectionTestUtils.setField(auction, "scheduledEndAt", LocalDateTime.now().plusMinutes(5));
        when(auctionRepository.findByLiveIdAndStatus(LIVE_ID, AuctionStatus.RUNNING))
                .thenReturn(List.of(auction));

        List<AuctionSnapshotResponse> closed = auctionCloseService.closeRunningAuctionsOfLive(LIVE_ID);

        assertThat(closed).hasSize(1);
        assertThat(auction.getStatus()).isEqualTo(AuctionStatus.FAILED);
    }

    private Bid 활성_입찰(Auction auction, long amount) {
        Bid bid = Bid.place(auction, bidder, amount, LocalDateTime.now());
        ReflectionTestUtils.setField(bid, "id", 9001L);
        return bid;
    }
}
