package com.ssafy.backend.global.storage;

import com.ssafy.backend.global.config.S3Config.AwsProperties;
import java.time.Duration;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.DeleteObjectRequest;
import software.amazon.awssdk.services.s3.model.HeadObjectRequest;
import software.amazon.awssdk.services.s3.model.HeadObjectResponse;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.presigner.model.GetObjectPresignRequest;
import software.amazon.awssdk.services.s3.presigner.model.PutObjectPresignRequest;

/**
 * product/tryon 등 도메인에서 공용으로 쓰는 S3 접근 컴포넌트. 버킷명은 호출부(도메인
 * 서비스)가 {@code S3Config.AwsProperties}에서 골라 넘긴다 — 이 클래스는 public/private
 * 버킷 구분을 모른다.
 *
 * 업로드 대상 존재 확인이 필요하면 {@link #headObject(String, String)}가 던지는
 * {@link software.amazon.awssdk.services.s3.model.NoSuchKeyException}을 호출부에서
 * 잡아 도메인 에러코드로 변환한다.
 */
@Service
@RequiredArgsConstructor
public class S3StorageService {

    private static final Duration UPLOAD_URL_TTL = Duration.ofMinutes(5);
    private static final Duration DOWNLOAD_URL_TTL = Duration.ofMinutes(10);

    private final S3Client s3Client;
    private final S3Presigner s3Presigner;
    private final AwsProperties awsProperties;

    public PresignedUpload createUploadUrl(String bucket, String key, String contentType) {
        PutObjectRequest putRequest =
                PutObjectRequest.builder().bucket(bucket).key(key).contentType(contentType).build();
        PutObjectPresignRequest presignRequest = PutObjectPresignRequest.builder()
                .signatureDuration(UPLOAD_URL_TTL)
                .putObjectRequest(putRequest)
                .build();
        String url = s3Presigner.presignPutObject(presignRequest).url().toString();
        return new PresignedUpload(url, UPLOAD_URL_TTL.toSeconds());
    }

    // 존재하지 않는 key 면 NoSuchKeyException(RuntimeException)을 그대로 던진다 — 호출부가 처리.
    public HeadObjectResponse headObject(String bucket, String key) {
        return s3Client.headObject(HeadObjectRequest.builder().bucket(bucket).key(key).build());
    }

    public void put(String bucket, String key, byte[] content, String contentType) {
        s3Client.putObject(
                PutObjectRequest.builder().bucket(bucket).key(key).contentType(contentType).build(),
                RequestBody.fromBytes(content));
    }

    public void delete(String bucket, String key) {
        s3Client.deleteObject(DeleteObjectRequest.builder().bucket(bucket).key(key).build());
    }

    // 브라우저가 직접 여는 URL이므로 s3Client의 내부(컨테이너 네트워크) endpoint가 아니라
    // publicEndpoint 기준으로 만든다. prod처럼 endpoint override가 전혀 없으면 AWS 기본
    // virtual-hosted style URL(s3Client.utilities())을 그대로 쓴다.
    public String publicUrl(String bucket, String key) {
        String publicEndpoint = awsProperties.s3().resolvedPublicEndpoint();
        if (StringUtils.hasText(publicEndpoint)) {
            return "%s/%s/%s".formatted(publicEndpoint, bucket, key);
        }
        return s3Client.utilities()
                .getUrl(builder -> builder.bucket(bucket).key(key))
                .toString();
    }

    public String presignedGetUrl(String bucket, String key) {
        GetObjectPresignRequest presignRequest = GetObjectPresignRequest.builder()
                .signatureDuration(DOWNLOAD_URL_TTL)
                .getObjectRequest(builder -> builder.bucket(bucket).key(key))
                .build();
        return s3Presigner.presignGetObject(presignRequest).url().toString();
    }

    public record PresignedUpload(String uploadUrl, long expiresInSeconds) {
    }
}