package com.ssafy.backend.live.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.tuple;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.live.dto.request.LiveProductLinkRequest;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveProduct;
import com.ssafy.backend.live.port.ProductQueryPort;
import com.ssafy.backend.live.port.ProductQueryPort.ProductSummary;
import com.ssafy.backend.live.repository.LiveProductRepository;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class LiveProductServiceTest {

    private static final Long HOST_ID = 1L;
    private static final Long OTHER_MEMBER_ID = 2L;
    private static final Long LIVE_ID = 101L;
    private static final Long PRODUCT_ID = 2001L;

    @Mock
    private LiveRepository liveRepository;

    @Mock
    private LiveProductRepository liveProductRepository;

    @Mock
    private ProductQueryPort productQueryPort;

    @Mock
    private Member host;

    private LiveProductService liveProductService;

    @BeforeEach
    void setUp() {
        liveProductService = new LiveProductService(liveRepository, liveProductRepository, productQueryPort);
    }

    private Live 예약된_라이브() {
        when(host.getId()).thenReturn(HOST_ID);
        return Live.schedule(host, "빈티지 데님 라이브", null, LocalDateTime.now().plusDays(1));
    }

    private LiveProductLinkRequest 연결_요청() {
        return new LiveProductLinkRequest(PRODUCT_ID, (short) 0);
    }

    @Test
    void 호스트_본인_상품이면_연결된다() {
        Live live = 예약된_라이브();
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live));
        when(productQueryPort.findById(PRODUCT_ID))
                .thenReturn(Optional.of(new ProductSummary(PRODUCT_ID, HOST_ID, "리바이스 501 빈티지")));
        when(liveProductRepository.existsByLiveIdAndProductIdAndRemovedAtIsNull(LIVE_ID, PRODUCT_ID))
                .thenReturn(false);
        when(liveProductRepository.save(any(LiveProduct.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));

        var response = liveProductService.linkProduct(HOST_ID, LIVE_ID, 연결_요청());

        assertThat(response.productId()).isEqualTo(PRODUCT_ID);
        assertThat(response.productTitle()).isEqualTo("리바이스 501 빈티지");
    }

    @Test
    void 남의_상품은_연결할_수_없다() {
        Live live = 예약된_라이브();
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live));
        when(productQueryPort.findById(PRODUCT_ID))
                .thenReturn(Optional.of(new ProductSummary(PRODUCT_ID, OTHER_MEMBER_ID, "남의 상품")));
        LiveProductLinkRequest request = 연결_요청();

        assertThatThrownBy(() -> liveProductService.linkProduct(HOST_ID, LIVE_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.NOT_PRODUCT_OWNER);
        verify(liveProductRepository, never()).save(any());
    }

    @Test
    void 본인_라이브가_아니면_연결할_수_없다() {
        when(host.getId()).thenReturn(HOST_ID);
        Live 남의_라이브 = Live.openNow(host, "남의 라이브", null, LocalDateTime.now());
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(남의_라이브));
        LiveProductLinkRequest request = 연결_요청();

        assertThatThrownBy(() -> liveProductService.linkProduct(OTHER_MEMBER_ID, LIVE_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.NOT_LIVE_HOST);
    }

    @Test
    void 이미_연결된_상품은_중복_연결되지_않는다() {
        Live live = 예약된_라이브();
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live));
        when(productQueryPort.findById(PRODUCT_ID))
                .thenReturn(Optional.of(new ProductSummary(PRODUCT_ID, HOST_ID, "리바이스 501 빈티지")));
        when(liveProductRepository.existsByLiveIdAndProductIdAndRemovedAtIsNull(LIVE_ID, PRODUCT_ID))
                .thenReturn(true);
        LiveProductLinkRequest request = 연결_요청();

        assertThatThrownBy(() -> liveProductService.linkProduct(HOST_ID, LIVE_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.PRODUCT_ALREADY_LINKED);
        verify(liveProductRepository, never()).save(any());
    }

    @Test
    void 존재하지_않는_상품은_연결할_수_없다() {
        Live live = 예약된_라이브();
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live));
        when(productQueryPort.findById(PRODUCT_ID)).thenReturn(Optional.empty());
        LiveProductLinkRequest request = 연결_요청();

        assertThatThrownBy(() -> liveProductService.linkProduct(HOST_ID, LIVE_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.PRODUCT_NOT_FOUND);
    }

    @Test
    void 연결_해제하면_삭제하지_않고_제외_시각을_남긴다() {
        Live live = 예약된_라이브();
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live));
        LiveProduct linked = LiveProduct.link(live, PRODUCT_ID, (short) 0, LocalDateTime.now());
        when(liveProductRepository.findByLiveIdAndProductIdAndRemovedAtIsNull(LIVE_ID, PRODUCT_ID))
                .thenReturn(Optional.of(linked));

        liveProductService.unlinkProduct(HOST_ID, LIVE_ID, PRODUCT_ID);

        assertThat(linked.getRemovedAt()).isNotNull();
        assertThat(linked.isLinked()).isFalse();
        // 다시보기 타임라인(LIVE-008) 근거가 남아야 하므로 물리 삭제하지 않는다.
        verify(liveProductRepository, never()).delete(any());
    }

    @Test
    void 연결되지_않은_상품은_해제할_수_없다() {
        Live live = 예약된_라이브();
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live));
        when(liveProductRepository.findByLiveIdAndProductIdAndRemovedAtIsNull(LIVE_ID, PRODUCT_ID))
                .thenReturn(Optional.empty());

        assertThatThrownBy(() -> liveProductService.unlinkProduct(HOST_ID, LIVE_ID, PRODUCT_ID))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.LIVE_PRODUCT_NOT_FOUND);
    }

    @Test
    void 방송이_시작되면_상품을_추가할_수_없다() {
        // 운영 정책 — 시청자가 보고 있는 판매 목록이 도중에 바뀌면 안 된다.
        when(host.getId()).thenReturn(HOST_ID);
        Live 진행중인_라이브 = Live.openNow(host, "빈티지 데님 라이브", null, LocalDateTime.now());
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(진행중인_라이브));
        LiveProductLinkRequest request = 연결_요청();

        assertThatThrownBy(() -> liveProductService.linkProduct(HOST_ID, LIVE_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_LIVE_STATE);
        verify(liveProductRepository, never()).save(any());
    }

    @Test
    void 방송이_시작되면_상품을_제외할_수_없다() {
        when(host.getId()).thenReturn(HOST_ID);
        Live 진행중인_라이브 = Live.openNow(host, "빈티지 데님 라이브", null, LocalDateTime.now());
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(진행중인_라이브));

        assertThatThrownBy(() -> liveProductService.unlinkProduct(HOST_ID, LIVE_ID, PRODUCT_ID))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_LIVE_STATE);
    }

    @Test
    void 개설_시_편성한_상품이_순서대로_저장된다() {
        Live live = Live.schedule(host, "빈티지 데님 라이브", null, LocalDateTime.now().plusDays(1));
        when(productQueryPort.findById(2001L))
                .thenReturn(Optional.of(new ProductSummary(2001L, HOST_ID, "리바이스 501")));
        when(productQueryPort.findById(2002L))
                .thenReturn(Optional.of(new ProductSummary(2002L, HOST_ID, "칼하트 워크팬츠")));

        liveProductService.linkProductsOnCreate(HOST_ID, live, List.of(2001L, 2002L));

        ArgumentCaptor<LiveProduct> captor = ArgumentCaptor.forClass(LiveProduct.class);
        verify(liveProductRepository, times(2)).save(captor.capture());
        assertThat(captor.getAllValues())
                .extracting(LiveProduct::getProductId, LiveProduct::getSortOrder)
                .containsExactly(tuple(2001L, (short) 0), tuple(2002L, (short) 1));
    }

    @Test
    void 개설_시_같은_상품을_두_번_담으면_거부된다() {
        // DB 부분 UNIQUE 인덱스에 걸려 500 이 되기 전에 걸러낸다.
        Live live = Live.schedule(host, "빈티지 데님 라이브", null, LocalDateTime.now().plusDays(1));
        List<Long> 중복_편성 = List.of(PRODUCT_ID, PRODUCT_ID);

        assertThatThrownBy(() -> liveProductService.linkProductsOnCreate(HOST_ID, live, 중복_편성))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.PRODUCT_ALREADY_LINKED);
        verify(liveProductRepository, never()).save(any());
    }

    @Test
    void 개설_시_남의_상품은_편성할_수_없다() {
        Live live = Live.schedule(host, "빈티지 데님 라이브", null, LocalDateTime.now().plusDays(1));
        when(productQueryPort.findById(PRODUCT_ID))
                .thenReturn(Optional.of(new ProductSummary(PRODUCT_ID, OTHER_MEMBER_ID, "남의 상품")));
        List<Long> 편성 = List.of(PRODUCT_ID);

        assertThatThrownBy(() -> liveProductService.linkProductsOnCreate(HOST_ID, live, 편성))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.NOT_PRODUCT_OWNER);
    }
}