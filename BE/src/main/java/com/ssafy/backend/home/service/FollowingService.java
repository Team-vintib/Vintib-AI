package com.ssafy.backend.home.service;

import com.ssafy.backend.home.dto.response.FollowedSellerResponse;
import com.ssafy.backend.home.dto.response.FollowingContentResponse;
import com.ssafy.backend.home.dto.response.LiveCardResponse;
import com.ssafy.backend.home.dto.response.ProductCardResponse;
import java.time.LocalDateTime;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 팔로잉 콘텐츠 조회(HOME-002) 서비스.
 *
 * <p><b>현재는 Mock 응답을 반환한다.</b> 팔로우 관계·상품은 서윤 도메인에 의존하는데 아직 팔로잉
 * 조회용 질의가 없다. FE가 Mock 기준으로 팔로잉 탭 개발에 착수할 수 있게 응답 스펙만 확정한다.
 * 실데이터 전환 시 아래 {@code mock*} 조립부만 Repository 조회로 교체한다.
 *
 * <p><b>{@code products}는 팔로우한 판매자의 상품이다</b> — 개인화 추천(REC-001)이 아니다.
 * FE가 이 목록을 '추천 상품'으로 표시하고 있었는데 의미가 다르다
 * (FE 요청 009-home-card-response-fields 요청 7).
 */
@Service
@Transactional(readOnly = true)
public class FollowingService {

    private static final String LIVE_THUMBNAIL = "https://picsum.photos/seed/live%d/640/360";
    private static final String PRODUCT_THUMBNAIL = "https://picsum.photos/seed/product%d/480/480";
    private static final String SELLER_PROFILE = "https://picsum.photos/seed/seller%d/200/200";
    private static final String SELLER_COVER = "https://picsum.photos/seed/seller%dcover/800/300";

    public FollowingContentResponse getFollowingContent(Long memberId) {
        // TODO: Repository 조회로 교체 — memberId가 팔로우한 회원의 라이브(정윤)·상품(서윤) 조회
        List<LiveCardResponse> lives = mockFollowingLives();
        List<ProductCardResponse> products = mockFollowingProducts(memberId);
        List<FollowedSellerResponse> followedSellers = mockFollowedSellers();
        boolean empty = lives.isEmpty() && products.isEmpty() && followedSellers.isEmpty();
        return new FollowingContentResponse(empty, lives, products, followedSellers);
    }

    private List<LiveCardResponse> mockFollowingLives() {
        return List.of(
                new LiveCardResponse(103L, "단골 셀러 라이브", "빈티지장인",
                        LIVE_THUMBNAIL.formatted(103), "LIVE",
                        null, LocalDateTime.now().minusMinutes(15), 64, 4)
        );
    }

    private List<ProductCardResponse> mockFollowingProducts(Long memberId) {
        return List.of(
                new ProductCardResponse(2003L, "폴로 램스울 니트", "Polo Ralph Lauren",
                        PRODUCT_THUMBNAIL.formatted(2003), "NORMAL", "ON_SALE", 39000L, false,
                        "빈티지장인", "상의", memberId == null ? null : true, null, null)
        );
    }

    private List<FollowedSellerResponse> mockFollowedSellers() {
        return List.of(
                new FollowedSellerResponse(31L, "빈티지장인",
                        SELLER_PROFILE.formatted(31), SELLER_COVER.formatted(31),
                        1284, 37,
                        103L, "LIVE", "단골 셀러 라이브", LocalDateTime.now().minusMinutes(15)),
                new FollowedSellerResponse(32L, "구제셀러",
                        SELLER_PROFILE.formatted(32), SELLER_COVER.formatted(32),
                        512, 18,
                        null, null, null, null)
        );
    }
}