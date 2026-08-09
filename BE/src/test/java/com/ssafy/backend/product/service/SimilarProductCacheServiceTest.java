package com.ssafy.backend.product.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.client.dto.SimilarProductAiResponse;
import com.ssafy.backend.product.entity.SimilarProductCandidate;
import com.ssafy.backend.product.repository.SimilarProductCandidateRepository;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.client.RestClientException;

/**
 * {@link SimilarProductCacheService} 단위 테스트(CH034). AI 호출 실패가 예외로 새지 않는 것과
 * (배치가 상품 하나 때문에 멈추면 안 된다), 저장되는 rank/score가 AI 응답 순서 그대로인지 본다.
 */
@ExtendWith(MockitoExtension.class)
class SimilarProductCacheServiceTest {

    @Mock
    private AiClient aiClient;

    @Mock
    private SimilarProductCandidateRepository candidateRepository;

    private SimilarProductCacheService cacheService;

    private void setUp() {
        cacheService = new SimilarProductCacheService(aiClient, candidateRepository);
    }

    @Test
    void AI_응답을_순위_그대로_후보로_저장한다() {
        setUp();
        SimilarProductAiResponse response = new SimilarProductAiResponse(
                1L,
                List.of(
                        new SimilarProductAiResponse.Item(2L, 0.9),
                        new SimilarProductAiResponse.Item(3L, 0.8)));
        when(aiClient.getSimilarProducts(1L, SimilarProductCacheService.CANDIDATE_K)).thenReturn(response);

        cacheService.refreshCache(1L);

        verify(candidateRepository).deleteByProductId(1L);
        ArgumentCaptor<List<SimilarProductCandidate>> captor = ArgumentCaptor.forClass(List.class);
        verify(candidateRepository).saveAll(captor.capture());
        List<SimilarProductCandidate> saved = captor.getValue();
        assertThat(saved).hasSize(2);
        assertThat(saved.get(0).getSimilarProductId()).isEqualTo(2L);
        assertThat(saved.get(0).getRank()).isEqualTo(0);
        assertThat(saved.get(0).getScore()).isEqualTo(0.9);
        assertThat(saved.get(1).getSimilarProductId()).isEqualTo(3L);
        assertThat(saved.get(1).getRank()).isEqualTo(1);
    }

    @Test
    void AI_호출이_실패해도_예외를_던지지_않는다() {
        setUp();
        when(aiClient.getSimilarProducts(1L, SimilarProductCacheService.CANDIDATE_K))
                .thenThrow(new RestClientException("connection refused"));

        assertThatCode(() -> cacheService.refreshCache(1L)).doesNotThrowAnyException();

        verify(candidateRepository, never()).deleteByProductId(1L);
        verify(candidateRepository, never()).saveAll(anyList());
    }

    @Test
    void 임베딩이_없어_빈_목록이면_기존_캐시만_지우고_새로_저장하지_않는다() {
        setUp();
        SimilarProductAiResponse response = new SimilarProductAiResponse(1L, List.of());
        when(aiClient.getSimilarProducts(1L, SimilarProductCacheService.CANDIDATE_K)).thenReturn(response);

        cacheService.refreshCache(1L);

        verify(candidateRepository).deleteByProductId(1L);
        verify(candidateRepository, never()).saveAll(anyList());
    }
}
