package com.ssafy.backend.product.service;

import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.product.dto.request.ProductImageRegisterRequest;
import com.ssafy.backend.product.dto.request.ProductImageUpdateRequest;
import com.ssafy.backend.product.dto.request.ProductImageUploadUrlRequest;
import com.ssafy.backend.product.dto.response.ProductImageResponse;
import com.ssafy.backend.product.dto.response.ProductImageUploadUrlResponse;
import com.ssafy.backend.product.entity.AiModelCutStatus;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.ProductImage;
import com.ssafy.backend.product.entity.QualityInspectionStatus;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductImageRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestClientException;
import software.amazon.awssdk.services.s3.model.HeadObjectResponse;
import software.amazon.awssdk.services.s3.model.NoSuchKeyException;

@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ProductImageService {

    private static final int MAX_IMAGES_PER_PRODUCT = 10;
    private static final long MAX_IMAGE_SIZE_BYTES = 10L * 1024 * 1024;
    private static final Map<String, String> ALLOWED_CONTENT_TYPE_EXTENSIONS =
            Map.of("image/jpeg", "jpg", "image/png", "png", "image/webp", "webp");

    // 상품 카테고리 -> mask_type 자동 판별은 아직 없다(docs/requests/BE/035-tryon-product-category.md
    // 미해결). 정확도보다 파이프라인이 실제로 도는지가 이번 목적이라 상의 고정으로 간다.
    private static final String DEFAULT_AI_MODEL_CUT_MASK_TYPE = "upper";

    // 카테고리(leaf, Category.nameEn) -> AI SAM3 GarmentCategory(6종, `worker/models/sam3/
    // contracts.py`) 매핑. SAM3는 의류(상/하의·아우터) 전용이라 신발/가방/액세서리/원피스·
    // 점프슈트는 대응값이 없다 — 이 맵에 없으면 하자 검수를 트리거하지 않는다.
    // ⚠️ 라벨링된 기준 없이 잡은 매핑(특히 TSHIRT/SLEEVELESS→TOP_SHIRT, HOODIE/SWEATSHIRT→
    // TOP_KNIT, JACKET/CARDIGAN/HOOD_ZIPUP→OUTER_JACKET, COAT/PADDED_JACKET→OUTER_COAT 경계는
    // 판단 근거가 약하다) — AI/BE가 함께 다시 검토할 대상.
    private static final Map<String, String> GARMENT_CATEGORY_BY_LEAF_NAME = Map.ofEntries(
            Map.entry("TSHIRT", "TOP_SHIRT"),
            Map.entry("SHIRT", "TOP_SHIRT"),
            Map.entry("SLEEVELESS", "TOP_SHIRT"),
            Map.entry("KNIT", "TOP_KNIT"),
            Map.entry("HOODIE", "TOP_KNIT"),
            Map.entry("SWEATSHIRT", "TOP_KNIT"),
            Map.entry("JACKET", "OUTER_JACKET"),
            Map.entry("CARDIGAN", "OUTER_JACKET"),
            Map.entry("HOOD_ZIPUP", "OUTER_JACKET"),
            Map.entry("COAT", "OUTER_COAT"),
            Map.entry("PADDED_JACKET", "OUTER_COAT"),
            Map.entry("DENIM", "BOTTOM_PANTS"),
            Map.entry("SLACKS", "BOTTOM_PANTS"),
            Map.entry("CARGO_PANTS", "BOTTOM_PANTS"),
            Map.entry("SHORT_PANTS", "BOTTOM_PANTS"),
            Map.entry("JOGGER_PANTS", "BOTTOM_PANTS"),
            Map.entry("COTTON_PANTS", "BOTTOM_PANTS"),
            Map.entry("SKIRT", "BOTTOM_SKIRT"));

    private final ProductRepository productRepository;
    private final ProductImageRepository productImageRepository;
    private final CategoryRepository categoryRepository;
    private final S3StorageService s3StorageService;
    private final AwsProperties awsProperties;
    private final AiClient aiClient;

    @Transactional
    public ProductImageUploadUrlResponse createUploadUrl(
            Long sellerId, Long productId, ProductImageUploadUrlRequest request) {
        getOwnedProduct(sellerId, productId);

        String extension = ALLOWED_CONTENT_TYPE_EXTENSIONS.get(request.contentType());
        if (extension == null) {
            throw new CustomException(ErrorCode.INVALID_IMAGE_TYPE);
        }

        String key = "product-images/%d/%s.%s".formatted(productId, UUID.randomUUID(), extension);
        S3StorageService.PresignedUpload upload =
                s3StorageService.createUploadUrl(awsProperties.s3().publicBucket(), key, request.contentType());

        return new ProductImageUploadUrlResponse(key, upload.uploadUrl(), upload.expiresInSeconds());
    }

    @Transactional
    public ProductImageResponse registerImage(Long sellerId, Long productId, ProductImageRegisterRequest request) {
        Product product = getOwnedProduct(sellerId, productId);

        if (productImageRepository.countByProductId(productId) >= MAX_IMAGES_PER_PRODUCT) {
            throw new CustomException(ErrorCode.PRODUCT_IMAGE_LIMIT_EXCEEDED);
        }
        if (!request.key().startsWith("product-images/%d/".formatted(productId))) {
            throw new CustomException(ErrorCode.PRODUCT_IMAGE_UPLOAD_NOT_CONFIRMED);
        }

        String bucket = awsProperties.s3().publicBucket();
        verifyUploaded(bucket, request.key());

        // 대표 이미지는 상품당 1장만 유지 — 새 이미지를 대표로 등록하기 전에 기존 대표를 먼저 내린다.
        if (request.isPrimary()) {
            productImageRepository.clearPrimary(productId);
        }

        ProductImage image = ProductImage.builder()
                .product(product)
                .imageKey(request.key())
                .sortOrder(request.sortOrder())
                .primary(request.isPrimary())
                .build();
        productImageRepository.save(image);

        String imageUrl = s3StorageService.publicUrl(bucket, image.getImageKey());
        if (request.isPrimary()) {
            triggerAiModelCutJob(product, imageUrl);
        }
        triggerQualityInspectionJob(product);

        return ProductImageResponse.of(image, imageUrl);
    }

    /**
     * 대표 이미지가 등록되면 AI 착용컷 job을 접수한다(`docs/requests/BE/
     * 039-registration-ai-model-tryon.md`). 보조 기능이라 실패해도 이미지 등록 자체는
     * 그대로 성공시킨다 — 로그만 남기고 상태는 NONE으로 둔다(재시도는 이번 범위 밖).
     */
    private void triggerAiModelCutJob(Product product, String productImageUrl) {
        if (!product.isAiModelEnabled() || product.getAiModelCutStatus() != AiModelCutStatus.NONE) {
            return;
        }
        try {
            String jobId = aiClient.createRegistrationModelCutJob(
                    productImageUrl, product.getAiModelGender().name(), DEFAULT_AI_MODEL_CUT_MASK_TYPE);
            product.startAiModelCutJob(jobId);
        } catch (RestClientException e) {
            log.warn("AI 착용컷 job 접수 실패(productId={}): {}", product.getId(), e.getMessage());
        }
    }

    /**
     * 앞/뒤 사진(sortOrder 0/1)이 둘 다 등록된 시점에 하자 검수 job을 접수한다
     * (`docs/requests/BE/041-quality-inspection-integration.md`). 모델컷과 같은 이유로
     * 실패해도 이미지 등록 자체는 그대로 성공시킨다 — 로그만 남기고 상태는 NONE으로 둔다.
     *
     * <p>카테고리가 SAM3 GarmentCategory(6종)에 대응되지 않으면(신발/가방/액세서리/원피스 등)
     * 조용히 건너뛴다 — 검수 자체를 지원하지 않는 카테고리다.
     */
    private void triggerQualityInspectionJob(Product product) {
        if (product.getQualityInspectionStatus() != QualityInspectionStatus.NONE) {
            return;
        }

        List<ProductImage> images =
                productImageRepository.findAllByProductIdOrderBySortOrderAsc(product.getId());
        String frontKey = findImageKeyBySortOrder(images, 0);
        String backKey = findImageKeyBySortOrder(images, 1);
        if (frontKey == null || backKey == null) {
            return;
        }

        Optional<String> category = resolveGarmentCategory(product.getCategoryId());
        if (category.isEmpty()) {
            return;
        }

        String bucket = awsProperties.s3().publicBucket();
        List<String> imageUrls = List.of(
                s3StorageService.publicUrl(bucket, frontKey), s3StorageService.publicUrl(bucket, backKey));
        try {
            String jobId = aiClient.createQualityInspectionJob(product.getId(), imageUrls, category.get());
            product.startQualityInspectionJob(jobId);
        } catch (RestClientException e) {
            log.warn("하자 검수 job 접수 실패(productId={}): {}", product.getId(), e.getMessage());
        }
    }

    private String findImageKeyBySortOrder(List<ProductImage> images, int sortOrder) {
        return images.stream()
                .filter(image -> image.getSortOrder().intValue() == sortOrder)
                .findFirst()
                .map(ProductImage::getImageKey)
                .orElse(null);
    }

    private Optional<String> resolveGarmentCategory(Long categoryId) {
        return categoryRepository.findById(categoryId)
                .map(Category::getNameEn)
                .map(GARMENT_CATEGORY_BY_LEAF_NAME::get);
    }

    @Transactional
    public ProductImageResponse updateImage(
            Long sellerId, Long productId, Long imageId, ProductImageUpdateRequest request) {
        getOwnedProduct(sellerId, productId);
        ProductImage image = getOwnedImage(productId, imageId);

        if (request.sortOrder() != null) {
            image.changeSortOrder(request.sortOrder());
        }
        if (request.isPrimary() != null) {
            if (request.isPrimary()) {
                productImageRepository.clearPrimaryExcept(productId, imageId);
                image.markAsPrimary();
            } else {
                image.unmarkAsPrimary();
            }
        }

        String bucket = awsProperties.s3().publicBucket();
        return ProductImageResponse.of(image, s3StorageService.publicUrl(bucket, image.getImageKey()));
    }

    @Transactional
    public void deleteImage(Long sellerId, Long productId, Long imageId) {
        getOwnedProduct(sellerId, productId);
        ProductImage image = getOwnedImage(productId, imageId);

        s3StorageService.delete(awsProperties.s3().publicBucket(), image.getImageKey());
        productImageRepository.delete(image);
    }

    /**
     * 여러 상품의 대표 이미지 URL을 한 번에 가져온다(목록 응답용, N+1 방지).
     *
     * <p>대표 이미지가 없는 상품은 반환되는 Map에 키 자체가 없다 — 호출부에서 {@code get()}이
     * {@code null}이면 대표 이미지 없음으로 처리한다.
     */
    public Map<Long, String> getPrimaryImageUrls(Collection<Long> productIds) {
        if (productIds.isEmpty()) {
            return Map.of();
        }
        String bucket = awsProperties.s3().publicBucket();
        return productImageRepository.findByProduct_IdInAndPrimaryTrue(productIds).stream()
                .collect(Collectors.toMap(
                        image -> image.getProduct().getId(),
                        image -> s3StorageService.publicUrl(bucket, image.getImageKey())));
    }

    public List<ProductImageResponse> getImages(Long productId) {
        String bucket = awsProperties.s3().publicBucket();
        return productImageRepository.findAllByProductIdOrderBySortOrderAsc(productId).stream()
                .map(image -> ProductImageResponse.of(image, s3StorageService.publicUrl(bucket, image.getImageKey())))
                .toList();
    }

    private Product getOwnedProduct(Long sellerId, Long productId) {
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new CustomException(ErrorCode.PRODUCT_NOT_FOUND));
        if (!product.isOwnedBy(sellerId)) {
            throw new CustomException(ErrorCode.NOT_PRODUCT_OWNER);
        }
        return product;
    }

    private ProductImage getOwnedImage(Long productId, Long imageId) {
        ProductImage image = productImageRepository.findById(imageId)
                .orElseThrow(() -> new CustomException(ErrorCode.PRODUCT_IMAGE_NOT_FOUND));
        if (!image.belongsTo(productId)) {
            throw new CustomException(ErrorCode.PRODUCT_IMAGE_NOT_FOUND);
        }
        return image;
    }

    // presigned PUT 자체는 최대 용량을 강제하지 못하므로, 등록 확인 시점에 실제 업로드된
    // 객체를 HeadObject 로 검증한다. 기준 초과 시 객체를 지우고 에러로 되돌린다.
    private void verifyUploaded(String bucket, String key) {
        HeadObjectResponse head;
        try {
            head = s3StorageService.headObject(bucket, key);
        } catch (NoSuchKeyException e) {
            throw new CustomException(ErrorCode.PRODUCT_IMAGE_UPLOAD_NOT_CONFIRMED);
        }
        if (head.contentLength() != null && head.contentLength() > MAX_IMAGE_SIZE_BYTES) {
            s3StorageService.delete(bucket, key);
            throw new CustomException(ErrorCode.PRODUCT_IMAGE_UPLOAD_NOT_CONFIRMED);
        }
    }
}