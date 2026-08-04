package com.ssafy.backend.auction.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyCollection;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.auction.dto.request.AuctionConfigRequest;
import com.ssafy.backend.auction.dto.response.AuctionResponse;
import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.auction.dto.response.AuctionSnapshotResponse;
import com.ssafy.backend.auction.entity.AuctionStatus;
import com.ssafy.backend.auction.entity.Bid;
import com.ssafy.backend.auction.entity.BidStatus;
import com.ssafy.backend.auction.dto.request.BidRequest;
import com.ssafy.backend.auction.dto.response.BidResponse;
import com.ssafy.backend.auction.port.PointCommandPort;
import com.ssafy.backend.auction.port.ProductCommandPort;
import com.ssafy.backend.auction.repository.AuctionRepository;
import com.ssafy.backend.auction.repository.BidRepository;
import com.ssafy.backend.global.response.CursorPageResponse;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.port.NotificationCommandPort;
import com.ssafy.backend.live.port.ProductQueryPort;
import com.ssafy.backend.live.repository.LiveProductRepository;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Pageable;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class AuctionServiceTest {

    private static final Long HOST_ID = 1L;
    private static final Long OTHER_MEMBER_ID = 2L;
    private static final Long LIVE_ID = 101L;
    private static final Long PRODUCT_ID = 2001L;
    private static final Long AUCTION_ID = 301L;

    @Mock
    private AuctionRepository auctionRepository;

    @Mock
    private LiveRepository liveRepository;

    @Mock
    private LiveProductRepository liveProductRepository;

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
    private NotificationCommandPort notificationCommandPort;

    @Mock
    private Member host;

    @Mock
    private Member bidder;

    private AuctionService auctionService;

    @BeforeEach
    void setUp() {
        auctionService = new AuctionService(
                auctionRepository,
                bidRepository,
                liveRepository,
                liveProductRepository,
                memberRepository,
                productQueryPort,
                productCommandPort,
                pointCommandPort,
                notificationCommandPort);
    }

    private Live 진행중인_라이브() {
        when(host.getId()).thenReturn(HOST_ID);
        return Live.openNow(host, "빈티지 데님 라이브", null, null, LocalDateTime.now());
    }

    private AuctionConfigRequest 설정_요청() {
        return new AuctionConfigRequest(PRODUCT_ID, 10_000L, 1_000L, 60);
    }

    private void 연결된_상품이다() {
        when(liveProductRepository.existsByLiveIdAndProductIdAndRemovedAtIsNull(LIVE_ID, PRODUCT_ID))
                .thenReturn(true);
    }

    @Test
    void 연결된_상품에_조건을_설정하면_READY_경매가_생성된다() {
        Live live = 진행중인_라이브();
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live));
        연결된_상품이다();
        when(auctionRepository.existsByLiveIdAndProductIdAndStatusIn(
                eq(LIVE_ID), eq(PRODUCT_ID), anyCollection()))
                .thenReturn(false);
        when(auctionRepository.save(any(Auction.class))).thenAnswer(invocation -> invocation.getArgument(0));

        AuctionResponse response = auctionService.configureAuction(HOST_ID, LIVE_ID, 설정_요청());

        assertThat(response.status()).isEqualTo(AuctionStatus.READY);
        assertThat(response.productId()).isEqualTo(PRODUCT_ID);
        assertThat(response.startPrice()).isEqualTo(10_000L);
        assertThat(response.bidUnit()).isEqualTo(1_000L);
        assertThat(response.durationSeconds()).isEqualTo(60);
        // 아직 입찰이 없으므로 현재가는 0이다.
        assertThat(response.currentPrice()).isZero();
    }

    @Test
    void 라이브에_연결되지_않은_상품에는_경매를_걸_수_없다() {
        Live live = 진행중인_라이브();
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live));
        when(liveProductRepository.existsByLiveIdAndProductIdAndRemovedAtIsNull(LIVE_ID, PRODUCT_ID))
                .thenReturn(false);
        AuctionConfigRequest request = 설정_요청();

        assertThatThrownBy(() -> auctionService.configureAuction(HOST_ID, LIVE_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.LIVE_PRODUCT_NOT_FOUND);
        verify(auctionRepository, never()).save(any());
    }

    @Test
    void 같은_상품에_끝나지_않은_경매가_있으면_다시_설정할_수_없다() {
        Live live = 진행중인_라이브();
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live));
        연결된_상품이다();
        when(auctionRepository.existsByLiveIdAndProductIdAndStatusIn(
                eq(LIVE_ID), eq(PRODUCT_ID), anyCollection()))
                .thenReturn(true);
        AuctionConfigRequest request = 설정_요청();

        assertThatThrownBy(() -> auctionService.configureAuction(HOST_ID, LIVE_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.AUCTION_ALREADY_CONFIGURED);
        verify(auctionRepository, never()).save(any());
    }

    @Test
    void 본인_라이브가_아니면_경매를_설정할_수_없다() {
        when(host.getId()).thenReturn(HOST_ID);
        Live 남의_라이브 = Live.openNow(host, "남의 라이브", null, null, LocalDateTime.now());
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(남의_라이브));
        AuctionConfigRequest request = 설정_요청();

        assertThatThrownBy(() -> auctionService.configureAuction(OTHER_MEMBER_ID, LIVE_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.NOT_LIVE_HOST);
    }

    @Test
    void 존재하지_않는_라이브에는_경매를_설정할_수_없다() {
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.empty());
        AuctionConfigRequest request = 설정_요청();

        assertThatThrownBy(() -> auctionService.configureAuction(HOST_ID, LIVE_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.LIVE_NOT_FOUND);
    }

    @Test
    void 조건을_설정하면_상품이_경매_예정으로_바뀐다() {
        // 이게 빠져 있어서 조건을 걸어도 상품은 DRAFT·ON_SALE 에 머물렀고 홈에 상시 판매처럼 보였다.
        Live live = 진행중인_라이브();
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live));
        연결된_상품이다();
        when(auctionRepository.existsByLiveIdAndProductIdAndStatusIn(
                eq(LIVE_ID), eq(PRODUCT_ID), anyCollection()))
                .thenReturn(false);
        when(auctionRepository.save(any(Auction.class))).thenAnswer(invocation -> invocation.getArgument(0));

        auctionService.configureAuction(HOST_ID, LIVE_ID, 설정_요청());

        verify(productCommandPort).markAuctionScheduled(PRODUCT_ID);
    }

    // ---------- 현황 조회 (AUCT-002) ----------

    private Auction 준비된_경매(Live live) {
        return Auction.configure(live, PRODUCT_ID, 10_000L, 1_000L, 60);
    }

    @Test
    void 경매가_없으면_현황은_null이다() {
        // 아직 경매를 걸지 않은 방송이 정상이다. 404 로 만들면 시청자 진입마다 에러가 뜬다.
        when(liveRepository.existsById(LIVE_ID)).thenReturn(true);
        when(auctionRepository.findPanelCandidates(eq(LIVE_ID), any(Pageable.class)))
                .thenReturn(List.of());

        assertThat(auctionService.getCurrentSnapshot(LIVE_ID)).isNull();
    }

    @Test
    void 존재하지_않는_라이브의_현황은_조회할_수_없다() {
        when(liveRepository.existsById(LIVE_ID)).thenReturn(false);

        assertThatThrownBy(() -> auctionService.getCurrentSnapshot(LIVE_ID))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.LIVE_NOT_FOUND);
    }

    @Test
    void 입찰이_없으면_다음_입찰가는_시작가_그대로다() {
        // 시작가에 증액 단위를 더하면 시작가로는 아무도 살 수 없어 "시작가"가 무의미해진다.
        // 현황 조회에는 호스트 판정이 없으므로 host.getId() 를 스텁하지 않는다.
        Auction auction = 준비된_경매(Live.openNow(host, "빈티지 데님 라이브", null, null, LocalDateTime.now()));
        when(liveRepository.existsById(LIVE_ID)).thenReturn(true);
        when(auctionRepository.findPanelCandidates(eq(LIVE_ID), any(Pageable.class)))
                .thenReturn(List.of(auction));
        when(productQueryPort.findById(PRODUCT_ID))
                .thenReturn(Optional.of(new ProductQueryPort.ProductSummary(PRODUCT_ID, HOST_ID, "리바이스 501")));

        AuctionSnapshotResponse snapshot = auctionService.getCurrentSnapshot(LIVE_ID);

        assertThat(snapshot.currentPrice()).isZero();
        assertThat(snapshot.nextBidPrice()).isEqualTo(10_000L);
        assertThat(snapshot.highestBidderId()).isNull();
        assertThat(snapshot.highestBidderNickname()).isNull();
        assertThat(snapshot.productTitle()).isEqualTo("리바이스 501");
        // 남은 시간 계산의 기준점이다. 없으면 FE 가 자기 시계로 카운트다운해 서버와 어긋난다.
        assertThat(snapshot.serverNow()).isNotNull();
    }

    // ---------- 경매 시작 (AUCT-002) ----------

    @Test
    void 준비된_경매를_시작하면_RUNNING이_되고_종료_예정_시각이_박힌다() {
        Live live = 진행중인_라이브();
        Auction auction = 준비된_경매(live);
        when(auctionRepository.findWithLiveById(AUCTION_ID)).thenReturn(Optional.of(auction));
        when(auctionRepository.existsByLiveIdAndStatus(any(), eq(AuctionStatus.RUNNING))).thenReturn(false);
        when(productQueryPort.findById(PRODUCT_ID)).thenReturn(Optional.empty());

        AuctionSnapshotResponse snapshot = auctionService.startAuction(HOST_ID, AUCTION_ID);

        assertThat(snapshot.status()).isEqualTo(AuctionStatus.RUNNING);
        assertThat(snapshot.startedAt()).isNotNull();
        // 종료 예정 시각 = 시작 + 진행 시간. 연장은 이후 입찰에서 따로 밀린다.
        assertThat(snapshot.endsAt()).isEqualTo(snapshot.startedAt().plusSeconds(60));
        // 경매가 돌면 상품도 "경매 진행 중"이어야 한다 — 두 상태는 짝이다.
        verify(productCommandPort).markAuctionInProgress(PRODUCT_ID);
    }

    @Test
    void 이미_진행_중인_경매는_다시_시작할_수_없다() {
        // 다시 시작하면 종료 시각이 밀려 이미 들어온 입찰의 기회가 뒤집힌다.
        Live live = 진행중인_라이브();
        Auction auction = 준비된_경매(live);
        auction.start(LocalDateTime.now());
        when(auctionRepository.findWithLiveById(AUCTION_ID)).thenReturn(Optional.of(auction));

        assertThatThrownBy(() -> auctionService.startAuction(HOST_ID, AUCTION_ID))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.AUCTION_NOT_STARTABLE);
    }

    @Test
    void 한_라이브에_진행_중인_경매가_있으면_다른_경매를_시작할_수_없다() {
        // 둘이 동시에 돌면 시청자가 어느 쪽에 입찰하는지 알 수 없고 화면도 하나뿐이다(LIVE-004).
        Live live = 진행중인_라이브();
        Auction auction = 준비된_경매(live);
        when(auctionRepository.findWithLiveById(AUCTION_ID)).thenReturn(Optional.of(auction));
        when(auctionRepository.existsByLiveIdAndStatus(any(), eq(AuctionStatus.RUNNING))).thenReturn(true);

        assertThatThrownBy(() -> auctionService.startAuction(HOST_ID, AUCTION_ID))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.AUCTION_ALREADY_RUNNING);
    }

    @Test
    void 본인_라이브가_아니면_경매를_시작할_수_없다() {
        Live live = 진행중인_라이브();
        Auction auction = 준비된_경매(live);
        when(auctionRepository.findWithLiveById(AUCTION_ID)).thenReturn(Optional.of(auction));

        assertThatThrownBy(() -> auctionService.startAuction(OTHER_MEMBER_ID, AUCTION_ID))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.NOT_LIVE_HOST);
    }

    @Test
    void 종료된_방송의_경매는_시작할_수_없다() {
        Live live = 진행중인_라이브();
        live.transitionTo(com.ssafy.backend.live.entity.LiveStatus.ENDED, LocalDateTime.now());
        Auction auction = 준비된_경매(live);
        when(auctionRepository.findWithLiveById(AUCTION_ID)).thenReturn(Optional.of(auction));

        assertThatThrownBy(() -> auctionService.startAuction(HOST_ID, AUCTION_ID))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_LIVE_STATE);
    }

    @Test
    void 존재하지_않는_경매는_시작할_수_없다() {
        when(auctionRepository.findWithLiveById(AUCTION_ID)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> auctionService.startAuction(HOST_ID, AUCTION_ID))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.AUCTION_NOT_FOUND);
    }

    @Test
    void 시작에_실패하면_상품_상태를_건드리지_않는다() {
        Live live = 진행중인_라이브();
        Auction auction = 준비된_경매(live);
        when(auctionRepository.findWithLiveById(AUCTION_ID)).thenReturn(Optional.of(auction));

        assertThatThrownBy(() -> auctionService.startAuction(OTHER_MEMBER_ID, AUCTION_ID))
                .isInstanceOf(CustomException.class);

        verify(productCommandPort, never()).markAuctionInProgress(any());
    }

    // ---------- 입찰 (AUCT-003~006) ----------

    /** 경매 ID가 실제로 채워진 진행 중 경매. {@code Auction.configure}는 ID를 채우지 않으므로
     *  {@code holdForBid(..., auction.getId(), ...)} 검증에 실제 값을 쓰려면 직접 넣어야 한다. */
    private Auction 진행중인_경매() {
        Auction auction = 준비된_경매(Live.openNow(host, "빈티지 데님 라이브", null, null, LocalDateTime.now()));
        org.springframework.test.util.ReflectionTestUtils.setField(auction, "id", AUCTION_ID);
        auction.start(LocalDateTime.now());
        return auction;
    }

    private Bid 저장된_입찰(Auction auction, Member bidder, long amount) {
        Bid bid = Bid.place(auction, bidder, amount, LocalDateTime.now());
        org.springframework.test.util.ReflectionTestUtils.setField(bid, "id", 9001L);
        return bid;
    }

    private void 입찰_처리를_준비한다(Auction auction) {
        when(auctionRepository.findByIdForUpdate(AUCTION_ID)).thenReturn(Optional.of(auction));
        when(memberRepository.findById(OTHER_MEMBER_ID)).thenReturn(Optional.of(bidder));
        when(bidRepository.save(any(Bid.class))).thenAnswer(invocation -> {
            Bid bid = invocation.getArgument(0);
            org.springframework.test.util.ReflectionTestUtils.setField(bid, "id", 9001L);
            return bid;
        });
    }

    @Test
    void 첫_입찰은_시작가로_성공한다() {
        Auction auction = 진행중인_경매();
        입찰_처리를_준비한다(auction);

        AuctionSnapshotResponse snapshot =
                auctionService.placeBid(OTHER_MEMBER_ID, AUCTION_ID, new BidRequest(10_000L));

        assertThat(snapshot.currentPrice()).isEqualTo(10_000L);
        assertThat(snapshot.highestBidderId()).isEqualTo(OTHER_MEMBER_ID);
        // 첫 입찰에는 풀어 줄 직전 최고 입찰자가 없다.
        verify(pointCommandPort, never()).releaseHoldForAuction(any());
        verify(pointCommandPort).holdForBid(OTHER_MEMBER_ID, AUCTION_ID, 9001L, 10_000L);
    }

    @Test
    void 상위_입찰이_들어오면_직전_최고_입찰자의_보류가_해제되고_그_입찰은_OUTBID된다() {
        Auction auction = 진행중인_경매();
        auction.applyBid(HOST_ID, 10_000L, LocalDateTime.now());
        Bid 직전_입찰 = 저장된_입찰(auction, host, 10_000L);
        when(bidRepository.findByAuction_IdAndStatus(AUCTION_ID, BidStatus.ACTIVE))
                .thenReturn(Optional.of(직전_입찰));
        입찰_처리를_준비한다(auction);

        auctionService.placeBid(OTHER_MEMBER_ID, AUCTION_ID, new BidRequest(11_000L));

        assertThat(직전_입찰.getStatus()).isEqualTo(BidStatus.OUTBID);
        verify(pointCommandPort).releaseHoldForAuction(AUCTION_ID);
        verify(notificationCommandPort).notify(
                eq(host), eq("AUCTION_OUTBID"), any(), any(), eq("AUCTION"), eq(AUCTION_ID));
    }

    @Test
    void 첫_입찰에는_밀린_사람이_없어_알림도_없다() {
        Auction auction = 진행중인_경매();
        입찰_처리를_준비한다(auction);

        auctionService.placeBid(OTHER_MEMBER_ID, AUCTION_ID, new BidRequest(10_000L));

        verify(notificationCommandPort, never()).notify(any(), any(), any(), any(), any(), any());
    }

    @Test
    void 진행_중이_아닌_경매는_입찰할_수_없다() {
        // READY, 아직 시작 전 — host.getId() 스텁이 필요한 경로(configureAuction)를 타지 않는다.
        Auction auction = 준비된_경매(Live.openNow(host, "빈티지 데님 라이브", null, null, LocalDateTime.now()));
        when(auctionRepository.findByIdForUpdate(AUCTION_ID)).thenReturn(Optional.of(auction));

        assertThatThrownBy(() -> auctionService.placeBid(OTHER_MEMBER_ID, AUCTION_ID, new BidRequest(10_000L)))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.AUCTION_NOT_ACTIVE);
    }

    @Test
    void 종료_시각이_지난_경매는_입찰할_수_없다() {
        Auction auction = 준비된_경매(Live.openNow(host, "빈티지 데님 라이브", null, null, LocalDateTime.now()));
        auction.start(LocalDateTime.now().minusSeconds(120)); // durationSeconds=60 → 이미 지남
        when(auctionRepository.findByIdForUpdate(AUCTION_ID)).thenReturn(Optional.of(auction));

        assertThatThrownBy(() -> auctionService.placeBid(OTHER_MEMBER_ID, AUCTION_ID, new BidRequest(10_000L)))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.AUCTION_NOT_ACTIVE);
    }

    @Test
    void 직전_최고_입찰자_본인은_연속으로_입찰할_수_없다() {
        // AUCT-006 — 이미 HELD 보류를 쥐고 있어 두 번째 보류를 만들 수 없다는 전제와 짝이다.
        Auction auction = 진행중인_경매();
        auction.applyBid(OTHER_MEMBER_ID, 10_000L, LocalDateTime.now());
        when(auctionRepository.findByIdForUpdate(AUCTION_ID)).thenReturn(Optional.of(auction));

        assertThatThrownBy(() -> auctionService.placeBid(OTHER_MEMBER_ID, AUCTION_ID, new BidRequest(11_000L)))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.CONSECUTIVE_BID_NOT_ALLOWED);
    }

    @Test
    void 다음_입찰가보다_낮으면_거부된다() {
        Auction auction = 진행중인_경매();
        when(auctionRepository.findByIdForUpdate(AUCTION_ID)).thenReturn(Optional.of(auction));

        assertThatThrownBy(() -> auctionService.placeBid(OTHER_MEMBER_ID, AUCTION_ID, new BidRequest(9_000L)))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.BID_LOWER_THAN_CURRENT);
    }

    @Test
    void 다음_입찰가보다_높으면_거부된다() {
        // 화면에 보이던 nextBidPrice 가 그 사이 바뀌었다는 뜻이다.
        Auction auction = 진행중인_경매();
        when(auctionRepository.findByIdForUpdate(AUCTION_ID)).thenReturn(Optional.of(auction));

        assertThatThrownBy(() -> auctionService.placeBid(OTHER_MEMBER_ID, AUCTION_ID, new BidRequest(50_000L)))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.BID_PRICE_MISMATCH);
    }

    @Test
    void 종료_임박_입찰이면_5초_연장된다() {
        // durationSeconds=60, 58초 전에 시작 → 종료까지 2초 남음(3초 이내) → 연장 대상.
        Auction auction = 준비된_경매(Live.openNow(host, "빈티지 데님 라이브", null, null, LocalDateTime.now()));
        auction.start(LocalDateTime.now().minusSeconds(58));
        LocalDateTime endBeforeBid = auction.getScheduledEndAt();
        입찰_처리를_준비한다(auction);

        AuctionSnapshotResponse snapshot =
                auctionService.placeBid(OTHER_MEMBER_ID, AUCTION_ID, new BidRequest(10_000L));

        assertThat(snapshot.extensionCount()).isEqualTo((short) 1);
        assertThat(snapshot.endsAt()).isEqualTo(endBeforeBid.plusSeconds(5));
    }

    @Test
    void 포인트_보류가_실패하면_예외가_전파된다() {
        Auction auction = 진행중인_경매();
        입찰_처리를_준비한다(auction);
        org.mockito.Mockito.doThrow(new CustomException(ErrorCode.INSUFFICIENT_POINTS))
                .when(pointCommandPort).holdForBid(any(), any(), any(), org.mockito.ArgumentMatchers.anyLong());

        assertThatThrownBy(() -> auctionService.placeBid(OTHER_MEMBER_ID, AUCTION_ID, new BidRequest(10_000L)))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INSUFFICIENT_POINTS);
    }

    @Test
    void 존재하지_않는_경매에는_입찰할_수_없다() {
        when(auctionRepository.findByIdForUpdate(AUCTION_ID)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> auctionService.placeBid(OTHER_MEMBER_ID, AUCTION_ID, new BidRequest(10_000L)))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.AUCTION_NOT_FOUND);
    }

    // ---------- 입찰 내역 조회 ----------

    @Test
    void 입찰_내역이_최신순으로_반환되고_본인_여부가_표시된다() {
        Auction auction = 진행중인_경매();
        Bid bid = 저장된_입찰(auction, bidder, 10_000L);
        when(bidder.getId()).thenReturn(OTHER_MEMBER_ID);
        when(auctionRepository.existsById(AUCTION_ID)).thenReturn(true);
        when(bidRepository.findPageByAuctionId(eq(AUCTION_ID), eq(null), any()))
                .thenReturn(List.of(bid));

        CursorPageResponse<BidResponse> response =
                auctionService.getBidHistory(AUCTION_ID, null, 20, OTHER_MEMBER_ID);

        assertThat(response.content()).hasSize(1);
        assertThat(response.content().get(0).isMine()).isTrue();
        assertThat(response.hasNext()).isFalse();
    }

    @Test
    void 비회원이_조회하면_isMine이_항상_false다() {
        Auction auction = 진행중인_경매();
        Bid bid = 저장된_입찰(auction, bidder, 10_000L);
        when(bidder.getId()).thenReturn(OTHER_MEMBER_ID);
        when(auctionRepository.existsById(AUCTION_ID)).thenReturn(true);
        when(bidRepository.findPageByAuctionId(eq(AUCTION_ID), eq(null), any()))
                .thenReturn(List.of(bid));

        CursorPageResponse<BidResponse> response =
                auctionService.getBidHistory(AUCTION_ID, null, 20, null);

        assertThat(response.content().get(0).isMine()).isFalse();
    }

    @Test
    void 존재하지_않는_경매의_입찰_내역은_조회할_수_없다() {
        when(auctionRepository.existsById(AUCTION_ID)).thenReturn(false);

        assertThatThrownBy(() -> auctionService.getBidHistory(AUCTION_ID, null, 20, null))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.AUCTION_NOT_FOUND);
    }
}