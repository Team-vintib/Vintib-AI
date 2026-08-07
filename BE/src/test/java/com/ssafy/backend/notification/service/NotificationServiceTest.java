package com.ssafy.backend.notification.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.notification.dto.response.NotificationItemResponse;
import com.ssafy.backend.notification.dto.response.NotificationReadAllResponse;
import com.ssafy.backend.notification.dto.response.NotificationResponse;
import com.ssafy.backend.notification.dto.response.NotificationUnreadCountResponse;
import com.ssafy.backend.notification.entity.Notification;
import com.ssafy.backend.notification.entity.NotificationCategory;
import com.ssafy.backend.notification.repository.NotificationRepository;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class NotificationServiceTest {

    private static final Long MEMBER_ID = 1L;
    private static final Long OTHER_MEMBER_ID = 2L;
    private static final Long NOTIFICATION_ID = 10L;

    @Mock
    private NotificationRepository notificationRepository;

    @Mock
    private Member owner;

    private NotificationService notificationService;
    private Notification notification;

    @BeforeEach
    void setUp() {
        notificationService = new NotificationService(notificationRepository);
        notification = Notification.builder()
                .member(owner)
                .type("AUCTION_WON")
                .title("낙찰되었습니다")
                .build();
        ReflectionTestUtils.setField(notification, "id", NOTIFICATION_ID);
    }

    @Test
    void 알림_읽음_처리에_성공한다() {
        when(owner.getId()).thenReturn(MEMBER_ID);
        when(notificationRepository.findById(NOTIFICATION_ID)).thenReturn(Optional.of(notification));

        NotificationResponse response = notificationService.markAsRead(MEMBER_ID, NOTIFICATION_ID);

        assertThat(response.id()).isEqualTo(NOTIFICATION_ID);
        assertThat(response.isRead()).isTrue();
    }

    @Test
    void 이미_읽은_알림도_에러_없이_처리된다() {
        when(owner.getId()).thenReturn(MEMBER_ID);
        notification.markAsRead();
        when(notificationRepository.findById(NOTIFICATION_ID)).thenReturn(Optional.of(notification));

        NotificationResponse response = notificationService.markAsRead(MEMBER_ID, NOTIFICATION_ID);

        assertThat(response.isRead()).isTrue();
    }

    @Test
    void 존재하지_않는_알림을_읽음_처리하면_예외를_던진다() {
        when(notificationRepository.findById(NOTIFICATION_ID)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> notificationService.markAsRead(MEMBER_ID, NOTIFICATION_ID))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.NOTIFICATION_NOT_FOUND);
    }

    @Test
    void 본인_소유가_아닌_알림을_읽음_처리하면_예외를_던진다() {
        when(owner.getId()).thenReturn(OTHER_MEMBER_ID);
        when(notificationRepository.findById(NOTIFICATION_ID)).thenReturn(Optional.of(notification));

        assertThatThrownBy(() -> notificationService.markAsRead(MEMBER_ID, NOTIFICATION_ID))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.NOTIFICATION_NOT_FOUND);
    }

    @Test
    void 알림_목록을_읽지않음_우선_최신순으로_정렬해서_조회한다() {
        Pageable requested = PageRequest.of(0, 20);
        when(notificationRepository.findByMember_Id(eq(MEMBER_ID), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(notification), requested, 1));

        PageResponse<NotificationItemResponse> response =
                notificationService.getNotifications(MEMBER_ID, false, null, requested);

        assertThat(response.content()).hasSize(1);
        assertThat(response.content().get(0).id()).isEqualTo(NOTIFICATION_ID);

        ArgumentCaptor<Pageable> pageableCaptor = ArgumentCaptor.forClass(Pageable.class);
        verify(notificationRepository).findByMember_Id(eq(MEMBER_ID), pageableCaptor.capture());
        Sort sort = pageableCaptor.getValue().getSort();
        assertThat(sort.getOrderFor("read").getDirection()).isEqualTo(Sort.Direction.ASC);
        assertThat(sort.getOrderFor("createdAt").getDirection()).isEqualTo(Sort.Direction.DESC);
    }

    @Test
    void unreadOnly가_true이면_읽지_않은_알림만_조회한다() {
        Pageable requested = PageRequest.of(0, 20);
        when(notificationRepository.findByMember_IdAndReadFalse(eq(MEMBER_ID), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(notification), requested, 1));

        notificationService.getNotifications(MEMBER_ID, true, null, requested);

        verify(notificationRepository).findByMember_IdAndReadFalse(eq(MEMBER_ID), any(Pageable.class));
        verify(notificationRepository, never()).findByMember_Id(eq(MEMBER_ID), any(Pageable.class));
    }

    @Test
    void 알림이_없으면_빈_목록을_반환한다() {
        Pageable requested = PageRequest.of(0, 20);
        when(notificationRepository.findByMember_Id(eq(MEMBER_ID), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(), requested, 0));

        PageResponse<NotificationItemResponse> response =
                notificationService.getNotifications(MEMBER_ID, false, null, requested);

        assertThat(response.content()).isEmpty();
    }

    @Test
    void 읽지_않은_알림이_있으면_전부_읽음_처리하고_처리_건수를_반환한다() {
        when(notificationRepository.markAllAsReadByMemberId(MEMBER_ID)).thenReturn(3);

        NotificationReadAllResponse response = notificationService.markAllAsRead(MEMBER_ID, null);

        assertThat(response.updatedCount()).isEqualTo(3);
        verify(notificationRepository).markAllAsReadByMemberId(MEMBER_ID);
    }

    @Test
    void 이미_모두_읽은_상태면_0건을_반환한다() {
        when(notificationRepository.markAllAsReadByMemberId(MEMBER_ID)).thenReturn(0);

        NotificationReadAllResponse response = notificationService.markAllAsRead(MEMBER_ID, null);

        assertThat(response.updatedCount()).isEqualTo(0);
    }

    @Test
    void category가_LIVE이면_LIVE_계열_type만_IN_조건으로_조회한다() {
        Pageable requested = PageRequest.of(0, 20);
        when(notificationRepository.findByMember_IdAndTypeIn(eq(MEMBER_ID), any(), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(notification), requested, 1));

        notificationService.getNotifications(MEMBER_ID, false, NotificationCategory.LIVE, requested);

        ArgumentCaptor<Collection<String>> typesCaptor = ArgumentCaptor.forClass(Collection.class);
        verify(notificationRepository)
                .findByMember_IdAndTypeIn(eq(MEMBER_ID), typesCaptor.capture(), any(Pageable.class));
        assertThat(typesCaptor.getValue()).containsExactlyInAnyOrder("LIVE_REMINDER", "LIVE_STARTED");
    }

    @Test
    void category가_TRADE이면_나머지_카테고리_type을_NOT_IN_조건으로_조회한다() {
        Pageable requested = PageRequest.of(0, 20);
        when(notificationRepository.findByMember_IdAndTypeNotIn(eq(MEMBER_ID), any(), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(), requested, 0));

        notificationService.getNotifications(MEMBER_ID, false, NotificationCategory.TRADE, requested);

        verify(notificationRepository)
                .findByMember_IdAndTypeNotIn(
                        eq(MEMBER_ID), eq(NotificationCategory.excludedTypesForCatchAll()), any(Pageable.class));
    }

    @Test
    void category가_POINT이면_POINT_type만_읽음_처리한다() {
        when(notificationRepository.markAllAsReadByMemberIdAndTypeIn(eq(MEMBER_ID), any())).thenReturn(2);

        NotificationReadAllResponse response =
                notificationService.markAllAsRead(MEMBER_ID, NotificationCategory.POINT);

        assertThat(response.updatedCount()).isEqualTo(2);
        verify(notificationRepository)
                .markAllAsReadByMemberIdAndTypeIn(eq(MEMBER_ID), eq(NotificationCategory.POINT.types()));
        verify(notificationRepository, never()).markAllAsReadByMemberId(any());
    }

    @Test
    void category가_없으면_전체_안읽음_수를_반환한다() {
        when(notificationRepository.countByMember_IdAndReadFalse(MEMBER_ID)).thenReturn(4L);

        NotificationUnreadCountResponse response = notificationService.getUnreadCount(MEMBER_ID, null);

        assertThat(response.unreadCount()).isEqualTo(4L);
        verify(notificationRepository, never()).countByMember_IdAndReadFalseAndTypeIn(any(), any());
        verify(notificationRepository, never()).countByMember_IdAndReadFalseAndTypeNotIn(any(), any());
    }

    @Test
    void category가_SHIPPING이면_SHIPPING_type만_IN_조건으로_안읽음_수를_센다() {
        when(notificationRepository.countByMember_IdAndReadFalseAndTypeIn(eq(MEMBER_ID), any())).thenReturn(1L);

        NotificationUnreadCountResponse response =
                notificationService.getUnreadCount(MEMBER_ID, NotificationCategory.SHIPPING);

        assertThat(response.unreadCount()).isEqualTo(1L);
        verify(notificationRepository)
                .countByMember_IdAndReadFalseAndTypeIn(eq(MEMBER_ID), eq(NotificationCategory.SHIPPING.types()));
    }

    @Test
    void category가_TRADE이면_나머지_카테고리_type을_제외하고_안읽음_수를_센다() {
        when(notificationRepository.countByMember_IdAndReadFalseAndTypeNotIn(eq(MEMBER_ID), any()))
                .thenReturn(0L);

        NotificationUnreadCountResponse response =
                notificationService.getUnreadCount(MEMBER_ID, NotificationCategory.TRADE);

        assertThat(response.unreadCount()).isEqualTo(0L);
        verify(notificationRepository)
                .countByMember_IdAndReadFalseAndTypeNotIn(
                        eq(MEMBER_ID), eq(NotificationCategory.excludedTypesForCatchAll()));
    }
}