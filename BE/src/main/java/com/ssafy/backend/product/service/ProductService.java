package com.ssafy.backend.product.service;

import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.client.dto.AiJobResponse;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.dto.request.AiQualityFindingRequest;
import com.ssafy.backend.product.dto.request.ProductCreateRequest;
import com.ssafy.backend.product.dto.request.ProductListFilterParams;
import com.ssafy.backend.product.dto.request.ProductSortType;
import com.ssafy.backend.product.dto.request.ProductStatusUpdateRequest;
import com.ssafy.backend.product.dto.request.ProductUpdateRequest;
import com.ssafy.backend.product.dto.response.AiQualityAnalysisImageResponse;
import com.ssafy.backend.product.dto.response.AiQualityAnalysisResponse;
import com.ssafy.backend.product.dto.response.AiQualityFindingResponse;
import com.ssafy.backend.product.dto.response.ProductAiModelCutResponse;
import com.ssafy.backend.product.dto.response.ProductDetailResponse;
import com.ssafy.backend.product.dto.response.ProductImageResponse;
import com.ssafy.backend.product.dto.response.ProductMarketPriceResponse;
import com.ssafy.backend.product.dto.response.ProductQualityInspectionResponse;
import com.ssafy.backend.product.dto.response.ProductResponse;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.product.dto.response.LinkedLiveSummaryResponse;
import com.ssafy.backend.product.dto.response.SimilarProductResponse;
import com.ssafy.backend.product.entity.AiModelCutStatus;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.ProductDefect;
import com.ssafy.backend.product.entity.ProductImageRole;
import com.ssafy.backend.product.entity.ProductQualityFinding;
import com.ssafy.backend.product.entity.QualityInspectionStatus;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.port.OrderQueryPort;
import com.ssafy.backend.product.port.dto.CompletedOrderSummary;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductDefectRepository;
import com.ssafy.backend.product.repository.ProductQualityFindingRepository;
import com.ssafy.backend.product.port.LiveQueryPort;
import com.ssafy.backend.product.port.SocialQueryPort;
import com.ssafy.backend.product.repository.ProductRepository;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.Function;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestClientException;

