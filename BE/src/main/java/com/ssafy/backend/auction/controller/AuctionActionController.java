package com.ssafy.backend.auction.controller;

import com.ssafy.backend.auction.dto.response.AuctionEventResponse;
import com.ssafy.backend.auction.dto.response.AuctionSnapshotResponse;
import com.ssafy.backend.auction.service.AuctionService;
import com.ssafy.backend.global.response.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 경매 진행 동작(AUCT-002~). 시작·입찰·종료가 여기로 들어온다.
 *
 * <p><b>경로에 {@code liveId}가 없다.</b> {@code auctionId}만으로 경매가 유일하게 정해지고,
 * 라이브는 경매에서 따라 나온다. FE 요청서(009 §3.2)도 이 형태로 요청했다 — 조건 설정
 * ({@code /api/lives/{liveId}/auctions})은 "이 방송에 경매를 건다"는 뜻이라 라이브가 경로에 있는
 * 것이 맞지만, 진행 동작은 이미 만들어진 경매를 가리키면 된다.
 */
@Tag(name = "경매(Auctions)", description = "경매 조건 설정/진행 API")
@RestController
@RequestMapping("/api/auctions/{auctionId}")
@RequiredArgsConstructor
public class AuctionActionController {

    private final AuctionService auctionService;
    private final SimpMessagingTemplate messagingTemplate;

    @Operation(
            summary = "경매 시작",
            description = "준비 중(READY)인 경매를 시작한다. **호스트만 가능하다.** 시작 시각과 종료 예정 "
                    + "시각(`endsAt = 시작 + durationSeconds`)이 이때 확정되고, 상품은 "
                    + "`AUCTION_IN_PROGRESS`로 바뀐다.\n\n"
                    + "**한 방송에서 동시에 진행할 수 있는 경매는 하나뿐이다** — 이미 진행 중인 경매가 "
                    + "있으면 409다. 먼저 그 경매를 끝내야 한다.\n\n"
                    + "시작은 `/topic/lives/{liveId}/auctions`로 `AUCTION_STARTED` 이벤트와 함께 "
                    + "모든 시청자에게 전파된다. 응답과 이벤트의 `auction`은 같은 현황이다.")
    @SecurityRequirement(name = "bearerAuth")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "시작 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "400",
                    description = "이미 시작했거나 끝난 경매(A006), 종료·취소된 방송(L007)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 라이브가 아님(L004)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "경매 없음(A005)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "409",
                    description = "이 방송에 이미 진행 중인 경매가 있음(A007)")
    })
    @PostMapping("/start")
    public ResponseEntity<ApiResponse<AuctionSnapshotResponse>> start(
            Authentication authentication, @PathVariable Long auctionId) {
        Long hostId = (Long) authentication.getPrincipal();
        AuctionSnapshotResponse snapshot = auctionService.startAuction(hostId, auctionId);

        // 커밋이 끝난 뒤에 나간다 — 소개 상품 전환·방송 상태 전파와 같은 이유다.
        // 커밋 전에 쏘면 롤백 시 시청자 화면에서만 경매가 시작된 채로 남는다.
        messagingTemplate.convertAndSend(
                "/topic/lives/" + snapshot.liveId() + "/auctions",
                AuctionEventResponse.started(snapshot));

        return ResponseEntity.ok(ApiResponse.success(snapshot));
    }
}
