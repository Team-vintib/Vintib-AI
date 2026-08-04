package com.ssafy.backend.global.config;

import java.sql.Connection;
import java.sql.Statement;
import java.util.List;
import javax.sql.DataSource;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * {@code schema.sql}의 <b>부분 인덱스</b>를 기동 시 만들어 둔다.
 *
 * <h2>왜 필요한가</h2>
 *
 * 우리 스키마는 몇 가지 핵심 규칙을 <b>부분 UNIQUE 인덱스</b>로 못 박아 두었다.
 *
 * <ul>
 *   <li>{@code ux_auction_live_running} — 한 라이브에서 동시에 진행 중인 경매는 1개 (LIVE-004)</li>
 *   <li>{@code ux_bid_auction_price} — 같은 경매의 같은 가격 단계는 단 한 번만 성립
 *       (중복 클릭 AUCT-004 · 동시 입찰 경합 AUCT-005의 최후 방어선)</li>
 *   <li>{@code ux_point_hold_member_active} — 한 회원이 전체 경매를 통틀어 가질 수 있는
 *       {@code HELD} 보류는 1개(연속 입찰 금지 AUCT-006 · 다른 경매 동시 참여 금지 AUCT-009의
 *       최후 방어선)</li>
 *   <li>{@code ux_live_product_active} — 제외되지 않은 같은 상품을 같은 라이브에 두 번 연결 불가</li>
 * </ul>
 *
 * <p>그런데 <b>JPA 는 부분 인덱스({@code WHERE} 절이 붙은 인덱스)를 표현할 수 없고</b>, 우리
 * 운영/로컬은 {@code ddl-auto}(create/update)로 엔티티에서 스키마를 만든다. 즉 이 인덱스들은
 * <b>문서에만 있고 실제 DB 에는 없었다.</b> 애플리케이션 검증이 1차 방어인 것은 맞지만, 동시
 * 요청에서는 "둘 다 검사를 통과한 뒤 둘 다 쓰는" 창이 남는다 — 그 창을 막는 것이 이 인덱스들의
 * 유일한 역할이라 없으면 안전망이 통째로 비어 있는 셈이다.
 *
 * <p>그래서 Hibernate 가 테이블을 만든 <b>다음에</b> 여기서 직접 만든다.
 *
 * <h2>주의</h2>
 *
 * <p>{@code IF NOT EXISTS} 라 여러 번 떠도 안전하다. <b>실패해도 기동은 막지 않는다</b> —
 * 인덱스가 없으면 경합 시 중복이 생길 수 있지만, 서비스가 통째로 안 뜨는 것보다는 낫다.
 * 대신 경고를 남겨 배포 로그에서 눈에 띄게 한다.
 *
 * <p>이 클래스는 임시방편이 아니라 <b>{@code ddl-auto} 를 쓰는 동안의 정식 보완책</b>이다.
 * 나중에 Flyway 같은 마이그레이션 도구를 도입하면 {@code schema.sql} 이 그대로 기준이 되므로
 * 이 클래스는 지운다.
 */
@Slf4j
@Component
@Order(0)
@RequiredArgsConstructor
public class PartialIndexInitializer implements ApplicationRunner {

    private static final List<String> STATEMENTS = List.of(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_auction_live_running
                ON auction (live_id) WHERE status = 'RUNNING'
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_bid_auction_price
                ON bid (auction_id, bid_price)
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_point_hold_member_active
                ON point_hold (member_id) WHERE status = 'HELD'
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_live_product_active
                ON live_product (live_id, product_id) WHERE removed_at IS NULL
            """,
            """
            CREATE INDEX IF NOT EXISTS ix_live_reminder_pending
                ON live_reminder (live_id) WHERE notified_at IS NULL
            """);

    private final DataSource dataSource;

    @Override
    public void run(ApplicationArguments args) {
        try (Connection connection = dataSource.getConnection();
             Statement statement = connection.createStatement()) {
            int succeeded = 0;
            for (String ddl : STATEMENTS) {
                // 각 문장을 따로 잡는다 — 하나가 실패해도(예: 기존 데이터 중복) 나머지 안전망은
                // 그대로 만들어져야 한다. 한 번 실패했다고 다음 문장을 건너뛰면 안 된다.
                try {
                    statement.execute(ddl);
                    succeeded++;
                } catch (Exception e) {
                    log.error("!! 부분 인덱스 생성 실패 - 이 안전망 없이 뜬다. "
                            + "기존 데이터에 중복이 있는지 확인할 것: {}", ddl, e);
                }
            }
            log.info("부분 인덱스 확인 완료 - {}/{}개", succeeded, STATEMENTS.size());
        } catch (Exception e) {
            log.error("!! 부분 인덱스 초기화 자체가 실패했다 - DB 연결을 확인할 것", e);
        }
    }
}
