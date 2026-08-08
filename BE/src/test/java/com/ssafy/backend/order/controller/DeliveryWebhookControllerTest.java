package com.ssafy.backend.order.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

import com.ssafy.backend.global.client.DeliveryTrackingClient;
import com.ssafy.backend.order.service.DeliveryWebhookService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;

@ExtendWith(MockitoExtension.class)
class DeliveryWebhookControllerTest {

    @Mock
    private DeliveryWebhookService deliveryWebhookService;

    @Mock
    private DeliveryTrackingClient deliveryTrackingClient;

    @Test
    void 서명_헤더가_모두_없으면_검증없이_200을_반환한다() {
        DeliveryWebhookController controller =
                new DeliveryWebhookController(deliveryWebhookService, deliveryTrackingClient);

        var response = controller.receive(null, null, null);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        verify(deliveryWebhookService, never()).handle(any(), any(), any());
    }
}
