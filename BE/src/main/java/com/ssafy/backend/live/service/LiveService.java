package com.ssafy.backend.live.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.live.dto.request.LiveCurrentProductRequest;
import com.ssafy.backend.live.dto.request.LiveInstantRequest;
import com.ssafy.backend.live.dto.request.LiveScheduleRequest;
import com.ssafy.backend.live.dto.request.LiveListSort;
import com.ssafy.backend.live.dto.request.LiveStatusUpdateRequest;
import com.ssafy.backend.live.dto.response.CurrentProductResponse;
import com.ssafy.backend.live.dto.response.LiveCategoryResponse;
import com.ssafy.backend.live.dto.response.LiveDetailResponse;
import com.ssafy.backend.live.dto.response.LiveListItemResponse;
import com.ssafy.backend.live.dto.response.LiveResponse;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.live.port.NotificationCommandPort;
import com.ssafy.backend.live.port.ProductQueryPort.CategorySummary;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.social.entity.Follow;
import com.ssafy.backend.social.repository.FollowRepository;
import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class LiveService {

    private final LiveRepository liveRepository;
    private final MemberRepository memberRepository;
    private final LiveProductService liveProductService;
    private final LiveViewerService liveViewerService;
    private final LiveReminderService liveReminderService;
    private final FollowRepository followRepository;
    private final NotificationCommandPort notificationCommandPort;
    // 종료 시 정리할 리소스가 늘어나면 구현체만 추가한다 — 종료 로직은 다시 열지 않는다.
    private final List<LiveCleanupHook> cleanupHooks;

    // 공개 목록에는 예정·진행 중만 나온다. 종료·취소는 결과에서도 상태 필터에서도 빠진다.
    public static final List<LiveStatus> PUBLIC_STATUSES = List.of(LiveStatus.SCHEDULED, LiveStatus.LIVE);

    // 마이페이지 라이브 관리(MY-005) — 본인 조회일 때는 종료·취소 이력까지 전부 본다.
    public static final List<LiveStatus> ALL_STATUSES = List.of(LiveStatus.values());

    /**
     * 방송 시작 알림을 보낼 팔로워 상한(FE 요청 004 §3.2 LIVE_STARTED).
     *
     * <p>팔로워가 아주 많은 판매자라면 알림 INSERT가 방송 시작 트랜잭션을 오래 붙잡는다.
     * {@link #MAX_VIEWERS_SORT_CANDIDATES}와 같은 이유로 상한을 둔다 — 이 규모에서는 사실상
     * 전원에게 가지만, 나중에 실제로 잘리는 사례가 생기면 비동기 발송으로 옮긴다.
     */
    private static final int MAX_FOLLOWER_NOTIFICATIONS = 500;

    /**
     * 시청자 수 정렬에서 한 번에 고려하는 방송 수의 상한.
     *
     * <p>이 정렬은 SQL 로 자를 수 없어 후보를 모두 읽어 메모리에서 세운다. 상한이 없으면 방송이
     * 쌓일수록 한 요청이 테이블 전체를 끌어온다. 공개 목록에 나올 수 있는 것은 예정·진행 중뿐이라
     * 실제로는 이 값에 한참 못 미치지만, 넘어설 규모가 되면 {@code live} 에 현재 시청자 수 컬럼을
     * 두고 SQL 정렬로 바꾸는 것이 맞다.
     */
    private static final int MAX_VIEWERS_SORT_CANDIDATES = 500;

    /**
     * 예약 라이브 개설(LIVE-001). 방송 예정 시각이 미래인지는 요청 DTO({@code @Future})가 검증한다.
     *
     * <p><b>판매 상품을 개설과 같은 트랜잭션에서 편성한다.</b> 상품 없는 방송이 만들어지면
     * 카테고리도 없고 팔 것도 없는 빈 방이 목록에 뜬다. 편성이 실패하면 방송도 만들어지지 않는다.
     */
    @Transactional
    public LiveResponse scheduleLive(Long hostId, LiveScheduleRequest request) {
        Member host = findHost(hostId);

        Live live = liveRepository.save(
                Live.schedule(
                        host,
                        request.title(),
                        request.thumbnailUrl(),
                        request.description(),
                        request.scheduledAt()));
        liveProductService.linkProductsOnCreate(hostId, live, request.productIds());

        return LiveResponse.from(live);
    }

    /**
     * 즉시 라이브 개설(LIVE-002). 예약을 거치지 않고 곧바로 LIVE 상태로 만든다.
     *
     * <p>시작 시각은 클라이언트가 보낸 값이 아니라 서버 시각으로 박는다 — 방송 시작 순서·경매 종료
     * 판정이 전부 서버 시각 기준이어야 하기 때문이다(erd.md §6).
     *
     * <p>즉시 개설은 생성 즉시 {@code LIVE}가 되어 <b>이후 편성을 바꿀 수 없다.</b> 그래서
     * 상품 편성이 개설 요청에 반드시 포함돼야 한다.
     */
    @Transactional
    public LiveResponse openLiveNow(Long hostId, LiveInstantRequest request) {
        Member host = findHost(hostId);

        Live live = liveRepository.save(
                Live.openNow(
                        host,
                        request.title(),
                        request.thumbnailUrl(),
                        request.description(),
                        LocalDateTime.now()));
        liveProductService.linkProductsOnCreate(hostId, live, request.productIds());

        // 즉시 개설은 생성 시점에 이미 LIVE 라 여기서 room 을 배정한다. 이름에 ID 가 들어가므로
        // save() 로 ID 가 나온 뒤여야 한다.
        live.assignOpenviduRoom(LiveVideoService.newRoomName(live.getId()));

        notifyFollowersLiveStarted(live);

        return LiveResponse.from(live);
    }

    /**
     * 라이브 시청 정보 조회(LIVE-005). <b>비회원도 조회할 수 있다.</b>
     *
     * <p>편성 상품을 함께 담아 시청 화면 진입 시 왕복을 늘리지 않는다. 상품 조회는
     * {@link LiveProductService}에 위임해 연결 조회 규칙(제외된 건 제외)을 한 곳에만 둔다.
     *
     * @param viewerId 조회한 회원 ID. <b>비회원이면 null</b>. 호스트 여부({@code isHost})를 서버가
     *                 계산해 내려주기 위해 받는다 — FE 가 {@code hostId}를 직접 비교하면 재입장 시
     *                 회원 정보 복원이 렌더보다 늦어 "내 방송인데 팔로우 버튼이 뜨는" 문제가 생긴다
     */
    public LiveDetailResponse getLiveDetail(Long liveId, Long viewerId) {
        Live live = liveRepository.findById(liveId)
                .orElseThrow(() -> new CustomException(ErrorCode.LIVE_NOT_FOUND));

        List<LiveCategoryResponse> categories = liveProductService.getLiveCategories(liveId).stream()
                .map(LiveCategoryResponse::from)
                .toList();

        return LiveDetailResponse.of(
                live,
                liveProductService.getLinkedProducts(liveId),
                categories,
                // 화면 진입 시 초기값. 이후 변화는 /topic/lives/{liveId}/viewers 로 간다.
                liveViewerService.getViewerCount(liveId),
                viewerId,
                liveReminderService.isRegistered(viewerId, liveId));
    }

    /**
     * 라이브 목록(LIVE-005). <b>비회원도 조회할 수 있다.</b> {@code hostId}를 넘기면 그 호스트의
     * 라이브만 걸러 마이페이지 라이브 관리(MY-005)로도 쓴다 — 허용 상태 범위(공개는 예정·진행
     * 중만, 본인 조회는 종료·취소 포함 전체)는 호출부(컨트롤러)가 판단해 {@code statuses}로 확정해
     * 넘긴다. 카테고리 필터는 편성 상품을 통해 걸리며, 대분류를 고르면 하위 소분류 상품을 건
     * 방송까지 잡힌다.
     *
     * @param categoryIds 비어 있으면 카테고리 필터를 걸지 않는다
     * @param hostId      null이면 호스트 필터를 걸지 않는다
     * @param statuses    조회 대상 상태 목록(컨트롤러가 이미 공개/본인 조회 여부에 맞게 확정한 값)
     */
    public PageResponse<LiveListItemResponse> getLives(
            List<Long> categoryIds, Long hostId, List<LiveStatus> statuses, LiveListSort sort, int page, int size) {
        boolean filterByCategory = categoryIds != null && !categoryIds.isEmpty();
        List<Long> productIds = filterByCategory
                ? liveProductService.findProductIdsInCategories(categoryIds)
                : List.of();
        if (filterByCategory && productIds.isEmpty()) {
            // 해당 카테고리 상품이 하나도 없으면 매칭될 라이브도 없다. IN () 로 쿼리가 깨지는 것도 막는다.
            return PageResponse.from(Page.empty(PageRequest.of(page, size)));
        }

        boolean filterByHost = hostId != null;

        if (sort.isInMemory()) {
            return getLivesByViewerCount(statuses, filterByCategory, productIds, filterByHost, hostId, page, size);
        }

        Page<Live> lives = liveRepository.findPublicLives(
                statuses, filterByCategory, productIds, filterByHost, hostId,
                PageRequest.of(page, size, sort.toSort()));

        List<Long> liveIds = idsOf(lives.getContent());
        Map<Long, List<CategorySummary>> categoriesByLiveId =
                liveProductService.getCategoriesByLiveIds(liveIds);
        Map<Long, Integer> viewerCounts = liveViewerService.getViewerCounts(liveIds);

        return PageResponse.from(lives.map(live -> toListItem(live, categoriesByLiveId, viewerCounts)));
    }

    /**
     * 시청자 수 많은 순 목록(-450).
     *
     * <p><b>SQL 로 정렬할 수 없어 후보를 읽어 메모리에서 정렬한다.</b> 현재 시청자 수는 Redis 에만
     * 있는 값이라 {@code ORDER BY} 로 걸 컬럼이 없다.
     *
     * <p>후보는 {@link #MAX_VIEWERS_SORT_CANDIDATES} 까지만 본다. 그래서 {@code totalElements} 도
     * 전체 개수가 아니라 <b>실제로 정렬 대상이 된 수</b>다 — 전체 개수를 내려보내면 도달할 수 없는
     * 페이지가 있다고 알려주는 셈이 된다.
     */
    private PageResponse<LiveListItemResponse> getLivesByViewerCount(
            List<LiveStatus> statuses, boolean filterByCategory, List<Long> productIds,
            boolean filterByHost, Long hostId, int page, int size) {
        List<Live> candidates = liveRepository.findPublicLives(
                        statuses,
                        filterByCategory,
                        productIds,
                        filterByHost,
                        hostId,
                        PageRequest.of(0, MAX_VIEWERS_SORT_CANDIDATES, LiveListSort.VIEWERS_DESC.toSort()))
                .getContent();

        Map<Long, Integer> viewerCounts = liveViewerService.getViewerCounts(idsOf(candidates));

        // 동률에서 id DESC 로 한 번 더 세운다 — 시청자 0명인 예약 방송이 여럿이면 그쪽이 전부
        // 동률이라, 마지막 기준이 없으면 페이지를 넘길 때 순서가 흔들린다.
        List<Live> sorted = candidates.stream()
                .sorted(Comparator.<Live>comparingInt(live -> viewerCounts.getOrDefault(live.getId(), 0))
                        .reversed()
                        .thenComparing(Live::getId, Comparator.reverseOrder()))
                .toList();

        // page 는 상한이 없어 곱셈이 int 를 넘을 수 있다. long 으로 계산해야 음수로 뒤집히지 않는다.
        int from = (int) Math.min((long) page * size, sorted.size());
        int to = (int) Math.min((long) from + size, sorted.size());
        List<Live> pageContent = sorted.subList(from, to);

        Map<Long, List<CategorySummary>> categoriesByLiveId =
                liveProductService.getCategoriesByLiveIds(idsOf(pageContent));
        List<LiveListItemResponse> items = pageContent.stream()
                .map(live -> toListItem(live, categoriesByLiveId, viewerCounts))
                .toList();

        return PageResponse.from(new PageImpl<>(items, PageRequest.of(page, size), sorted.size()));
    }

    private LiveListItemResponse toListItem(
            Live live,
            Map<Long, List<CategorySummary>> categoriesByLiveId,
            Map<Long, Integer> viewerCounts) {
        return LiveListItemResponse.of(
                live,
                categoriesByLiveId.getOrDefault(live.getId(), List.of()).stream()
                        .map(LiveCategoryResponse::from)
                        .toList(),
                viewerCounts.getOrDefault(live.getId(), 0));
    }

    private List<Long> idsOf(List<Live> lives) {
        return lives.stream().map(Live::getId).toList();
    }

    /**
     * 방송 상태 전이(예정→진행→종료). 호스트 본인만 바꿀 수 있다.
     *
     * <p>전이 시각은 서버 시각으로 박는다. 종료로 전이되면 리소스 정리 훅을 부른다.
     */
    @Transactional
    public LiveResponse transitionStatus(Long hostId, Long liveId, LiveStatusUpdateRequest request) {
        Live live = liveRepository.findById(liveId)
                .orElseThrow(() -> new CustomException(ErrorCode.LIVE_NOT_FOUND));

        if (!live.isHostedBy(hostId)) {
            throw new CustomException(ErrorCode.NOT_LIVE_HOST);
        }
        if (!live.canTransitionTo(request.status())) {
            throw new CustomException(ErrorCode.INVALID_LIVE_STATE);
        }

        live.transitionTo(request.status(), LocalDateTime.now());

        // 예정 방송이 실제로 시작되는 지점. 여기서 room 을 배정한다 — 미디어 서버를 부르지 않고
        // 이름만 정한다(LiveKit 은 첫 참가자가 들어올 때 room 을 자동 생성한다).
        if (request.status() == LiveStatus.LIVE) {
            live.assignOpenviduRoom(LiveVideoService.newRoomName(live.getId()));
            notifyFollowersLiveStarted(live);
        }
        if (request.status() == LiveStatus.ENDED) {
            cleanupHooks.forEach(hook -> hook.onLiveEnded(live));
        }

        return LiveResponse.from(live);
    }

    /**
     * 방송 시작을 팔로워에게 알린다(FE 요청 004 §3.2 LIVE_STARTED). 즉시 개설·예약 개설 후 시작
     * 두 경로 모두에서 부른다 — "방송이 실제로 시작되는 순간"이 공통 지점이다.
     */
    private void notifyFollowersLiveStarted(Live live) {
        List<Member> followers = followRepository
                .findByFollowing_Id(live.getHost().getId(), PageRequest.of(0, MAX_FOLLOWER_NOTIFICATIONS))
                .map(Follow::getFollower)
                .getContent();

        followers.forEach(follower -> notificationCommandPort.notify(
                follower,
                "LIVE_STARTED",
                "%s님이 라이브를 시작했어요".formatted(live.getHost().getNickname()),
                live.getTitle(),
                "LIVE",
                live.getId()));
    }

    /**
     * 지금 소개 중인 상품을 바꾼다(LIVE-004). 호스트 본인만.
     *
     * <p><b>편성 변경과 다른 판정을 쓴다.</b> 상품 편성은 방송이 시작되면 잠기지만(운영 정책),
     * 소개 상품 전환은 <b>방송 중에 하는 것이 본래 용도</b>다. 그래서 {@code isOpenForEditing}이
     * 아니라 {@code isClosed}로 막는다 — 끝난 방송에서만 거부한다.
     *
     * @param productId 소개할 상품. <b>{@code null}이면 해제</b>(잡담 구간 등)
     */
    @Transactional
    public CurrentProductResponse changeCurrentProduct(
            Long hostId, Long liveId, LiveCurrentProductRequest request) {
        Live live = liveRepository.findById(liveId)
                .orElseThrow(() -> new CustomException(ErrorCode.LIVE_NOT_FOUND));

        if (!live.isHostedBy(hostId)) {
            throw new CustomException(ErrorCode.NOT_LIVE_HOST);
        }
        if (live.isClosed()) {
            throw new CustomException(ErrorCode.INVALID_LIVE_STATE);
        }
        // 편성되지 않은 상품을 소개 중으로 두면 시청자가 목록에 없는 상품의 NOW 배지를 보게 된다.
        if (request.productId() != null
                && !liveProductService.isLinked(liveId, request.productId())) {
            throw new CustomException(ErrorCode.LIVE_PRODUCT_NOT_FOUND);
        }

        live.changeCurrentProduct(request.productId());

        return CurrentProductResponse.of(liveId, request.productId());
    }

    private Member findHost(Long hostId) {
        return memberRepository.findById(hostId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
    }
}