package com.ssafy.backend.order.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.ssafy.backend.business.entity.BusinessInfo;
import com.ssafy.backend.business.entity.BusinessVerificationStatus;
import com.ssafy.backend.business.repository.BusinessInfoRepository;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.business.dto.response.InvoiceResponse;
import com.ssafy.backend.order.entity.Invoice;
import com.ssafy.backend.order.entity.Order;
import com.ssafy.backend.order.repository.InvoiceRepository;
import com.ssafy.backend.order.repository.OrderRepository;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class InvoiceServiceTest {

    private static final Long ORDER_ID = 10L;
    private static final Long BUYER_ID = 1L;
    private static final Long SELLER_ID = 2L;
    private static final Long OTHER_MEMBER_ID = 999L;

    @Mock
    private OrderRepository orderRepository;

    @Mock
    private InvoiceRepository invoiceRepository;

    @Mock
    private BusinessInfoRepository businessInfoRepository;

    @Mock
    private Order order;

    @Mock
    private Member seller;

    @Mock
    private BusinessInfo sellerBusinessInfo;

    private InvoiceService invoiceService;

    @BeforeEach
    void setUp() {
        invoiceService = new InvoiceService(orderRepository, invoiceRepository, businessInfoRepository);
    }

    @Test
    void 발행에_성공하면_주문금액_기준으로_부가세를_계산한다() {
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(order));
        when(order.isPartyOf(BUYER_ID)).thenReturn(true);
        when(order.getSeller()).thenReturn(seller);
        when(seller.getId()).thenReturn(SELLER_ID);
        when(order.getOrderPrice()).thenReturn(110_000L);
        when(invoiceRepository.existsByOrder_Id(ORDER_ID)).thenReturn(false);
        when(businessInfoRepository.findById(SELLER_ID)).thenReturn(Optional.of(sellerBusinessInfo));
        when(sellerBusinessInfo.getVerificationStatus()).thenReturn(BusinessVerificationStatus.APPROVED);
        when(sellerBusinessInfo.getBusinessNumber()).thenReturn("1234567890");
        when(sellerBusinessInfo.getBusinessName()).thenReturn("빈티브 상회");
        when(sellerBusinessInfo.getRepresentativeName()).thenReturn("홍길동");
        when(invoiceRepository.save(any(Invoice.class))).thenAnswer(invocation -> {
            Invoice invoice = invocation.getArgument(0);
            ReflectionTestUtils.setField(invoice, "id", 1L);
            return invoice;
        });
        when(order.getId()).thenReturn(ORDER_ID);

        InvoiceResponse response = invoiceService.issueInvoice(ORDER_ID, BUYER_ID);

        assertThat(response.supplyAmount()).isEqualTo(100_000L);
        assertThat(response.taxAmount()).isEqualTo(10_000L);
        assertThat(response.totalAmount()).isEqualTo(110_000L);
        assertThat(response.businessNumber()).isEqualTo("1234567890");
    }

    @Test
    void 이미_발행된_주문이면_예외를_던진다() {
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(order));
        when(order.isPartyOf(BUYER_ID)).thenReturn(true);
        when(invoiceRepository.existsByOrder_Id(ORDER_ID)).thenReturn(true);

        assertThatThrownBy(() -> invoiceService.issueInvoice(ORDER_ID, BUYER_ID))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.INVOICE_ALREADY_ISSUED);
    }

    @Test
    void 존재하지_않는_주문이면_예외를_던진다() {
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> invoiceService.issueInvoice(ORDER_ID, BUYER_ID))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.ORDER_NOT_FOUND);
    }

    @Test
    void 거래_당사자가_아니면_발행을_거부한다() {
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(order));
        when(order.isPartyOf(OTHER_MEMBER_ID)).thenReturn(false);

        assertThatThrownBy(() -> invoiceService.issueInvoice(ORDER_ID, OTHER_MEMBER_ID))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.INVOICE_FORBIDDEN);
    }

    @Test
    void 판매자가_사업자_승인을_받지_않았으면_발행을_거부한다() {
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(order));
        when(order.isPartyOf(BUYER_ID)).thenReturn(true);
        when(invoiceRepository.existsByOrder_Id(ORDER_ID)).thenReturn(false);
        when(order.getSeller()).thenReturn(seller);
        when(seller.getId()).thenReturn(SELLER_ID);
        when(businessInfoRepository.findById(SELLER_ID)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> invoiceService.issueInvoice(ORDER_ID, BUYER_ID))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.INVOICE_ISSUER_NOT_APPROVED_BUSINESS);
    }

    @Test
    void 조회에_성공하면_인보이스를_반환한다() {
        Invoice invoice = Invoice.builder()
                .order(order)
                .businessNumber("1234567890")
                .businessName("빈티브 상회")
                .representativeName("홍길동")
                .supplyAmount(100_000L)
                .taxAmount(10_000L)
                .totalAmount(110_000L)
                .build();
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(order));
        when(order.isPartyOf(BUYER_ID)).thenReturn(true);
        when(order.getId()).thenReturn(ORDER_ID);
        when(invoiceRepository.findByOrder_Id(ORDER_ID)).thenReturn(Optional.of(invoice));

        InvoiceResponse response = invoiceService.getInvoice(ORDER_ID, BUYER_ID);

        assertThat(response.orderId()).isEqualTo(ORDER_ID);
        assertThat(response.totalAmount()).isEqualTo(110_000L);
    }

    @Test
    void 발행된_인보이스가_없으면_조회시_예외를_던진다() {
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(order));
        when(order.isPartyOf(BUYER_ID)).thenReturn(true);
        when(invoiceRepository.findByOrder_Id(ORDER_ID)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> invoiceService.getInvoice(ORDER_ID, BUYER_ID))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.INVOICE_NOT_FOUND);
    }
}
