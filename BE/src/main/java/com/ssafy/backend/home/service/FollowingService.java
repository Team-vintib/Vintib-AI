package com.ssafy.backend.home.service;

import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.home.dto.response.FollowedSellerResponse;
import com.ssafy.backend.home.dto.response.FollowingContentResponse;
import com.ssafy.backend.home.dto.response.LiveCardResponse;
import com.ssafy.backend.home.dto.response.ProductCardResponse;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.product.entity.Brand;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.port.SocialQueryPort;
import com.ssafy.backend.product.repository.BrandRepository;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductImageRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import com.ssafy.backend.social.entity.Follow;
import com.ssafy.backend.social.repository.FollowRepository;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 팔로잉 콘텐츠 조회(HOME-002) 서비스.
 *
 * <p><b>{@code followedSellers}·{@code products}는 실데이터다</b>(SY024). {@code products}는
 * 팔로우한 판매자의 상시 판매(ON_SALE) 상품만 채운다 — {@code ProductCardResponse}의
 * sellType/sellStatus 허용값이 아직 경매 도메인과 1:1로 매핑 확정되지 않았고, 경매 예정 상품은
 * {@code auction} 패키지 조회가 별도로 필요해 이번 범위를 벗어난다.
 *
 * <p><b>{@code lives}도 실데이터다</b> — 팔로우한 판매자들의 진행 중·예정 방송을 최신순으로 채운다.
 * 카드 조립은 홈(HOME-001)과 같은 {@link LiveCardAssembler}를 쓴다.
 *
 * <p><b>{@code products}는 팔로우한 판매자의 상품이다</b> — 개인화 추천(REC-001)이 아니다.
 * FE가 이 목록을 '추천 상품'으로 표시하고 있었는데 의미가 다르다
 * (FE 요청 009-home-card-response-fields 요청 7).
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class FollowingService {

    private static final int FOLLOWED_SELLER_LIMIT = 10;
    private static final int PRODUCT_LIMIT = 20;
    private static final int LIVE_LIMIT = 10;

    private final FollowRepository followRepository;
    private final ProductRepository productRepository;
    private final ProductImageRepository productImageRepository;
    private final CategoryRepository categoryRepository;
    private final BrandRepository brandRepository;
    private final SocialQueryPort socialQueryPort;
    private final S3StorageService s3StorageService;
    private final AwsProperties awsProperties;
    private final LiveRepository liveRepository;
    private final LiveCardAssembler liveCardAssembler;

    public FollowingContentResponse getFollowingContent(Long memberId) {
        Pageable sellerPageable =
                PageRequest.of(0, FOLLOWED_SELLER_LIMIT, Sort.by(Sort.Direction.DESC, "createdAt"));
        List<Member> followedSellers = followRepository.findByFollower_Id(memberId, sellerPageable)
                .map(Follow::getFollowing)
                .getContent();

        // 방송은 한 번만 조회해 판매자 카드의 라이브 배지와 라이브 섹션이 함께 쓴다 —
        // 둘이 따로 조회하면 같은 화면 안에서 서로 다른 스냅샷을 보여 줄 수 있다.
        List<Live> followedLives = findFollowedLives(followedSellers);

        List<FollowedSellerResponse> followedSellerResponses =
                toFollowedSellerResponses(followedSellers, followedLives);
        List<ProductCardResponse> products = toProductCards(followedSellers, memberId);
        List<LiveCardResponse> lives = liveCardAssembler.toCards(followedLives);

        boolean empty = lives.isEmpty() && products.isEmpty() && followedSellerResponses.isEmpty();
        return new FollowingContentResponse(empty, lives, products, followedSellerResponses);
    }

    /**
     * 팔로우한 판매자들의 진행 중·예정 방송. 종료·취소는 넣지 않는다 — 팔로잉 홈은 "지금 볼 것"을
     * 보여 주는 화면이고, 지난 방송은 판매자 프로필에서 본다.
     */
    private List<Live> findFollowedLives(List<Member> followedSellers) {
        if (followedSellers.isEmpty()) {
            return List.of();
        }
        List<Long> sellerIds = followedSellers.stream().map(Member::getId).toList();
        return liveRepository.findByHost_IdInAndStatusInOrderByCreatedAtDesc(
                sellerIds,
                List.of(LiveStatus.LIVE, LiveStatus.SCHEDULED),
                PageRequest.of(0, LIVE_LIMIT));
    }

    private List<FollowedSellerResponse> toFollowedSellerResponses(
            List<Member> sellers, List<Live> followedLives) {
        if (sellers.isEmpty()) {
            return List.of();
        }
        List<Long> sellerIds = sellers.stream().map(Member::getId).toList();
        Map<Long, Long> followerCounts = toFollowerCountMap(sellerIds);
        Map<Long, Long> productCounts = toProductCountMap(sellerIds);
        Map<Long, Live> liveByHostId = toBadgeLiveByHostId(followedLives);

        return sellers.stream()
                .map(seller -> {
                    Live live = liveByHostId.get(seller.getId());
                    return new FollowedSellerResponse(
                            seller.getId(),
                            seller.getNickname(),
                            seller.getProfileImageUrl(),
                            // Member에 커버 이미지 컬럼이 아직 없다(프로필 커버 업로드 기능 미구현).
                            null,
                            followerCounts.getOrDefault(seller.getId(), 0L).intValue(),
                            productCounts.getOrDefault(seller.getId(), 0L).intValue(),
                            live == null ? null : live.getId(),
                            live == null ? null : live.getStatus().name(),
                            live == null ? null : live.getTitle(),
                            live == null ? null : liveAt(live));
                })
                .toList();
    }

    /**
     * 판매자 카드에 배지로 띄울 방송 하나를 고른다. <b>진행 중이 예정보다 우선</b>이다 —
     * 지금 볼 수 있는 방송이 있는데 예약 방송을 안내하면 클릭이 헛돈다.
     */
    private Map<Long, Live> toBadgeLiveByHostId(List<Live> lives) {
        Map<Long, Live> byHostId = new HashMap<>();
        lives.forEach(live -> byHostId.merge(
                live.getHost().getId(),
                live,
                (kept, candidate) -> kept.getStatus() == LiveStatus.LIVE ? kept : candidate));
        return byHostId;
    }

    private LocalDateTime liveAt(Live live) {
        return live.getStatus() == LiveStatus.LIVE ? live.getStartedAt() : live.getScheduledAt();
    }

    private List<ProductCardResponse> toProductCards(List<Member> followedSellers, Long viewerId) {
        if (followedSellers.isEmpty()) {
            return List.of();
        }
        List<Long> sellerIds = followedSellers.stream().map(Member::getId).toList();
        // Collectors.toMap은 값이 null이면 NPE를 던지는데, 닉네임은 온보딩 전이면 null일 수 있어
        // HashMap에 직접 채운다(Map.put은 null 값을 허용).
        Map<Long, String> sellerNameById = new HashMap<>();
        followedSellers.forEach(seller -> sellerNameById.put(seller.getId(), seller.getNickname()));

        List<Product> products = productRepository.findBySeller_IdInAndSaleStatusOrderByCreatedAtDesc(
                sellerIds, SaleStatus.ON_SALE, PageRequest.of(0, PRODUCT_LIMIT));
        if (products.isEmpty()) {
            return List.of();
        }

        List<Long> productIds = products.stream().map(Product::getId).toList();
        Map<Long, String> thumbnailByProductId = toThumbnailMap(productIds);

        List<Long> categoryIds = products.stream()
                .map(Product::getCategoryId)
                .filter(Objects::nonNull)
                .distinct()
                .toList();
        Map<Long, String> categoryNameById = categoryRepository.findAllById(categoryIds).stream()
                .collect(Collectors.toMap(Category::getId, Category::getName));

        List<Long> brandIds =
                products.stream().map(Product::getBrandId).filter(Objects::nonNull).distinct().toList();
        Map<Long, String> brandNameById = brandRepository.findAllById(brandIds).stream()
                .collect(Collectors.toMap(Brand::getId, Brand::getName));

        return products.stream()
                .map(product -> new ProductCardResponse(
                        product.getId(),
                        product.getTitle(),
                        brandNameById.get(product.getBrandId()),
                        thumbnailByProductId.get(product.getId()),
                        "NORMAL",
                        "ON_SALE",
                        product.getPrice(),
                        false,
                        sellerNameById.get(product.getSeller().getId()),
                        categoryNameById.get(product.getCategoryId()),
                        socialQueryPort.isWishedBy(product.getId(), viewerId),
                        null,
                        null))
                .toList();
    }

    private Map<Long, String> toThumbnailMap(List<Long> productIds) {
        String bucket = awsProperties.s3().publicBucket();
        return productImageRepository.findByProduct_IdInAndPrimaryTrue(productIds).stream()
                .collect(Collectors.toMap(
                        image -> image.getProduct().getId(),
                        image -> s3StorageService.publicUrl(bucket, image.getImageKey()),
                        (a, b) -> a));
    }

    private Map<Long, Long> toFollowerCountMap(List<Long> memberIds) {
        return followRepository.countFollowersByMemberIds(memberIds).stream()
                .collect(Collectors.toMap(
                        FollowRepository.MemberFollowerCount::getMemberId,
                        FollowRepository.MemberFollowerCount::getCount));
    }

    private Map<Long, Long> toProductCountMap(List<Long> sellerIds) {
        return productRepository.countBySellerIdsAndSaleStatusNot(sellerIds, SaleStatus.DRAFT).stream()
                .collect(Collectors.toMap(
                        ProductRepository.SellerProductCount::getSellerId,
                        ProductRepository.SellerProductCount::getCount));
    }
}
