package com.ssafy.backend.live.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.live.dto.request.LiveThumbnailUploadUrlRequest;
import com.ssafy.backend.live.dto.response.LiveThumbnailUploadUrlResponse;
import com.ssafy.backend.member.repository.MemberRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class LiveThumbnailServiceTest {

    private static final Long MEMBER_ID = 1L;
    private static final String PUBLIC_BUCKET = "public-bucket";

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private S3StorageService s3StorageService;

    private AwsProperties awsProperties;
    private LiveThumbnailService liveThumbnailService;

    @BeforeEach
    void setUp() {
        awsProperties = new AwsProperties(
                "us-east-1",
                "test-key",
                "test-secret",
                new AwsProperties.S3("", "", PUBLIC_BUCKET, "private-bucket"));
        liveThumbnailService = new LiveThumbnailService(memberRepository, s3StorageService, awsProperties);
    }

    @Test
    void 업로드_URL_발급시_public_버킷에_presigned_PUT과_공개_URL을_함께_내려준다() {
        when(memberRepository.existsById(MEMBER_ID)).thenReturn(true);
        when(s3StorageService.createUploadUrl(eq(PUBLIC_BUCKET), anyString(), eq("image/jpeg")))
                .thenReturn(new S3StorageService.PresignedUpload("https://s3.example/put", 300));
        when(s3StorageService.publicUrl(eq(PUBLIC_BUCKET), anyString()))
                .thenReturn("https://cdn.example.com/live-thumbnails/1/new.jpg");

        LiveThumbnailUploadUrlResponse response = liveThumbnailService.createUploadUrl(
                MEMBER_ID, MEMBER_ID, new LiveThumbnailUploadUrlRequest("image/jpeg"));

        assertThat(response.uploadUrl()).isEqualTo("https://s3.example/put");
        assertThat(response.key()).startsWith("live-thumbnails/1/");
        assertThat(response.url()).isEqualTo("https://cdn.example.com/live-thumbnails/1/new.jpg");
        assertThat(response.expiresInSeconds()).isEqualTo(300);
    }

    @Test
    void 지원하지_않는_이미지_타입이면_업로드_URL_발급을_거부한다() {
        when(memberRepository.existsById(MEMBER_ID)).thenReturn(true);

        assertThatThrownBy(() -> liveThumbnailService.createUploadUrl(
                        MEMBER_ID, MEMBER_ID, new LiveThumbnailUploadUrlRequest("image/gif")))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.INVALID_IMAGE_TYPE);
    }

    @Test
    void 본인이_아니면_업로드_URL_발급이_거부된다() {
        Long otherMemberId = 999L;

        assertThatThrownBy(() -> liveThumbnailService.createUploadUrl(
                        MEMBER_ID, otherMemberId, new LiveThumbnailUploadUrlRequest("image/jpeg")))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.MEMBER_FORBIDDEN);
    }

    @Test
    void 존재하지_않는_회원이면_업로드_URL_발급이_거부된다() {
        when(memberRepository.existsById(MEMBER_ID)).thenReturn(false);

        assertThatThrownBy(() -> liveThumbnailService.createUploadUrl(
                        MEMBER_ID, MEMBER_ID, new LiveThumbnailUploadUrlRequest("image/jpeg")))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.USER_NOT_FOUND);
    }
}
