import axios from 'axios'

// AI 게이트웨이를 BE를 거치지 않고 직접 호출하는 전용 인스턴스.
// docs/requests/FE/036-quality-finding-bbox-rendering.md, docs/requests/BE/041-quality-inspection-integration.md,
// docs/requests/BE/028-pricing-async.md가 확정한 대로, 품질 검증·가격 추천 job의 결과 조회는
// BE를 거치지 않고 FE가 `GET /ai/jobs/{job_id}`를 외부 경로로 직접 폴링한다.
// 공용 `http`(@/shared/api/http.ts)는 BE 게이트웨이(`/api`) + 인증 토큰 부착용이라 이 용도로는 쓸 수 없다.
const AI_GATEWAY_BASE_URL = import.meta.env.VITE_AI_GATEWAY_BASE_URL ?? 'https://i15a108.p.ssafy.io'

export const aiGatewayHttp = axios.create({
  baseURL: AI_GATEWAY_BASE_URL,
  timeout: 15_000,
})

export type AiJobStatus = 'queued' | 'processing' | 'success' | 'failed'

interface AiJobResponse<T> {
  job_id: string
  status: AiJobStatus
  result: T | null
  error: string | null
  worker_id?: string
}

export class AiJobFailedError extends Error {
  constructor(reason: string) {
    super(reason)
    this.name = 'AiJobFailedError'
  }
}

export class AiJobPollTimeoutError extends Error {
  constructor() {
    super('AI 작업 결과를 기다리는 시간이 초과되었습니다.')
    this.name = 'AiJobPollTimeoutError'
  }
}

export interface PollAiJobOptions {
  intervalMs?: number
  timeoutMs?: number
}

const DEFAULT_POLL_INTERVAL_MS = 3_000
const DEFAULT_POLL_TIMEOUT_MS = 300_000

const sleep = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms))

// job_id 하나를 완료(success/failed)까지 반복 조회한다. 404(TTL 1시간 만료)는 실패로 취급한다.
// 취소가 필요한 호출부(페이지 이탈 등)는 바깥에서 토큰 체크로 감싸서 쓴다(기존 AI 착용컷
// 폴링 패턴, ProductRegistrationPage.vue의 pollAiModelCutStatus 참고).
export const pollAiJob = async <T>(
  jobId: string,
  { intervalMs = DEFAULT_POLL_INTERVAL_MS, timeoutMs = DEFAULT_POLL_TIMEOUT_MS }: PollAiJobOptions = {},
): Promise<T> => {
  const deadline = Date.now() + timeoutMs

  while (Date.now() < deadline) {
    const job = await fetchAiJob<T>(jobId)

    if (job?.status === 'success') {
      if (job.result === null) {
        throw new AiJobFailedError('AI 작업 결과가 비어 있습니다.')
      }

      return job.result
    }

    if (job?.status === 'failed') {
      throw new AiJobFailedError(job.error ?? 'AI 작업이 실패했습니다.')
    }

    await sleep(intervalMs)
  }

  throw new AiJobPollTimeoutError()
}

const fetchAiJob = async <T>(jobId: string): Promise<AiJobResponse<T> | null> => {
  try {
    const response = await aiGatewayHttp.get<AiJobResponse<T>>(`/ai/jobs/${jobId}`)
    return response.data
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      throw new AiJobFailedError('AI 작업을 찾을 수 없습니다(만료되었을 수 있습니다).')
    }

    // 그 외(일시적 네트워크 오류 등)는 다음 폴링에서 재시도한다.
    return null
  }
}
