package com.ssafy.backend.product.service;

import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.client.dto.AiJobResponse;
import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.product.dto.request.ProductClassifyTriggerRequest;
import com.ssafy.backend.product.dto.request.ProductPreUploadUrlRequest;
import com.ssafy.backend.product.dto.response.ProductClassifyJobResponse;
import com.ssafy.backend.product.dto.response.ProductClassifyResultResponse;
import com.ssafy.backend.product.dto.response.ProductClassifyResultResponse.CategorySuggestion;
import com.ssafy.backend.product.dto.response.ProductClassifyResultResponse.ColorSuggestion;
import com.ssafy.backend.product.dto.response.ProductClassifyStatus;
import com.ssafy.backend.product.dto.response.ProductClassifyStatusResponse;
import com.ssafy.backend.product.dto.response.ProductPreUploadUrlResponse;
import com.ssafy.backend.product.support.CategoryIdResolver;
import com.ssafy.backend.product.support.CategoryIdResolver.CategoryIds;
import java.util.Map;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import software.amazon.awssdk.services.s3.model.HeadObjectResponse;
import software.amazon.awssdk.services.s3.model.NoSuchKeyException;

/**
 * 상품 생성 전(사전업로드) 사진으로 AI 카테고리·색상 분류를 트리거·조회한다(방향 B,
 * `docs/requests/BE/045-classify-pre-upload-integration.md`).
 *
 * <p><b>완전 무상태 프록시다 — DB에 아무 것도 쓰지 않는다.</b> 아직 상품이 없어 결과를 매달
 * 엔티티가 없다 — jobId는 FE가 직접 들고 있다가 상태 조회에 쓴다(사용자 확정). 하자검수
 * (`ProductImageService.triggerQualityInspectionJob`)와 트리거 시점이 반대인 이유도 여기
 * 있다 — 분류는 사용자가 카테고리를 고르기 *전에* 폼을 프리필해야 의미가 있어서, 상품
 * 생성 후로 미룰 수 없다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ProductPreUploadService {

    private static final Map<String, String> ALLOWED_CONTENT_TYPE_EXTENSIONS =
            Map.of("image/jpeg", "jpg", "image/png", "png", "image/webp", "webp");
    private static final long MAX_IMAGE_SIZE_BYTES = 10L * 1024 * 1024;
    private static final String PRE_UPLOAD_PREFIX = "pre-upload/";

    private final S3StorageService s3StorageService;
    private final AwsProperties awsProperties;
    private final AiClient aiClient;

    public ProductPreUploadUrlResponse createUploadUrl(Long sellerId, ProductPreUploadUrlRequest request) {
        String extension = ALLOWED_CONTENT_TYPE_EXTENSIONS.get(request.contentType());
        if (extension == null) {
            throw new CustomException(ErrorCode.INVALID_IMAGE_TYPE);
        }

        String key = "%s%d/%s.%s".formatted(PRE_UPLOAD_PREFIX, sellerId, UUID.randomUUID(), extension);
        S3StorageService.PresignedUpload upload =
                s3StorageService.createUploadUrl(awsProperties.s3().publicBucket(), key, request.contentType());

        return new ProductPreUploadUrlResponse(key, upload.uploadUrl(), upload.expiresInSeconds());
    }

    public ProductClassifyJobResponse triggerClassify(Long sellerId, ProductClassifyTriggerRequest request) {
        if (!request.key().startsWith(PRE_UPLOAD_PREFIX + sellerId + "/")) {
            throw new CustomException(ErrorCode.PRODUCT_IMAGE_UPLOAD_NOT_CONFIRMED);
        }

        String bucket = awsProperties.s3().publicBucket();
        verifyUploaded(bucket, request.key());
        String imageUrl = s3StorageService.publicUrl(bucket, request.key());

        try {
            String jobId = aiClient.createClassifyJob(imageUrl);
            return new ProductClassifyJobResponse(jobId);
        } catch (RestClientException e) {
            log.warn("분류 job 접수 실패(sellerId={}, key={}): {}", sellerId, request.key(), e.getMessage());
            throw new CustomException(ErrorCode.PRODUCT_CLASSIFY_JOB_FAILED);
        }
    }

    public ProductClassifyStatusResponse getClassifyStatus(String jobId) {
        AiJobResponse job;
        try {
            job = aiClient.getJob(jobId);
        } catch (RestClientException e) {
            log.warn("분류 job 상태 조회 실패(jobId={}): {}", jobId, e.getMessage());
            throw new CustomException(ErrorCode.PRODUCT_CLASSIFY_JOB_FAILED);
        }

        if (job.isFailed()) {
            return ProductClassifyStatusResponse.failed(job.error());
        }
        if (!job.isSuccess()) {
            return ProductClassifyStatusResponse.pending(ProductClassifyStatus.fromAiStatus(job.status()));
        }
        return ProductClassifyStatusResponse.completed(parseResult(job.result()));
    }

    @SuppressWarnings("unchecked")
    private ProductClassifyResultResponse parseResult(Map<String, Object> result) {
        Map<String, Object> fields = (Map<String, Object>) result.get("fields");
        CategorySuggestion category = parseCategory((Map<String, Object>) fields.get("category"));
        ColorSuggestion colorPrimary = parseColor((Map<String, Object>) fields.get("color_primary"));
        String taxonomyVersion = (String) result.get("taxonomy_version");
        return new ProductClassifyResultResponse(category, colorPrimary, taxonomyVersion);
    }

    private CategorySuggestion parseCategory(Map<String, Object> category) {
        if (category == null || category.get("value") == null) {
            return null;
        }
        String subcategoryCode = (String) category.get("value");
        CategoryIds ids = CategoryIdResolver.resolve(subcategoryCode);
        if (ids == null) {
            log.warn("categoryId 조회표에 없는 소분류 코드입니다: {}", subcategoryCode);
            return null;
        }
        return new CategorySuggestion(
                ids.majorCategoryId(),
                ids.categoryId(),
                (String) category.get("action"),
                toDouble(category.get("score")));
    }

    private ColorSuggestion parseColor(Map<String, Object> colorPrimary) {
        if (colorPrimary == null || colorPrimary.get("value") == null) {
            return null;
        }
        return new ColorSuggestion(
                (String) colorPrimary.get("value"),
                (String) colorPrimary.get("action"),
                toDouble(colorPrimary.get("score")));
    }

    private double toDouble(Object value) {
        return value instanceof Number number ? number.doubleValue() : 0.0;
    }

    // presigned PUT 자체는 최대 용량을 강제하지 못하므로, 등록 확인 시점에 실제 업로드된
    // 객체를 HeadObject로 검증한다(ProductImageService.verifyUploaded와 동일 로직).
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
