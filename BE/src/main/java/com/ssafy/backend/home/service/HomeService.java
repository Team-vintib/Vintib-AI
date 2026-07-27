package com.ssafy.backend.home.service;

import com.ssafy.backend.home.dto.response.HomeContentResponse;
import com.ssafy.backend.home.dto.response.LiveCardResponse;
import com.ssafy.backend.home.dto.response.ProductCardResponse;
import java.time.LocalDateTime;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 홈 콘텐츠 조회(HOME-001) 서비스.
 *
 * <p><b>현재는 Mock 응답을 반환한다.</b> 홈에 노출할 라이브는 내 도메인, 상품은 서윤 도메인에 의존하는데
 * 이번 주엔 해당 테이블이 없다. FE가 Mock 기준으로 홈 화면 개발에 착수할 수 있게 응답 스펙만 확정한다.
 * 2주차에 상품 도메인 + 라이브 CRUD가 준비되면 아래 {@code mock*} 조립부만 Repository 조회로 교체한다.
 */
@Service
@Transactional(readOnly = true)
public class HomeService {

    public HomeContentResponse getHomeContent() {
        // TODO(2주차): Repository 조회로 교체 — 진행 중/예약 라이브(정윤), 상시 판매/경매 예정 상품(서윤)
        return new HomeContentResponse(
                mockLiveNow(),
                mockScheduledLives(),
                mockOnSaleProducts(),
                mockUpcomingAuctionProducts()
        );
    }

    private List<LiveCardResponse> mockLiveNow() {
        return List.of(
                new LiveCardResponse(101L, "빈티지 데님 라이브", "빈티지장인",
                        "https://cdn.example.com/live/101.jpg", "LIVE", null, 152, 5),
                new LiveCardResponse(102L, "90s 스트릿 셀렉션", "구제셀러",
                        "https://cdn.example.com/live/102.jpg", "LIVE", null, 87, 3)
        );
    }

    private List<LiveCardResponse> mockScheduledLives() {
        return List.of(
                new LiveCardResponse(201L, "주말 아메카지 특집", "빈티지장인",
                        "https://cdn.example.com/live/201.jpg", "SCHEDULED",
                        LocalDateTime.of(2026, 7, 27, 20, 0), null, 4)
        );
    }

    private List<ProductCardResponse> mockOnSaleProducts() {
        return List.of(
                new ProductCardResponse(2001L, "리바이스 501 빈티지", "Levi's",
                        "https://cdn.example.com/product/2001.jpg", "NORMAL", "ON_SALE", 45000L, false),
                new ProductCardResponse(2002L, "칼하트 더블니 워크팬츠", "Carhartt",
                        "https://cdn.example.com/product/2002.jpg", "NORMAL", "ON_SALE", 68000L, false)
        );
    }

    private List<ProductCardResponse> mockUpcomingAuctionProducts() {
        return List.of(
                new ProductCardResponse(3001L, "버버리 노바체크 트렌치", "Burberry",
                        "https://cdn.example.com/product/3001.jpg", "AUCTION_SCHEDULED", "ON_SALE", null, true)
        );
    }
}