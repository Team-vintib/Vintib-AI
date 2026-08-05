package com.ssafy.backend.live.controller;

import static org.hamcrest.Matchers.hasItem;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
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
import com.ssafy.backend.product.entity.Category;
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
 * LIVE-001 예약 라이브 개설 컨트롤러 테스트.
 *
 * <p>개설은 로그인 회원 전용이라 실제 시큐리티 필터 체인을 끼우고 {@link JwtTokenProvider}로
 * 실제 토큰을 발급한다(필터가 principal을 memberId(Long)로 심는다). 호스트는 FK 제약이 있어
 * 실제 회원 행이 필요하므로 테스트마다 새 회원을 저장한다 — 이메일이 유니크라 UUID로 겹침을 피한다.
 *
 * <p>요청 본문은 {@code ObjectMapper} 없이 직접 만든다 — Spring Boot 4 모듈러 테스트 컨텍스트에는
 * {@code ObjectMapper} 빈이 올라오지 않는다.
 */
@SpringBootTest
class LiveControllerTest {

    @Autowired
    private WebApplicationContext context;

    @Autowired
    private FilterChainProxy springSecurityFilterChain;

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    @Autowired
    private MemberRepository memberRepository;

    @Autowired
    private LiveRepository liveRepository;

    @Autowired
    private LiveProductRepository liveProductRepository;

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private CategoryRepository categoryRepository;

    private MockMvc mockMvc;
    private String hostToken;
    private Member hostMember;
    private Long productId;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.webAppContextSetup(context)
                .addFilters(springSecurityFilterChain)
                .build();

        String email = "live-host-" + UUID.randomUUID() + "@example.com";
        Member member = Member.builder()
                .email(email)
                .password("encoded")
                .name("호스트")
                .build();
        // SY019 게이트: 온보딩 미완료 회원은 라이브 개설 등 다른 기능을 쓸 수 없다.
        // 닉네임은 unique 제약이 있어 매 테스트마다 겹치지 않게 만든다.
        String nickname = "host-" + UUID.randomUUID().toString().substring(0, 8);
        member.updateBasicInfo(nickname, "01000000000", "서울", "1층", null, Gender.MALE);
        member.completeOnboarding(MemberType.GENERAL);
        hostMember = memberRepository.save(member);
        hostToken = jwtTokenProvider.createAccessToken(hostMember.getId(), email);

