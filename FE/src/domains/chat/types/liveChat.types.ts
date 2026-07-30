export type LiveChatAuthorRole = 'HOST' | 'VIEWER'

export type LiveReactionEmoji = '❤️' | '🔥' | '👏' | '😮'

export interface LiveChatMessage {
  id: string
  author: string
  body: string
  role: LiveChatAuthorRole
}
