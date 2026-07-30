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
import com.ssafy.backend.notification.dto.response.NotificationResponse;
import com.ssafy.backend.notification.entity.Notification;
import com.ssafy.backend.notification.repository.NotificationRepository;
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
                notificationService.getNotifications(MEMBER_ID, false, requested);

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

        notificationService.getNotifications(MEMBER_ID, true, requested);

        verify(notificationRepository).findByMember_IdAndReadFalse(eq(MEMBER_ID), any(Pageable.class));
        verify(notificationRepository, never()).findByMember_Id(eq(MEMBER_ID), any(Pageable.class));
    }

    @Test
    void 알림이_없으면_빈_목록을_반환한다() {
        Pageable requested = PageRequest.of(0, 20);
        when(notificationRepository.findByMember_Id(eq(MEMBER_ID), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(), requested, 0));

        PageResponse<NotificationItemResponse> response =
                notificationService.getNotifications(MEMBER_ID, false, requested);

        assertThat(response.content()).isEmpty();
    }
}