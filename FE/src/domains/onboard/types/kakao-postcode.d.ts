interface KakaoPostcodeData {
  zonecode: string
  address: string
  roadAddress: string
  jibunAddress: string
  userSelectedType: 'R' | 'J'
}

interface KakaoPostcodeOptions {
  oncomplete: (data: KakaoPostcodeData) => void
}

interface KakaoPostcodeInstance {
  open: () => void
}

type KakaoPostcodeConstructor = new (options: KakaoPostcodeOptions) => KakaoPostcodeInstance

interface KakaoNamespace {
  Postcode?: KakaoPostcodeConstructor
}

interface Window {
  kakao?: KakaoNamespace
}
