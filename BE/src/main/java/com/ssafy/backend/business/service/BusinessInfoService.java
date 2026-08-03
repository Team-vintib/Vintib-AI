package com.ssafy.backend.business.service;

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
import java.util.Map;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import software.amazon.awssdk.services.s3.model.HeadObjectResponse;
import software.amazon.awssdk.services.s3.model.NoSuchKeyException;

/**
 * 사업자 인증 정보(BIZ-001)의 제출/조회/재제출.
 *
 * <p>사업자등록증은 {@code TryOnProfileService}와 동일한 presigned 2단계 업로드를 쓴다 —
 * 개인 사업 서류라 비공개 버킷에 저장하고, 조회 시마다 짧은 만료시간의 presigned GET URL을
 * 즉석 발급한다. 관리자 승인/거절 API가 아직 없어 이번 범위는 제출/조회/재제출까지다.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class BusinessInfoService {

    private static final long MAX_IMAGE_SIZE_BYTES = 10L * 1024 * 1024;
    private static final Map<String, String> ALLOWED_CONTENT_TYPE_EXTENSIONS =
            Map.of("image/jpeg", "jpg", "image/png", "png", "image/webp", "webp");

    private final BusinessInfoRepository businessInfoRepository;
    private final MemberRepository memberRepository;
    private final S3StorageService s3StorageService;
    private final AwsProperties awsProperties;

    public BusinessCertificateUploadUrlResponse createUploadUrl(Long memberId, BusinessCertificateUploadUrlRequest request) {
        String extension = ALLOWED_CONTENT_TYPE_EXTENSIONS.get(request.contentType());
        if (extension == null) {
            throw new CustomException(ErrorCode.INVALID_IMAGE_TYPE);
        }

        String key = "business-certificates/%d/%s.%s".formatted(memberId, UUID.randomUUID(), extension);
        S3StorageService.PresignedUpload upload = s3StorageService.createUploadUrl(
                awsProperties.s3().privateBucket(), key, request.contentType());

        return new BusinessCertificateUploadUrlResponse(key, upload.uploadUrl(), upload.expiresInSeconds());
    }

    @Transactional
    public BusinessInfoResponse submit(Long memberId, BusinessInfoSubmitRequest request) {
        String bucket = awsProperties.s3().privateBucket();
        BusinessInfo businessInfo = businessInfoRepository.findById(memberId).orElse(null);

        if (businessInfo == null) {
            verifyUploaded(bucket, request.certificateKey());
            Member member = memberRepository.findById(memberId)
                    .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
            businessInfo = BusinessInfo.builder()
                    .member(member)
                    .businessNumber(request.businessNumber())
                    .businessName(request.businessName())
                    .representativeName(request.representativeName())
                    .certificateKey(request.certificateKey())
                    .build();
            businessInfoRepository.save(businessInfo);
            return toResponse(businessInfo);
        }

        if (businessInfo.getVerificationStatus() != BusinessVerificationStatus.REJECTED) {
            throw new CustomException(ErrorCode.BUSINESS_INFO_ALREADY_SUBMITTED);
        }

        verifyUploaded(bucket, request.certificateKey());
        String oldKey = businessInfo.getCertificateKey();
        if (!request.certificateKey().equals(oldKey)) {
            s3StorageService.delete(bucket, oldKey);
        }
        businessInfo.resubmit(
                request.businessNumber(), request.businessName(), request.representativeName(), request.certificateKey());
        businessInfoRepository.save(businessInfo);
        return toResponse(businessInfo);
    }

    public BusinessInfoResponse getStatus(Long memberId) {
        BusinessInfo businessInfo = businessInfoRepository.findById(memberId).orElse(null);
        if (businessInfo == null) {
            return new BusinessInfoResponse("NONE", null, null, null, null, null, null);
        }
        return toResponse(businessInfo);
    }

    // presigned PUT 자체는 최대 용량을 강제하지 못하므로, 등록 확인 시점에 실제 업로드된
    // 객체를 HeadObject로 검증한다(TryOnProfileService.verifyUploaded와 동일 패턴).
    private void verifyUploaded(String bucket, String key) {
        if (!key.startsWith("business-certificates/")) {
            throw new CustomException(ErrorCode.BUSINESS_CERTIFICATE_UPLOAD_NOT_CONFIRMED);
        }
        HeadObjectResponse head;
        try {
            head = s3StorageService.headObject(bucket, key);
        } catch (NoSuchKeyException e) {
            throw new CustomException(ErrorCode.BUSINESS_CERTIFICATE_UPLOAD_NOT_CONFIRMED);
        }
        if (head.contentLength() != null && head.contentLength() > MAX_IMAGE_SIZE_BYTES) {
            s3StorageService.delete(bucket, key);
            throw new CustomException(ErrorCode.BUSINESS_CERTIFICATE_UPLOAD_NOT_CONFIRMED);
        }
    }

    private BusinessInfoResponse toResponse(BusinessInfo businessInfo) {
        String certificateUrl =
                s3StorageService.presignedGetUrl(awsProperties.s3().privateBucket(), businessInfo.getCertificateKey());
        return new BusinessInfoResponse(
                businessInfo.getVerificationStatus().name(),
                businessInfo.getBusinessNumber(),
                businessInfo.getBusinessName(),
                businessInfo.getRepresentativeName(),
                certificateUrl,
                businessInfo.getSubmittedAt(),
                businessInfo.getVerifiedAt());
    }
}
