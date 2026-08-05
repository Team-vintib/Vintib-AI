package com.ssafy.backend.auction.port;

/**
 * 경매가 상품 판매 상태를 바꾸는 유일한 창구.
 *
 * <p>경매와 상품 상태는 <b>짝을 이루지만 별개 축</b>이다 — 경매가 {@code READY}면 상품은
 * {@code AUCTION_SCHEDULED}, 경매가 {@code RUNNING}이면 상품은 {@code AUCTION_IN_PROGRESS}다.
 * 이 짝을 맞추지 않으면 홈·상품 목록에서 "경매 중인데 상시 판매로 보이는" 상품이 생긴다
 * (실제로 조건 설정 시 전이가 빠져 있어 상품이 {@code DRAFT}·{@code ON_SALE}에 머물렀다).
 *
 * <p><b>포트로 격리하는 이유.</b> {@code product}는 서윤 담당 영역이다. 경매 서비스가
 * {@code ProductRepository}를 직접 잡으면 상품 도메인이 바뀔 때 경매가 함께 깨지고, 같은 파일을
 * 양쪽에서 고쳐 병합 충돌이 잦아진다. {@code live/port/ProductQueryPort}와 같은 방식이다.
 */
public interface ProductCommandPort {

    /**
     * 경매 예정으로 표시한다(경매 조건 설정 시).
     *
     * @return 실제로 바뀐 상품 수(0이면 이미 그 상태였거나 상품이 없다)
     */
    int markAuctionScheduled(Long productId);

    /**
     * 경매 진행 중으로 표시한다(경매 시작 시).
     *
     * @return 실제로 바뀐 상품 수
     */
    int markAuctionInProgress(Long productId);

    /**
     * 낙찰돼 팔렸다고 표시한다(AUCT-012).
     *
     * <p>이게 빠지면 <b>같은 물건을 또 팔 수 있다</b> — 낙찰자만 기록되고 상품은 계속
     * {@code AUCTION_IN_PROGRESS}에 남아 다음 방송에서 다시 경매에 걸린다.
     *
     * @return 실제로 바뀐 상품 수
     */
    int markSold(Long productId);
}
