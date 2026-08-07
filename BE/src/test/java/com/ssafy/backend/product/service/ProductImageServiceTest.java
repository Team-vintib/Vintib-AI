package com.ssafy.backend.product.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.product.dto.request.ProductImageRegisterRequest;
import com.ssafy.backend.product.dto.request.ProductImageUpdateRequest;
import com.ssafy.backend.product.dto.request.ProductImageUploadUrlRequest;
import com.ssafy.backend.product.dto.response.ProductImageResponse;
import com.ssafy.backend.product.dto.response.ProductImageUploadUrlResponse;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.ProductImage;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductImageRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import software.amazon.awssdk.services.s3.model.HeadObjectResponse;
import software.amazon.awssdk.services.s3.model.NoSuchKeyException;

@ExtendWith(MockitoExtension.class)
class ProductImageServiceTest {

    private static final Long SELLER_ID = 1L;
    private static final Long PRODUCT_ID = 1L;
    private static final String PUBLIC_BUCKET = "public-bucket";

    @Mock
    private ProductRepository productRepository;

    @Mock
    private ProductImageRepository productImageRepository;

    @Mock
    private CategoryRepository categoryRepository;

    @Mock
    private S3StorageService s3StorageService;

    @Mock
    private Member seller;

    @Mock
    private Product imageProduct;

    @Mock
    private AiClient aiClient;

    private AwsProperties awsProperties;
    private ProductImageService productImageService;
    private Product product;

    @BeforeEach
    void setUp() {
        awsProperties = new AwsProperties(
                "us-east-1",
                "test-key",
                "test-secret",
                new AwsProperties.S3("", "", PUBLIC_BUCKET, "private-bucket"));
        productImageService = new ProductImageService(
                productRepository, productImageRepository, categoryRepository, s3StorageService, awsProperties,
                aiClient);
        product = Product.builder().seller(seller).title("빈티지 자켓").build();
    }

