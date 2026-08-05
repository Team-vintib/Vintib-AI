package com.ssafy.backend.search.service;

import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.home.dto.response.LiveCardResponse;
import com.ssafy.backend.home.dto.response.ProductCardResponse;
import com.ssafy.backend.home.service.LiveCardAssembler;
import com.ssafy.backend.home.service.ProductCardAssembler;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.entity.SaleType;
import com.ssafy.backend.product.repository.ProductRepository;
import com.ssafy.backend.search.dto.request.SearchSort;
import com.ssafy.backend.search.dto.request.SearchType;
import com.ssafy.backend.search.dto.response.SearchResponse;
import com.ssafy.backend.search.dto.response.UserSearchItemResponse;
import com.ssafy.backend.search.repository.SearchQueryRepository;
import com.ssafy.backend.social.repository.FollowRepository;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 통합 검색(SEARCH-001/002).
 *
 * <p>세 도메인을 한 번에 훑지만 <b>요청한 탭만 조회한다</b> — {@code type=PRODUCT}인데 라이브·회원까지
 * 매번 세는 것은 그대로 낭비다. 조회하지 않은 섹션은 null로 내려 FE가 "0건"과 구분한다.
 *
 * <p>카드 조립은 홈과 같은 {@link ProductCardAssembler}·{@link LiveCardAssembler}를 쓴다.
 * 같은 상품이 홈과 검색에서 다르게 보이면 안 된다.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class SearchService {

    // 공개 상태만 검색된다. 종료·취소된 방송이 나오면 눌러도 시청할 수 없다.
    private static final List<LiveStatus> PUBLIC_LIVE_STATUSES =
            List.of(LiveStatus.LIVE, LiveStatus.SCHEDULED);

    private final SearchQueryRepository searchQueryRepository;
    private final ProductRepository productRepository;
    private final FollowRepository followRepository;
    private final ProductCardAssembler productCardAssembler;
    private final LiveCardAssembler liveCardAssembler;

    /**
     * @param viewerId 로그인 회원 ID. <b>비회원이면 null</b>이며 찜·팔로우 여부가 null로 나간다
     */
    public SearchResponse search(
            String keyword,
            SearchType type,
            List<Long> categoryIds,
            List<String> conditionGrades,
            List<SaleType> saleTypes,
            Long minPrice,
            Long maxPrice,
            SearchSort sort,
            int page,
            int size,
            Long viewerId) {

        String trimmed = keyword.trim();

        return new SearchResponse(
                type.includes(SearchType.PRODUCT)
                        ? searchProducts(
                                trimmed, categoryIds, conditionGrades, saleTypes,
                                minPrice, maxPrice, sort, page, size, viewerId)
                        : null,
                type.includes(SearchType.LIVE) ? searchLives(trimmed, page, size) : null,
                type.includes(SearchType.USER) ? searchUsers(trimmed, page, size, viewerId) : null);
    }

    private PageResponse<ProductCardResponse> searchProducts(
            String keyword,
            List<Long> categoryIds,
            List<String> conditionGrades,
            List<SaleType> saleTypes,
            Long minPrice,
            Long maxPrice,
            SearchSort sort,
            int page,
            int size,
            Long viewerId) {

        boolean hasCategoryFilter = isNotEmpty(categoryIds);
        boolean hasConditionFilter = isNotEmpty(conditionGrades);
        boolean hasSaleTypeFilter = isNotEmpty(saleTypes);

        Page<Product> found = searchQueryRepository.searchProducts(
                keyword,
                hasCategoryFilter, hasCategoryFilter ? categoryIds : List.of(0L),
                hasConditionFilter, hasConditionFilter ? conditionGrades : List.of(""),
                hasSaleTypeFilter, hasSaleTypeFilter ? saleTypes : List.of(SaleType.DIRECT_SALE),
                minPrice != null, minPrice,
                maxPrice != null, maxPrice,
                PageRequest.of(page, size, sort.toProductSort()));

        return replaceContent(found, productCardAssembler.toCards(found.getContent(), viewerId));
    }

    private PageResponse<LiveCardResponse> searchLives(String keyword, int page, int size) {
        Page<Live> found = searchQueryRepository.searchLives(
                keyword,
                PUBLIC_LIVE_STATUSES,
                PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt")));

        return replaceContent(found, liveCardAssembler.toCards(found.getContent()));
    }

    private PageResponse<UserSearchItemResponse> searchUsers(
            String keyword, int page, int size, Long viewerId) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.ASC, "nickname"));
        Page<Member> found = searchQueryRepository.searchMembers(keyword, pageable);
        if (found.isEmpty()) {
            return replaceContent(found, List.of());
        }

        List<Long> memberIds = found.getContent().stream().map(Member::getId).toList();
        Map<Long, Long> followerCounts = followRepository.countFollowersByMemberIds(memberIds).stream()
                .collect(Collectors.toMap(
                        FollowRepository.MemberFollowerCount::getMemberId,
                        FollowRepository.MemberFollowerCount::getCount));
        Map<Long, Long> productCounts =
                productRepository.countBySellerIdsAndSaleStatusNot(memberIds, SaleStatus.DRAFT).stream()
                        .collect(Collectors.toMap(
                                ProductRepository.SellerProductCount::getSellerId,
                                ProductRepository.SellerProductCount::getCount));

        List<UserSearchItemResponse> items = found.getContent().stream()
                .map(member -> new UserSearchItemResponse(
                        member.getId(),
                        member.getNickname(),
                        member.getProfileImageUrl(),
                        followerCounts.getOrDefault(member.getId(), 0L).intValue(),
                        productCounts.getOrDefault(member.getId(), 0L).intValue(),
                        followingFor(viewerId, member.getId())))
                .toList();

        return replaceContent(found, items);
    }

    /**
     * 팔로우 여부. 비회원에게는 false 가 아니라 null 을 준다 — 찜 여부와 같은 이유다.
     * 자기 자신은 팔로우할 수 없으므로 항상 false 다.
     */
    private Boolean followingFor(Long viewerId, Long targetId) {
        if (viewerId == null) {
            return null;
        }
        return !viewerId.equals(targetId)
                && followRepository.existsByFollower_IdAndFollowing_Id(viewerId, targetId);
    }

    /**
     * 페이지 메타(총 개수·다음 페이지 여부)는 엔티티 조회 결과에서 그대로 가져오고 내용만 카드로
     * 바꾼다. 카드 목록으로 페이지를 다시 만들면 총 개수를 잃는다.
     */
    private <E, T> PageResponse<T> replaceContent(Page<E> source, List<T> content) {
        return new PageResponse<>(
                content,
                source.getNumber(),
                source.getSize(),
                source.getTotalElements(),
                source.getTotalPages(),
                source.hasNext());
    }

    private boolean isNotEmpty(Collection<?> values) {
        return values != null && !values.isEmpty();
    }
}
