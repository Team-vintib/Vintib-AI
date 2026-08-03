package com.ssafy.backend.home.service;

import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.home.dto.response.FollowedSellerResponse;
import com.ssafy.backend.home.dto.response.FollowingContentResponse;
import com.ssafy.backend.home.dto.response.LiveCardResponse;
import com.ssafy.backend.home.dto.response.ProductCardResponse;
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
 * <p><b>{@code lives}는 여전히 빈 배열이다</b> — {@code LiveRepository}에 host 기준 조회가 없고,
 * HOME-001의 라이브 섹션 자체가 아직 Mock이라 라이브 카드 조회 로직(썸네일·시청자 수·상태 매핑)이
 * 정의된 적이 없다. HOME-001 실데이터 전환과 함께 채워질 지점이다.
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

    private final FollowRepository followRepository;
    private final ProductRepository productRepository;
    private final ProductImageRepository productImageRepository;
    private final CategoryRepository categoryRepository;
    private final BrandRepository brandRepository;
    private final SocialQueryPort socialQueryPort;
    private final S3StorageService s3StorageService;
    private final AwsProperties awsProperties;

    public FollowingContentResponse getFollowingContent(Long memberId) {
        Pageable sellerPageable =
                PageRequest.of(0, FOLLOWED_SELLER_LIMIT, Sort.by(Sort.Direction.DESC, "createdAt"));
        List<Member> followedSellers = followRepository.findByFollower_Id(memberId, sellerPageable)
                .map(Follow::getFollowing)
                .getContent();

        List<FollowedSellerResponse> followedSellerResponses = toFollowedSellerResponses(followedSellers);
        List<ProductCardResponse> products = toProductCards(followedSellers, memberId);
        // TODO(정윤): LiveRepository에 host 기준 조회가 생기고 HOME-001 라이브 섹션이 실데이터로
        // 전환되면 이 자리에 팔로우한 판매자의 진행/예약 라이브를 채운다.
        List<LiveCardResponse> lives = List.of();

        boolean empty = lives.isEmpty() && products.isEmpty() && followedSellerResponses.isEmpty();
        return new FollowingContentResponse(empty, lives, products, followedSellerResponses);
    }

    private List<FollowedSellerResponse> toFollowedSellerResponses(List<Member> sellers) {
        if (sellers.isEmpty()) {
            return List.of();
        }
        List<Long> sellerIds = sellers.stream().map(Member::getId).toList();
        Map<Long, Long> followerCounts = toFollowerCountMap(sellerIds);
        Map<Long, Long> productCounts = toProductCountMap(sellerIds);

        return sellers.stream()
                .map(seller -> new FollowedSellerResponse(
                        seller.getId(),
                        seller.getNickname(),
                        seller.getProfileImageUrl(),
                        // Member에 커버 이미지 컬럼이 아직 없다(프로필 커버 업로드 기능 미구현).
                        null,
                        followerCounts.getOrDefault(seller.getId(), 0L).intValue(),
                        productCounts.getOrDefault(seller.getId(), 0L).intValue(),
                        // 라이브 연동 전이라 항상 null(TODO 정윤 — 위 getFollowingContent 주석 참고).
                        null, null, null, null))
                .toList();
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
