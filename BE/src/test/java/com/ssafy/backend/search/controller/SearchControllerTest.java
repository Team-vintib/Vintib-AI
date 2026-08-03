package com.ssafy.backend.search.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.ssafy.backend.auth.jwt.JwtTokenProvider;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
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
import org.springframework.security.web.FilterChainProxy;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

/**
 * SEARCH-001/002 통합 검색 테스트.
 *
 * <p>검색어를 <b>이 테스트에서만 쓰는 고유 문자열</b>로 만든다 — 로컬 DB에는 다른 테스트가 남긴
 * 행이 쌓여 있어, 흔한 단어로 찾으면 무엇이 잡혔는지 단정할 수 없다.
 */
@SpringBootTest
class SearchControllerTest {

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

    private MockMvc mockMvc;
    private String keyword;
    private Member seller;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.webAppContextSetup(context)
                .addFilters(springSecurityFilterChain)
                .build();

        keyword = "zzsearch" + UUID.randomUUID().toString().substring(0, 8);

        seller = Member.builder()
                .email("search-" + UUID.randomUUID() + "@example.com")
                .password("encoded")
                .name("판매자")
                .build();
        seller.updateBasicInfo(keyword + "셀러", "01000000000", "서울", "1층", null, Gender.MALE);
        seller.completeOnboarding(MemberType.GENERAL);
        seller = memberRepository.save(seller);

        Product product = Product.builder()
                .seller(seller)
                .categoryId(categoryRepository.findAll().get(0).getId())
                .title(keyword + " 데님 자켓")
                .build();
        product.registerDirectSale(45_000L);
        productRepository.save(product);

        liveRepository.save(Live.openNow(seller, keyword + " 라이브", null, null, LocalDateTime.now()));
    }

    @Test
    void 검색어로_상품_라이브_회원을_한_번에_찾는다() throws Exception {
        mockMvc.perform(get("/api/search").param("keyword", keyword))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.products.content.length()").value(1))
                .andExpect(jsonPath("$.data.lives.content.length()").value(1))
                .andExpect(jsonPath("$.data.users.content.length()").value(1));
    }

    @Test
    void 조회하지_않은_섹션은_null로_내려간다() throws Exception {
        // 빈 배열은 "0건", null 은 "조회하지 않음" — FE 가 둘을 구분해야 한다.
        mockMvc.perform(get("/api/search").param("keyword", keyword).param("type", "PRODUCT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.products").exists())
                .andExpect(jsonPath("$.data.lives").doesNotExist())
                .andExpect(jsonPath("$.data.users").doesNotExist());
    }

    @Test
    void 결과가_없으면_빈_배열이지_null이_아니다() throws Exception {
        mockMvc.perform(get("/api/search").param("keyword", "zz없는검색어" + UUID.randomUUID()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.products.content").isEmpty())
                .andExpect(jsonPath("$.data.products.totalElements").value(0));
    }

    @Test
    void 종료된_방송은_검색되지_않는다() throws Exception {
        Live 종료된_방송 = liveRepository.save(
                Live.openNow(seller, keyword + " 끝난 방송", null, null, LocalDateTime.now()));
        종료된_방송.transitionTo(LiveStatus.ENDED, LocalDateTime.now());
        liveRepository.save(종료된_방송);

        mockMvc.perform(get("/api/search").param("keyword", keyword).param("type", "LIVE"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.lives.content.length()").value(1));
    }

    @Test
    void 가격_범위_필터가_상품에_적용된다() throws Exception {
        mockMvc.perform(get("/api/search")
                        .param("keyword", keyword)
                        .param("type", "PRODUCT")
                        .param("minPrice", "50000"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.products.content").isEmpty());
    }

    @Test
    void 비회원_요청이면_찜_팔로우_여부가_null로_내려간다() throws Exception {
        mockMvc.perform(get("/api/search").param("keyword", keyword))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.products.content[0].isWished").doesNotExist())
                .andExpect(jsonPath("$.data.users.content[0].isFollowing").doesNotExist());
    }

    @Test
    void 로그인_요청이면_찜_팔로우_여부가_채워진다() throws Exception {
        String token = jwtTokenProvider.createAccessToken(seller.getId(), seller.getEmail());

        mockMvc.perform(get("/api/search").param("keyword", keyword)
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.products.content[0].isWished").isBoolean())
                .andExpect(jsonPath("$.data.users.content[0].isFollowing").isBoolean());
    }

    @Test
    void 검색어가_비면_400이다() throws Exception {
        mockMvc.perform(get("/api/search").param("keyword", "  "))
                .andExpect(status().isBadRequest());
    }
}
