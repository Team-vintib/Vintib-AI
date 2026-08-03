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
import com.ssafy.backend.auction.entity.AuctionStatus;
import com.ssafy.backend.auction.repository.AuctionRepository;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.repository.LiveProductRepository;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import java.time.LocalDateTime;
import java.util.Optional;
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

    @Mock
    private AuctionRepository auctionRepository;

    @Mock
    private LiveRepository liveRepository;

    @Mock
    private LiveProductRepository liveProductRepository;

    @Mock
    private Member host;

    private AuctionService auctionService;

    @BeforeEach
    void setUp() {
        auctionService = new AuctionService(auctionRepository, liveRepository, liveProductRepository);
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
}