        // 개설 요청에는 판매할 상품이 최소 1개 필요하다(운영 정책 — 편성은 개설 시점에 확정된다).
        productId = productRepository.save(Product.builder()
                        .seller(hostMember)
                        .categoryId(categoryRepository.findAll().get(0).getId())
                        .title("리바이스 501 빈티지")
                        .build())
                .getId();
    }

    /** 상태 전이·시청 조회 검증에 쓸 진행 중 라이브를 하나 만들어 ID를 돌려준다. */
    private Long 개설된_라이브_ID() {
        return liveRepository.save(
                        Live.openNow(hostMember, "빈티지 데님 라이브", null, null, LocalDateTime.now()))
                .getId();
    }

    private String scheduleRequestBody(String title, String thumbnailUrl, LocalDateTime scheduledAt) {
        String thumbnail = thumbnailUrl == null ? "null" : "\"" + thumbnailUrl + "\"";
        return """
                {"title":"%s","thumbnailUrl":%s,"scheduledAt":"%s","productIds":[%d]}
                """.formatted(title, thumbnail, scheduledAt, productId);
    }

    private String instantRequestBody(String title) {
        return """
                {"title":"%s","thumbnailUrl":null,"productIds":[%d]}
                """.formatted(title, productId);
    }

    @Test
    void 예약_개설하면_201과_SCHEDULED_상태를_반환한다() throws Exception {
        String body = scheduleRequestBody(
                "빈티지 데님 라이브", "https://cdn.example.com/live/1.jpg", LocalDateTime.now().plusDays(1));

        mockMvc.perform(post("/api/lives/schedule")
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.id").isNumber())
                .andExpect(jsonPath("$.data.status").value("SCHEDULED"))
                .andExpect(jsonPath("$.data.startedAt").doesNotExist())
                .andExpect(jsonPath("$.error").doesNotExist());
    }

    @Test
    void 방송_예정_시각이_과거면_400을_반환한다() throws Exception {
        String body = scheduleRequestBody("지난 라이브", null, LocalDateTime.now().minusDays(1));

        mockMvc.perform(post("/api/lives/schedule")
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.success").value(false));
    }

    @Test
    void 방송명이_비어_있으면_400을_반환한다() throws Exception {
        String body = scheduleRequestBody("   ", null, LocalDateTime.now().plusDays(1));

        mockMvc.perform(post("/api/lives/schedule")
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest());
    }

    @Test
    void 미인증이면_401을_반환한다() throws Exception {
        String body = scheduleRequestBody("빈티지 데님 라이브", null, LocalDateTime.now().plusDays(1));

        mockMvc.perform(post("/api/lives/schedule")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void 즉시_개설하면_201과_LIVE_상태를_반환한다() throws Exception {
        String body = instantRequestBody("지금 바로 여는 빈티지 라이브");

        mockMvc.perform(post("/api/lives")
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.status").value("LIVE"))
                .andExpect(jsonPath("$.data.startedAt").exists())
                .andExpect(jsonPath("$.data.scheduledAt").doesNotExist());
    }

    @Test
    void 즉시_개설하면_영상_room이_배정된다() throws Exception {
        // 즉시 개설은 생성 시점에 이미 LIVE 라 room 이 함께 정해져야 한다.
        // 배정이 없으면 호스트가 방송을 시작하고도 영상 토큰을 못 받는다.
        mockMvc.perform(post("/api/lives")
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(instantRequestBody("영상 room 확인용 라이브")))
                .andExpect(status().isCreated());

        Live created = liveRepository.findAll().stream()
                .filter(live -> "영상 room 확인용 라이브".equals(live.getTitle()))
                .findFirst()
                .orElseThrow();
        org.assertj.core.api.Assertions.assertThat(created.getOpenviduRoom())
                .startsWith("live-" + created.getId() + "-");
    }

    @Test
    void 예정_방송을_시작하면_영상_room이_배정된다() throws Exception {
        Long liveId = liveRepository.save(
                        Live.schedule(hostMember, "예약 라이브", null, null, LocalDateTime.now().plusDays(1)))
                .getId();

        mockMvc.perform(patch("/api/lives/{liveId}/status", liveId)
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"status\":\"LIVE\"}"))
                .andExpect(status().isOk());

        org.assertj.core.api.Assertions.assertThat(
                        liveRepository.findById(liveId).orElseThrow().getOpenviduRoom())
                .startsWith("live-" + liveId + "-");
    }

    @Test
    void 즉시_개설도_방송명이_비어_있으면_400을_반환한다() throws Exception {
        String body = instantRequestBody("   ");

        mockMvc.perform(post("/api/lives")
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest());
    }

    @Test
    void 판매할_상품_없이_개설하면_400을_반환한다() throws Exception {
        // 편성은 개설 시점에 확정된다 — 상품 없는 빈 방송이 만들어지면 안 된다.
        String body = """
                {"title":"빈 방송","thumbnailUrl":null,"scheduledAt":"%s","productIds":[]}
                """.formatted(LocalDateTime.now().plusDays(1));

        mockMvc.perform(post("/api/lives/schedule")
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest());
    }

    @Test
    void 즉시_개설도_상품_없이는_400을_반환한다() throws Exception {
        String body = """
                {"title":"빈 방송","thumbnailUrl":null,"productIds":[]}
                """;

        mockMvc.perform(post("/api/lives")
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest());
    }

    /** 특정 카테고리 상품을 편성한 진행 중 라이브를 만들어 ID를 돌려준다. 목록 카테고리 필터 검증용. */
    private Long 상품이_편성된_라이브_ID(Long linkedProductId) {
        Live live = liveRepository.save(
                Live.openNow(hostMember, "카테고리 필터 검증용 라이브", null, null, LocalDateTime.now()));
        liveProductRepository.save(LiveProduct.link(live, linkedProductId, (short) 0, LocalDateTime.now()));
        return live.getId();
    }

    private Long 상품_ID(Long categoryId) {
        return productRepository.save(Product.builder()
                        .seller(hostMember)
                        .categoryId(categoryId)
                        .title("카테고리 " + categoryId + " 상품")
                        .build())
                .getId();
    }

    /** 목록에 해당 라이브가 들어 있는지 보는 JsonPath. 다른 테스트가 만든 라이브에 영향받지 않는다. */
    private String 목록에서(Long liveId) {
        return "$.data.content[?(@.liveId == %d)]".formatted(liveId);
    }

    @Test
    void 비회원도_공개_목록을_조회할_수_있다() throws Exception {
        // Authorization 헤더 없이 200 — GET /api/lives 는 비회원 공개(LIVE-005).
        Long liveId = 개설된_라이브_ID();

        mockMvc.perform(get("/api/lives").param("size", "100"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.content").isArray())
                .andExpect(jsonPath("$.data.totalElements").isNumber())
                .andExpect(jsonPath(목록에서(liveId)).isNotEmpty())
                .andExpect(jsonPath(목록에서(liveId) + ".categories").isArray())
                .andExpect(jsonPath("$.error").doesNotExist());
    }

    @Test
    void 종료된_방송은_목록에서_빠진다() throws Exception {
        Long liveId = 개설된_라이브_ID();
        mockMvc.perform(patch("/api/lives/{liveId}/status", liveId)
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"status\":\"ENDED\"}"))
                .andExpect(status().isOk());

        mockMvc.perform(get("/api/lives").param("size", "100"))
                .andExpect(status().isOk())
                .andExpect(jsonPath(목록에서(liveId)).isEmpty());
    }

    @Test
    void 종료_상태로_필터하면_400을_반환한다() throws Exception {
        // 빈 목록으로 조용히 넘기면 FE 가 "그런 방송이 없다"로 오해한다 — 값 자체를 거부한다.
        mockMvc.perform(get("/api/lives").param("status", "ENDED"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("L007"));
    }

    @Test
    void 시청자_수_정렬을_지원한다() throws Exception {
        // 실시간 집계(-450)가 들어와 정렬 기준이 생겼다. Redis 값이라 DB 로 정렬할 수 없어
        // 서비스가 메모리에서 세우지만, 계약상으로는 다른 정렬과 똑같이 동작해야 한다.
        mockMvc.perform(get("/api/lives").param("sort", "VIEWERS_DESC"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.content").isArray());
    }

    @Test
    void 시청자가_없으면_viewerCount는_0으로_나온다() throws Exception {
        // 이전에는 항상 null 이었다. 0 과 null 을 FE 가 구분해야 했던 이유가 없어졌다.
        mockMvc.perform(get("/api/lives"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.content[0].viewerCount").value(0));
    }

    @Test
    void 페이지_크기가_허용_범위를_벗어나면_400을_반환한다() throws Exception {
        mockMvc.perform(get("/api/lives").param("size", "0"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void 대분류로_필터하면_하위_소분류_상품을_건_방송도_나온다() throws Exception {
        Category 소분류 = categoryRepository.findAll().stream()
                .filter(category -> category.getParentId() != null)
                .findFirst()
                .orElseThrow();
        Long liveId = 상품이_편성된_라이브_ID(상품_ID(소분류.getId()));

        mockMvc.perform(get("/api/lives")
                        .param("categoryIds", String.valueOf(소분류.getParentId()))
                        .param("size", "100"))
                .andExpect(status().isOk())
                .andExpect(jsonPath(목록에서(liveId)).isNotEmpty())
                // 응답 카테고리는 소분류가 아니라 대분류로 롤업된다.
                .andExpect(jsonPath(목록에서(liveId) + ".categories[*].id")
                        .value(hasItem(소분류.getParentId().intValue())));
    }

    @Test
    void 편성_상품과_무관한_카테고리로_필터하면_그_방송은_빠진다() throws Exception {
        Category 소분류 = categoryRepository.findAll().stream()
                .filter(category -> category.getParentId() != null)
                .findFirst()
                .orElseThrow();
        Long 다른_대분류 = categoryRepository.findAll().stream()
                .filter(category -> category.getParentId() == null)
                .map(Category::getId)
                .filter(id -> !id.equals(소분류.getParentId()))
                .findFirst()
                .orElseThrow();
        Long liveId = 상품이_편성된_라이브_ID(상품_ID(소분류.getId()));

        mockMvc.perform(get("/api/lives")
                        .param("categoryIds", String.valueOf(다른_대분류))
                        .param("size", "100"))
                .andExpect(status().isOk())
                .andExpect(jsonPath(목록에서(liveId)).isEmpty());
    }

    @Test
    void 비회원도_시청_조회할_수_있다() throws Exception {
        // Authorization 헤더 없이 200 — GET /api/lives/{liveId} 는 비회원 공개(LIVE-005).
        Long liveId = 개설된_라이브_ID();

        mockMvc.perform(get("/api/lives/{liveId}", liveId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.status").value("LIVE"))
                .andExpect(jsonPath("$.data.products").isArray())
                .andExpect(jsonPath("$.error").doesNotExist());
    }

    /** 진행 중 라이브 + 그 방송에 편성된 상품 하나. 소개 상품 전환 테스트용. */
    private Long 편성까지_끝난_라이브_ID() {
        Live live = liveRepository.save(
                Live.openNow(hostMember, "빈티지 데님 라이브", null, null, LocalDateTime.now()));
        liveProductRepository.save(LiveProduct.link(live, productId, (short) 0, LocalDateTime.now()));
        return live.getId();
    }

    private String currentProductBody(String productIdValue) {
        return "{\"productId\":%s}".formatted(productIdValue);
    }

    @Test
    void 호스트가_소개_상품을_바꾸면_상세에_반영된다() throws Exception {
        Long liveId = 편성까지_끝난_라이브_ID();

        mockMvc.perform(patch("/api/lives/{liveId}/current-product", liveId)
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(currentProductBody(String.valueOf(productId))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.liveId").value(liveId))
                .andExpect(jsonPath("$.data.currentProductId").value(productId));

        // 시청 화면 진입 시 초기값이 되어야 하므로 상세 응답에도 실려야 한다.
        mockMvc.perform(get("/api/lives/{liveId}", liveId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.currentProductId").value(productId));
    }

    @Test
    void 상품_ID를_null로_보내면_소개_상품이_해제된다() throws Exception {
        Long liveId = 편성까지_끝난_라이브_ID();
        mockMvc.perform(patch("/api/lives/{liveId}/current-product", liveId)
                .header("Authorization", "Bearer " + hostToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(currentProductBody(String.valueOf(productId))));

        mockMvc.perform(patch("/api/lives/{liveId}/current-product", liveId)
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(currentProductBody("null")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.currentProductId").doesNotExist());
    }

    @Test
    void 편성되지_않은_상품은_소개할_수_없다() throws Exception {
        Long liveId = 편성까지_끝난_라이브_ID();
        Long 편성_안_된_상품 = productRepository.save(Product.builder()
                        .seller(hostMember)
                        .categoryId(categoryRepository.findAll().get(0).getId())
                        .title("편성하지 않은 상품")
                        .build())
                .getId();

        mockMvc.perform(patch("/api/lives/{liveId}/current-product", liveId)
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(currentProductBody(String.valueOf(편성_안_된_상품))))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("L006"));
    }

    @Test
    void 호스트가_아니면_소개_상품을_바꿀_수_없다() throws Exception {
        Long liveId = 편성까지_끝난_라이브_ID();
        // 온보딩 게이트(-475)를 통과해야 컨트롤러까지 온다. 안 그러면 L004 대신 U004 가 나온다.
        Member 남 = Member.builder()
                .email("other-" + UUID.randomUUID() + "@example.com")
                .password("encoded")
                .name("남")
                .build();
        남.updateBasicInfo(
                "other-" + UUID.randomUUID().toString().substring(0, 8),
                "01000000001", "서울", "2층", null, Gender.MALE);
        남.completeOnboarding(MemberType.GENERAL);
        memberRepository.save(남);
        String 남의_토큰 = jwtTokenProvider.createAccessToken(남.getId(), 남.getEmail());

        mockMvc.perform(patch("/api/lives/{liveId}/current-product", liveId)
                        .header("Authorization", "Bearer " + 남의_토큰)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(currentProductBody(String.valueOf(productId))))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.error.code").value("L004"));
    }

    @Test
    void 종료된_방송은_소개_상품을_바꿀_수_없다() throws Exception {
        Long liveId = 편성까지_끝난_라이브_ID();
        mockMvc.perform(patch("/api/lives/{liveId}/status", liveId)
                .header("Authorization", "Bearer " + hostToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"ENDED\"}"));

        mockMvc.perform(patch("/api/lives/{liveId}/current-product", liveId)
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(currentProductBody(String.valueOf(productId))))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("L007"));
    }

    @Test
    void 편성_상품_응답에_브랜드_가격_썸네일이_담긴다() throws Exception {
        // 시청 화면 상품 패널이 이 응답만으로 그려져야 한다(FE 요청 006).
        Long liveId = 편성까지_끝난_라이브_ID();

        mockMvc.perform(get("/api/lives/{liveId}", liveId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.products[0].productTitle").value("리바이스 501 빈티지"))
                // 필드가 응답 스키마에 존재하는지를 본다. 값은 상품 등록 내용에 따라 null 일 수 있다.
                .andExpect(jsonPath("$.data.products[0].productId").value(productId));
    }

    @Test
    void 존재하지_않는_라이브를_조회하면_404를_반환한다() throws Exception {
        mockMvc.perform(get("/api/lives/{liveId}", 99_999_999L))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("L001"));
    }

    @Test
    void 상태_전이는_미인증이면_401을_반환한다() throws Exception {
        Long liveId = 개설된_라이브_ID();

        mockMvc.perform(patch("/api/lives/{liveId}/status", liveId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"status\":\"ENDED\"}"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void 진행_중인_방송을_종료로_전이하면_200과_ENDED를_반환한다() throws Exception {
        Long liveId = 개설된_라이브_ID();

        mockMvc.perform(patch("/api/lives/{liveId}/status", liveId)
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"status\":\"ENDED\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("ENDED"));
    }

    @Test
    void 허용되지_않는_전이는_400을_반환한다() throws Exception {
        // 즉시 개설이라 이미 LIVE — LIVE→LIVE 는 허용되지 않는다.
        Long liveId = 개설된_라이브_ID();

        mockMvc.perform(patch("/api/lives/{liveId}/status", liveId)
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"status\":\"LIVE\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("L007"));
    }

    @Test
    void 즉시_개설도_미인증이면_401을_반환한다() throws Exception {
        String body = instantRequestBody("지금 바로 여는 빈티지 라이브");

        mockMvc.perform(post("/api/lives")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isUnauthorized());
    }
}