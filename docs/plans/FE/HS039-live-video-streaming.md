# HS039 — 라이브 영상 송출/재생 (LiveKit 통합)

## 배경/목표
지금 FE는 라이브 영상을 실제로 송출/재생하지 않는다. 방송자는 영상 토큰만 발급받아 라벨만 띄우고([LiveBroadcastPage] `loadVideoToken`), 시청자 화면([LiveVideoStage])은 포스터 이미지만 보여준다. → 라이브를 시작해도 영상이 안 나옴("검은 화면").

BE가 미디어 서버 = **LiveKit**(운영 배포 완료)임을 확인해 줬고, FE는 `livekit-client` SDK로 **방송자 카메라 송출(PUBLISHER)** + **시청자 영상 재생(VIEWER)**을 붙이면 된다. BE API/스펙 변경 없음. (상세 스펙은 메모리 `live-video-livekit-spec` 참고)

## 작업 내용
- `livekit-client` 2.x 의존성 추가.
- 연결 유틸 `live/api/liveVideoRoom.ts`: `POST /lives/{id}/video-token` 발급 → `Room.connect(serverUrl, token)` → 역할별 처리(PUBLISHER=카메라/마이크 송출+로컬 프리뷰, VIEWER=원격 트랙 구독→video 요소 attach) → 정리(disconnect).
- `LiveVideoStage.vue`가 영상 라이프사이클을 소유: `<video>` 요소 추가, `status==='LIVE'`가 되면 연결, 연결되면 스트림 표시(그 전엔 포스터/상태), ENDED/언마운트 시 disconnect.
- 시청자/방송자 페이지는 `:live-id`만 넘기고 기존 `loadVideoToken` 라벨 로직 제거.
- 토큰은 캐싱하지 않고 연결 직전 항상 새로 발급, `status==='LIVE'` 가드. 실패(400 L013 / 503 L012 / 연결 실패)면 포스터+안내로 degrade.
- 채팅·시청자수·반응은 STOMP(/ws) 그대로 — 건드리지 않음.

## 구현 목록
- [ ] `livekit-client` 의존성 추가
- [ ] `liveVideoRoom.ts` 연결 유틸 작성
- [ ] `LiveVideoStage.vue`에 `<video>` + 연결/정리 로직
- [ ] 시청자 배선: `LiveWatchPage.vue`에 `:live-id`, 기존 토큰 라벨 제거
- [ ] 방송자 배선: `LiveBroadcastPage.vue`에 `:live-id`, 기존 토큰 라벨 제거
- [ ] 타입체크 + 프로덕션 빌드 통과

## 확인 필요 / 의존
- BE가 운영 env 실검증(livekit 컨테이너 공인 IP, `PROD_OPENVIDU_SERVER_URL`, UDP 버퍼)은 아직. **SDK를 붙였는데 에러 없이 검게만 나오면 BE env 문제 가능성** → BE 확인 요청.
- 로컬은 livekit 컨테이너가 없으면 503(L012) → 폴백(포스터 유지)으로 처리.
- 시청자 오디오 자동재생은 브라우저 정책상 막힐 수 있음(영상은 별도 처리해 안 막히게 함). 필요 시 후속으로 "소리 켜기" 제스처 버튼 추가.

## 브랜치 / 커밋
- 브랜치: `feat/217-live-video-streaming` (epic 217, develop-FE 기준).
- 커밋: 작업 단위 한글 `[S15P11A108-<key>] feat: ...`. push·MR은 사용자가 직접.
