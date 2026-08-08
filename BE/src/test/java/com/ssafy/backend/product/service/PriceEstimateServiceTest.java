package com.ssafy.backend.product.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.client.dto.PricingEstimateJobRequest;
import com.ssafy.backend.product.dto.request.PriceEstimateRequest;
import com.ssafy.backend.product.dto.response.PriceEstimateJobResponse;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class PriceEstimateServiceTest {

    @Mock
    private AiClient aiClient;

    @Mock
    private GarmentCategoryMapper garmentCategoryMapper;

    private PriceEstimateService priceEstimateService;

    @org.junit.jupiter.api.BeforeEach
    void setUp() {
        priceEstimateService = new PriceEstimateService(aiClient, garmentCategoryMapper);
    }

    @Test
    void 상품_id가_없으면_임시값을_채워_AI에_접수한다() {
        when(garmentCategoryMapper.resolve(1L)).thenReturn(Optional.of("TOP_KNIT"));
        when(aiClient.createPricingEstimateJob(any())).thenReturn("job-1");
        PriceEstimateRequest request =
                new PriceEstimateRequest("빈티지 니트", 1L, "메종키츠네", 82.0, "A", null);

        PriceEstimateJobResponse response = priceEstimateService.createEstimateJob(request);

        assertThat(response.jobId()).isEqualTo("job-1");
        ArgumentCaptor<PricingEstimateJobRequest> captor = ArgumentCaptor.forClass(PricingEstimateJobRequest.class);
        verify(aiClient).createPricingEstimateJob(captor.capture());
        PricingEstimateJobRequest sent = captor.getValue();
        assertThat(sent.productId()).isEqualTo(1L);
        assertThat(sent.productName()).isEqualTo("빈티지 니트");
        assertThat(sent.brand()).isEqualTo("메종키츠네");
        assertThat(sent.category()).isEqualTo("TOP_KNIT");
        assertThat(sent.conditionScore()).isEqualTo(82.0);
        assertThat(sent.conditionGrade()).isEqualTo("A");
    }

    @Test
    void 상품_id가_있으면_그대로_에코해서_보낸다() {
        when(garmentCategoryMapper.resolve(null)).thenReturn(Optional.empty());
        when(aiClient.createPricingEstimateJob(any())).thenReturn("job-2");
        PriceEstimateRequest request = new PriceEstimateRequest("빈티지 니트", null, null, 50.0, "C", 42L);

        priceEstimateService.createEstimateJob(request);

        ArgumentCaptor<PricingEstimateJobRequest> captor = ArgumentCaptor.forClass(PricingEstimateJobRequest.class);
        verify(aiClient).createPricingEstimateJob(captor.capture());
        assertThat(captor.getValue().productId()).isEqualTo(42L);
        assertThat(captor.getValue().category()).isNull();
    }
}
