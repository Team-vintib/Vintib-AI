package com.ssafy.backend.product.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.client.dto.AiJobResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.product.dto.response.ProductAiModelCutResponse;
import com.ssafy.backend.product.entity.AiModelCutStatus;
import com.ssafy.backend.product.entity.AiModelGender;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.ProductRepository;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ProductAiJobStatusServiceTest {

    @Mock
    private ProductRepository productRepository;

    @Mock
    private AiClient aiClient;

    @Mock
    private Member seller;

    private ProductAiJobStatusService productAiJobStatusService;

    @BeforeEach
    void setUp() {
        productAiJobStatusService = new ProductAiJobStatusService(productRepository, aiClient);
    }

    @Test
    void PENDING_상태의_착용컷_조회시_AI가_완료를_돌려주면_COMPLETED로_갱신된다() {
        Product product = Product.builder()
                .seller(seller)
                .title("빈티지 자켓")
                .aiModelEnabled(true)
                .aiModelGender(AiModelGender.MALE)
                .build();
        product.startAiModelCutJob("job-123");
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));
        when(aiClient.getJob("job-123")).thenReturn(new AiJobResponse(
                "success", Map.of("image_url", "https://ai.example/result.png"), null));

        ProductAiModelCutResponse response = productAiJobStatusService.getAiModelCutStatus(1L);

        assertThat(response.status()).isEqualTo(AiModelCutStatus.COMPLETED);
        assertThat(response.imageUrl()).isEqualTo("https://ai.example/result.png");
    }

    @Test
    void NONE_상태의_착용컷은_AI를_조회하지_않고_그대로_반환한다() {
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductAiModelCutResponse response = productAiJobStatusService.getAiModelCutStatus(1L);

        assertThat(response.status()).isEqualTo(AiModelCutStatus.NONE);
        verify(aiClient, never()).getJob(any());
    }
}
