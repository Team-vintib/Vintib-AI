package com.ssafy.backend.product.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.dto.request.ProductCreateRequest;
import com.ssafy.backend.product.dto.request.ProductListFilterParams;
import com.ssafy.backend.product.dto.request.ProductSortType;
import com.ssafy.backend.product.dto.request.ProductStatusUpdateRequest;
import com.ssafy.backend.product.dto.request.ProductUpdateRequest;
import com.ssafy.backend.product.dto.response.ProductDetailResponse;
import com.ssafy.backend.product.dto.response.ProductResponse;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.product.dto.response.LinkedLiveSummaryResponse;
import com.ssafy.backend.product.entity.Brand;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.ProductDefect;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.repository.BrandRepository;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductDefectRepository;
import com.ssafy.backend.product.port.LiveQueryPort;
import com.ssafy.backend.product.port.SocialQueryPort;
import com.ssafy.backend.product.repository.ProductRepository;
import java.util.ArrayList;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ProductService {


    private final ProductRepository productRepository;
    private final MemberRepository memberRepository;
    private final ProductImageService productImageService;
    private final CategoryRepository categoryRepository;
    private final BrandRepository brandRepository;
    private final ProductDefectRepository productDefectRepository;
    private final SocialQueryPort socialQueryPort;
    private final LiveQueryPort liveQueryPort;

    @Transactional
    public ProductResponse createProduct(Long sellerId, ProductCreateRequest request) {
        Member seller = memberRepository.findById(sellerId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

        // 카테고리는 필수이며 실제로 존재해야 한다. DTO의 @NotNull 은 "값이 있는지"만 보므로
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
                .brandId(request.brandId())
                .title(request.title())
                .description(request.description())
                .conditionGrade(request.conditionGrade())
                .sizeLabel(request.sizeLabel())
                .color(request.color())
                .material(request.material())
                .measurements(request.measurements())
                .aiModelEnabled(request.aiModelEnabled())
                .aiModelGender(request.aiModelEnabled() ? request.aiModelGender() : null)
                .build();

        Product saved = productRepository.save(product);
        saveDefects(saved, request.defects());

        return ProductResponse.from(saved);
    }

    // 등록 시점에 판매자가 입력한 하자 목록을 순서대로 저장한다.
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

    // DRAFT(최초 등록) 또는 AUCTION_SCHEDULED(경매 예정 상품의 상시 판매 전환, PROD-004/PROD-005/AUCT-014)에서 호출된다.
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

    // DRAFT(최초 등록, PROD-003) 또는 ON_SALE(상시 판매 상품의 경매 전환, PROD-004)에서 호출된다.
    // 시작가/증액 단위/경매 시간은 여기서 다루지 않는다 — "경매 시작 전에 설정한다"고 명시돼 있고,
    // 그건 AUCT-001(경매 조건 설정) 영역이다.
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

    /** 마이페이지 판매 상품 관리(MY-002) — 본인 소유 상품을 등록일 최신순으로 전부 반환한다(DRAFT 등 비공개 상태 포함). */
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
        String brandName = product.getBrandId() == null ? null : brandRepository.findById(product.getBrandId())
                .map(Brand::getName)
                .orElse(null);

        Long sellerId = product.getSeller().getId();
        long sellerProductCount = productRepository.countBySeller_IdAndSaleStatusNot(sellerId, SaleStatus.DRAFT);
        long sellerFollowerCount = socialQueryPort.countFollowers(sellerId);
        boolean isWished = socialQueryPort.isWishedBy(productId, viewerId);

        LinkedLiveSummaryResponse linkedLive = liveQueryPort.findLinkedLive(productId)
                .map(LinkedLiveSummaryResponse::from)
                .orElse(null);

        return ProductDetailResponse.from(
                product,
                categoryName,
                brandName,
                productImageService.getImages(productId),
                defects,
                isWished,
                sellerFollowerCount,
                sellerProductCount,
                linkedLive);
    }

    @Transactional
    public ProductResponse updateProduct(Long sellerId, Long productId, ProductUpdateRequest request) {
        Product product = getOwnedEditableProduct(sellerId, productId);

        // 등록과 같은 이유로 존재 여부를 본다 — product.category_id 에 FK 가 걸려 있어
        // 없는 ID 를 그대로 넣으면 제약 위반이 500 으로 새어 나간다.
        if (request.categoryId() != null && !categoryRepository.existsById(request.categoryId())) {
            throw new CustomException(ErrorCode.CATEGORY_NOT_FOUND);
        }

        product.update(
                request.title(),
                request.description(),
                request.categoryId(),
                request.brandId(),
                request.conditionGrade(),
                request.sizeLabel(),
                request.color(),
                request.material(),
                request.measurements());

        // defects는 null이면 미반영, non-null이면 전체 교체(빈 리스트면 전부 삭제).
        if (request.defects() != null) {
            productDefectRepository.deleteAllByProductId(productId);
            saveDefects(product, request.defects());
        }

        return ProductResponse.from(product);
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