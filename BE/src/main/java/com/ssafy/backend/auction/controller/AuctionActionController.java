package com.ssafy.backend.auction.controller;

import com.ssafy.backend.auction.dto.request.BidRequest;
import com.ssafy.backend.auction.dto.response.AuctionEventResponse;
import com.ssafy.backend.auction.dto.response.AuctionSnapshotResponse;
import com.ssafy.backend.auction.dto.response.AuctionWinnerResponse;
import com.ssafy.backend.auction.dto.response.BidResponse;
import com.ssafy.backend.auction.service.AuctionService;
import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.global.response.CursorPageResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.security.core.Authentication;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
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
@Validated
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

    @Operation(
            summary = "입찰",
            description = "경매에 입찰한다. **`amount`는 반드시 직전 현황의 `nextBidPrice`와 정확히 같아야 "
                    + "한다** — 그 이상·이하 모두 거부된다. 낮으면 A002, 높으면(값이 그 사이 바뀌었다는 "
                    + "뜻) A008이다.\n\n"
                    + "**직전 최고 입찰자 본인은 연속으로 입찰할 수 없다**(AUCT-006, A009). "
                    + "**최고 입찰자인 동안에는 다른 경매에 입찰할 수 없다**(AUCT-009, A011) — "
                    + "먼저 그 경매에서 상위 입찰에 밀리거나 경매가 끝나야 한다.\n\n"
                    + "성공하면 보류가 갱신되고 직전 최고 입찰자의 보류는 자동으로 풀린다. "
                    + "종료 3초 이하로 남은 상태에서 입찰이 들어오면 종료 시각이 5초 뒤로 밀린다"
                    + "(AUCT-010) — 응답과 이벤트의 `endsAt`으로 확인한다.\n\n"
                    + "동기 응답으로 성공 snapshot을 즉시 돌려주고, 같은 내용이 "
                    + "`/topic/lives/{liveId}/auctions`로 `BID_PLACED` 이벤트로도 전파된다.")
    @SecurityRequirement(name = "bearerAuth")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "입찰 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "400",
                    description = "진행 중이 아니거나 종료된 경매(A001), 금액 불일치(A002/A008), "
                            + "연속 입찰(A009), 잔액 부족(W001)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "경매 없음(A005)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "409",
                    description = "같은 금액 중복 입찰(A010), 다른 경매에 이미 최고 입찰자로 참여 중(A011)")
    })
    @PostMapping("/bids")
    public ResponseEntity<ApiResponse<AuctionSnapshotResponse>> placeBid(
            Authentication authentication,
            @PathVariable Long auctionId,
            @Valid @RequestBody BidRequest request) {
        Long bidderId = (Long) authentication.getPrincipal();
        AuctionSnapshotResponse snapshot = auctionService.placeBid(bidderId, auctionId, request);

        // 커밋 이후에 나간다 — 롤백되면 시청자 화면에 유령 입찰이 남을 수 있다.
        messagingTemplate.convertAndSend(
                "/topic/lives/" + snapshot.liveId() + "/auctions",
                AuctionEventResponse.bidPlaced(snapshot));

        return ResponseEntity.ok(ApiResponse.success(snapshot));
    }

    @Operation(
            summary = "입찰 내역 조회",
            description = "이 경매의 입찰 내역을 최신순 커서 페이징으로 반환한다. **비회원도 조회할 수 "
                    + "있다** — 지금 얼마까지 붙었는지 보는 것은 관전이지 참여가 아니다.\n\n"
                    + "커서는 page 번호가 아니라 bidId다. 응답의 nextCursor를 다음 요청에 그대로 "
                    + "넣는다. 토큰을 함께 보내면 본인 입찰에 `isMine=true`가 붙는다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "경매 없음(A005)")
    })
    @GetMapping("/bids")
    public ResponseEntity<ApiResponse<CursorPageResponse<BidResponse>>> getBidHistory(
            Authentication authentication,
            @PathVariable Long auctionId,
            @Parameter(description = "이 bidId보다 오래된 입찰을 최신순으로. 첫 페이지는 생략")
            @RequestParam(required = false) Long cursor,
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) int size) {
        Long viewerId = authentication != null ? (Long) authentication.getPrincipal() : null;
        CursorPageResponse<BidResponse> response =
                auctionService.getBidHistory(auctionId, cursor, size, viewerId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(
            summary = "경매 결과 조회",
            description = "낙찰자와 낙찰가를 조회한다. **비회원도 조회할 수 있다.**\n\n"
                    + "**유찰도 200이다** — `status`가 `FAILED`이고 낙찰자 관련 필드가 전부 null이다. "
                    + "아직 끝나지 않은 경매(`READY`/`RUNNING`)도 그대로 내려주므로, 종료 여부는 "
                    + "`status`로 판단한다.\n\n"
                    + "경매는 종료 시각이 지나면 서버 스케줄러가 자동으로 마감하며, 그 순간 "
                    + "`/topic/lives/{liveId}/auctions`로 `AUCTION_CLOSED` 이벤트가 전파된다 — "
                    + "이 API는 그 이벤트를 놓쳤거나 나중에 결과를 다시 확인할 때 쓴다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "경매 없음(A005)")
    })
    @GetMapping("/winner")
    public ResponseEntity<ApiResponse<AuctionWinnerResponse>> getWinner(@PathVariable Long auctionId) {
        return ResponseEntity.ok(ApiResponse.success(auctionService.getWinner(auctionId)));
    }
}
