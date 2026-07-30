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
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductRepository;
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

    private static final List<SaleStatus> HIDDEN_FROM_LIST = List.of(SaleStatus.DRAFT, SaleStatus.PRIVATE);

    private final ProductRepository productRepository;
    private final MemberRepository memberRepository;
    private final ProductImageService productImageService;
    private final CategoryRepository categoryRepository;

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
                .build();

        return ProductResponse.from(productRepository.save(product));
    }

    @Transactional
    public ProductResponse registerDirectSale(Long sellerId, Long productId, ProductStatusUpdateRequest request) {
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new CustomException(ErrorCode.PRODUCT_NOT_FOUND));

        if (!product.isOwnedBy(sellerId)) {
            throw new CustomException(ErrorCode.NOT_PRODUCT_OWNER);
        }
        if (product.getSaleStatus() != SaleStatus.DRAFT) {
            throw new CustomException(ErrorCode.INVALID_PRODUCT_STATE);
        }

        product.registerDirectSale(request.price());

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
        if (product.isPrivate() && !product.isOwnedBy(viewerId)) {
            throw new CustomException(ErrorCode.PRODUCT_NOT_FOUND);
        }
        return ProductDetailResponse.from(product, productImageService.getImages(productId));
    }

    @Transactional
    public ProductResponse updateProduct(Long sellerId, Long productId, ProductUpdateRequest request) {
        Product product = getOwnedEditableProduct(sellerId, productId);

        product.update(
                request.title(),
                request.description(),
                request.categoryId(),
                request.brandId(),
                request.conditionGrade(),
                request.sizeLabel());

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