    @Test
    void 업로드_URL을_발급하면_상품_ID가_key에_포함된다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(product));
        when(s3StorageService.createUploadUrl(eq(PUBLIC_BUCKET), anyString(), eq("image/jpeg")))
                .thenReturn(new S3StorageService.PresignedUpload("https://s3.example/upload", 300));

        ProductImageUploadUrlResponse response = productImageService.createUploadUrl(
                SELLER_ID, PRODUCT_ID, new ProductImageUploadUrlRequest("photo.jpg", "image/jpeg"));

        assertThat(response.key()).startsWith("product-images/" + PRODUCT_ID + "/");
        assertThat(response.uploadUrl()).isEqualTo("https://s3.example/upload");
    }

    @Test
    void 지원하지_않는_이미지_타입이면_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(product));

        assertThatThrownBy(() -> productImageService.createUploadUrl(
                SELLER_ID, PRODUCT_ID, new ProductImageUploadUrlRequest("photo.gif", "image/gif")))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 본인이_등록한_상품이_아니면_업로드_URL_발급을_거부한다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(product));

        assertThatThrownBy(() -> productImageService.createUploadUrl(
                2L, PRODUCT_ID, new ProductImageUploadUrlRequest("photo.jpg", "image/jpeg")))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 업로드가_확인되면_이미지를_등록한다() {
        String key = "product-images/%d/abc.jpg".formatted(PRODUCT_ID);
        when(seller.getId()).thenReturn(SELLER_ID);
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(product));
        when(productImageRepository.countByProductId(PRODUCT_ID)).thenReturn(0);
        when(s3StorageService.headObject(PUBLIC_BUCKET, key))
                .thenReturn(HeadObjectResponse.builder().contentLength(1024L).build());
        when(s3StorageService.publicUrl(PUBLIC_BUCKET, key)).thenReturn("https://s3.example/" + key);

        ProductImageResponse response = productImageService.registerImage(
                SELLER_ID, PRODUCT_ID, new ProductImageRegisterRequest(key, (short) 0, true));

        assertThat(response.url()).isEqualTo("https://s3.example/" + key);
        assertThat(response.isPrimary()).isTrue();
        verify(aiClient, org.mockito.Mockito.never()).createRegistrationModelCutJob(anyString(), anyString(), anyString());
    }

    @Test
    void AI_착용컷이_켜진_상품에_대표_이미지를_등록하면_job을_접수한다() {
        String key = "product-images/%d/abc.jpg".formatted(PRODUCT_ID);
        com.ssafy.backend.product.entity.Product aiProduct = com.ssafy.backend.product.entity.Product.builder()
                .seller(seller)
                .title("빈티지 자켓")
                .aiModelEnabled(true)
                .aiModelGender(com.ssafy.backend.product.entity.AiModelGender.MALE)
                .build();
        when(seller.getId()).thenReturn(SELLER_ID);
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(aiProduct));
        when(productImageRepository.countByProductId(PRODUCT_ID)).thenReturn(0);
        when(s3StorageService.headObject(PUBLIC_BUCKET, key))
                .thenReturn(HeadObjectResponse.builder().contentLength(1024L).build());
        when(s3StorageService.publicUrl(PUBLIC_BUCKET, key)).thenReturn("https://s3.example/" + key);
        when(aiClient.createRegistrationModelCutJob("https://s3.example/" + key, "MALE", "upper"))
                .thenReturn("job-456");

        productImageService.registerImage(SELLER_ID, PRODUCT_ID, new ProductImageRegisterRequest(key, (short) 0, true));

        assertThat(aiProduct.getAiModelCutStatus())
                .isEqualTo(com.ssafy.backend.product.entity.AiModelCutStatus.PENDING);
        assertThat(aiProduct.getAiModelCutJobId()).isEqualTo("job-456");
    }

    @Test
    void AI_착용컷_job_접수가_실패해도_이미지_등록은_성공한다() {
        String key = "product-images/%d/abc.jpg".formatted(PRODUCT_ID);
        com.ssafy.backend.product.entity.Product aiProduct = com.ssafy.backend.product.entity.Product.builder()
                .seller(seller)
                .title("빈티지 자켓")
                .aiModelEnabled(true)
                .aiModelGender(com.ssafy.backend.product.entity.AiModelGender.FEMALE)
                .build();
        when(seller.getId()).thenReturn(SELLER_ID);
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(aiProduct));
        when(productImageRepository.countByProductId(PRODUCT_ID)).thenReturn(0);
        when(s3StorageService.headObject(PUBLIC_BUCKET, key))
                .thenReturn(HeadObjectResponse.builder().contentLength(1024L).build());
        when(s3StorageService.publicUrl(PUBLIC_BUCKET, key)).thenReturn("https://s3.example/" + key);
        when(aiClient.createRegistrationModelCutJob(anyString(), anyString(), anyString()))
                .thenThrow(new org.springframework.web.client.RestClientException("connection refused"));

        ProductImageResponse response = productImageService.registerImage(
                SELLER_ID, PRODUCT_ID, new ProductImageRegisterRequest(key, (short) 0, true));

        assertThat(response.url()).isEqualTo("https://s3.example/" + key);
        assertThat(aiProduct.getAiModelCutStatus())
                .isEqualTo(com.ssafy.backend.product.entity.AiModelCutStatus.NONE);
    }

    @Test
    void 앞뒤_사진이_모두_등록되면_하자_검수_job을_접수한다() {
        String backKey = "product-images/%d/back.jpg".formatted(PRODUCT_ID);
        String frontKey = "product-images/%d/front.jpg".formatted(PRODUCT_ID);
        Long categoryId = 31L;
        com.ssafy.backend.product.entity.Product qualityProduct =
                com.ssafy.backend.product.entity.Product.builder()
                        .seller(seller)
                        .categoryId(categoryId)
                        .title("빈티지 니트")
                        .build();
        com.ssafy.backend.product.entity.Category knitCategory =
                org.mockito.Mockito.mock(com.ssafy.backend.product.entity.Category.class);
        when(knitCategory.getNameEn()).thenReturn("KNIT");

        when(seller.getId()).thenReturn(SELLER_ID);
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(qualityProduct));
        when(productImageRepository.countByProductId(PRODUCT_ID)).thenReturn(1);
        when(s3StorageService.headObject(PUBLIC_BUCKET, backKey))
                .thenReturn(HeadObjectResponse.builder().contentLength(1024L).build());
        when(s3StorageService.publicUrl(PUBLIC_BUCKET, backKey)).thenReturn("https://s3.example/" + backKey);
        when(s3StorageService.publicUrl(PUBLIC_BUCKET, frontKey)).thenReturn("https://s3.example/" + frontKey);
        when(productImageRepository.findAllByProductIdOrderBySortOrderAsc(any())).thenReturn(java.util.List.of(
                ProductImage.builder().imageKey(frontKey).sortOrder((short) 0).primary(true).build(),
                ProductImage.builder().imageKey(backKey).sortOrder((short) 1).primary(false).build()));
        when(categoryRepository.findById(categoryId)).thenReturn(Optional.of(knitCategory));
        // qualityProduct는 실제로 저장된 적 없는 순수 builder 인스턴스라 getId()는 null이다
        // (production에서는 productRepository.findById로 가져온 실제 엔티티라 ID가 있다).
        when(aiClient.createQualityInspectionJob(
                org.mockito.ArgumentMatchers.isNull(),
                eq(java.util.List.of("https://s3.example/" + frontKey, "https://s3.example/" + backKey)),
                eq("TOP_KNIT")))
                .thenReturn("job-quality-1");

        productImageService.registerImage(
                SELLER_ID, PRODUCT_ID, new ProductImageRegisterRequest(backKey, (short) 1, false));

        assertThat(qualityProduct.getQualityInspectionStatus())
                .isEqualTo(com.ssafy.backend.product.entity.QualityInspectionStatus.PENDING);
        assertThat(qualityProduct.getQualityInspectionJobId()).isEqualTo("job-quality-1");
    }

    @Test
    void 대응되는_GarmentCategory가_없으면_하자_검수를_건너뛴다() {
        String backKey = "product-images/%d/back.jpg".formatted(PRODUCT_ID);
        String frontKey = "product-images/%d/front.jpg".formatted(PRODUCT_ID);
        Long categoryId = 999L;
        com.ssafy.backend.product.entity.Product shoeProduct =
                com.ssafy.backend.product.entity.Product.builder()
                        .seller(seller)
                        .categoryId(categoryId)
                        .title("운동화")
                        .build();
        com.ssafy.backend.product.entity.Category sneakersCategory =
                org.mockito.Mockito.mock(com.ssafy.backend.product.entity.Category.class);
        when(sneakersCategory.getNameEn()).thenReturn("SNEAKERS");

        when(seller.getId()).thenReturn(SELLER_ID);
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(shoeProduct));
        when(productImageRepository.countByProductId(PRODUCT_ID)).thenReturn(1);
        when(s3StorageService.headObject(PUBLIC_BUCKET, backKey))
                .thenReturn(HeadObjectResponse.builder().contentLength(1024L).build());
        when(s3StorageService.publicUrl(PUBLIC_BUCKET, backKey)).thenReturn("https://s3.example/" + backKey);
        when(productImageRepository.findAllByProductIdOrderBySortOrderAsc(any())).thenReturn(java.util.List.of(
                ProductImage.builder().imageKey(frontKey).sortOrder((short) 0).primary(true).build(),
                ProductImage.builder().imageKey(backKey).sortOrder((short) 1).primary(false).build()));
        when(categoryRepository.findById(categoryId)).thenReturn(Optional.of(sneakersCategory));

        productImageService.registerImage(
                SELLER_ID, PRODUCT_ID, new ProductImageRegisterRequest(backKey, (short) 1, false));

        assertThat(shoeProduct.getQualityInspectionStatus())
                .isEqualTo(com.ssafy.backend.product.entity.QualityInspectionStatus.NONE);
        verify(aiClient, org.mockito.Mockito.never())
                .createQualityInspectionJob(any(), any(), anyString());
    }

    @Test
    void 업로드되지_않은_key로_등록하면_예외를_던진다() {
        String key = "product-images/%d/missing.jpg".formatted(PRODUCT_ID);
        when(seller.getId()).thenReturn(SELLER_ID);
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(product));
        when(productImageRepository.countByProductId(PRODUCT_ID)).thenReturn(0);
        when(s3StorageService.headObject(PUBLIC_BUCKET, key))
                .thenThrow(NoSuchKeyException.builder().message("no such key").build());

        assertThatThrownBy(() -> productImageService.registerImage(
                SELLER_ID, PRODUCT_ID, new ProductImageRegisterRequest(key, (short) 0, false)))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 이미지가_10장이면_추가_등록을_거부한다() {
        String key = "product-images/%d/eleventh.jpg".formatted(PRODUCT_ID);
        when(seller.getId()).thenReturn(SELLER_ID);
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(product));
        when(productImageRepository.countByProductId(PRODUCT_ID)).thenReturn(10);

        assertThatThrownBy(() -> productImageService.registerImage(
                SELLER_ID, PRODUCT_ID, new ProductImageRegisterRequest(key, (short) 10, false)))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 이미지_삭제시_존재하지_않으면_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(product));
        when(productImageRepository.findById(any())).thenReturn(Optional.empty());

        assertThatThrownBy(() -> productImageService.deleteImage(SELLER_ID, PRODUCT_ID, 99L))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 이미지_수정시_정렬순서만_바꾼다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(imageProduct.getId()).thenReturn(PRODUCT_ID);
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(product));
        ProductImage image = ProductImage.builder()
                .product(imageProduct)
                .imageKey("product-images/1/a.jpg")
                .sortOrder((short) 0)
                .primary(false)
                .build();
        when(productImageRepository.findById(5L)).thenReturn(Optional.of(image));
        when(s3StorageService.publicUrl(eq(PUBLIC_BUCKET), anyString())).thenReturn("https://s3.example/a.jpg");

        ProductImageResponse response = productImageService.updateImage(
                SELLER_ID, PRODUCT_ID, 5L, new ProductImageUpdateRequest((short) 3, null));

        assertThat(response.sortOrder()).isEqualTo((short) 3);
        assertThat(response.isPrimary()).isFalse();
    }

    @Test
    void 대표_이미지로_지정하면_같은_상품의_다른_대표를_해제한다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(imageProduct.getId()).thenReturn(PRODUCT_ID);
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(product));
        ProductImage image = ProductImage.builder()
                .product(imageProduct)
                .imageKey("product-images/1/a.jpg")
                .sortOrder((short) 0)
                .primary(false)
                .build();
        when(productImageRepository.findById(5L)).thenReturn(Optional.of(image));
        when(s3StorageService.publicUrl(eq(PUBLIC_BUCKET), anyString())).thenReturn("https://s3.example/a.jpg");

        ProductImageResponse response = productImageService.updateImage(
                SELLER_ID, PRODUCT_ID, 5L, new ProductImageUpdateRequest(null, true));

        verify(productImageRepository).clearPrimaryExcept(PRODUCT_ID, 5L);
        assertThat(response.isPrimary()).isTrue();
    }

    @Test
    void 다른_상품의_이미지를_수정하려_하면_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(imageProduct.getId()).thenReturn(999L);
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(product));
        ProductImage image = ProductImage.builder()
                .product(imageProduct)
                .imageKey("product-images/999/a.jpg")
                .sortOrder((short) 0)
                .primary(false)
                .build();
        when(productImageRepository.findById(5L)).thenReturn(Optional.of(image));

        assertThatThrownBy(() -> productImageService.updateImage(
                SELLER_ID, PRODUCT_ID, 5L, new ProductImageUpdateRequest((short) 1, null)))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 여러_상품의_대표_이미지_URL을_배치로_조회한다() {
        when(imageProduct.getId()).thenReturn(PRODUCT_ID);
        ProductImage primaryImage = ProductImage.builder()
                .product(imageProduct)
                .imageKey("product-images/1/a.jpg")
                .sortOrder((short) 0)
                .primary(true)
                .build();
        when(productImageRepository.findByProduct_IdInAndPrimaryTrue(java.util.List.of(PRODUCT_ID)))
                .thenReturn(java.util.List.of(primaryImage));
        when(s3StorageService.publicUrl(PUBLIC_BUCKET, "product-images/1/a.jpg"))
                .thenReturn("https://s3.example/product-images/1/a.jpg");

        java.util.Map<Long, String> result = productImageService.getPrimaryImageUrls(java.util.List.of(PRODUCT_ID));

        assertThat(result).containsEntry(PRODUCT_ID, "https://s3.example/product-images/1/a.jpg");
    }

    @Test
    void 상품_ID_목록이_비어있으면_배치_조회_없이_빈_맵을_반환한다() {
        java.util.Map<Long, String> result = productImageService.getPrimaryImageUrls(java.util.List.of());

        assertThat(result).isEmpty();
    }
}