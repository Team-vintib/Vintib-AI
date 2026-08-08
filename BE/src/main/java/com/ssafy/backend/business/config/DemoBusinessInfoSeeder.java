package com.ssafy.backend.business.config;

import com.ssafy.backend.business.entity.BusinessInfo;
import com.ssafy.backend.business.entity.BusinessVerificationStatus;
import com.ssafy.backend.business.repository.BusinessInfoRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * 데모 사업자 계정 2명의 사업자 인증을 승인 완료 상태로 시드한다. {@code DemoMemberSeeder}
 * ({@code @Order(1)})가 만든 회원이 있어야 하므로 그 이후, 상품/주문/팔로우와는 의존이 없어
 * 같은 {@code @Order(2)}를 쓴다.
 *
 * <p>관리자 승인 API가 아직 없어(BusinessInfo 클래스 설명 참고) {@code submit()} 서비스를 거치지
 * 않고 엔티티를 직접 만들어 {@link BusinessInfo#approve()}까지 바로 호출한다 — 인증서 이미지도
 * 실제 업로드가 필요 없다(제출 시점의 {@code HeadObject} 검증은 {@code submit()} 안에만 있고,
 * 이 시더는 그 경로를 안 탄다).
 */
@Slf4j
@Component
@RequiredArgsConstructor
@Order(2)
public class DemoBusinessInfoSeeder implements ApplicationRunner {

    private record BusinessSeed(String email, String businessNumber, String businessName, String representativeName) {
    }

    private static final List<BusinessSeed> BUSINESS_SEEDS = List.of(
            new BusinessSeed("vintibb1@gmail.com", "123-45-67890", "쓱털어온옷장", "한서윤"),
            new BusinessSeed("vintibb2@gmail.com", "234-56-78901", "구제불능", "정인웅"));

    private final MemberRepository memberRepository;
    private final BusinessInfoRepository businessInfoRepository;

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        BUSINESS_SEEDS.forEach(this::seedApprovedBusinessInfo);
    }

    private void seedApprovedBusinessInfo(BusinessSeed seed) {
        Member member = memberRepository.findByEmail(seed.email()).orElse(null);
        if (member == null) {
            log.warn("사업자 인증 시드 대상 회원이 없다: {}", seed.email());
            return;
        }

        BusinessInfo businessInfo = businessInfoRepository.findById(member.getId()).orElse(null);
        if (businessInfo == null) {
            businessInfo = BusinessInfo.builder()
                    .member(member)
                    .businessNumber(seed.businessNumber())
                    .businessName(seed.businessName())
                    .representativeName(seed.representativeName())
                    .certificateKey("business-certificates/%d/seed-cert.jpg".formatted(member.getId()))
                    .build();
            businessInfo.approve();
            businessInfoRepository.save(businessInfo);
            log.info("시드 사업자 인증 승인: {}", seed.email());
        } else if (businessInfo.getVerificationStatus() != BusinessVerificationStatus.APPROVED) {
            businessInfo.approve();
            log.info("시드 사업자 인증 승인으로 갱신: {}", seed.email());
        }
    }
}
