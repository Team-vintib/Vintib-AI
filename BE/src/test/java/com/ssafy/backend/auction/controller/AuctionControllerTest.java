package com.ssafy.backend.auction.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.ssafy.backend.auth.jwt.JwtTokenProvider;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveProduct;
import com.ssafy.backend.live.repository.LiveProductRepository;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Gender;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.entity.MemberType;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import java.time.LocalDateTime;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.web.FilterChainProxy;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

/**
 * AUCT-001 경매 조건 설정 컨트롤러 테스트.
 *
 * <p>Bean Validation(400)과 인증(401)은 서비스 단위 테스트로는 확인되지 않아 실제 필터 체인을 끼운다.
 * 상품·라이브·연결은 FK 제약이 있어 실제 행을 저장해 두고 시작한다.
 *
 * <p>요청 본문은 {@code ObjectMapper} 없이 직접 만든다 — Spring Boot 4 모듈러 테스트 컨텍스트에는
 * {@code ObjectMapper} 빈이 올라오지 않는다.
 */
@SpringBootTest
class AuctionControllerTest {

    @Autowired
    private WebApplicationContext context;

    @Autowired
    private FilterChainProxy springSecurityFilterChain;

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    @Autowired
    private MemberRepository memberRepository;

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private CategoryRepository categoryRepository;

    @Autowired
    private LiveRepository liveRepository;

    @Autowired
    private LiveProductRepository liveProductRepository;

    private MockMvc mockMvc;
    private String hostToken;
    private Long liveId;
    private Long linkedProductId;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.webAppContextSetup(context)
                .addFilters(springSecurityFilterChain)
                .build();

        String email = "auction-host-" + UUID.randomUUID() + "@example.com";
        Member host = Member.builder()
                .email(email)
                .password("encoded")
                .name("호스트")
                .build();
        // SY019 게이트: 온보딩 미완료 회원은 경매 설정 등 다른 기능을 쓸 수 없다.
        // 닉네임은 unique 제약이 있어 매 테스트마다 겹치지 않게 만든다.
        String nickname = "host-" + UUID.randomUUID().toString().substring(0, 8);
        host.updateBasicInfo(nickname, "01000000000", "서울", "1층", null, Gender.MALE);
        host.completeOnboarding(MemberType.GENERAL);
        host = memberRepository.save(host);
        hostToken = jwtTokenProvider.createAccessToken(host.getId(), email);

        // 카테고리는 필수다(PROD-001). 시드된 마스터에서 아무거나 하나 집는다 — 경매 검증에
        // 카테고리 값 자체는 무관하고, NOT NULL 제약만 만족시키면 된다.
        Product product = productRepository.save(Product.builder()
                .seller(host)
                .categoryId(categoryRepository.findAll().get(0).getId())
                .title("리바이스 501 빈티지")
                .build());
        linkedProductId = product.getId();

        Live live = liveRepository.save(Live.openNow(host, "빈티지 데님 라이브", null, LocalDateTime.now()));
        liveId = live.getId();
        liveProductRepository.save(LiveProduct.link(live, linkedProductId, (short) 0, LocalDateTime.now()));
    }

    private String configRequestBody(Long productId, Long startPrice, Long bidUnit, Integer durationSeconds) {
        return """
                {"productId":%d,"startPrice":%d,"bidUnit":%d,"durationSeconds":%d}
                """.formatted(productId, startPrice, bidUnit, durationSeconds);
    }

    @Test
    void 연결된_상품에_조건을_설정하면_201과_READY를_반환한다() throws Exception {
        mockMvc.perform(post("/api/lives/{liveId}/auctions", liveId)
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(configRequestBody(linkedProductId, 10_000L, 1_000L, 60)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.status").value("READY"))
                .andExpect(jsonPath("$.data.currentPrice").value(0))
                .andExpect(jsonPath("$.error").doesNotExist());
    }

    @Test
    void 증액_단위가_0이면_400을_반환한다() throws Exception {
        mockMvc.perform(post("/api/lives/{liveId}/auctions", liveId)
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(configRequestBody(linkedProductId, 10_000L, 0L, 60)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.success").value(false));
    }

    @Test
    void 진행_시간이_0이면_400을_반환한다() throws Exception {
        mockMvc.perform(post("/api/lives/{liveId}/auctions", liveId)
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(configRequestBody(linkedProductId, 10_000L, 1_000L, 0)))
                .andExpect(status().isBadRequest());
    }

    @Test
    void 라이브에_연결되지_않은_상품이면_404를_반환한다() throws Exception {
        long 연결되지_않은_상품 = linkedProductId + 999_999L;

        mockMvc.perform(post("/api/lives/{liveId}/auctions", liveId)
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(configRequestBody(연결되지_않은_상품, 10_000L, 1_000L, 60)))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("L006"));
    }

    @Test
    void 미인증이면_401을_반환한다() throws Exception {
        mockMvc.perform(post("/api/lives/{liveId}/auctions", liveId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(configRequestBody(linkedProductId, 10_000L, 1_000L, 60)))
                .andExpect(status().isUnauthorized());
    }
}