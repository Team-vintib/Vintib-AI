package com.ssafy.backend.product.config;

import com.ssafy.backend.product.repository.CategoryRepository;
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

// 카테고리/브랜드 마스터 시드(SY007). 마이그레이션 도구(Flyway 등) 없이, 카테고리 테이블이
// 비어 있을 때만 실행해 재기동·재배포 시 중복 삽입을 막는다.
// ProductSeeder(@Order(2))가 이 시드에 의존하므로 @Order(1)로 먼저 실행되게 한다.
@Slf4j
@Component
@RequiredArgsConstructor
@Order(1)
public class CategoryBrandSeeder implements ApplicationRunner {

    private final CategoryRepository categoryRepository;
    private final DataSource dataSource;

    @Override
    public void run(ApplicationArguments args) throws Exception {
        if (categoryRepository.count() > 0) {
            return;
        }

        log.info("카테고리/브랜드 마스터 시드를 실행합니다.");
        try (Connection connection = dataSource.getConnection()) {
            // 기본 auto-commit 상태로 실행하면 스크립트 중간에 실패해도 앞선 INSERT는 이미 커밋된다.
            // 그러면 category 테이블이 비어 있지 않게 되어 다음 재기동에서도 영영 재시도하지 못하고
            // 마스터 데이터가 반쪽 상태로 굳어버린다 — 전체를 하나의 트랜잭션으로 묶어 all-or-nothing으로 만든다.
            connection.setAutoCommit(false);
            try {
                ScriptUtils.executeSqlScript(connection, new ClassPathResource("db/seed.sql"));
                connection.commit();
            } catch (Exception e) {
                connection.rollback();
                throw e;
            }
        }
    }
}