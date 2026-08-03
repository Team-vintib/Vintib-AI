package com.ssafy.backend.order.repository;

import com.ssafy.backend.order.entity.Invoice;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface InvoiceRepository extends JpaRepository<Invoice, Long> {

    boolean existsByOrder_Id(Long orderId);

    Optional<Invoice> findByOrder_Id(Long orderId);
}
