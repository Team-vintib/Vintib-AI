package com.ssafy.backend.product.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.dto.request.ProductCreateRequest;
import com.ssafy.backend.product.dto.request.ProductStatusUpdateRequest;
import com.ssafy.backend.product.dto.request.ProductUpdateRequest;
import com.ssafy.backend.product.dto.response.ProductResponse;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** 상품 등록/수정/삭제·판매 채널 전환(CUD). */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ProductCommandService {

    private final ProductRepository productRepository;
    private final MemberRepository memberRepository;
        private final CategoryRepository categoryRepository;

        @Transactional
        public ProductResponse createProduct(Long sellerId, ProductCreateRequest request) {
            Member seller = memberRepository.findById(sellerId)
                    .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

            // 카테고리 필수. 없는 ID 를 그대로 넣으면 FK 위반이 500 으로 새어 나감.
            if (!categoryRepository.existsById(request.categoryId())) {
            throw new CustomException(ErrorCode.CATEGORY_NOT_FOUND);
        }
        // aiModelEnabled=true인데 gender가 없으면 어떤 성별 모델 사진으로 합성할지 정할 수 없음.
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
                .defects(request.defects())
                .aiModelEnabled(request.aiModelEnabled())
                .aiModelGender(request.aiModelEnabled() ? request.aiModelGender() : null)
                .build();

        Product saved = productRepository.save(product);

        return ProductResponse.from(saved);
    }

    // DRAFT/AUCTION_SCHEDULED에서 호출.
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

    // DRAFT/ON_SALE에서 호출.
    // 시작가/증액 단위/경매 시간은 경매 조건 설정에서.
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

    @Transactional
    public ProductResponse updateProduct(Long sellerId, Long productId, ProductUpdateRequest request) {
        Product product = getOwnedEditableProduct(sellerId, productId);

        // 없는 ID 를 그대로 넣으면 FK 위반이 500 으로 새어 나감.
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
                request.defects(),
                request.matchKey(),
                request.excludedQualityFindingKeys(),
                request.priceEstimateSnapshot());

        // 가격은 정찰제만. 경매 상품은 price가 항상 null. 시작가는 AUCT 쪽 Auction 엔티티에.
        if (request.price() != null) {
            if (!product.isDirectSale()) {
                throw new CustomException(ErrorCode.INVALID_PRODUCT_STATE);
            }
            product.updatePrice(request.price());
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