package com.ssafy.backend.tryon.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.BDDMockito.given;

import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.client.dto.AiJobResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import com.ssafy.backend.tryon.entity.TryOnResult;
import com.ssafy.backend.tryon.entity.TryOnResultStatus;
import com.ssafy.backend.tryon.repository.TryOnResultRepository;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

/**
 * {@code getResults()}/{@code getResult()}의 pending 갱신이 <b>실제로 DB에 저장되는지</b>
 * 검증한다.
 *
 * <p>Mockito 단위 테스트({@link TryOnResultServiceTest})는 리포지토리를 목으로 두므로,
 * Hibernate가 read-only 트랜잭션에서 flush를 건너뛰는 문제(실측으로 발견된 버그의 원인)를
 * 잡아내지 못한다 — 그래서 여기는 실제 DB에 붙는 통합 테스트로 분리했다.
 *
 * <p><b>테스트 자체에 {@code @Transactional}을 걸지 않는다.</b> 걸면 서비스 메서드 호출이 그
 * 바깥 테스트 트랜잭션에 합류해서, 서비스 자신의 readOnly 설정과 무관하게 항상 플러시돼 버려
 * 정작 잡으려던 버그를 놓친다 — {@code @AfterEach}로 직접 정리한다.
 */
@SpringBootTest
class TryOnResultServicePersistenceTest {

    @Autowired
    private TryOnResultService tryOnResultService;

    @Autowired
    private TryOnResultRepository tryOnResultRepository;

    @Autowired
    private MemberRepository memberRepository;

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private CategoryRepository categoryRepository;

    @MockitoBean
    private AiClient aiClient;

    private Member member;
    private Product product;
    private TryOnResult pendingResult;

    @BeforeEach
    void setUp() {
        member = memberRepository.save(Member.builder()
                .email("tryon-persist-" + UUID.randomUUID() + "@example.com")
                .password("encoded")
                .name("시착러")
                .build());
        Long categoryId = categoryRepository.findAll().stream()
                .filter(category -> category.getParentId() != null)
                .map(Category::getId)
                .findFirst()
                .orElseThrow(() -> new IllegalStateException("시드된 소분류 카테고리가 없다"));
        product = productRepository.save(Product.builder()
                .seller(member)
                .categoryId(categoryId)
                .title("테스트 상품")
                .build());
        pendingResult = tryOnResultRepository.save(TryOnResult.builder()
                .member(member)
                .product(product)
                .jobId("test-job-" + UUID.randomUUID())
                .status(TryOnResultStatus.PENDING)
                .build());
    }

    @AfterEach
    void tearDown() {
        tryOnResultRepository.deleteById(pendingResult.getId());
        productRepository.deleteById(product.getId());
        memberRepository.deleteById(member.getId());
    }

    @Test
    void 목록_조회로_완료된_job이_DB에_실제로_저장된다() {
        given(aiClient.getJob(pendingResult.getJobId())).willReturn(new AiJobResponse(
                "success", Map.of("image_url", "https://ai.example/persisted.png"), null));

        tryOnResultService.getResults(member.getId());

        // 별도 조회로 진짜 커밋됐는지 확인한다 — 같은 트랜잭션 안에서만 보이는 상태가 아님을 보장.
        TryOnResult reloaded = tryOnResultRepository.findById(pendingResult.getId()).orElseThrow();
        assertThat(reloaded.getStatus()).isEqualTo(TryOnResultStatus.SUCCESS);
        assertThat(reloaded.getResultImageUrl()).isEqualTo("https://ai.example/persisted.png");
    }
}
