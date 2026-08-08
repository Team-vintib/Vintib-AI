package com.ssafy.backend.tryon.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.client.dto.AiJobResponse;
import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import com.ssafy.backend.product.service.ProductImageService;
import com.ssafy.backend.tryon.dto.response.TryOnResultResponse;
import com.ssafy.backend.tryon.entity.MemberBodyProfile;
import com.ssafy.backend.tryon.entity.TryOnResult;
import com.ssafy.backend.tryon.entity.TryOnResultStatus;
import com.ssafy.backend.tryon.repository.MemberBodyProfileRepository;
import com.ssafy.backend.tryon.repository.TryOnResultRepository;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestClientException;

@ExtendWith(MockitoExtension.class)
class TryOnResultServiceTest {

    private static final Long MEMBER_ID = 1L;
    private static final Long PRODUCT_ID = 1L;
    private static final String PRIVATE_BUCKET = "private-bucket";

    @Mock
    private TryOnResultRepository tryOnResultRepository;

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private ProductRepository productRepository;

    @Mock
    private MemberBodyProfileRepository memberBodyProfileRepository;

    @Mock
    private ProductImageService productImageService;

    @Mock
    private S3StorageService s3StorageService;

    @Mock
    private AiClient aiClient;

    @Mock
    private CategoryRepository categoryRepository;

    @Mock
    private Member member;

    @Mock
    private Product product;

    private AwsProperties awsProperties;
    private TryOnResultService tryOnResultService;

    @BeforeEach
    void setUp() {
        awsProperties = new AwsProperties(
                "us-east-1",
                "test-key",
                "test-secret",
                new AwsProperties.S3("", "", "public-bucket", PRIVATE_BUCKET));
        tryOnResultService = new TryOnResultService(
                tryOnResultRepository,
                memberRepository,
                productRepository,
                memberBodyProfileRepository,
                productImageService,
                s3StorageService,
                awsProperties,
                aiClient,
                categoryRepository);
    }

    @Test
    void 목록_조회시_각_결과에_presigned_URL을_채운다() {
        when(product.getId()).thenReturn(PRODUCT_ID);
        TryOnResult result = TryOnResult.builder()
                .member(member)
                .product(product)
                .imageKey("tryon-results/1/a.jpg")
                .status(TryOnResultStatus.SUCCESS)
                .build();
        when(tryOnResultRepository.findAllByMemberIdAndDeletedAtIsNullOrderByCreatedAtDesc(MEMBER_ID))
                .thenReturn(List.of(result));
        when(s3StorageService.presignedGetUrl(PRIVATE_BUCKET, "tryon-results/1/a.jpg"))
                .thenReturn("https://s3.example/presigned");

        List<TryOnResultResponse> responses = tryOnResultService.getResults(MEMBER_ID);

        assertThat(responses).hasSize(1);
        assertThat(responses.get(0).imageUrl()).isEqualTo("https://s3.example/presigned");
        assertThat(responses.get(0).productId()).isEqualTo(PRODUCT_ID);
    }

    @Test
    void 목록_조회시_상품의_대분류_카테고리를_함께_반환한다() {
        Long leafCategoryId = 31L;
        Long topCategoryId = 5L;
        when(product.getId()).thenReturn(PRODUCT_ID);
        when(product.getCategoryId()).thenReturn(leafCategoryId);
        Category leaf = org.mockito.Mockito.mock(Category.class);
        when(leaf.getId()).thenReturn(leafCategoryId);
        when(leaf.getDepth()).thenReturn((short) 3);
        when(leaf.getParentId()).thenReturn(topCategoryId);
        Category top = org.mockito.Mockito.mock(Category.class);
        when(top.getId()).thenReturn(topCategoryId);
        when(top.getName()).thenReturn("아우터");
        when(categoryRepository.findAllById(java.util.Set.of(leafCategoryId))).thenReturn(List.of(leaf));
        when(categoryRepository.findAllById(java.util.Set.of(topCategoryId))).thenReturn(List.of(top));
        TryOnResult result = TryOnResult.builder()
                .member(member)
                .product(product)
                .imageKey("tryon-results/1/a.jpg")
                .status(TryOnResultStatus.SUCCESS)
                .build();
        when(tryOnResultRepository.findAllByMemberIdAndDeletedAtIsNullOrderByCreatedAtDesc(MEMBER_ID))
                .thenReturn(List.of(result));
        when(s3StorageService.presignedGetUrl(PRIVATE_BUCKET, "tryon-results/1/a.jpg"))
                .thenReturn("https://s3.example/presigned");

        List<TryOnResultResponse> responses = tryOnResultService.getResults(MEMBER_ID);

        assertThat(responses.get(0).categoryId()).isEqualTo(topCategoryId);
        assertThat(responses.get(0).categoryName()).isEqualTo("아우터");
    }

