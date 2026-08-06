import { Room, RoomEvent, Track } from 'livekit-client'
import type { RemoteTrack } from 'livekit-client'

import { issueLiveVideoToken } from '@/domains/live/api/liveControlApi'

export type LiveVideoRole = 'PUBLISHER' | 'VIEWER'

export interface LiveVideoSession {
  role: LiveVideoRole
  disconnect: () => Promise<void>
}

/**
 * 라이브 영상 룸(LiveKit)에 접속한다.
 *
 * - 라이브 status가 LIVE일 때만 호출한다(SCHEDULED/ENDED면 BE가 400 L013).
 * - 토큰은 캐싱하지 않고 연결 직전 항상 새로 발급받는다(LIVE 전환마다 room 이름이 새로 배정됨).
 * - serverUrl은 그대로 넘긴다('/rtc'는 SDK가 붙임).
 * - 역할은 서버가 정한다(호스트=PUBLISHER, 그 외=VIEWER).
 */
export const connectLiveVideo = async (
  liveId: number,
  videoEl: HTMLVideoElement,
  onDisconnected?: () => void,
): Promise<LiveVideoSession> => {
  const { token, serverUrl, role } = await issueLiveVideoToken(liveId)

  const room = new Room({ adaptiveStream: true, dynacast: true })
  const attachedAudioEls: HTMLMediaElement[] = []

  if (onDisconnected) {
    room.on(RoomEvent.Disconnected, onDisconnected)
  }

  // 시청자: 호스트의 원격 트랙을 구독한다. 영상은 video 요소에 붙이고, 오디오는 별도 요소에 붙여
  // (오디오 트랙까지 video 요소에 붙이면 자동재생 정책으로 영상 재생이 통째로 막힐 수 있어) 재생한다.
  room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack) => {
    if (track.kind === Track.Kind.Video) {
      track.attach(videoEl)
    } else if (track.kind === Track.Kind.Audio) {
      const audioEl = track.attach()
      audioEl.style.display = 'none'
      document.body.appendChild(audioEl)
      attachedAudioEls.push(audioEl)
    }
  })

  await room.connect(serverUrl, token)

  if (role === 'PUBLISHER') {
    // 방송자: 카메라/마이크 송출 + 자기 화면 프리뷰(자기 소리는 음소거해 에코 방지).
    videoEl.muted = true
    await room.localParticipant.enableCameraAndMicrophone()
    const cameraTrack = room.localParticipant.getTrackPublication(Track.Source.Camera)?.videoTrack
    cameraTrack?.attach(videoEl)
  } else {
    // 시청자: 자동재생이 막혀 있으면 best-effort로 오디오 재생을 시도한다(제스처 없으면 무시됨).
    void room.startAudio().catch(() => undefined)
  }

  const disconnect = async () => {
    attachedAudioEls.forEach((el) => el.remove())
    attachedAudioEls.length = 0
    await room.disconnect()
  }

  return { role, disconnect }
}
