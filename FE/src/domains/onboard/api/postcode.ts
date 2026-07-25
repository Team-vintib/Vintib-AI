const POSTCODE_SCRIPT_ID = 'kakao-postcode-script'
const POSTCODE_SCRIPT_URL = 'https://t1.kakaocdn.net/mapjsapi/bundle/postcode/prod/postcode.v2.js'
const POSTCODE_LOAD_TIMEOUT_MS = 10_000

let postcodeScriptPromise: Promise<void> | null = null

export interface PostcodeAddress {
  zonecode: string
  address: string
}

const isPostcodeReady = () => typeof window.kakao?.Postcode === 'function'

const loadPostcodeScript = () => {
  if (isPostcodeReady()) {
    return Promise.resolve()
  }

  if (postcodeScriptPromise) {
    return postcodeScriptPromise
  }

  postcodeScriptPromise = new Promise<void>((resolve, reject) => {
    const existingScript = document.getElementById(POSTCODE_SCRIPT_ID) as HTMLScriptElement | null

    const scriptElement = existingScript ?? document.createElement('script')

    const cleanup = () => {
      window.clearTimeout(timeoutId)
      scriptElement.removeEventListener('load', handleLoad)
      scriptElement.removeEventListener('error', handleError)
    }

    const rejectLoading = (message: string) => {
      cleanup()
      scriptElement.remove()
      postcodeScriptPromise = null
      reject(new Error(message))
    }

    const handleLoad = () => {
      cleanup()

      if (isPostcodeReady()) {
        resolve()
        return
      }

      postcodeScriptPromise = null
      reject(new Error('Kakao 우편번호 서비스를 초기화하지 못했습니다.'))
    }

    const handleError = () => {
      rejectLoading('Kakao 우편번호 서비스를 불러오지 못했습니다.')
    }

    scriptElement.addEventListener('load', handleLoad, { once: true })
    scriptElement.addEventListener('error', handleError, { once: true })

    const timeoutId = window.setTimeout(() => {
      rejectLoading('Kakao 우편번호 서비스 연결 시간이 초과되었습니다.')
    }, POSTCODE_LOAD_TIMEOUT_MS)

    if (!existingScript) {
      scriptElement.id = POSTCODE_SCRIPT_ID
      scriptElement.src = POSTCODE_SCRIPT_URL
      scriptElement.async = true
      document.head.appendChild(scriptElement)
    }
  })

  return postcodeScriptPromise
}

export const openPostcodeSearch = async (handleComplete: (result: PostcodeAddress) => void) => {
  await loadPostcodeScript()

  const Postcode = window.kakao?.Postcode

  if (!Postcode) {
    throw new Error('Kakao 우편번호 서비스를 사용할 수 없습니다.')
  }

  new Postcode({
    oncomplete: (data) => {
      const selectedAddress = data.userSelectedType === 'R' ? data.roadAddress : data.jibunAddress

      handleComplete({
        zonecode: data.zonecode,
        address: selectedAddress || data.address,
      })
    },
  }).open()
}
