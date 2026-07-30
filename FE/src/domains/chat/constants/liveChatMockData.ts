import type {
  LiveChatMessage,
  LiveReactionEmoji,
} from '@/domains/chat/types/liveChat.types'

export const LIVE_REACTION_EMOJIS: LiveReactionEmoji[] = ['❤️', '🔥', '👏', '😮']

export const LIVE_CHAT_MOCK_MESSAGES: LiveChatMessage[] = [
  {
    id: 'chat-1',
    author: 'VintageKing92',
    body: '와 이거 진짜 레어한 아이템이에요!!',
    role: 'VIEWER',
  },
  {
    id: 'chat-2',
    author: 'Vintage Hunter',
    body: '네 맞습니다! 1980년대 정품 가죽 가방이에요.',
    role: 'HOST',
  },
  {
    id: 'chat-3',
    author: 'fashionlover',
    body: '저도 입찰하고 싶은데 포인트가...',
    role: 'VIEWER',
  },
  {
    id: 'chat-4',
    author: 'collector_jk',
    body: '얼마까지 올라갈까요?',
    role: 'VIEWER',
  },
  {
    id: 'chat-5',
    author: 'user1',
    body: '저 입찰했어요!!',
    role: 'VIEWER',
  },
  {
    id: 'chat-6',
    author: 'Vintage Hunter',
    body: '현재 경매 진행 중! 🔥',
    role: 'HOST',
  },
  {
    id: 'chat-7',
    author: 'vintage_pro',
    body: '이 색감 너무 예쁘다',
    role: 'VIEWER',
  },
]
