package com.ssafy.backend.member.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.business.repository.BusinessInfoRepository;
import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.member.dto.request.MemberImageKeyRequest;
import com.ssafy.backend.member.dto.request.MemberImageUploadUrlRequest;
import com.ssafy.backend.member.dto.response.MemberImageUploadUrlResponse;
import com.ssafy.backend.member.dto.response.MemberProfileResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import software.amazon.awssdk.services.s3.model.HeadObjectResponse;
import software.amazon.awssdk.services.s3.model.NoSuchKeyException;

@ExtendWith(MockitoExtension.class)
class MemberImageServiceTest {

    private static final Long MEMBER_ID = 1L;
    private static final String PUBLIC_BUCKET = "public-bucket";

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private BusinessInfoRepository businessInfoRepository;

    @Mock
    private S3StorageService s3StorageService;

    private AwsProperties awsProperties;
    private MemberImageService memberImageService;

    @BeforeEach
    void setUp() {
        awsProperties = new AwsProperties(
                "us-east-1",
                "test-key",
                "test-secret",
                new AwsProperties.S3("", "", PUBLIC_BUCKET, "private-bucket"));
        memberImageService =
                new MemberImageService(memberRepository, businessInfoRepository, s3StorageService, awsProperties);
    }

    private Member createMember() {
        return Member.builder().email("user@example.com").password("encoded").name("홍길동").build();
    }

    @Test
    void 프로필_이미지_업로드_URL_발급시_public_버킷에_presigned_PUT을_발급한다() {
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(createMember()));
        when(s3StorageService.createUploadUrl(eq(PUBLIC_BUCKET), anyString(), eq("image/jpeg")))
                .thenReturn(new S3StorageService.PresignedUpload("https://s3.example/put", 300));

        MemberImageUploadUrlResponse response = memberImageService.createProfileImageUploadUrl(
                MEMBER_ID, MEMBER_ID, new MemberImageUploadUrlRequest("image/jpeg"));

