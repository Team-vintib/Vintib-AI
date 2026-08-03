package com.ssafy.backend.global.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * 주기 실행 활성화.
 *
 * <p>애플리케이션 클래스가 아니라 별도 설정으로 두는 이유는, 테스트에서 스케줄러만 끄고 싶을 때
 * 이 설정 하나만 제외하면 되기 때문이다.
 *
 * <p>현재 등록된 작업은 예약 라이브 알림 발송({@code LiveReminderScheduler})이다.
 * 경매 마감 스케줄러(-466)도 여기에 얹힌다.
 */
@Configuration
@EnableScheduling
public class SchedulingConfig {
}
