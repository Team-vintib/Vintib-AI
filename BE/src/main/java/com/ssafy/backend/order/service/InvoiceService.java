package com.ssafy.backend.order.service;

import com.ssafy.backend.business.entity.BusinessInfo;
import com.ssafy.backend.business.entity.BusinessVerificationStatus;
import com.ssafy.backend.business.repository.BusinessInfoRepository;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.business.dto.response.InvoiceResponse;
import com.ssafy.backend.order.entity.Invoice;
import com.ssafy.backend.order.entity.Order;
import com.ssafy.backend.order.repository.InvoiceRepository;
import com.ssafy.backend.order.repository.OrderRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 세금계산서(BIZ-002) 발행/조회.
 *
 * <p>{@code business} 패키지의 {@link BusinessInfoRepository}를 직접 참조한다 — "상위 도메인이
 * 하위 도메인을 직접 참조"하는 기존 컨벤션(예: WishService → ProductRepository)과 동일해
 * 별도 포트가 필요 없다.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class InvoiceService {

    private final OrderRepository orderRepository;
    private final InvoiceRepository invoiceRepository;
    private final BusinessInfoRepository businessInfoRepository;

    @Transactional
    public InvoiceResponse issueInvoice(Long orderId, Long memberId) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new CustomException(ErrorCode.ORDER_NOT_FOUND));
        if (!order.isPartyOf(memberId)) {
            throw new CustomException(ErrorCode.INVOICE_FORBIDDEN);
        }
        if (invoiceRepository.existsByOrder_Id(orderId)) {
            throw new CustomException(ErrorCode.INVOICE_ALREADY_ISSUED);
        }

        BusinessInfo sellerBusinessInfo = businessInfoRepository.findById(order.getSeller().getId()).orElse(null);
        if (sellerBusinessInfo == null || sellerBusinessInfo.getVerificationStatus() != BusinessVerificationStatus.APPROVED) {
            throw new CustomException(ErrorCode.INVOICE_ISSUER_NOT_APPROVED_BUSINESS);
        }

        Invoice invoice = Invoice.issue(
                order,
                sellerBusinessInfo.getBusinessNumber(),
                sellerBusinessInfo.getBusinessName(),
                sellerBusinessInfo.getRepresentativeName());
        invoiceRepository.save(invoice);
        return toResponse(invoice);
    }

    public InvoiceResponse getInvoice(Long orderId, Long memberId) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new CustomException(ErrorCode.ORDER_NOT_FOUND));
        if (!order.isPartyOf(memberId)) {
            throw new CustomException(ErrorCode.INVOICE_FORBIDDEN);
        }

        Invoice invoice = invoiceRepository.findByOrder_Id(orderId)
                .orElseThrow(() -> new CustomException(ErrorCode.INVOICE_NOT_FOUND));
        return toResponse(invoice);
    }

    private InvoiceResponse toResponse(Invoice invoice) {
        return new InvoiceResponse(
                invoice.getId(),
                invoice.getOrder().getId(),
                invoice.getBusinessNumber(),
                invoice.getBusinessName(),
                invoice.getRepresentativeName(),
                invoice.getSupplyAmount(),
                invoice.getTaxAmount(),
                invoice.getTotalAmount(),
                invoice.getIssuedAt());
    }
}
