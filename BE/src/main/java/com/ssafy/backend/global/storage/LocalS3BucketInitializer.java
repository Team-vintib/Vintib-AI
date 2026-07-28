package com.ssafy.backend.global.storage;

import com.ssafy.backend.global.config.S3Config.AwsProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.CreateBucketRequest;
import software.amazon.awssdk.services.s3.model.HeadBucketRequest;
import software.amazon.awssdk.services.s3.model.NoSuchBucketException;
import software.amazon.awssdk.services.s3.model.PutBucketPolicyRequest;

// 로컬 MinIO에는 버킷이 미리 없다. AWS 콘솔에서 수동으로 만드는 실제 S3와 달리,
// 로컬은 기동할 때마다 없으면 만들어야 개발자가 매번 손으로 세팅하지 않아도 된다.
@Slf4j
@Component
@Profile("local")
@RequiredArgsConstructor
public class LocalS3BucketInitializer implements ApplicationRunner {

    private final S3Client s3Client;
    private final AwsProperties awsProperties;

    @Override
    public void run(ApplicationArguments args) {
        ensureBucket(awsProperties.s3().privateBucket(), false);
        ensureBucket(awsProperties.s3().publicBucket(), true);
    }

    private void ensureBucket(String bucket, boolean publicRead) {
        if (bucketExists(bucket)) {
            return;
        }
        log.info("MinIO 버킷을 생성합니다: {}", bucket);
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