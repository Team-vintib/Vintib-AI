package com.ssafy.backend.auction.controller;

import com.ssafy.backend.auction.dto.response.LiveBroadcastSummaryResponse;
import com.ssafy.backend.auction.dto.response.LiveUnsoldProductResponse;
import com.ssafy.backend.auction.service.LiveBroadcastResultService;
import com.ssafy.backend.global.response.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 방송 종료 결과 조회(LIVE-006, FE 요청 018) — 판매자 방송 종료 대시보드와 미낙찰 상품 처리 화면.
 *
 * <p>경로는 라이브지만 {@code auction} 패키지에 있다 — 이유는
 * {@link LiveBroadcastResultService} 주석 참고({@code AuctionController}도 같은 형태다).
 */
@Tag(name = "라이브 / 채팅(Lives)", description = "라이브 방송 개설/조회 API")
@RestController
@RequestMapping("/api/lives/{liveId}")
@RequiredArgsConstructor
public class LiveBroadcastResultController {

    private final LiveBroadcastResultService liveBroadcastResultService;

    @Operation(
            summary = "방송 종료 요약 조회",
            description = "방송 종료 대시보드에 쓰는 판매 요약이다. **호스트 본인만 조회할 수 있다** — "
                    + "판매 실적이라 시청자에게 공개하지 않는다.\n\n"
                    + "`results`는 **편성 상품 전체**가 기준이며 편성 순서를 따른다. 경매를 걸지 않은 "
                    + "편성 상품도 `UNSOLD`로 포함된다.\n\n"
                    + "**경매 낙찰과 방송 중 정찰가 즉시구매를 함께 센다** — `soldVia`로 구분한다"
                    + "(`AUCTION`/`DIRECT_SALE`). 안 팔린 상품에도 편성 시점의 `saleType`/"
                    + "`registeredPrice`가 채워진다.\n\n"
                    + "방송이 끝나기 전에 불러도 200이며, 그 시점까지의 결과를 준다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 라이브가 아님(L004)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "라이브 없음(L001)")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping("/summary")
    public ResponseEntity<ApiResponse<LiveBroadcastSummaryResponse>> getSummary(
            Authentication authentication, @PathVariable Long liveId) {
        Long requesterId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(
                liveBroadcastResultService.getSummary(liveId, requesterId)));
    }

    @Operation(
            summary = "방송별 유찰 상품 목록 조회",
            description = "이 방송에서 안 팔린 상품 목록이다. **호스트 본인만 조회할 수 있다.**\n\n"
                    + "**상품 판매 상태가 아니라 이 방송의 경매 결과로 찾는다** — 유찰 상품은 판매 상태가 "
                    + "`AUCTION_SCHEDULED`로 돌아가기 때문에, 상태만 보면 다른 방송에서 유찰됐거나 아직 "
                    + "한 번도 경매에 안 걸린 상품까지 섞인다.\n\n"
                    + "같은 상품에 재경매를 걸었다면 **마지막 경매 결과만** 본다 — 유찰 뒤 다시 걸어 "
                    + "낙찰됐으면 이 목록에 나오지 않는다. 경매를 아예 걸지 않은 편성 상품도 제외된다"
                    + "(방송 전체를 보려면 `/summary`를 쓴다).\n\n"
                    + "`startPrice`는 마지막 경매의 시작가라 재경매 기본값으로 쓰면 된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 라이브가 아님(L004)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "라이브 없음(L001)")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping("/unsold-products")
    public ResponseEntity<ApiResponse<List<LiveUnsoldProductResponse>>> getUnsoldProducts(
            Authentication authentication, @PathVariable Long liveId) {
        Long requesterId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(
                liveBroadcastResultService.getUnsoldProducts(liveId, requesterId)));
    }
}
