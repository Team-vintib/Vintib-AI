package com.ssafy.backend.auction.controller;

import com.ssafy.backend.auction.dto.request.AuctionConfigRequest;
import com.ssafy.backend.auction.dto.response.AuctionResponse;
import com.ssafy.backend.auction.dto.response.AuctionSnapshotResponse;
import com.ssafy.backend.auction.service.AuctionService;
import com.ssafy.backend.global.response.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "경매(Auctions)", description = "경매 조건 설정/진행 API")
@RestController
@RequestMapping("/api/lives/{liveId}/auctions")
@RequiredArgsConstructor
public class AuctionController {

    private final AuctionService auctionService;

    @Operation(
            summary = "경매 조건 설정",
            description = "라이브에 연결된 상품에 시작가·증액 단위·진행 시간을 설정한다. 생성 직후 상태는 READY이며 "
                    + "경매가 시작되지는 않는다. 라이브에 연결되지 않은 상품에는 설정할 수 없고, "
                    + "이미 진행 예정/진행 중인 경매가 있는 상품에는 다시 설정할 수 없다.")
    @SecurityRequirement(name = "bearerAuth")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "201", description = "설정 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "요청값 검증 실패 또는 종료·취소된 방송"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 라이브가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "라이브 없음 또는 라이브에 연결되지 않은 상품"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "409", description = "해당 상품에 이미 설정된 경매가 있음")
    })
    @PostMapping
    public ResponseEntity<ApiResponse<AuctionResponse>> configureAuction(
            Authentication authentication,
            @PathVariable Long liveId,
            @Valid @RequestBody AuctionConfigRequest request) {
        Long hostId = (Long) authentication.getPrincipal();
        AuctionResponse response = auctionService.configureAuction(hostId, liveId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(response));
    }

    @Operation(
            summary = "현재 경매 현황 조회",
            description = "라이브 진입 시 경매 패널을 초기화한다. **비회원도 조회할 수 있다.**\n\n"
                    + "**진행 중(RUNNING) 경매가 준비 중(READY)보다 우선**한다. 둘 다 없으면 "
                    + "`data`가 **`null`**이다 — 아직 경매를 걸지 않은 방송이 정상이므로 404가 아니다. "
                    + "종료된 경매는 여기서 나오지 않는다(낙찰 결과는 종료 이벤트로 전달된다).\n\n"
                    + "이후 변화는 `/topic/lives/{liveId}/auctions` 구독으로 받는다. "
                    + "남은 시간은 `endsAt - serverNow`로 계산한다 — 클라이언트 시계를 그대로 쓰면 "
                    + "카운트다운이 서버와 어긋난다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공(경매가 없으면 data=null)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "라이브 없음(L001)")
    })
    @GetMapping("/current")
    public ResponseEntity<ApiResponse<AuctionSnapshotResponse>> getCurrentAuction(
            @PathVariable Long liveId) {
        return ResponseEntity.ok(ApiResponse.success(auctionService.getCurrentSnapshot(liveId)));
    }
}