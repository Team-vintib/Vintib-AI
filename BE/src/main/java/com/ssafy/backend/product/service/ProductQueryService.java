package com.ssafy.backend.product.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.product.dto.request.ProductListFilterParams;
import com.ssafy.backend.product.dto.request.ProductSortType;
import com.ssafy.backend.product.dto.response.AiQualityAnalysisImageResponse;
import com.ssafy.backend.product.dto.response.AiQualityAnalysisResponse;
import com.ssafy.backend.product.dto.response.AiQualityFindingResponse;
import com.ssafy.backend.product.dto.response.LinkedLiveSummaryResponse;
import com.ssafy.backend.product.dto.response.ProductDetailResponse;
import com.ssafy.backend.product.dto.response.ProductImageResponse;
import com.ssafy.backend.product.dto.response.ProductMarketPriceResponse;
import com.ssafy.backend.product.dto.response.ProductPriceEstimateResponse;
import com.ssafy.backend.product.dto.response.ProductResponse;
import com.ssafy.backend.product.dto.response.SimilarProductResponse;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.ProductImageRole;
import com.ssafy.backend.product.entity.QualityInspectionStatus;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.port.LiveQueryPort;
import com.ssafy.backend.product.port.OrderQueryPort;
import com.ssafy.backend.product.port.SocialQueryPort;
import com.ssafy.backend.product.port.dto.CompletedOrderSummary;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.Function;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** 상품 목록/상세/시세 비교 등 읽기 전용 조회. */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ProductQueryService {

    // 그래프용 표본으로 충분한 개수. 상세 조회 왕복마다 전수 조회하지 않도록 상한을 둔다.
    private static final int SIMILAR_PRODUCT_LIMIT = 20;

    // "동일 상품 시세" 매물 수 상한 — findSimilarProducts와 같은 기준.
    private static final int MARKET_PRICE_LIMIT = 20;

    private final ProductRepository productRepository;
    private final ProductImageService productImageService;
    private final CategoryRepository categoryRepository;
    private final SocialQueryPort socialQueryPort;
    private final LiveQueryPort liveQueryPort;
    private final OrderQueryPort orderQueryPort;

    public PageResponse<ProductResponse> getProductList(ProductListFilterParams filter, Pageable pageable) {
        Sort sort = buildSort(filter.resolvedSort());
        Pageable sortedPageable = PageRequest.of(pageable.getPageNumber(), pageable.getPageSize(), sort);

        // 카테고리 필터가 없으면 JPQL에 빈 리스트를 넘기면 안 된다(IN 절 오류).
        // 플래그가 false일 때는 쿼리에서 조건을 건너뛰므로 더미값을 넣어도 무방하다.
        List<Long> categoryIds = filter.hasCategoryFilter() ? filter.categoryIds() : List.of(-1L);
        List<String> conditionGrades = filter.hasConditionFilter() ? filter.conditionGrades() : List.of("");

        Page<Product> products = productRepository.findWithFilter(
                filter.hasCategoryFilter(), categoryIds,
                filter.hasConditionFilter(), conditionGrades,
                filter.hasSaleTypeFilter(), filter.saleType(),
                filter.hasMinPriceFilter(), filter.minPrice(),
                filter.hasMaxPriceFilter(), filter.maxPrice(),
                filter.hasSellerFilter(), filter.sellerId(),
                sortedPageable);

        return PageResponse.from(products.map(ProductResponse::from));
    }

    /** 마이페이지 판매 상품 관리 — 본인 소유 상품을 등록일 최신순으로 전부 반환(DRAFT 등 비공개 상태 포함). */
    public PageResponse<ProductResponse> getMyProducts(Long sellerId, Pageable pageable) {
        Page<Product> products = productRepository.findBySeller_IdOrderByCreatedAtDesc(sellerId, pageable);
        return PageResponse.from(products.map(ProductResponse::from));
    }

    private Sort buildSort(ProductSortType sortType) {
        return switch (sortType) {
            case PRICE_ASC -> Sort.by(Sort.Direction.ASC, "price");
            case PRICE_DESC -> Sort.by(Sort.Direction.DESC, "price");
            default -> Sort.by(Sort.Direction.DESC, "createdAt");
        };
    }

    public ProductDetailResponse getProductDetail(Long viewerId, Long productId) {
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new CustomException(ErrorCode.PRODUCT_NOT_FOUND));

        if (product.isDeleted()) {
            throw new CustomException(ErrorCode.PRODUCT_NOT_FOUND);
        }
        if (product.isDraft() && !product.isOwnedBy(viewerId)) {
            throw new CustomException(ErrorCode.PRODUCT_NOT_FOUND);
        }
        // defects는 항상 배열. JSONB 컬럼은 한 번도 안 써지면 null이므로, 빈 리스트로 맞춘다.
        List<String> defects = Objects.requireNonNullElse(product.getDefects(), List.<String>of());

        String categoryName = product.getCategoryId() == null ? null : categoryRepository.findById(product.getCategoryId())
                .map(Category::getName)
                .orElse(null);

        Long sellerId = product.getSeller().getId();
        long sellerProductCount = productRepository.countBySeller_IdAndSaleStatusNot(sellerId, SaleStatus.DRAFT);
        long sellerFollowerCount = socialQueryPort.countFollowers(sellerId);
        boolean isWished = socialQueryPort.isWishedBy(productId, viewerId);

        LinkedLiveSummaryResponse linkedLive = liveQueryPort.findLinkedLive(productId)
                .map(LinkedLiveSummaryResponse::from)
                .orElse(null);

        List<SimilarProductResponse> similarProducts = productRepository.findSimilarProducts(
                        product.getCategoryId(),
                        productId,
                        product.getBrand(),
                        PageRequest.of(0, SIMILAR_PRODUCT_LIMIT))
                .stream()
                .map(SimilarProductResponse::from)
                .toList();

        List<ProductImageResponse> images = productImageService.getImages(productId);

        return ProductDetailResponse.from(
                product,
                categoryName,
                images,
                defects,
                isWished,
                sellerFollowerCount,
                sellerProductCount,
                linkedLive,
                similarProducts,
                buildAiQualityAnalysis(product, images),
                buildPriceEstimate(product));
    }

    /** 등록 시 확정 등급으로 저장해둔 AI 시세 산정 스냅샷. 없으면(가격 산정 전) null. */
    private ProductPriceEstimateResponse buildPriceEstimate(Product product) {
        Map<String, Object> result = product.getPriceEstimateResult();
        return result == null ? null : ProductPriceEstimateResponse.from(result);
    }

    /**
     * 상품 상세 "AI 분석" 탭. 별도 저장 테이블 없이 @link Product#getQualityInspectionResult()}
     * 원본(AI가 완료 시점에 캐시해둔 JSON)에서 매 조회마다 조립.
     * {@code section}/{@code no}/{@code description} 등을 그대로 저장하므로 등록 화면과 항상 일치한다.
     *
     * <p>상태는 {@link Product#getQualityInspectionStatus()}를 그대로 매핑.
     */
    @SuppressWarnings("unchecked")
    private AiQualityAnalysisResponse buildAiQualityAnalysis(Product product, List<ProductImageResponse> images) {
        QualityInspectionStatus status = product.getQualityInspectionStatus();
        if (status == QualityInspectionStatus.NONE) {
            return AiQualityAnalysisResponse.notRequested();
        }
        if (status == QualityInspectionStatus.PENDING || status == QualityInspectionStatus.PROCESSING) {
            return AiQualityAnalysisResponse.analyzing();
        }
        if (status == QualityInspectionStatus.FAILED) {
            return AiQualityAnalysisResponse.failed();
        }

        Map<String, Object> result = product.getQualityInspectionResult();
        List<Map<String, Object>> findings = result == null
                ? List.of()
                : (List<Map<String, Object>>) result.getOrDefault("findings", List.of());
        if (findings.isEmpty()) {
            return AiQualityAnalysisResponse.noFindings();
        }

        List<String> excludedKeys = Objects.requireNonNullElse(
                product.getExcludedQualityFindingKeys(), List.<String>of());
        List<Map<String, Object>> imageSummaries =
                (List<Map<String, Object>>) result.getOrDefault("image_summaries", List.of());

        Map<ProductImageRole, String> imageUrlByRole = images.stream()
                .filter(image -> image.role() == ProductImageRole.FRONT || image.role() == ProductImageRole.BACK)
                .collect(Collectors.toMap(ProductImageResponse::role, ProductImageResponse::url, (a, b) -> a));

        List<AiQualityAnalysisImageResponse> imageResponses = new ArrayList<>();
        for (ProductImageRole role : List.of(ProductImageRole.FRONT, ProductImageRole.BACK)) {
            // AI는 photoRole을 모르고 image_index(앞=0/뒤=1)만 안다 — role↔image_index 변환.
            int imageIndex = role == ProductImageRole.FRONT ? 0 : 1;

            List<AiQualityFindingResponse> roleFindings = findings.stream()
                    .filter(finding -> imageIndex == asInt(finding.get("image_index")))
                    .map(finding -> AiQualityFindingResponse.from(
                            finding, excludedKeys.contains(finding.get("key"))))
                    .toList();
            if (roleFindings.isEmpty()) {
                continue;
            }

            String summary = imageSummaries.stream()
                    .filter(entry -> imageIndex == asInt(entry.get("image_index")))
                    .map(entry -> (String) entry.get("summary"))
                    .findFirst()
                    .orElse(null);
            String url = imageUrlByRole.get(role);
            imageResponses.add(new AiQualityAnalysisImageResponse(
                    role == ProductImageRole.FRONT ? "앞면" : "뒷면", url, url, summary, roleFindings));
        }

        return imageResponses.isEmpty()
                ? AiQualityAnalysisResponse.noFindings()
                : AiQualityAnalysisResponse.completed(imageResponses);
    }

    private static int asInt(Object value) {
        return value instanceof Number number ? number.intValue() : -1;
    }

    /**
     * "동일 상품 시세" — 같은 {@code matchKey}를 가진 다른 상품들의 호가/완료거래가.
     * {@code matchKey}가 아직 없으면(가격 책정 전 상품) 빈 목록. 404가 아닌 "판정 근거 없음".
     */
    public ProductMarketPriceResponse getMarketPrice(Long productId) {
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new CustomException(ErrorCode.PRODUCT_NOT_FOUND));

        List<Product> listingProducts = product.getMatchKey() == null
                ? List.of()
                : productRepository.findByMatchKeyAndIdNot(
                        product.getMatchKey(), productId, PageRequest.of(0, MARKET_PRICE_LIMIT));

        List<Long> orderLookupIds = new ArrayList<>(listingProducts.stream().map(Product::getId).toList());
        orderLookupIds.add(productId);
        Map<Long, CompletedOrderSummary> completedOrderByProductId = orderQueryPort
                .findCompletedOrders(orderLookupIds).stream()
                .collect(Collectors.toMap(
                        CompletedOrderSummary::productId, Function.identity(), (first, second) -> first));

        List<ProductMarketPriceResponse.Item> listings = listingProducts.stream()
                .map(p -> toMarketPriceItem(p, completedOrderByProductId))
                .filter(Objects::nonNull)
                .toList();

        return new ProductMarketPriceResponse(
                productId,
                product.getMatchKey(),
                toMarketPriceItem(product, completedOrderByProductId),
                listings);
    }

    /** ON_SALE/SOLD가 아니면 null. */
    private ProductMarketPriceResponse.Item toMarketPriceItem(
            Product product, Map<Long, CompletedOrderSummary> completedOrderByProductId) {
        if (product.getSaleStatus() == SaleStatus.ON_SALE) {
            return new ProductMarketPriceResponse.Item(
                    product.getId(), product.getTitle(), product.getPrice(), "ASKING");
        }
        if (product.getSaleStatus() == SaleStatus.SOLD) {
            CompletedOrderSummary order = completedOrderByProductId.get(product.getId());
            if (order == null) {
                return null; // 완료 거래 근거를 못 찾음. 시세 x.
            }
            String priceKind = order.auctionWin() ? "SOLD_AUCTION" : "SOLD_DIRECT";
            return new ProductMarketPriceResponse.Item(
                    product.getId(), product.getTitle(), order.orderPrice(), priceKind);
        }
        return null;
    }
}