package com.ssafy.backend.auction.entity;

import static org.assertj.core.api.Assertions.assertThat;

import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.member.entity.Member;
import java.time.LocalDateTime;
import org.junit.jupiter.api.Test;

class AuctionTest {

    private static final Long PRODUCT_ID = 2001L;

    private final Live live = Live.openNow(
            Member.builder().email("host@example.com").password("encoded").name("호스트").build(),
            "빈티지 데님 라이브",
            null,
            LocalDateTime.of(2026, 7, 27, 21, 30));

    @Test
    void 경매_조건을_설정하면_READY_상태로_생성된다() {
        Auction auction = Auction.configure(live, PRODUCT_ID, 10_000L, 1_000L, 60);

        assertThat(auction.getStatus()).isEqualTo(AuctionStatus.READY);
        assertThat(auction.getLive()).isSameAs(live);
        assertThat(auction.getProductId()).isEqualTo(PRODUCT_ID);
        assertThat(auction.getStartPrice()).isEqualTo(10_000L);
        assertThat(auction.getBidUnit()).isEqualTo(1_000L);
        assertThat(auction.getDurationSeconds()).isEqualTo(60);
    }

    @Test
    void 시작_전_경매는_현재가가_0이고_입찰자_낙찰_정보가_비어_있다() {
        Auction auction = Auction.configure(live, PRODUCT_ID, 10_000L, 1_000L, 60);

        assertThat(auction.getCurrentPrice()).isZero();
        assertThat(auction.getExtensionCount()).isZero();
        assertThat(auction.getTopBidderId()).isNull();
        assertThat(auction.getWinnerId()).isNull();
        assertThat(auction.getFinalPrice()).isNull();
    }

    @Test
    void 시작_전_경매는_시작_종료_시각이_아직_정해지지_않는다() {
        Auction auction = Auction.configure(live, PRODUCT_ID, 10_000L, 1_000L, 60);

        assertThat(auction.getStartedAt()).isNull();
        assertThat(auction.getScheduledEndAt()).isNull();
        assertThat(auction.getEndedAt()).isNull();
    }
}