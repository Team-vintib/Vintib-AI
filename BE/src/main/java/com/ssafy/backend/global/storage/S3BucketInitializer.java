package com.ssafy.backend.global.storage;

import com.ssafy.backend.global.config.S3Config.AwsProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.CreateBucketRequest;
import software.amazon.awssdk.services.s3.model.HeadBucketRequest;
import software.amazon.awssdk.services.s3.model.NoSuchBucketException;
import software.amazon.awssdk.services.s3.model.PutBucketPolicyRequest;

/**
 * 기동 시 버킷이 없으면 만들고, public 버킷에 익명 읽기 정책을 적용한다.
 *
 * <p>실행 조건이 프로필이 아니라 {@code aws.s3.endpoint} 설정 여부인 이유: 로컬뿐 아니라
 * 운영도 자체 호스팅 MinIO 를 쓰기 때문이다(팀에 AWS 계정이 없다 — 계획 JY006).
 * endpoint 가 비어 있다는 건 실제 AWS S3 를 본다는 뜻이고, 그때는 버킷·정책을 콘솔에서
 * 관리해야 하므로 애플리케이션이 건드리면 안 된다 — 그 경우 아무것도 하지 않는다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class S3BucketInitializer implements ApplicationRunner {

    private final S3Client s3Client;
    private final AwsProperties awsProperties;

    @Override
    public void run(ApplicationArguments args) {
        if (!StringUtils.hasText(awsProperties.s3().endpoint())) {
            return;
        }
        ensureBucket(awsProperties.s3().privateBucket(), false);
        ensureBucket(awsProperties.s3().publicBucket(), true);
    }

    private void ensureBucket(String bucket, boolean publicRead) {
        if (bucketExists(bucket)) {
            return;
        }
        log.info("오브젝트 스토리지 버킷을 생성합니다: {}", bucket);
        s3Client.createBucket(CreateBucketRequest.builder().bucket(bucket).build());
        if (publicRead) {
            s3Client.putBucketPolicy(PutBucketPolicyRequest.builder()
                    .bucket(bucket)
                    .policy(publicReadPolicy(bucket))
                    .build());
        }
    }

    private boolean bucketExists(String bucket) {
        try {
            s3Client.headBucket(HeadBucketRequest.builder().bucket(bucket).build());
            return true;
        } catch (NoSuchBucketException e) {
            return false;
        }
    }

    private String publicReadPolicy(String bucket) {
        return """
                {
                  "Version": "2012-10-17",
                  "Statement": [{
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": "arn:aws:s3:::%s/*"
                  }]
                }
                """.formatted(bucket);
    }
}