@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ProductService {

    // 그래프용 표본으로 충분한 개수. 상세 조회 왕복마다 전수 조회하지 않도록 상한을 둔다.
    private static final int SIMILAR_PRODUCT_LIMIT = 20;

    // "동일 상품 시세"(CH001) 매물 수 상한 — findSimilarProducts와 같은 기준.
    private static final int MARKET_PRICE_LIMIT = 20;

    private final ProductRepository productRepository;
    private final MemberRepository memberRepository;
    private final ProductImageService productImageService;
    private final CategoryRepository categoryRepository;
    private final ProductDefectRepository productDefectRepository;
    private final ProductQualityFindingRepository productQualityFindingRepository;
    private final SocialQueryPort socialQueryPort;
    private final LiveQueryPort liveQueryPort;
    private final OrderQueryPort orderQueryPort;
    private final AiClient aiClient;

    @Transactional
    public ProductResponse createProduct(Long sellerId, ProductCreateRequest request) {
        Member seller = memberRepository.findById(sellerId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

        // 카테고리는 필수이며 실제로 존재해야 함. DTO의 @NotNull 은 "값이 있는지"만 보므로
        // 없는 ID 를 그대로 넣으면 FK 위반이 500 으로 새어 나간다.
        if (!categoryRepository.existsById(request.categoryId())) {
            throw new CustomException(ErrorCode.CATEGORY_NOT_FOUND);
        }
        // aiModelEnabled=true인데 gender가 없으면 어떤 성별 모델 사진으로 합성할지 정할 수 없다.
        if (request.aiModelEnabled() && request.aiModelGender() == null) {
            throw new CustomException(ErrorCode.AI_MODEL_GENDER_REQUIRED);
        }

        Product product = Product.builder()
                .seller(seller)
                .categoryId(request.categoryId())
                .brand(request.brand())
                .title(request.title())
                .description(request.description())
                .conditionGrade(request.conditionGrade())
                .conditionScore(request.conditionScore())
                .sizeLabel(request.sizeLabel())
                .color(request.color())
                .material(request.material())
                .measurements(request.measurements())
                .aiModelEnabled(request.aiModelEnabled())
                .aiModelGender(request.aiModelEnabled() ? request.aiModelGender() : null)
                .build();

        Product saved = productRepository.save(product);
        saveDefects(saved, request.defects());
        saveQualityFindings(saved, request.aiQualityFindings());

        return ProductResponse.from(saved);
    }

    // 등록 시 사용자가 인정·확정한 AI 품질 검수 finding을 순서대로 저장.
    private void saveQualityFindings(Product product, List<AiQualityFindingRequest> findings) {
        if (findings == null || findings.isEmpty()) {
            return;
        }
        List<ProductQualityFinding> entities = new ArrayList<>();
        for (int i = 0; i < findings.size(); i++) {
            AiQualityFindingRequest finding = findings.get(i);
            if (finding.photoRole() != ProductImageRole.FRONT && finding.photoRole() != ProductImageRole.BACK) {
                throw new CustomException(ErrorCode.AI_QUALITY_FINDING_INVALID_PHOTO_ROLE);
            }
            entities.add(ProductQualityFinding.builder()
                    .product(product)
                    .photoRole(finding.photoRole())
                    .description(finding.description())
                    .box(toBoxMap(finding.box()))
                    .sortOrder((short) i)
                    .build());
        }
        productQualityFindingRepository.saveAll(entities);
    }

    private Map<String, Integer> toBoxMap(AiQualityFindingRequest.Box box) {
        if (box == null) {
            return null;
        }
        return Map.of("x", box.x(), "y", box.y(), "width", box.width(), "height", box.height());
    }

    // 등록 시점에 판매자가 입력한 하자 목록 순서대로 저장.
    private void saveDefects(Product product, List<String> defects) {
        if (defects == null || defects.isEmpty()) {
            return;
        }
        List<ProductDefect> entities = new ArrayList<>();
        for (int i = 0; i < defects.size(); i++) {
            entities.add(ProductDefect.builder()
                    .product(product)
                    .content(defects.get(i))
                    .sortOrder((short) i)
                    .build());
        }
        productDefectRepository.saveAll(entities);
    }

    // DRAFT(최초 등록) 또는 AUCTION_SCHEDULED(경매 예정 상품의 상시 판매 전환)에서 호출.
    @Transactional
    public ProductResponse registerDirectSale(Long sellerId, Long productId, ProductStatusUpdateRequest request) {
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new CustomException(ErrorCode.PRODUCT_NOT_FOUND));

        if (!product.isOwnedBy(sellerId)) {
            throw new CustomException(ErrorCode.NOT_PRODUCT_OWNER);
        }
        if (product.getSaleStatus() != SaleStatus.DRAFT && product.getSaleStatus() != SaleStatus.AUCTION_SCHEDULED) {
            throw new CustomException(ErrorCode.INVALID_PRODUCT_STATE);
        }

        product.registerDirectSale(request.price());

        return ProductResponse.from(product);
    }

    // DRAFT(최초 등록) 또는 ON_SALE(상시 판매 상품의 경매 전환)에서 호출.
    // 시작가/증액 단위/경매 시간은 경매 조건 설정에서 함.
    @Transactional
    public ProductResponse scheduleAuction(Long sellerId, Long productId) {
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new CustomException(ErrorCode.PRODUCT_NOT_FOUND));

        if (!product.isOwnedBy(sellerId)) {
            throw new CustomException(ErrorCode.NOT_PRODUCT_OWNER);
        }
        if (product.getSaleStatus() != SaleStatus.DRAFT && product.getSaleStatus() != SaleStatus.ON_SALE) {
            throw new CustomException(ErrorCode.INVALID_PRODUCT_STATE);
        }

        product.scheduleAuction();

        return ProductResponse.from(product);
    }

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
        List<String> defects = productDefectRepository.findAllByProductIdOrderBySortOrderAsc(productId).stream()
                .map(ProductDefect::getContent)
                .toList();

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
                buildAiQualityAnalysis(productId, images));
    }

    /**
     * 상품 상세 "AI 분석" 탭. 등록 시 저장해둔 finding을 사진(FRONT/BACK)별로 묶어 낸다.
     *
     * <p><b>{@code NOT_REQUESTED}와 {@code NO_FINDINGS}를 구분하지 않는다.</b> "요청 자체가
     * 없었다"와 "요청은 했는데 인정된 하자가 0건"은 저장 형태(finding row 0개)가 똑같아서
     * 구분할 수 없다 — 둘 다 FE에서 캐러셀을 안 그리는 결과는 같으므로 구분 없이
     * {@code NOT_REQUESTED}로 합친다.
     */
    private AiQualityAnalysisResponse buildAiQualityAnalysis(Long productId, List<ProductImageResponse> images) {
        List<ProductQualityFinding> findings =
                productQualityFindingRepository.findAllByProductIdOrderBySortOrderAsc(productId);
        if (findings.isEmpty()) {
            return AiQualityAnalysisResponse.notRequested();
        }

        Map<ProductImageRole, String> imageUrlByRole = images.stream()
                .filter(image -> image.role() == ProductImageRole.FRONT || image.role() == ProductImageRole.BACK)
                .collect(Collectors.toMap(ProductImageResponse::role, ProductImageResponse::url, (a, b) -> a));

        List<AiQualityAnalysisImageResponse> imageResponses = new ArrayList<>();
        for (ProductImageRole role : List.of(ProductImageRole.FRONT, ProductImageRole.BACK)) {
            List<AiQualityFindingResponse> roleFindings = findings.stream()
                    .filter(finding -> finding.getPhotoRole() == role)
                    .map(AiQualityFindingResponse::from)
                    .toList();
            if (roleFindings.isEmpty()) {
                continue;
            }
            String url = imageUrlByRole.get(role);
            imageResponses.add(new AiQualityAnalysisImageResponse(
                    role == ProductImageRole.FRONT ? "앞면" : "뒷면", url, url, null, roleFindings));
        }

        return AiQualityAnalysisResponse.completed(imageResponses);
    }

    /**
     * "동일 상품 시세"(CH001, 047·025 반영) — 같은 {@code matchKey}를 가진 다른 상품들의
     * 호가/완료거래가. {@code matchKey}가 아직 없으면(가격 책정 전 상품) 빈 목록을 준다 —
     * 404가 아니라 "판정 근거 없음"으로 다룬다(AI 쪽 comps 없음과 같은 원칙).
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

    /** ON_SALE(호가)/SOLD(완료거래)가 아니면 아직 시세로 쓸 가격이 없다 — null을 돌려준다. */
    private ProductMarketPriceResponse.Item toMarketPriceItem(
            Product product, Map<Long, CompletedOrderSummary> completedOrderByProductId) {
        if (product.getSaleStatus() == SaleStatus.ON_SALE) {
            return new ProductMarketPriceResponse.Item(
                    product.getId(), product.getTitle(), product.getPrice(), "ASKING");
        }
        if (product.getSaleStatus() == SaleStatus.SOLD) {
            CompletedOrderSummary order = completedOrderByProductId.get(product.getId());
            if (order == null) {
                return null; // 완료거래 근거를 못 찾음 — 시세로 안 쓴다
            }
            String priceKind = order.auctionWin() ? "SOLD_AUCTION" : "SOLD_DIRECT";
            return new ProductMarketPriceResponse.Item(
                    product.getId(), product.getTitle(), order.orderPrice(), priceKind);
        }
        return null;
    }

    @Transactional
    public ProductResponse updateProduct(Long sellerId, Long productId, ProductUpdateRequest request) {
        Product product = getOwnedEditableProduct(sellerId, productId);

        // 등록과 같은 이유로 존재 여부 확인 — product.category_id 에 FK 가 걸려 있어
        // 없는 ID 를 그대로 넣으면 제약 위반이 500 으로 새어 나간다.
        if (request.categoryId() != null && !categoryRepository.existsById(request.categoryId())) {
            throw new CustomException(ErrorCode.CATEGORY_NOT_FOUND);
        }

        product.update(
                request.title(),
                request.description(),
                request.categoryId(),
                request.brand(),
                request.conditionGrade(),
                request.sizeLabel(),
                request.color(),
                request.material(),
                request.measurements(),
                request.matchKey());

        // defects는 null이면 미반영, non-null이면 전체 교체(빈 리스트면 전부 삭제).
        if (request.defects() != null) {
            productDefectRepository.deleteAllByProductId(productId);
            saveDefects(product, request.defects());
        }

        // aiQualityFindings도 같은 규칙 — DRAFT 우선 생성 상품은 확정 시점(PATCH)에만 값이 온다(046).
        if (request.aiQualityFindings() != null) {
            productQualityFindingRepository.deleteAllByProductId(productId);
            saveQualityFindings(product, request.aiQualityFindings());
        }

        // 가격은 상시 판매 상품에만 의미가 있다 — 경매 상품은 price가 항상 null이고
        // 시작가는 AUCT 쪽 Auction 엔티티가 별도로 갖는다.
        if (request.price() != null) {
            if (!product.isDirectSale()) {
                throw new CustomException(ErrorCode.INVALID_PRODUCT_STATE);
            }
            product.updatePrice(request.price());
        }

        return ProductResponse.from(product);
    }

    /**
     * AI 착용컷 생성 상태/결과 조회.
     *
     * <p>백그라운드 스케줄러 없이, 아직 안 끝난 job이면 조회하는 이 시점에 AI를 다시 찔러
     * 최신 상태를 반영하는 "지연 폴링" 방식이다 — 구조가 가장 단순해서 MVP로 채택했다
     * (범위 밖: 캐싱, 스케줄러화).
     */
    @Transactional
    public ProductAiModelCutResponse getAiModelCutStatus(Long productId) {
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new CustomException(ErrorCode.PRODUCT_NOT_FOUND));

        if (product.getAiModelCutStatus() == AiModelCutStatus.PENDING
                || product.getAiModelCutStatus() == AiModelCutStatus.PROCESSING) {
            refreshAiModelCutStatus(product);
        }

        return ProductAiModelCutResponse.from(product);
    }

    private void refreshAiModelCutStatus(Product product) {
        try {
            AiJobResponse job = aiClient.getJob(product.getAiModelCutJobId());
            if (job.isSuccess()) {
                Object imageUrl = job.result() != null ? job.result().get("image_url") : null;
                if (imageUrl != null) {
                    product.completeAiModelCutJob(imageUrl.toString());
                } else {
                    product.failAiModelCutJob();
                }
            } else if (job.isFailed()) {
                product.failAiModelCutJob();
            } else if ("processing".equals(job.status())) {
                product.markAiModelCutProcessing();
            }
            // queued -> PENDING 그대로 둔다.
        } catch (RestClientException e) {
            // 일시적 네트워크 오류일 수 있다 — FAILED로 단정하지 않고 다음 폴링에서 재시도한다.
            log.warn(
                    "AI 착용컷 job 상태 조회 실패(productId={}, jobId={}): {}",
                    product.getId(), product.getAiModelCutJobId(), e.getMessage());
        }
    }

    /**
     * 하자 검수 상태/결과를 조회한다(`docs/requests/BE/041-quality-inspection-integration.md`).
     *
     * <p>FE는 AI 게이트웨이를 직접 폴링하지 않는다 — BE가 이 엔드포인트에서 아직 안 끝난 job이면
     * 조회 시점에 AI를 대신 조회해 최신화한다(모델컷과 같은 지연 폴링 방식).
     */
    @Transactional
    public ProductQualityInspectionResponse getQualityInspectionStatus(Long productId) {
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new CustomException(ErrorCode.PRODUCT_NOT_FOUND));

        if (product.getQualityInspectionStatus() == QualityInspectionStatus.PENDING
                || product.getQualityInspectionStatus() == QualityInspectionStatus.PROCESSING) {
            refreshQualityInspectionStatus(product);
        }

        return ProductQualityInspectionResponse.from(product);
    }

    private void refreshQualityInspectionStatus(Product product) {
        try {
            AiJobResponse job = aiClient.getJob(product.getQualityInspectionJobId());
            if (job.isSuccess()) {
                if (job.result() != null) {
                    product.completeQualityInspectionJob(job.result());
                } else {
                    product.failQualityInspectionJob();
                }
            } else if (job.isFailed()) {
                product.failQualityInspectionJob();
            } else if ("processing".equals(job.status())) {
                product.markQualityInspectionProcessing();
            }
            // queued -> PENDING 그대로 둔다.
        } catch (RestClientException e) {
            // 일시적 네트워크 오류일 수 있다 — FAILED로 단정하지 않고 다음 폴링에서 재시도한다.
            log.warn(
                    "하자 검수 job 상태 조회 실패(productId={}, jobId={}): {}",
                    product.getId(), product.getQualityInspectionJobId(), e.getMessage());
        }
    }

    @Transactional
    public void deleteProduct(Long sellerId, Long productId) {
        Product product = getOwnedEditableProduct(sellerId, productId);

        product.softDelete();
    }

    private Product getOwnedEditableProduct(Long sellerId, Long productId) {
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new CustomException(ErrorCode.PRODUCT_NOT_FOUND));

        if (!product.isOwnedBy(sellerId)) {
            throw new CustomException(ErrorCode.NOT_PRODUCT_OWNER);
        }
        if (!product.isEditable()) {
            throw new CustomException(ErrorCode.INVALID_PRODUCT_STATE);
        }

        return product;
    }
}