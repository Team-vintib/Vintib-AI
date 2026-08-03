import type { PageMeta } from '@/shared/types/api.types'

export interface PublicProfile {
  id: number
  nickname: string
  profileImageUrl: string | null
  description: string
  coverImageUrl: string | null
  followerCount: number
  followingCount: number
  productCount: number
  liveCount: number
  isFollowing: boolean
  businessVerified: boolean
}

export interface FollowUser {
  id: number
  nickname: string
  profileImageUrl: string | null
  followerCount: number
  productCount: number
  isFollowing: boolean
}

export interface FollowResponse {
  targetUserId: number
  isFollowing: boolean
  followerCount: number
}

export interface FollowUserPage {
  items: FollowUser[]
  meta: PageMeta
}

export type FollowListKind = 'followers' | 'following'

