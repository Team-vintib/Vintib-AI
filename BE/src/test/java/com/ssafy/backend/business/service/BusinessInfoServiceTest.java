package com.ssafy.backend.business.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.business.dto.request.BusinessCertificateUploadUrlRequest;
import com.ssafy.backend.business.dto.request.BusinessInfoSubmitRequest;
import com.ssafy.backend.business.dto.response.BusinessCertificateUploadUrlResponse;
import com.ssafy.backend.business.dto.response.BusinessInfoResponse;
import com.ssafy.backend.business.entity.BusinessInfo;
import com.ssafy.backend.business.entity.BusinessVerificationStatus;
import com.ssafy.backend.business.repository.BusinessInfoRepository;
import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;
import software.amazon.awssdk.services.s3.model.HeadObjectResponse;
import software.amazon.awssdk.services.s3.model.NoSuchKeyException;

@ExtendWith(MockitoExtension.class)
class BusinessInfoServiceTest {

    private static final Long MEMBER_ID = 1L;
    private static final String PRIVATE_BUCKET = "private-bucket";

    @Mock
    private BusinessInfoRepository businessInfoRepository;

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private S3StorageService s3StorageService;

    @Mock
    private Member member;

    private AwsProperties awsProperties;
    private BusinessInfoService businessInfoService;

    @BeforeEach
    void setUp() {
        awsProperties = new AwsProperties(
                "us-east-1",
                "test-key",
                "test-secret",
                new AwsProperties.S3("", "", "public-bucket", PRIVATE_BUCKET));
        businessInfoService =
                new BusinessInfoService(businessInfoRepository, memberRepository, s3StorageService, awsProperties);
    }

    @Test
    void 업로드_URL_발급시_private_버킷에_presigned_PUT을_발급한다() {
        when(s3StorageService.createUploadUrl(eq(PRIVATE_BUCKET), anyString(), eq("image/jpeg")))
                .thenReturn(new S3StorageService.PresignedUpload("https://s3.example/put", 300));

        BusinessCertificateUploadUrlResponse response = businessInfoService.createUploadUrl(
                MEMBER_ID, new BusinessCertificateUploadUrlRequest("image/jpeg"));

        assertThat(response.uploadUrl()).isEqualTo("https://s3.example/put");
        assertThat(response.key()).startsWith("business-certificates/1/");
    }

