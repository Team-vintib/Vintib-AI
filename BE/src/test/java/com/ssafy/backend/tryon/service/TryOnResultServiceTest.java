package com.ssafy.backend.tryon.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.ProductRepository;
import com.ssafy.backend.tryon.dto.response.TryOnResultResponse;
import com.ssafy.backend.tryon.entity.TryOnResult;
import com.ssafy.backend.tryon.repository.TryOnResultRepository;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

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
    private S3StorageService s3StorageService;

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
                tryOnResultRepository, memberRepository, productRepository, s3StorageService, awsProperties);
    }

    @Test
    void 목록_조회시_각_결과에_presigned_URL을_채운다() {
        when(product.getId()).thenReturn(PRODUCT_ID);
        TryOnResult result =
                TryOnResult.builder().member(member).product(product).imageKey("tryon-results/1/a.jpg").build();
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
    void 본인의_시착_결과가_아니면_조회를_거부한다() {
        when(member.getId()).thenReturn(MEMBER_ID);
        TryOnResult result =
                TryOnResult.builder().member(member).product(product).imageKey("tryon-results/1/a.jpg").build();
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
        TryOnResult result =
                TryOnResult.builder().member(member).product(product).imageKey("tryon-results/1/a.jpg").build();
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
}