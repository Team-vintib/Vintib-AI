package com.ssafy.backend.auction.port;

/**
 * 경매 입찰이 포인트를 보류·해제하는 유일한 창구(AUCT-007~009).
 *
 * <p>포인트 잔액 이동·원장 기록은 {@code point} 패키지 엔티티(《PointAccount》·《PointHold》·
 * 《PointTransaction》) 세 개를 함께 다뤄야 하는데, {@code AuctionService}가 그 셋을 직접 조립하면
 * 포인트 도메인 내부 구조가 바뀔 때마다 경매 코드가 함께 흔들린다. {@code ProductCommandPort}와
 * 같은 이유로 좁은 인터페이스 뒤에 숨긴다.
 *
 * <p>두 메서드 다 <b>실패하면 예외를 던진다</b> — 잔액 부족·다른 경매 보류 중복은 경매
 * 서비스가 판단할 게 아니라 포인트 상태 그 자체가 아는 사실이라 여기서 확정한다.
 */
public interface PointCommandPort {

    /**
     * 새 최고 입찰의 보류를 만든다. {@code available → bidHeld}로 옮기고 원장에 남긴다.
     *
     * @throws com.ssafy.backend.global.exception.CustomException
     *         잔액 부족(INSUFFICIENT_POINTS) 또는 이미 다른 경매에서 최고 입찰자로
     *         보류 중(ACTIVE_HOLD_ELSEWHERE)일 때
     */
    void holdForBid(Long memberId, Long auctionId, Long bidId, long amount);

    /**
     * 이 경매의 현재 보류를 해제한다(상위 입찰에 밀렸을 때). <b>보류가 없으면 아무 일도
     * 하지 않는다</b> — 첫 입찰에는 풀어 줄 직전 최고 입찰자가 없다.
     */
    void releaseHoldForAuction(Long auctionId);

    /**
     * 낙찰자의 보류를 거래 대금으로 전환한다(AUCT-012). {@code bidHeld → available → tradeEscrow}로
     * 옮기고 원장에 {@code BID_RELEASE}·{@code PAYMENT} 두 건을 남긴다.
     *
     * <p><b>보류를 그대로 두면 안 되는 이유.</b> 낙찰자의 포인트가 영구히 잠기는 것도 문제지만,
     * 더 큰 것은 {@code ux_point_hold_member_active} 때문에 <b>그 회원이 이후 어떤 경매에도
     * 입찰할 수 없게 된다</b>는 점이다.
     *
     * <p>보류가 없으면 아무 일도 하지 않는다 — 입찰이 하나도 없던 경매(유찰)에는 전환할 대상이 없다.
     *
     * @param orderId 이 낙찰로 만들어진 주문. 원장의 {@code PAYMENT} 기록이 가리킨다
     */
    void convertHoldToPayment(Long auctionId, Long orderId);
}
