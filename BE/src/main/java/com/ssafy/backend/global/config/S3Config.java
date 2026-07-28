package com.ssafy.backend.global.config;

import java.net.URI;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.util.StringUtils;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.S3Configuration;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;

/**
 * S3 클라이언트 설정. local 프로필은 endpoint 를 MinIO 로 override 하고,
 * prod 는 endpoint 를 비워 AWS 기본 리졸버를 그대로 쓴다.
 *
 * <p>{@code endpoint} 와 {@code publicEndpoint} 를 분리하는 이유: docker-compose로 백엔드까지
 * 컨테이너로 띄우면 백엔드→MinIO 직접 호출(HeadObject 등)은 컨테이너 네트워크 주소(minio:9000)를
 * 써야 하지만, presigned URL은 브라우저/FE가 직접 여는 것이므로 호스트에 발행된 포트(localhost:9000)를
 * 가리켜야 한다. 하나의 endpoint로 두 역할을 겸하면 presigned URL이 컨테이너 밖에서 열리지 않는다.
 * publicEndpoint를 비워두면 endpoint를 그대로 쓴다(IDE에서 백엔드를 호스트로 직접 띄우는 경우 등
 * 두 주소가 같을 때).
 */
@Configuration
@EnableConfigurationProperties(S3Config.AwsProperties.class)
public class S3Config {

    @ConfigurationProperties(prefix = "aws")
    public record AwsProperties(String region, String accessKey, String secretKey, S3 s3) {
        public record S3(String endpoint, String publicEndpoint, String publicBucket, String privateBucket) {

            public String resolvedPublicEndpoint() {
                return StringUtils.hasText(publicEndpoint) ? publicEndpoint : endpoint;
            }
        }
    }

    @Bean
    public S3Client s3Client(AwsProperties properties) {
        var builder = S3Client.builder()
                .region(Region.of(properties.region()))
                .credentialsProvider(credentialsProvider(properties));
        if (StringUtils.hasText(properties.s3().endpoint())) {
            builder.endpointOverride(URI.create(properties.s3().endpoint()))
                    .serviceConfiguration(pathStyleConfiguration());
        }
        return builder.build();
    }

    @Bean
    public S3Presigner s3Presigner(AwsProperties properties) {
        var builder = S3Presigner.builder()
                .region(Region.of(properties.region()))
                .credentialsProvider(credentialsProvider(properties));
        String publicEndpoint = properties.s3().resolvedPublicEndpoint();
        if (StringUtils.hasText(publicEndpoint)) {
            builder.endpointOverride(URI.create(publicEndpoint)).serviceConfiguration(pathStyleConfiguration());
        }
        return builder.build();
    }

    private StaticCredentialsProvider credentialsProvider(AwsProperties properties) {
        return StaticCredentialsProvider.create(
                AwsBasicCredentials.create(properties.accessKey(), properties.secretKey()));
    }

    // MinIO는 virtual-hosted style URL(https://{bucket}.{endpoint}/...)을 지원하지 않는다 — path style 강제.
    private S3Configuration pathStyleConfiguration() {
        return S3Configuration.builder().pathStyleAccessEnabled(true).build();
    }
}