    @Test
    void 카테고리를_찾을_수_없으면_카테고리_필드는_null이다() {
        when(product.getId()).thenReturn(PRODUCT_ID);
        when(product.getCategoryId()).thenReturn(999L);
        when(categoryRepository.findAllById(java.util.Set.of(999L))).thenReturn(List.of());
        TryOnResult result = TryOnResult.builder()
                .member(member)
                .product(product)
                .imageKey("tryon-results/1/a.jpg")
                .status(TryOnResultStatus.SUCCESS)
                .build();
        when(tryOnResultRepository.findAllByMemberIdAndDeletedAtIsNullOrderByCreatedAtDesc(MEMBER_ID))
                .thenReturn(List.of(result));
        when(s3StorageService.presignedGetUrl(PRIVATE_BUCKET, "tryon-results/1/a.jpg"))
                .thenReturn("https://s3.example/presigned");

        List<TryOnResultResponse> responses = tryOnResultService.getResults(MEMBER_ID);

        assertThat(responses.get(0).categoryId()).isNull();
        assertThat(responses.get(0).categoryName()).isNull();
    }

    @Test
    void 본인의_시착_결과가_아니면_조회를_거부한다() {
        when(member.getId()).thenReturn(MEMBER_ID);
        TryOnResult result = TryOnResult.builder()
                .member(member)
                .product(product)
                .imageKey("tryon-results/1/a.jpg")
                .status(TryOnResultStatus.SUCCESS)
                .build();
        when(tryOnResultRepository.findById(10L)).thenReturn(Optional.of(result));

        assertThatThrownBy(() -> tryOnResultService.getResult(2L, 10L)).isInstanceOf(CustomException.class);
    }

    @Test
    void 존재하지_않는_시착_결과를_조회하면_예외를_던진다() {
        when(tryOnResultRepository.findById(10L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> tryOnResultService.getResult(MEMBER_ID, 10L))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 삭제시_S3_객체를_지우고_소프트_삭제한다() {
        when(member.getId()).thenReturn(MEMBER_ID);
        TryOnResult result = TryOnResult.builder()
                .member(member)
                .product(product)
                .imageKey("tryon-results/1/a.jpg")
                .status(TryOnResultStatus.SUCCESS)
                .build();
        when(tryOnResultRepository.findById(10L)).thenReturn(Optional.of(result));

        tryOnResultService.deleteResult(MEMBER_ID, 10L);

        verify(s3StorageService).delete(PRIVATE_BUCKET, "tryon-results/1/a.jpg");
        assertThat(result.getDeletedAt()).isNotNull();
    }

    @Test
    void 시착_결과를_저장하면_private_버킷에_업로드한다() {
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(product));
        when(s3StorageService.presignedGetUrl(eq(PRIVATE_BUCKET), anyString()))
                .thenReturn("https://s3.example/presigned");

        byte[] bytes = {1, 2, 3};
        TryOnResultResponse response = tryOnResultService.saveResult(MEMBER_ID, PRODUCT_ID, bytes, "image/png");

        assertThat(response.imageUrl()).isEqualTo("https://s3.example/presigned");
        verify(s3StorageService).put(eq(PRIVATE_BUCKET), anyString(), eq(bytes), eq("image/png"));
    }

    @Test
    void 지원하지_않는_이미지_타입으로_저장하면_예외를_던진다() {
        assertThatThrownBy(() -> tryOnResultService.saveResult(MEMBER_ID, PRODUCT_ID, new byte[] {1}, "image/gif"))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 시착_프로필_사진이_없으면_생성을_거부한다() {
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(product));
        when(memberBodyProfileRepository.findById(MEMBER_ID)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> tryOnResultService.createResult(MEMBER_ID, PRODUCT_ID))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.TRYON_PROFILE_PHOTO_REQUIRED);
    }

    @Test
    void 상품_대표_이미지가_없으면_생성을_거부한다() {
        MemberBodyProfile bodyProfile = MemberBodyProfile.builder().member(member).build();
        ReflectionTestUtils.setField(bodyProfile, "bodyPhotoKey", "tryon-profiles/1/photo.jpg");
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(product));
        when(memberBodyProfileRepository.findById(MEMBER_ID)).thenReturn(Optional.of(bodyProfile));
        when(s3StorageService.presignedGetUrl(PRIVATE_BUCKET, "tryon-profiles/1/photo.jpg"))
                .thenReturn("https://s3.example/profile");
        when(productImageService.getPrimaryImageUrls(List.of(PRODUCT_ID))).thenReturn(Map.of());

