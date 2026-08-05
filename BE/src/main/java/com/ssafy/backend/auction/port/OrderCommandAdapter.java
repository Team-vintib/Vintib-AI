package com.ssafy.backend.auction.port;

import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.order.entity.Order;
import com.ssafy.backend.order.repository.OrderRepository;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.ProductRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

/**
 * {@link OrderCommandPort}의 유일한 구현. 주문 도메인에 대한 의존을 이 파일 하나로 묶는다
 * ({@link PointCommandAdapter}와 같은 구조).
 *
 * <p>판매자는 요청에서 받지 않고 <b>상품에서 읽는다</b> — 낙찰 주문은 사람이 만드는 것이
 * 아니라 스케줄러가 만들기 때문에, 넘겨받을 곳도 없고 넘겨받으면 오히려 상품 소유자와
 * 어긋날 여지가 생긴다.
 */
@Component
@RequiredArgsConstructor
public class OrderCommandAdapter implements OrderCommandPort {

    private final OrderRepository orderRepository;
    private final ProductRepository productRepository;
    private final MemberRepository memberRepository;

    @Override
    public Long createAuctionWinOrder(Auction auction) {
        Product product = productRepository.findById(auction.getProductId())
                .orElseThrow(() -> new CustomException(ErrorCode.PRODUCT_NOT_FOUND));
        Member buyer = memberRepository.findById(auction.getWinnerId())
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

        Order order = orderRepository.save(Order.createAuctionWin(
                buyer, product.getSeller(), product, auction, auction.getFinalPrice()));
        return order.getId();
    }
}
