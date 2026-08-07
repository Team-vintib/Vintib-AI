package com.ssafy.backend.notification.port;

import com.ssafy.backend.member.entity.Member;

/**
 * 다른 도메인이 알림을 만드는 유일한 창구.
 *
 * <p>{@code ProductQueryPort}와 같은 이유로 둔다 — 호출 도메인이 알림 도메인의 엔티티 구조를
 * 직접 다루면, 알림 쪽이 바뀔 때 호출부가 함께 깨진다. 어댑터 한 곳만 고치면 되게 좁혀 둔다.
 *
 * <h2>중복 알림 방지 정책</h2>
 *
 * <p>{@link #notify}는 그 자체로 멱등하지 않다 — 호출할 때마다 새 알림 row를 만든다. 대신
 * 지금까지의 모든 호출부가 <b>같은 이벤트가 두 번 들어와도 두 번째부터는 호출 지점 자체에
 * 도달하지 못하게</b> 한 방향 상태 전이 뒤에 {@code notify}를 두는 방식으로 중복을 막는다 —
 * 알림 레벨에서 따로 dedup 테이블/유니크 제약을 두지 않는다. 예:
 *
 * <ul>
 *   <li>{@code SHIPMENT_STARTED} — {@code Order}가 {@code PAID}일 때만 송장 등록이 되고,
 *       등록되면 즉시 {@code SHIPPING}으로 전이한다. 재등록 시도는 상태 검사에서 막힌다
 *       (송장 재등록 API 자체가 없다).</li>
 *   <li>{@code SHIPMENT_COMPLETED} — 배송완료 웹훅이 여러 번 와도 {@code order.status ==
 *       SHIPPING}일 때만 확정 로직(및 notify)이 실행된다. 첫 처리 후 상태가 바뀌므로 재웹훅은
 *       상태 갱신만 하고 조용히 무시한다({@code OrderService#updateShipmentTracking} 참고).</li>
 *   <li>{@code POINT_CHARGED} — {@code PointCharge.status == DONE}이면 {@code confirmCharge}가
 *       실제 적립 로직(및 notify) 없이 바로 반환한다(토스 confirm 중복 호출 대비).</li>
 *   <li>{@code POINT_REFUNDED} — {@code RefundRequest}가 {@code REQUESTED}일 때만 승인할 수
 *       있고, 승인되면 상태가 바뀐다. 같은 요청을 두 번 승인할 수 없다.</li>
 *   <li>{@code LIVE_REMINDER} — 발송 표시(reminder.markNotified)와 알림 생성이 한 트랜잭션이라
 *       다음 스케줄러 주기가 같은 대상을 다시 집어내지 않는다({@code LiveReminderService#dispatchDue}).</li>
 * </ul>
 *
 * <p><b>새 알림 트리거를 추가할 때</b>도 이 패턴을 따른다 — 상태 전이 가드(또는 그에 준하는
 * 멱등성 검사) 뒤에서만 {@code notify}를 호출한다. {@code ORDER_PAID}·{@code WITHDRAW_COMPLETED}처럼
 * 매 호출이 새로운 정당한 이벤트인 "생성" 계열 알림은 애초에 재시도 시나리오가 없어 이 패턴이
 * 필요 없다.
 */
public interface NotificationCommandPort {

    /**
     * 알림 한 건을 만든다. 이 메서드 자체는 멱등하지 않다 — 중복 방지 정책은 위 클래스 문서 참고.
     *
     * @param type    알림 종류
     * @param refType 클릭 시 이동할 대상 종류. {@code LIVE}면 FE 가 {@code /lives/{refId}}로 보낸다
     */
    void notify(Member member, String type, String title, String body, String refType, Long refId);
}