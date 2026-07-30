package com.ssafy.backend.home.service;

import com.ssafy.backend.home.dto.response.CategoryProductSectionResponse;
import com.ssafy.backend.home.dto.response.HomeContentResponse;
import com.ssafy.backend.home.dto.response.LiveCardResponse;
import com.ssafy.backend.home.dto.response.ProductCardResponse;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 홈 콘텐츠 조회(HOME-001) 서비스.
 *
 * <p><b>현재는 Mock 응답을 반환한다.</b> 홈에 노출할 라이브는 내 도메인, 상품은 서윤 도메인에 의존하는데
 * 아직 홈 조회용 질의가 없다. FE가 Mock 기준으로 홈 화면 개발에 착수할 수 있게 응답 스펙만 확정한다.
 * 실데이터 전환 시 아래 {@code mock*} 조립부만 Repository 조회로 교체한다.
 *
 * <p><b>썸네일은 실제로 열리는 URL을 쓴다.</b> 이전에는 {@code cdn.example.com}을 썼는데 접근이
 * 안 돼 FE가 카드마다 onerror fallback으로 때우고 있었다(FE 요청 009-home-card-response-fields).
 * Mock 단계에서는 placeholder 서비스를 써서 화면이 실제로 채워지게 한다.
 */
@Service
@Transactional(readOnly = true)
public class HomeService {

    private static final String LIVE_THUMBNAIL = "https://picsum.photos/seed/live%d/640/360";
    private static final String PRODUCT_THUMBNAIL = "https://picsum.photos/seed/product%d/480/480";

    /**
     * @param memberId 로그인 회원 ID. <b>비회원이면 null</b>이며 이때 상품 카드의 찜 여부는 null로 내린다.
     */
    public HomeContentResponse getHomeContent(Long memberId) {
        // TODO: Repository 조회로 교체 — 진행 중/예약 라이브(정윤), 상시 판매/경매 예정 상품(서윤)
        return new HomeContentResponse(
                mockLiveNow(),
                mockScheduledLives(),
                mockOnSaleProducts(memberId),
                mockUpcomingAuctionProducts(memberId),
                mockCategoryProductSections(memberId)
        );
    }

    // 비회원에게는 찜 상태를 알려줄 수 없다. false(=찜 안 함)로 내리면 FE가 "찜 해제 가능"으로
    // 오해하므로 null 로 구분한다.
    private Boolean wishedFor(Long memberId, boolean wished) {
        return memberId == null ? null : wished;
    }

    private List<LiveCardResponse> mockLiveNow() {
        return List.of(
                new LiveCardResponse(101L, "빈티지 데님 라이브", "빈티지장인",
                        LIVE_THUMBNAIL.formatted(101), "LIVE",
                        null, LocalDateTime.now().minusMinutes(32), 152, 5),
                new LiveCardResponse(102L, "90s 스트릿 셀렉션", "구제셀러",
                        LIVE_THUMBNAIL.formatted(102), "LIVE",
                        null, LocalDateTime.now().minusMinutes(8), 87, 3)
        );
    }

    private List<LiveCardResponse> mockScheduledLives() {
        return List.of(
                new LiveCardResponse(201L, "주말 아메카지 특집", "빈티지장인",
                        LIVE_THUMBNAIL.formatted(201), "SCHEDULED",
                        LocalDateTime.now().plusDays(2).withHour(20).withMinute(0), null, null, 4)
        );
    }

    private List<ProductCardResponse> mockOnSaleProducts(Long memberId) {
        return List.of(
                new ProductCardResponse(2001L, "리바이스 501 빈티지", "Levi's",
                        PRODUCT_THUMBNAIL.formatted(2001), "NORMAL", "ON_SALE", 45000L, false,
                        "빈티지장인", "하의", wishedFor(memberId, true), null, null),
                new ProductCardResponse(2002L, "칼하트 더블니 워크팬츠", "Carhartt",
                        PRODUCT_THUMBNAIL.formatted(2002), "NORMAL", "ON_SALE", 68000L, false,
                        "구제셀러", "하의", wishedFor(memberId, false), null, null)
        );
    }

    private List<ProductCardResponse> mockUpcomingAuctionProducts(Long memberId) {
        return List.of(
                new ProductCardResponse(3001L, "버버리 노바체크 트렌치", "Burberry",
                        PRODUCT_THUMBNAIL.formatted(3001), "AUCTION_SCHEDULED", "ON_SALE", null, true,
                        "빈티지장인", "아우터", wishedFor(memberId, false),
                        50000L, LocalDateTime.now().plusDays(1).withHour(21).withMinute(0))
        );
    }

    /**
     * 카테고리 탭 섹션. 탭 구성은 카테고리 마스터(SY007)의 최상위 6개를 따른다 —
     * 아우터·상의·하의·신발·가방·액세서리. FE 요청서의 '원피스'는 시드에 없어 '가방'으로 대체했다.
     */
    private List<CategoryProductSectionResponse> mockCategoryProductSections(Long memberId) {
        return List.of(
                categorySection(10L, "아우터", memberId, 4001L, 4002L, 4003L),
                categorySection(20L, "상의", memberId, 4101L, 4102L, 4103L),
                categorySection(30L, "하의", memberId, 4201L, 4202L, 4203L),
                categorySection(40L, "신발", memberId, 4301L, 4302L, 4303L),
                categorySection(50L, "가방", memberId, 4401L, 4402L, 4403L),
                categorySection(60L, "액세서리", memberId, 4501L, 4502L, 4503L)
        );
    }

    private CategoryProductSectionResponse categorySection(
            Long categoryId, String categoryName, Long memberId, Long... productIds) {
        List<ProductCardResponse> products = Arrays.stream(productIds)
                .map(productId -> new ProductCardResponse(
                        productId,
                        categoryName + " 빈티지 아이템 " + (productId % 10),
                        "Vintage",
                        PRODUCT_THUMBNAIL.formatted(productId),
                        "NORMAL", "ON_SALE", 39000L + (productId % 10) * 1000, false,
                        "빈티지장인", categoryName, wishedFor(memberId, false), null, null))
                .toList();

        return new CategoryProductSectionResponse(
                String.valueOf(categoryId), categoryName, categoryName, products);
    }
}