package com.ssafy.backend.member.dto.response;

import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.entity.MemberType;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 마이페이지 요약(에픽 S15P11A108-207 보너스) — 마이페이지 첫 화면에 필요한 카운터와
 * 포인트 잔액을 한 번에 내려준다.
 */
public record MypageSummaryResponse(
        User user,
        Counts counts,
        @Schema(description = "사용 가능 포인트 잔액", example = "10000") Long pointBalance) {

    public record User(
            @Schema(example = "1") Long id,
            @Schema(example = "vintagelover") String nickname,
            String profileImageUrl,
            @Schema(example = "GENERAL") MemberType memberType,
            @Schema(description = "NONE(미제출) | PENDING | APPROVED | REJECTED", example = "NONE")
            String businessVerificationStatus) {

        static User from(Member member, String businessVerificationStatus) {
            return new User(
                    member.getId(),
                    member.getNickname(),
                    member.getProfileImageUrl(),
                    member.getMemberType(),
                    businessVerificationStatus);
        }
    }

    public record Counts(
            @Schema(example = "0") long orders,
            @Schema(example = "0") long sales,
            @Schema(example = "3") long wishes,
            @Schema(example = "12") long followers,
            @Schema(example = "1") long unreadNotifications) {
    }

    public static MypageSummaryResponse of(
            Member member,
            String businessVerificationStatus,
            long orders,
            long sales,
            long wishes,
            long followers,
            long unreadNotifications,
            long pointBalance) {
        return new MypageSummaryResponse(
                User.from(member, businessVerificationStatus),
                new Counts(orders, sales, wishes, followers, unreadNotifications),
                pointBalance);
    }
}
