package com.ssafy.backend.product.config;

import com.ssafy.backend.product.repository.ProductRepository;
import java.sql.Connection;
import javax.sql.DataSource;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.datasource.init.ScriptUtils;
import org.springframework.stereotype.Component;

// 상품 데모 시드. 카테고리/브랜드/데모 회원 시드가 끝난 뒤 실행돼야 하므로
// CategoryBrandSeeder·DemoMemberSeeder(둘 다 @Order(1))보다 뒤에 도는 @Order(2)를 둔다.
// product 테이블이 비어 있을 때만 실행해 재기동·재배포 시 중복 삽입을 막는다.
@Slf4j
@Component
@RequiredArgsConstructor
@Order(2)
public class ProductSeeder implements ApplicationRunner {

    private final ProductRepository productRepository;
    private final DataSource dataSource;

    @Override
    public void run(ApplicationArguments args) throws Exception {
        if (productRepository.count() > 0) {
            return;
        }

        log.info("상품 데모 시드를 실행합니다.");
        try (Connection connection = dataSource.getConnection()) {
            connection.setAutoCommit(false);
            try {
                ScriptUtils.executeSqlScript(connection, new ClassPathResource("db/product-seed.sql"));
                ScriptUtils.executeSqlScript(connection, new ClassPathResource("db/product-image-seed.sql"));
                connection.commit();
            } catch (Exception e) {
                connection.rollback();
                throw e;
            }
        }
    }
}