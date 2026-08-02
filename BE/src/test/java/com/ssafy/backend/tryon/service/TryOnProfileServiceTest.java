package com.ssafy.backend.tryon.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.tryon.dto.request.TryOnProfileUpdateRequest;
import com.ssafy.backend.tryon.dto.request.TryOnProfileUploadUrlRequest;
import com.ssafy.backend.tryon.dto.response.TryOnProfileResponse;
import com.ssafy.backend.tryon.dto.response.TryOnProfileUploadUrlResponse;
import com.ssafy.backend.tryon.entity.MemberBodyProfile;
import com.ssafy.backend.tryon.repository.MemberBodyProfileRepository;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import software.amazon.awssdk.services.s3.model.HeadObjectResponse;
import software.amazon.awssdk.services.s3.model.NoSuchKeyException;

@ExtendWith(MockitoExtension.class)
class TryOnProfileServiceTest {

    private static final Long MEMBER_ID = 1L;
    private static final String PRIVATE_BUCKET = "private-bucket";

    @Mock
    private MemberBodyProfileRepository memberBodyProfileRepository;

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private S3StorageService s3StorageService;

    @Mock
    private Member member;

    private AwsProperties awsProperties;
    private TryOnProfileService tryOnProfileService;

    @BeforeEach
    void setUp() {
        awsProperties = new AwsProperties(
                "us-east-1",
                "test-key",
                "test-secret",
                new AwsProperties.S3("", "", "public-bucket", PRIVATE_BUCKET));
        tryOnProfileService =
                new TryOnProfileService(memberBodyProfileRepository, memberRepository, s3StorageService, awsProperties);
    }

    @Test
    void 업로드_URL_발급시_private_버킷에_presigned_PUT을_발급한다() {
        when(s3StorageService.createUploadUrl(eq(PRIVATE_BUCKET), anyString(), eq("image/jpeg")))
                .thenReturn(new S3StorageService.PresignedUpload("https://s3.example/put", 300));

        TryOnProfileUploadUrlResponse response =
                tryOnProfileService.createUploadUrl(MEMBER_ID, new TryOnProfileUploadUrlRequest("image/jpeg"));

        assertThat(response.uploadUrl()).isEqualTo("https://s3.example/put");
        assertThat(response.key()).startsWith("tryon-profiles/1/");
    }

