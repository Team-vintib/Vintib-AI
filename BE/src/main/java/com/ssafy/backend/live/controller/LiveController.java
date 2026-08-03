package com.ssafy.backend.live.controller;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.live.dto.request.LiveCurrentProductRequest;
import com.ssafy.backend.live.dto.request.LiveInstantRequest;
import com.ssafy.backend.live.dto.request.LiveListSort;
import com.ssafy.backend.live.dto.request.LiveScheduleRequest;
import com.ssafy.backend.live.dto.request.LiveStatusUpdateRequest;
import com.ssafy.backend.live.dto.response.CurrentProductResponse;
import com.ssafy.backend.live.dto.response.LiveDetailResponse;
import com.ssafy.backend.live.dto.response.LiveListItemResponse;
import com.ssafy.backend.live.dto.response.LiveResponse;
import com.ssafy.backend.live.dto.response.LiveStatusResponse;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.live.service.LiveService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.security.core.Authentication;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "라이브(Lives)", description = "라이브 방송 개설/조회 API")
@Validated
@RestController
@RequestMapping("/api/lives")
@RequiredArgsConstructor
public class LiveController {

    private final LiveService liveService;
    private final SimpMessagingTemplate messagingTemplate;

    @Operation(
            summary = "예약 라이브 개설",
            description = "방송 예정 시각을 지정해 라이브를 예약 개설한다. 생성 직후 상태는 SCHEDULED이며, "
                    + "방송 예정 시각은 반드시 미래여야 한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "201", description = "개설 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "요청값 검증 실패(방송명 누락, 예정 시각이 과거 등)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping("/schedule")
    public ResponseEntity<ApiResponse<LiveResponse>> scheduleLive(
            Authentication authentication, @Valid @RequestBody LiveScheduleRequest request) {
        Long hostId = (Long) authentication.getPrincipal();
        LiveResponse response = liveService.scheduleLive(hostId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(response));
    }

    @Operation(
            summary = "즉시 라이브 개설",
            description = "예약 없이 곧바로 방송을 시작한다. 생성 직후 상태는 LIVE이며, 시작 시각은 서버 시각으로 기록된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "201", description = "개설 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "요청값 검증 실패(방송명 누락 등)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping
    public ResponseEntity<ApiResponse<LiveResponse>> openLiveNow(
            Authentication authentication, @Valid @RequestBody LiveInstantRequest request) {
        Long hostId = (Long) authentication.getPrincipal();
        LiveResponse response = liveService.openLiveNow(hostId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(response));
    }

    @Operation(
            summary = "라이브 목록 조회",
            description = "예정·진행 중인 라이브를 페이지로 반환한다. **비회원도 조회할 수 있다.** "
                    + "종료·취소된 방송은 상태 필터 허용값에서도 결과에서도 제외된다. "
                    + "카테고리는 편성 상품에서 유도하므로 라이브 하나가 여러 카테고리를 가질 수 있고, "
                    + "대분류를 고르면 그 하위 소분류 상품을 건 방송까지 잡힌다. "
                    + "조건에 맞는 라이브가 없으면 404가 아니라 200과 빈 목록을 준다. "
                    + "`viewerCount`는 실시간 집계 값이며, 예약 방송은 0이다. "
                    + "`sort=VIEWERS_DESC`(시청자 수 많은 순)는 Redis 값으로 정렬하므로 최대 500개 방송까지만 "
                    + "대상으로 삼고, 그때 `totalElements`는 정렬 대상이 된 수를 뜻한다. "
                    + "`hostId`에 인증된 본인 ID를 넘기면 마이페이지 라이브 관리(MY-005)로 쓸 수 있다 — "
                    + "이때는 종료·취소된 방송까지 전부 조회된다(타인의 hostId를 넘기면 공개 상태만 보인다).")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "허용되지 않는 status·sort 값 또는 음수 page·size")
    })
    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<LiveListItemResponse>>> getPublicLives(
            Authentication authentication,
            @Parameter(description = "카테고리 ID 목록. 대분류를 주면 하위 소분류까지 포함한다")
            @RequestParam(required = false) List<Long> categoryIds,
            @Parameter(description = "호스트 회원 ID. 인증된 본인 ID를 넘기면 종료·취소 이력까지 본다(MY-005)")
            @RequestParam(required = false) Long hostId,
            @Parameter(description = "방송 상태. 생략하면 예정·진행 중 모두(본인 라이브 조회면 전체 상태)")
            @RequestParam(required = false) LiveStatus status,
            @RequestParam(defaultValue = "LATEST") LiveListSort sort,
            @RequestParam(defaultValue = "0") @Min(0) int page,
            @RequestParam(defaultValue = "12") @Min(1) @Max(100) int size) {
        Long viewerId = authentication != null ? (Long) authentication.getPrincipal() : null;
        boolean selfView = hostId != null && hostId.equals(viewerId);

        List<LiveStatus> statuses = resolveStatuses(status, selfView);
        PageResponse<LiveListItemResponse> response =
                liveService.getLives(categoryIds, hostId, statuses, sort, page, size);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    // 공개 조회에서 종료·취소를 조회하려는 요청은 값 자체를 거부한다 — 빈 목록으로 조용히 넘기면
    // FE 가 "그런 방송이 없다"로 오해한다. 본인 라이브 조회(selfView)는 관리 목적이라 예외를 둔다.
    private List<LiveStatus> resolveStatuses(LiveStatus status, boolean selfView) {
        if (status == null) {
            return selfView ? LiveService.ALL_STATUSES : LiveService.PUBLIC_STATUSES;
        }
        if (!selfView && status != LiveStatus.LIVE && status != LiveStatus.SCHEDULED) {
            throw new CustomException(ErrorCode.INVALID_LIVE_STATE);
        }
        return List.of(status);
    }

    @Operation(
            summary = "라이브 시청 정보 조회",
            description = "라이브 방 정보와 편성된 상품 목록을 함께 반환한다. **비회원도 조회할 수 있다.** "
                    + "영상 접속 토큰은 별도 발급 API가 담당한다. "
                    + "`currentViewerCount`는 현재 동시 시청자 수의 **초기값**이다 — 이후 변화는 "
                    + "`/topic/lives/{liveId}/viewers` 구독으로 받으며, 구독 직후 브로드캐스트가 오는 것은 "
                    + "보장되지 않으므로 초기값을 토픽에서 기다리면 안 된다.\n\n"
                    + "**토큰을 함께 보내면 `isHost`가 채워진다.** 비회원도 200이지만 그때는 항상 false다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "라이브 없음")
    })
    @GetMapping("/{liveId}")
    public ResponseEntity<ApiResponse<LiveDetailResponse>> getLiveDetail(
            Authentication authentication, @PathVariable Long liveId) {
        // 공개 엔드포인트라 authentication 이 null 일 수 있다. 토큰이 붙어 있으면
        // JwtAuthenticationFilter 가 이미 채워 두므로 여기서는 꺼내 쓰기만 한다.
        Long viewerId = authentication != null ? (Long) authentication.getPrincipal() : null;
        LiveDetailResponse response = liveService.getLiveDetail(liveId, viewerId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(
            summary = "지금 소개 중인 상품 변경",
            description = "라이브에서 지금 소개 중인 상품을 바꾼다(FE `NOW` 배지의 원천). **호스트만 가능하다.** "
                    + "이 방송에 편성된 상품이어야 하며, `productId`를 `null`로 보내면 해제된다"
                    + "(잡담 구간 등 아무 상품도 소개하지 않는 상태).\n\n"
                    + "**상품 편성 변경과 규칙이 다르다.** 편성은 방송이 시작되면 잠기지만, 소개 상품 전환은 "
                    + "방송 중에 하는 것이 본래 용도라 진행 중에도 허용된다. 종료·취소된 방송에서만 400이다.\n\n"
                    + "변경은 `/topic/lives/{liveId}/product`로 모든 시청자에게 전파된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "변경 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "400",
                    description = "종료·취소된 방송(L007)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 라이브가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "404",
                    description = "라이브 없음(L001) 또는 이 방송에 편성되지 않은 상품(L006)")
    })
    @PatchMapping("/{liveId}/current-product")
    public ResponseEntity<ApiResponse<CurrentProductResponse>> changeCurrentProduct(
            Authentication authentication,
            @PathVariable Long liveId,
            @Valid @RequestBody LiveCurrentProductRequest request) {
        Long hostId = (Long) authentication.getPrincipal();
        CurrentProductResponse response = liveService.changeCurrentProduct(hostId, liveId, request);

        // 커밋이 끝난 뒤에 나간다 — changeCurrentProduct 의 트랜잭션이 이 시점에 이미 닫혀 있다.
        // 커밋 전에 쏘면 롤백 시 시청자 화면의 NOW 배지만 옮겨진 채 남는다(설계 판단 2).
        messagingTemplate.convertAndSend("/topic/lives/" + liveId + "/product", response);

        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(
            summary = "방송 상태 전이",
            description = "방송 상태를 바꾼다. 허용되는 전이는 예정→진행(LIVE), 예정→취소(CANCELED), "
                    + "진행→종료(ENDED) 세 가지다. 종료·취소된 방송은 더 이상 전이되지 않는다. "
                    + "전이 시각은 서버 시각으로 기록된다.\n\n"
                    + "**전이는 `/topic/lives/{liveId}/status`로 모든 시청자에게 전파된다.** "
                    + "시청 중인 화면은 이 이벤트로 종료 안내로 전환하면 된다 — 이게 없으면 "
                    + "호스트가 종료해도 시청자 화면이 그대로 남는다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "전이 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "요청값 검증 실패 또는 허용되지 않는 전이"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 라이브가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "라이브 없음")
    })
    @PatchMapping("/{liveId}/status")
    public ResponseEntity<ApiResponse<LiveResponse>> transitionStatus(
            Authentication authentication,
            @PathVariable Long liveId,
            @Valid @RequestBody LiveStatusUpdateRequest request) {
        Long hostId = (Long) authentication.getPrincipal();
        LiveResponse response = liveService.transitionStatus(hostId, liveId, request);

        // 커밋이 끝난 뒤에 나간다 — 현재 소개 상품 전환과 같은 이유다. 커밋 전에 쏘면 롤백 시
        // 시청자 화면만 "종료됨"으로 넘어간 채 서버는 여전히 진행 중인 상태가 된다.
        messagingTemplate.convertAndSend(
                "/topic/lives/" + liveId + "/status", LiveStatusResponse.from(response));

        return ResponseEntity.ok(ApiResponse.success(response));
    }
}