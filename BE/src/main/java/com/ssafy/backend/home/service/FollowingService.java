package com.ssafy.backend.home.service;

import com.ssafy.backend.home.dto.response.FollowingContentResponse;
import com.ssafy.backend.home.dto.response.LiveCardResponse;
import com.ssafy.backend.home.dto.response.ProductCardResponse;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 팔로잉 콘텐츠 조회(HOME-002) 서비스.
 *
 * <p><b>현재는 Mock 응답을 반환한다.</b> 팔로우 관계·상품은 서윤 도메인에 의존하는데 이번 주엔
 * 해당 테이블이 없다. FE가 Mock 기준으로 팔로잉 탭 개발에 착수할 수 있게 응답 스펙만 확정한다.
 * 2주차에 팔로우·상품 도메인이 준비되면 아래 {@code mock*} 조립부만 Repository 조회로 교체한다.
 */
@Service
@Transactional(readOnly = true)
public class FollowingService {

    public FollowingContentResponse getFollowingContent(Long memberId) {
        // TODO(2주차): Repository 조회로 교체 — memberId가 팔로우한 회원의 라이브(정윤)·상품(서윤) 조회
        List<LiveCardResponse> lives = mockFollowingLives();
        List<ProductCardResponse> products = mockFollowingProducts();
        boolean empty = lives.isEmpty() && products.isEmpty();
        return new FollowingContentResponse(empty, lives, products);
    }

    private List<LiveCardResponse> mockFollowingLives() {
        return List.of(
                new LiveCardResponse(103L, "단골 셀러 라이브", "빈티지장인",
                        "https://cdn.example.com/live/103.jpg", "LIVE", null, 64, 4)
        );
    }

    private List<ProductCardResponse> mockFollowingProducts() {
        return List.of(
                new ProductCardResponse(2003L, "폴로 램스울 니트", "Polo Ralph Lauren",
                        "https://cdn.example.com/product/2003.jpg", "NORMAL", "ON_SALE", 39000L, false)
        );
    }
}