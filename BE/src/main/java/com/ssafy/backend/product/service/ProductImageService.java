package com.ssafy.backend.product.service;

import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.product.dto.request.ProductImageRegisterRequest;
import com.ssafy.backend.product.dto.request.ProductImageUpdateRequest;
import com.ssafy.backend.product.dto.request.ProductImageUploadUrlRequest;
import com.ssafy.backend.product.dto.response.ProductImageResponse;
import com.ssafy.backend.product.dto.response.ProductImageUploadUrlResponse;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.ProductImage;
import com.ssafy.backend.product.repository.ProductImageRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import software.amazon.awssdk.services.s3.model.HeadObjectResponse;
import software.amazon.awssdk.services.s3.model.NoSuchKeyException;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ProductImageService {

    private static final int MAX_IMAGES_PER_PRODUCT = 10;
    private static final long MAX_IMAGE_SIZE_BYTES = 10L * 1024 * 1024;
    private static final Map<String, String> ALLOWED_CONTENT_TYPE_EXTENSIONS =
            Map.of("image/jpeg", "jpg", "image/png", "png", "image/webp", "webp");

    private final ProductRepository productRepository;
    private final ProductImageRepository productImageRepository;
    private final S3StorageService s3StorageService;
    private final AwsProperties awsProperties;

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

        return ProductImageResponse.of(image, s3StorageService.publicUrl(bucket, image.getImageKey()));
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