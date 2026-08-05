package com.ssafy.backend.global.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;

/** {@code @Scheduled} 배치(예: 자동 구매 확정, ORDER-003)를 켠다. */
@Configuration
@EnableScheduling
public class SchedulingConfig {
}
