package com.ssafy.backend.live.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.live.dto.request.LiveInstantRequest;
import com.ssafy.backend.live.dto.request.LiveScheduleRequest;
import com.ssafy.backend.live.dto.request.LiveListSort;
import com.ssafy.backend.live.dto.request.LiveStatusUpdateRequest;
import com.ssafy.backend.live.dto.response.LiveCategoryResponse;
import com.ssafy.backend.live.dto.response.LiveDetailResponse;
import com.ssafy.backend.live.dto.response.LiveListItemResponse;
import com.ssafy.backend.live.dto.response.LiveResponse;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.live.port.ProductQueryPort.CategorySummary;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
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
    // 종료 시 정리할 리소스가 늘어나면 구현체만 추가한다 — 종료 로직은 다시 열지 않는다.
    private final List<LiveCleanupHook> cleanupHooks;

    // 공개 목록에는 예정·진행 중만 나온다. 종료·취소는 결과에서도 상태 필터에서도 빠진다.
    private static final List<LiveStatus> PUBLIC_STATUSES = List.of(LiveStatus.SCHEDULED, LiveStatus.LIVE);

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
                Live.schedule(host, request.title(), request.thumbnailUrl(), request.scheduledAt()));
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
                Live.openNow(host, request.title(), request.thumbnailUrl(), LocalDateTime.now()));
        liveProductService.linkProductsOnCreate(hostId, live, request.productIds());

        return LiveResponse.from(live);
    }

    /**
     * 라이브 시청 정보 조회(LIVE-005). <b>비회원도 조회할 수 있다.</b>
     *
     * <p>편성 상품을 함께 담아 시청 화면 진입 시 왕복을 늘리지 않는다. 상품 조회는
     * {@link LiveProductService}에 위임해 연결 조회 규칙(제외된 건 제외)을 한 곳에만 둔다.
     */
    public LiveDetailResponse getLiveDetail(Long liveId) {
        Live live = liveRepository.findById(liveId)
                .orElseThrow(() -> new CustomException(ErrorCode.LIVE_NOT_FOUND));

        List<LiveCategoryResponse> categories = liveProductService.getLiveCategories(liveId).stream()
                .map(LiveCategoryResponse::from)
                .toList();

        return LiveDetailResponse.of(live, liveProductService.getLinkedProducts(liveId), categories);
    }

    /**
     * 공개 라이브 목록(LIVE-005). <b>비회원도 조회할 수 있다.</b>
     *
     * <p>공개 목록에는 예정·진행 중만 나온다 — 끝났거나 취소된 방송은 상태 필터 허용값에서도,
     * 결과에서도 빠진다. 카테고리 필터는 편성 상품을 통해 걸리며, 대분류를 고르면 하위 소분류
     * 상품을 건 방송까지 잡힌다.
     *
     * @param categoryIds 비어 있으면 카테고리 필터를 걸지 않는다
     * @param status      null이면 예정·진행 중 모두
     */
    public PageResponse<LiveListItemResponse> getPublicLives(
            List<Long> categoryIds, LiveStatus status, LiveListSort sort, int page, int size) {
        List<LiveStatus> statuses = status == null ? PUBLIC_STATUSES : List.of(status);

        boolean filterByCategory = categoryIds != null && !categoryIds.isEmpty();
        List<Long> productIds = filterByCategory
                ? liveProductService.findProductIdsInCategories(categoryIds)
                : List.of();
        if (filterByCategory && productIds.isEmpty()) {
            // 해당 카테고리 상품이 하나도 없으면 매칭될 라이브도 없다. IN () 로 쿼리가 깨지는 것도 막는다.
            return PageResponse.from(Page.empty(PageRequest.of(page, size)));
        }

        Page<Live> lives = liveRepository.findPublicLives(
                statuses, filterByCategory, productIds, PageRequest.of(page, size, sort.toSort()));

        Map<Long, List<CategorySummary>> categoriesByLiveId =
                liveProductService.getCategoriesByLiveIds(lives.getContent().stream().map(Live::getId).toList());

        return PageResponse.from(lives.map(live -> LiveListItemResponse.of(
                live,
                categoriesByLiveId.getOrDefault(live.getId(), List.of()).stream()
                        .map(LiveCategoryResponse::from)
                        .toList())));
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

        if (request.status() == LiveStatus.ENDED) {
            cleanupHooks.forEach(hook -> hook.onLiveEnded(live));
        }

        return LiveResponse.from(live);
    }

    private Member findHost(Long hostId) {
        return memberRepository.findById(hostId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
    }
}