        assertThat(response.uploadUrl()).isEqualTo("https://s3.example/put");
        assertThat(response.key()).startsWith("member-profiles/1/");
    }

    @Test
    void 커버_이미지_업로드_URL_발급시_key가_member_covers_prefix다() {
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(createMember()));
        when(s3StorageService.createUploadUrl(eq(PUBLIC_BUCKET), anyString(), eq("image/png")))
                .thenReturn(new S3StorageService.PresignedUpload("https://s3.example/put", 300));

        MemberImageUploadUrlResponse response = memberImageService.createCoverImageUploadUrl(
                MEMBER_ID, MEMBER_ID, new MemberImageUploadUrlRequest("image/png"));

        assertThat(response.key()).startsWith("member-covers/1/");
    }

    @Test
    void 지원하지_않는_이미지_타입이면_업로드_URL_발급을_거부한다() {
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(createMember()));

        assertThatThrownBy(() -> memberImageService.createProfileImageUploadUrl(
                        MEMBER_ID, MEMBER_ID, new MemberImageUploadUrlRequest("image/gif")))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.INVALID_IMAGE_TYPE);
    }

    @Test
    void 본인이_아니면_업로드_URL_발급이_거부된다() {
        Long otherMemberId = 999L;

        assertThatThrownBy(() -> memberImageService.createProfileImageUploadUrl(
                        MEMBER_ID, otherMemberId, new MemberImageUploadUrlRequest("image/jpeg")))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.MEMBER_FORBIDDEN);
    }

    @Test
    void 프로필_이미지_확정시_공개_URL을_저장한다() {
        Member member = createMember();
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));
        when(businessInfoRepository.findById(MEMBER_ID)).thenReturn(Optional.empty());
        HeadObjectResponse head = mock(HeadObjectResponse.class);
        when(head.contentLength()).thenReturn(1024L);
        when(s3StorageService.headObject(PUBLIC_BUCKET, "member-profiles/1/new.jpg")).thenReturn(head);
        when(s3StorageService.publicUrl(PUBLIC_BUCKET, "member-profiles/1/new.jpg"))
                .thenReturn("https://cdn.example.com/member-profiles/1/new.jpg");

        MemberProfileResponse response = memberImageService.confirmProfileImage(
                MEMBER_ID, MEMBER_ID, new MemberImageKeyRequest("member-profiles/1/new.jpg"));

        assertThat(response.profileImageUrl()).isEqualTo("https://cdn.example.com/member-profiles/1/new.jpg");
    }

    @Test
    void 커버_이미지_확정시_공개_URL을_저장한다() {
        Member member = createMember();
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));
        when(businessInfoRepository.findById(MEMBER_ID)).thenReturn(Optional.empty());
        HeadObjectResponse head = mock(HeadObjectResponse.class);
        when(head.contentLength()).thenReturn(1024L);
        when(s3StorageService.headObject(PUBLIC_BUCKET, "member-covers/1/new.jpg")).thenReturn(head);
        when(s3StorageService.publicUrl(PUBLIC_BUCKET, "member-covers/1/new.jpg"))
                .thenReturn("https://cdn.example.com/member-covers/1/new.jpg");

        MemberProfileResponse response = memberImageService.confirmCoverImage(
                MEMBER_ID, MEMBER_ID, new MemberImageKeyRequest("member-covers/1/new.jpg"));

        assertThat(response.coverImageUrl()).isEqualTo("https://cdn.example.com/member-covers/1/new.jpg");
    }

    @Test
    void 다른_리소스_prefix의_key로_확정하면_예외를_던진다() {
        Member member = createMember();
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));

        assertThatThrownBy(() -> memberImageService.confirmProfileImage(
                        MEMBER_ID, MEMBER_ID, new MemberImageKeyRequest("member-covers/1/new.jpg")))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.MEMBER_IMAGE_UPLOAD_NOT_CONFIRMED);
    }

    @Test
    void 업로드가_확인되지_않은_key로_확정하면_예외를_던진다() {
        Member member = createMember();
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));
        when(s3StorageService.headObject(PUBLIC_BUCKET, "member-profiles/1/missing.jpg"))
                .thenThrow(NoSuchKeyException.builder().build());

        assertThatThrownBy(() -> memberImageService.confirmProfileImage(
                        MEMBER_ID, MEMBER_ID, new MemberImageKeyRequest("member-profiles/1/missing.jpg")))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.MEMBER_IMAGE_UPLOAD_NOT_CONFIRMED);
    }

    @Test
    void 용량_초과_이미지로_확정하면_S3에서_지우고_예외를_던진다() {
        Member member = createMember();
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));
        HeadObjectResponse head = mock(HeadObjectResponse.class);
        when(head.contentLength()).thenReturn(11L * 1024 * 1024);
        when(s3StorageService.headObject(PUBLIC_BUCKET, "member-profiles/1/big.jpg")).thenReturn(head);

        assertThatThrownBy(() -> memberImageService.confirmProfileImage(
                        MEMBER_ID, MEMBER_ID, new MemberImageKeyRequest("member-profiles/1/big.jpg")))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.MEMBER_IMAGE_UPLOAD_NOT_CONFIRMED);
        verify(s3StorageService).delete(PUBLIC_BUCKET, "member-profiles/1/big.jpg");
    }

    @Test
    void 본인이_아니면_이미지_확정이_거부된다() {
        Long otherMemberId = 999L;

        assertThatThrownBy(() -> memberImageService.confirmProfileImage(
                        MEMBER_ID, otherMemberId, new MemberImageKeyRequest("member-profiles/999/new.jpg")))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.MEMBER_FORBIDDEN);
    }

    @Test
    void 프로필_이미지_삭제시_S3_객체는_지우지_않고_컬럼만_비운다() {
        Member member = createMember();
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));

        memberImageService.deleteProfileImage(MEMBER_ID, MEMBER_ID);

        verify(s3StorageService, never()).delete(anyString(), anyString());
        assertThat(member.getProfileImageUrl()).isNull();
    }

    @Test
    void 본인이_아니면_이미지_삭제가_거부된다() {
        Long otherMemberId = 999L;

        assertThatThrownBy(() -> memberImageService.deleteCoverImage(MEMBER_ID, otherMemberId))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.MEMBER_FORBIDDEN);
    }
}
