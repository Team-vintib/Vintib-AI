package com.ssafy.backend.product.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.product.dto.request.ProductImageRegisterRequest;
import com.ssafy.backend.product.dto.request.ProductImageUploadUrlRequest;
import com.ssafy.backend.product.dto.response.ProductImageResponse;
import com.ssafy.backend.product.dto.response.ProductImageUploadUrlResponse;
import com.ssafy.backend.product.entity.Product;
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
    private S3StorageService s3StorageService;

    @Mock
    private Member seller;

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
        productImageService =
                new ProductImageService(productRepository, productImageRepository, s3StorageService, awsProperties);
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
}