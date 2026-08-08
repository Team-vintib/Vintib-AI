package com.ssafy.backend.home.service;

import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.auction.repository.AuctionRepository;
import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.home.dto.response.ProductCardResponse;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.port.SocialQueryPort;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductImageRepository;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

/**
 * 상품 목록을 홈/팔로잉 카드로 조립한다.
 *
 * <p>홈(HOME-001)과 팔로잉 홈(HOME-002)이 같은 카드를 그리는데, 브랜드명·카테고리명·대표
 * 이미지·찜 여부를 각자 채우면 규칙이 두 벌이 된다. <b>조립을 한 곳에 모아 두 화면이 항상 같은
 * 카드를 내도록 한다.</b>
 *
 * <p>부가 정보는 전부 <b>ID를 모아 한 번에</b> 조회한다 — 상품마다 브랜드·카테고리·이미지를
 * 따로 읽으면 카드 수만큼 쿼리가 나가고, 홈은 접속할 때마다 열리는 화면이다.
 */
@Component
@RequiredArgsConstructor
public class ProductCardAssembler {

    private final ProductImageRepository productImageRepository;
    private final CategoryRepository categoryRepository;
    private final AuctionRepository auctionRepository;
    private final SocialQueryPort socialQueryPort;
    private final S3StorageService s3StorageService;
    private final AwsProperties awsProperties;

    /**
     * @param viewerId 로그인 회원 ID. <b>비회원이면 null</b>이며 이때 찜 여부는 null로 나간다
     *                 — false로 내리면 FE가 "찜 해제 가능"으로 오해한다
     */
    public List<ProductCardResponse> toCards(List<Product> products, Long viewerId) {
        if (products.isEmpty()) {
            return List.of();
        }

        List<Long> productIds = products.stream().map(Product::getId).toList();
        Map<Long, String> thumbnailByProductId = toThumbnailMap(productIds);
        Map<Long, Auction> auctionByProductId = toAuctionMap(productIds);

        Map<Long, String> categoryNameById = categoryRepository.findAllById(distinct(products, Product::getCategoryId))
                .stream()
                .collect(Collectors.toMap(Category::getId, Category::getName));

        return products.stream()
                .map(product -> toCard(
                        product,
                        product.getBrand(),
                        categoryNameById.get(product.getCategoryId()),
                        thumbnailByProductId.get(product.getId()),
                        auctionByProductId.get(product.getId()),
                        viewerId))
                .toList();
    }

    private ProductCardResponse toCard(
            Product product,
            String brandName,
            String categoryName,
            String thumbnailUrl,
            Auction auction,
            Long viewerId) {
        boolean auctionScheduled = isAuction(product.getSaleStatus());

        return new ProductCardResponse(
                product.getId(),
                product.getTitle(),
                brandName,
                thumbnailUrl,
                auctionScheduled ? "AUCTION_SCHEDULED" : "NORMAL",
                toSellStatus(product.getSaleStatus()),
                // 경매 상품은 확정가가 없다. 가격 자리에 시작가를 넣으면 FE가 즉시구매가로 표시한다.
                auctionScheduled ? null : product.getPrice(),
                auctionScheduled,
                // 판매자는 이미 조회된 상품들이 공유하는 경우가 많아 영속성 컨텍스트에서 재사용된다.
                product.getSeller().getNickname(),
                categoryName,
                wishedFor(product.getId(), viewerId),
                auction == null ? null : auction.getStartPrice(),
                auctionStartsAt(auction));
    }

    /**
     * 찜 여부. <b>비회원에게는 false 가 아니라 null 을 준다</b> — false 로 내리면 FE 가
     * "찜 해제 가능"으로 오해한다. 포트가 원시 {@code boolean}을 돌려주므로 여기서 감싼다.
     * 비회원이면 조회 자체를 건너뛰어 카드 수만큼 나가던 질의도 사라진다.
     */
    private Boolean wishedFor(Long productId, Long viewerId) {
        return viewerId == null ? null : socialQueryPort.isWishedBy(productId, viewerId);
    }

    /**
     * 경매 시작 예정 시각. 경매는 방송 위에서만 열리므로(auction.live_id NOT NULL)
     * <b>그 방송의 예정 시각</b>이 곧 시작 시각이다. 이미 시작한 방송이면 실제 시작 시각을 쓴다.
     */
    private LocalDateTime auctionStartsAt(Auction auction) {
        if (auction == null) {
            return null;
        }
        LocalDateTime scheduledAt = auction.getLive().getScheduledAt();
        return scheduledAt != null ? scheduledAt : auction.getLive().getStartedAt();
    }

    private boolean isAuction(SaleStatus status) {
        return status == SaleStatus.AUCTION_SCHEDULED || status == SaleStatus.AUCTION_IN_PROGRESS;
    }

    // ProductCardResponse 의 sellStatus 허용값(ON_SALE/RESERVED/SOLD_OUT)으로 좁힌다.
    // 경매 진행·예정은 아직 팔리지 않았으므로 판매 중으로 본다 — 경매 여부는 sellType 이 말한다.
    private String toSellStatus(SaleStatus status) {
        return status == SaleStatus.SOLD ? "SOLD_OUT" : "ON_SALE";
    }

    private Map<Long, Auction> toAuctionMap(List<Long> productIds) {
        return auctionRepository.findByProductIdIn(productIds).stream()
                .collect(Collectors.toMap(Auction::getProductId, auction -> auction, (a, b) -> a));
    }

    private Map<Long, String> toThumbnailMap(List<Long> productIds) {
        String bucket = awsProperties.s3().publicBucket();
        return productImageRepository.findByProduct_IdInAndPrimaryTrue(productIds).stream()
                .collect(Collectors.toMap(
                        image -> image.getProduct().getId(),
                        image -> s3StorageService.publicUrl(bucket, image.getImageKey()),
                        (a, b) -> a));
    }

    private List<Long> distinct(
            List<Product> products, java.util.function.Function<Product, Long> extractor) {
        return products.stream().map(extractor).filter(Objects::nonNull).distinct().toList();
    }
}
