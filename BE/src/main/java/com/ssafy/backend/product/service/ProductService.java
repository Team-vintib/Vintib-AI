package com.ssafy.backend.product.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.dto.request.ProductCreateRequest;
import com.ssafy.backend.product.dto.request.ProductStatusUpdateRequest;
import com.ssafy.backend.product.dto.request.ProductUpdateRequest;
import com.ssafy.backend.product.dto.response.ProductDetailResponse;
import com.ssafy.backend.product.dto.response.ProductResponse;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.ProductDefect;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductDefectRepository;
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

    private static final List<SaleStatus> HIDDEN_FROM_LIST = List.of(SaleStatus.DRAFT);

    private final ProductRepository productRepository;
    private final MemberRepository memberRepository;
    private final ProductImageService productImageService;
    private final CategoryRepository categoryRepository;
    private final ProductDefectRepository productDefectRepository;

    @Transactional
    public ProductResponse createProduct(Long sellerId, ProductCreateRequest request) {
        Member seller = memberRepository.findById(sellerId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

        // 카테고리는 필수이며 실제로 존재해야 한다. DTO의 @NotNull 은 "값이 있는지"만 보므로
        // 없는 ID 를 그대로 넣으면 FK 위반이 500 으로 새어 나간다.
        if (!categoryRepository.existsById(request.categoryId())) {
            throw new CustomException(ErrorCode.CATEGORY_NOT_FOUND);
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

    public PageResponse<ProductResponse> getProductList(Pageable pageable) {
        // 정렬은 최신순 고정(PROD-008 범위 밖) — 클라이언트가 Pageable에 다른 sort를 실어 보내도 무시하고 createdAt DESC로 강제한다.
        Pageable sortedByLatest = PageRequest.of(
                pageable.getPageNumber(), pageable.getPageSize(), Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<Product> products = productRepository.findBySaleStatusNotIn(HIDDEN_FROM_LIST, sortedByLatest);
        return PageResponse.from(products.map(ProductResponse::from));
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
        return ProductDetailResponse.from(product, productImageService.getImages(productId), defects);
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