        assertThatThrownBy(() -> tryOnResultService.createResult(MEMBER_ID, PRODUCT_ID))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.PRODUCT_IMAGE_NOT_FOUND);
    }

    @Test
    void 시착_job을_접수하면_PENDING_상태로_저장된다() {
        MemberBodyProfile bodyProfile = MemberBodyProfile.builder().member(member).build();
        ReflectionTestUtils.setField(bodyProfile, "bodyPhotoKey", "tryon-profiles/1/photo.jpg");
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(product));
        when(memberBodyProfileRepository.findById(MEMBER_ID)).thenReturn(Optional.of(bodyProfile));
        when(s3StorageService.presignedGetUrl(PRIVATE_BUCKET, "tryon-profiles/1/photo.jpg"))
                .thenReturn("https://s3.example/profile");
        when(productImageService.getPrimaryImageUrls(List.of(PRODUCT_ID)))
                .thenReturn(Map.of(PRODUCT_ID, "https://s3.example/product.jpg"));
        when(aiClient.createTryOnJob(any())).thenReturn("job-123");

        TryOnResultResponse response = tryOnResultService.createResult(MEMBER_ID, PRODUCT_ID);

        assertThat(response.status()).isEqualTo(TryOnResultStatus.PENDING);
        assertThat(response.imageUrl()).isNull();
        verify(tryOnResultRepository).save(any(TryOnResult.class));
    }

    @Test
    void AI_job_접수에_실패하면_예외를_던진다() {
        MemberBodyProfile bodyProfile = MemberBodyProfile.builder().member(member).build();
        ReflectionTestUtils.setField(bodyProfile, "bodyPhotoKey", "tryon-profiles/1/photo.jpg");
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(product));
        when(memberBodyProfileRepository.findById(MEMBER_ID)).thenReturn(Optional.of(bodyProfile));
        when(s3StorageService.presignedGetUrl(PRIVATE_BUCKET, "tryon-profiles/1/photo.jpg"))
                .thenReturn("https://s3.example/profile");
        when(productImageService.getPrimaryImageUrls(List.of(PRODUCT_ID)))
                .thenReturn(Map.of(PRODUCT_ID, "https://s3.example/product.jpg"));
        when(aiClient.createTryOnJob(any())).thenThrow(new RestClientException("connection refused"));

        assertThatThrownBy(() -> tryOnResultService.createResult(MEMBER_ID, PRODUCT_ID))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.TRYON_JOB_CREATE_FAILED);
        verify(tryOnResultRepository, never()).save(any());
    }

    @Test
    void 대기중인_결과를_조회하면_AI_job_상태를_다시_확인해서_완료로_갱신한다() {
        when(member.getId()).thenReturn(MEMBER_ID);
        when(product.getId()).thenReturn(PRODUCT_ID);
        TryOnResult result = TryOnResult.builder()
                .member(member)
                .product(product)
                .jobId("job-123")
                .status(TryOnResultStatus.PENDING)
                .build();
        when(tryOnResultRepository.findById(10L)).thenReturn(Optional.of(result));
        when(aiClient.getJob("job-123")).thenReturn(new AiJobResponse(
                "success",
                Map.of("image_url", "https://ai.example/result.png", "fit_title", "적당해요"),
                null));

        TryOnResultResponse response = tryOnResultService.getResult(MEMBER_ID, 10L);

        assertThat(response.status()).isEqualTo(TryOnResultStatus.SUCCESS);
        assertThat(response.imageUrl()).isEqualTo("https://ai.example/result.png");
        assertThat(response.fitTitle()).isEqualTo("적당해요");
    }

    @Test
    void 대기중인_결과가_AI에서_실패로_나오면_FAILED로_갱신한다() {
        when(member.getId()).thenReturn(MEMBER_ID);
        TryOnResult result = TryOnResult.builder()
                .member(member)
                .product(product)
                .jobId("job-123")
                .status(TryOnResultStatus.PENDING)
                .build();
        when(tryOnResultRepository.findById(10L)).thenReturn(Optional.of(result));
        when(aiClient.getJob("job-123")).thenReturn(new AiJobResponse("failed", null, "worker error"));

        TryOnResultResponse response = tryOnResultService.getResult(MEMBER_ID, 10L);

        assertThat(response.status()).isEqualTo(TryOnResultStatus.FAILED);
        assertThat(response.imageUrl()).isNull();
    }
}