    @Test
    void 지원하지_않는_이미지_타입이면_업로드_URL_발급을_거부한다() {
        assertThatThrownBy(() -> tryOnProfileService.createUploadUrl(
                        MEMBER_ID, new TryOnProfileUploadUrlRequest("image/gif")))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.INVALID_IMAGE_TYPE);
    }

    @Test
    void 프로필이_없으면_조회시_예외를_던진다() {
        when(memberBodyProfileRepository.findById(MEMBER_ID)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> tryOnProfileService.getProfile(MEMBER_ID))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.TRYON_PROFILE_NOT_FOUND);
    }

    @Test
    void 사진_없이_신체_치수만으로_최초_등록된다() {
        when(memberBodyProfileRepository.findById(MEMBER_ID)).thenReturn(Optional.empty());
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));

        TryOnProfileResponse response = tryOnProfileService.upsertProfile(
                MEMBER_ID, new TryOnProfileUpdateRequest(null, (short) 170, (short) 60, null, null, null));

        assertThat(response.bodyPhotoUrl()).isNull();
        assertThat(response.heightCm()).isEqualTo((short) 170);
        assertThat(response.weightKg()).isEqualTo((short) 60);
    }

    @Test
    void 일부_필드만_보내면_기존_값이_유지된다() {
        MemberBodyProfile existing = MemberBodyProfile.builder().member(member).build();
        existing.mergeMeasurements((short) 170, (short) 60, (short) 90, (short) 70, (short) 95);
        when(memberBodyProfileRepository.findById(MEMBER_ID)).thenReturn(Optional.of(existing));

        TryOnProfileResponse response = tryOnProfileService.upsertProfile(
                MEMBER_ID, new TryOnProfileUpdateRequest(null, (short) 175, null, null, null, null));

        assertThat(response.heightCm()).isEqualTo((short) 175);
        assertThat(response.weightKg()).isEqualTo((short) 60);
        assertThat(response.chest()).isEqualTo((short) 90);
        assertThat(response.waist()).isEqualTo((short) 70);
        assertThat(response.hip()).isEqualTo((short) 95);
    }

    @Test
    void 사진을_교체하면_기존_S3_객체를_삭제하고_새_key로_바꾼다() {
        MemberBodyProfile existing = MemberBodyProfile.builder().member(member).build();
        existing.updatePhoto("tryon-profiles/1/old.jpg");
        when(memberBodyProfileRepository.findById(MEMBER_ID)).thenReturn(Optional.of(existing));
        HeadObjectResponse head = mock(HeadObjectResponse.class);
        when(head.contentLength()).thenReturn(1024L);
        when(s3StorageService.headObject(PRIVATE_BUCKET, "tryon-profiles/1/new.jpg")).thenReturn(head);
        when(s3StorageService.presignedGetUrl(PRIVATE_BUCKET, "tryon-profiles/1/new.jpg"))
                .thenReturn("https://s3.example/new");

        TryOnProfileResponse response = tryOnProfileService.upsertProfile(
                MEMBER_ID,
                new TryOnProfileUpdateRequest("tryon-profiles/1/new.jpg", null, null, null, null, null));

        verify(s3StorageService).delete(PRIVATE_BUCKET, "tryon-profiles/1/old.jpg");
        assertThat(response.bodyPhotoUrl()).isEqualTo("https://s3.example/new");
    }

    @Test
    void 업로드가_확인되지_않은_key면_예외를_던진다() {
        when(memberBodyProfileRepository.findById(MEMBER_ID)).thenReturn(Optional.empty());
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));
        when(s3StorageService.headObject(PRIVATE_BUCKET, "tryon-profiles/1/missing.jpg"))
                .thenThrow(NoSuchKeyException.builder().build());

        assertThatThrownBy(() -> tryOnProfileService.upsertProfile(
                        MEMBER_ID,
                        new TryOnProfileUpdateRequest("tryon-profiles/1/missing.jpg", null, null, null, null, null)))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.TRYON_PROFILE_UPLOAD_NOT_CONFIRMED);
    }

    @Test
    void 삭제시_S3_객체를_지우고_하드_삭제한다() {
        MemberBodyProfile existing = MemberBodyProfile.builder().member(member).build();
        existing.updatePhoto("tryon-profiles/1/a.jpg");
        when(memberBodyProfileRepository.findById(MEMBER_ID)).thenReturn(Optional.of(existing));

        tryOnProfileService.deleteProfile(MEMBER_ID);

        verify(s3StorageService).delete(PRIVATE_BUCKET, "tryon-profiles/1/a.jpg");
        verify(memberBodyProfileRepository).delete(existing);
    }

    @Test
    void 사진이_없는_프로필을_삭제해도_S3_삭제는_호출하지_않는다() {
        MemberBodyProfile existing = MemberBodyProfile.builder().member(member).build();
        when(memberBodyProfileRepository.findById(MEMBER_ID)).thenReturn(Optional.of(existing));

        tryOnProfileService.deleteProfile(MEMBER_ID);

        verify(s3StorageService, never()).delete(anyString(), anyString());
        verify(memberBodyProfileRepository).delete(existing);
    }

    @Test
    void 존재하지_않는_프로필을_삭제하면_예외를_던진다() {
        when(memberBodyProfileRepository.findById(MEMBER_ID)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> tryOnProfileService.deleteProfile(MEMBER_ID))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.TRYON_PROFILE_NOT_FOUND);
    }
}
