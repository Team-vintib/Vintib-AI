package com.ssafy.backend.auction.port;

import com.ssafy.backend.auction.entity.Auction;

/**
 * 경매 낙찰이 주문을 만드는 유일한 창구(AUCT-012).
 *
 * <p>{@code order}는 서윤 담당 영역이라 {@link ProductCommandPort}·{@link PointCommandPort}와
 * 같은 이유로 좁은 인터페이스 뒤에 숨긴다 — 경매 서비스가 {@code OrderRepository}와
 * {@code Product}·{@code Member} 엔티티를 직접 조립하면 주문 도메인이 바뀔 때 함께 깨진다.
 *
 * <p><b>왜 낙찰이 주문까지 만드는가.</b> 즉시구매와 달리 경매에는 구매자가 결제 버튼을 누르는
 * 시점이 없다 — 입찰한 순간 구매 의무가 확정되고(JY008 설계 판단 3) 그 금액이 이미 보류돼
 * 있다. 마감과 동시에 주문을 만들지 않으면 낙찰자의 포인트가 잠긴 채로 남고, 무엇보다
 * {@code ux_point_hold_member_active} 때문에 그 회원이 다른 경매에 입찰할 수 없게 된다
 * (설계 판단 12).
 */
public interface OrderCommandPort {

    /**
     * 낙찰 주문을 만든다. 상태는 {@code PAID}로 시작하며, 실제 대금 이동은 호출부가
     * {@link PointCommandPort#convertHoldToPayment}로 이어서 처리한다.
     *
     * <p>낙찰자·낙찰가는 이미 확정된 경매에서 읽는다 — {@link Auction#closeAsSuccess} 이후에
     * 부르거나, 최소한 {@code topBidderId}·{@code currentPrice}가 최종값인 시점이어야 한다.
     *
     * @return 만들어진 주문 ID
     * @throws com.ssafy.backend.global.exception.CustomException 상품이나 낙찰자가 없을 때
     */
    Long createAuctionWinOrder(Auction auction);
}