    @Test
    void 지원하지_않는_이미지_타입이면_업로드_URL_발급을_거부한다() {
        assertThatThrownBy(() -> businessInfoService.createUploadUrl(
                        MEMBER_ID, new BusinessCertificateUploadUrlRequest("image/gif")))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.INVALID_IMAGE_TYPE);
    }

    @Test
    void 최초_제출이_성공하면_PENDING으로_생성된다() {
        when(businessInfoRepository.findById(MEMBER_ID)).thenReturn(Optional.empty());
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));
        HeadObjectResponse head = mock(HeadObjectResponse.class);
        when(head.contentLength()).thenReturn(1024L);
        when(s3StorageService.headObject(PRIVATE_BUCKET, "business-certificates/1/a.jpg")).thenReturn(head);
        when(s3StorageService.presignedGetUrl(PRIVATE_BUCKET, "business-certificates/1/a.jpg"))
                .thenReturn("https://s3.example/a");

        BusinessInfoResponse response = businessInfoService.submit(
                MEMBER_ID,
                new BusinessInfoSubmitRequest("1234567890", "빈티브 상회", "홍길동", "business-certificates/1/a.jpg"));

        assertThat(response.status()).isEqualTo("PENDING");
        assertThat(response.businessNumber()).isEqualTo("1234567890");
        assertThat(response.certificateUrl()).isEqualTo("https://s3.example/a");
    }

    @Test
    void 업로드가_확인되지_않은_key로_제출하면_예외를_던진다() {
        when(businessInfoRepository.findById(MEMBER_ID)).thenReturn(Optional.empty());
        when(s3StorageService.headObject(PRIVATE_BUCKET, "business-certificates/1/missing.jpg"))
                .thenThrow(NoSuchKeyException.builder().build());

        assertThatThrownBy(() -> businessInfoService.submit(
                        MEMBER_ID,
                        new BusinessInfoSubmitRequest(
                                "1234567890", "빈티브 상회", "홍길동", "business-certificates/1/missing.jpg")))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.BUSINESS_CERTIFICATE_UPLOAD_NOT_CONFIRMED);
    }

    @Test
    void REJECTED_상태에서_재제출하면_필드가_갱신되고_PENDING으로_리셋된다() {
        BusinessInfo rejected = newBusinessInfo("business-certificates/1/old.jpg");
        ReflectionTestUtils.setField(rejected, "verificationStatus", BusinessVerificationStatus.REJECTED);
        when(businessInfoRepository.findById(MEMBER_ID)).thenReturn(Optional.of(rejected));
        HeadObjectResponse head = mock(HeadObjectResponse.class);
        when(head.contentLength()).thenReturn(1024L);
        when(s3StorageService.headObject(PRIVATE_BUCKET, "business-certificates/1/new.jpg")).thenReturn(head);
        when(s3StorageService.presignedGetUrl(PRIVATE_BUCKET, "business-certificates/1/new.jpg"))
                .thenReturn("https://s3.example/new");

        BusinessInfoResponse response = businessInfoService.submit(
                MEMBER_ID,
                new BusinessInfoSubmitRequest("2222222222", "새상호", "새대표", "business-certificates/1/new.jpg"));

        assertThat(response.status()).isEqualTo("PENDING");
        assertThat(response.businessNumber()).isEqualTo("2222222222");
        assertThat(response.businessName()).isEqualTo("새상호");
        verify(s3StorageService).delete(PRIVATE_BUCKET, "business-certificates/1/old.jpg");
    }

    @Test
    void PENDING_상태에서_재제출을_시도하면_예외를_던진다() {
        BusinessInfo pending = newBusinessInfo("business-certificates/1/old.jpg");
        when(businessInfoRepository.findById(MEMBER_ID)).thenReturn(Optional.of(pending));

        assertThatThrownBy(() -> businessInfoService.submit(
                        MEMBER_ID,
                        new BusinessInfoSubmitRequest(
                                "2222222222", "새상호", "새대표", "business-certificates/1/new.jpg")))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.BUSINESS_INFO_ALREADY_SUBMITTED);
        verify(s3StorageService, never()).delete(anyString(), anyString());
    }

    @Test
    void APPROVED_상태에서_재제출을_시도하면_예외를_던진다() {
        BusinessInfo approved = newBusinessInfo("business-certificates/1/old.jpg");
        ReflectionTestUtils.setField(approved, "verificationStatus", BusinessVerificationStatus.APPROVED);
        when(businessInfoRepository.findById(MEMBER_ID)).thenReturn(Optional.of(approved));

        assertThatThrownBy(() -> businessInfoService.submit(
                        MEMBER_ID,
                        new BusinessInfoSubmitRequest(
                                "2222222222", "새상호", "새대표", "business-certificates/1/new.jpg")))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.BUSINESS_INFO_ALREADY_SUBMITTED);
    }

    @Test
    void 제출_이력이_없으면_조회시_NONE을_반환한다() {
        when(businessInfoRepository.findById(MEMBER_ID)).thenReturn(Optional.empty());

        BusinessInfoResponse response = businessInfoService.getStatus(MEMBER_ID);

        assertThat(response.status()).isEqualTo("NONE");
        assertThat(response.businessNumber()).isNull();
        assertThat(response.certificateUrl()).isNull();
    }

    @Test
    void 제출_이력이_있으면_조회시_실제_상태와_presigned_URL을_반환한다() {
        BusinessInfo pending = newBusinessInfo("business-certificates/1/a.jpg");
        when(businessInfoRepository.findById(MEMBER_ID)).thenReturn(Optional.of(pending));
        when(s3StorageService.presignedGetUrl(PRIVATE_BUCKET, "business-certificates/1/a.jpg"))
                .thenReturn("https://s3.example/a");

        BusinessInfoResponse response = businessInfoService.getStatus(MEMBER_ID);

        assertThat(response.status()).isEqualTo("PENDING");
        assertThat(response.certificateUrl()).isEqualTo("https://s3.example/a");
    }

    private BusinessInfo newBusinessInfo(String certificateKey) {
        return BusinessInfo.builder()
                .member(member)
                .businessNumber("1111111111")
                .businessName("상호")
                .representativeName("대표")
                .certificateKey(certificateKey)
                .build();
    }
}
