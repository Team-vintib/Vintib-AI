package com.ssafy.backend.home.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.ssafy.backend.auth.jwt.JwtTokenProvider;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.entity.MemberType;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import com.ssafy.backend.social.entity.Follow;
import com.ssafy.backend.social.repository.FollowRepository;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.web.FilterChainProxy;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

/**
 * HOME-002 팔로잉 콘텐츠 조회 컨트롤러 테스트.
 *
 * <p>{@code followedSellers}·{@code products}가 SY024에서 실데이터로 바뀌어, 고정 memberId(1L)로
 * 토큰만 발급하던 이전 방식 대신 매 테스트가 회원/팔로우/상품을 직접 시드하고 그 ID로 토큰을 발급한다
 * (DB가 테스트 간 초기화되지 않아 ID를 하드코딩할 수 없다 — {@code ProductQueryAdapterTest}와 동일한 관례).
 */
@SpringBootTest
class FollowingControllerTest {

    @Autowired
    private WebApplicationContext context;

    @Autowired
    private FilterChainProxy springSecurityFilterChain;

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    @Autowired
    private MemberRepository memberRepository;

    @Autowired
    private FollowRepository followRepository;

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private CategoryRepository categoryRepository;

    private MockMvc mockMvc;
    private Member viewer;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.webAppContextSetup(context)
                .addFilters(springSecurityFilterChain)
                .build();
        viewer = Member.builder()
                .email("following-viewer-" + UUID.randomUUID() + "@example.com")
                .password("encoded")
                .name("조회자")
                .build();
        // /api/home/following은 OnboardingRequiredFilter 화이트리스트에 없어 온보딩 미완료 회원은
        // 403(ONBOARDING_REQUIRED)로 막힌다 — 테스트 회원도 실제 흐름과 같이 온보딩을 완료시켜 둔다.
        viewer.completeOnboarding(MemberType.GENERAL);
        viewer = memberRepository.save(viewer);
    }

    private String tokenFor(Member member) {
        return jwtTokenProvider.createAccessToken(member.getId(), member.getEmail());
    }

    private Member 판매자_생성() {
        return memberRepository.save(Member.builder()
                .email("following-seller-" + UUID.randomUUID() + "@example.com")
                .password("encoded")
                .name("판매자")
                .build());
    }

    @Test
    void 미인증이면_401을_반환한다() throws Exception {
        mockMvc.perform(get("/api/home/following"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void 팔로우가_없으면_빈_콘텐츠를_반환한다() throws Exception {
        mockMvc.perform(get("/api/home/following").header("Authorization", "Bearer " + tokenFor(viewer)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.empty").value(true))
                .andExpect(jsonPath("$.data.lives").isArray())
                .andExpect(jsonPath("$.data.products").isArray())
                .andExpect(jsonPath("$.data.followedSellers").isArray())
                .andExpect(jsonPath("$.data.followedSellers").isEmpty())
                .andExpect(jsonPath("$.error").doesNotExist());
    }

    @Test
    void 팔로우한_판매자와_그_상품이_실데이터로_채워진다() throws Exception {
        Member seller = 판매자_생성();
        followRepository.save(Follow.builder().follower(viewer).following(seller).build());

        Long categoryId = categoryRepository.findAll().get(0).getId();
        Product product = productRepository.save(
                Product.builder().seller(seller).categoryId(categoryId).title("팔로우한 판매자의 상품").build());
        product.registerDirectSale(50000L);
        productRepository.save(product);

        mockMvc.perform(get("/api/home/following").header("Authorization", "Bearer " + tokenFor(viewer)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.empty").value(false))
                .andExpect(jsonPath("$.data.followedSellers[0].sellerId").value(seller.getId()))
                .andExpect(jsonPath("$.data.followedSellers[0].followerCount").value(1))
                .andExpect(jsonPath("$.data.followedSellers[0].productCount").value(1))
                .andExpect(jsonPath("$.data.products[0].productId").value(product.getId()))
                .andExpect(jsonPath("$.data.products[0].sellType").value("NORMAL"))
                .andExpect(jsonPath("$.data.products[0].sellStatus").value("ON_SALE"))
                .andExpect(jsonPath("$.data.products[0].price").value(50000));
    }

    @Test
    void 라이브_섹션은_실데이터_연동_전이라_항상_비어있다() throws Exception {
        Member seller = 판매자_생성();
        followRepository.save(Follow.builder().follower(viewer).following(seller).build());

        mockMvc.perform(get("/api/home/following").header("Authorization", "Bearer " + tokenFor(viewer)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.lives").isArray())
                .andExpect(jsonPath("$.data.lives").isEmpty());
    }
}
