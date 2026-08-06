<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

const emit = defineEmits<{
  close: []
  select: [file: File]
}>()

const dialogElement = ref<HTMLElement | null>(null)
const videoElement = ref<HTMLVideoElement | null>(null)
const isCameraStarting = ref(false)
const isCameraReady = ref(false)
const isFrontFacingCamera = ref(true)
const cameraStage = ref<'live' | 'captured'>('live')
const cameraError = ref('')
const capturedFile = ref<File | null>(null)
const capturedPreviewUrl = ref('')

let cameraStream: MediaStream | null = null
let cameraRequestId = 0
let previousBodyOverflow = ''

const releaseCapturedPreviewUrl = () => {
  if (!capturedPreviewUrl.value) {
    return
  }

  URL.revokeObjectURL(capturedPreviewUrl.value)
  capturedPreviewUrl.value = ''
}

const stopCameraStream = () => {
  cameraRequestId += 1
  cameraStream?.getTracks().forEach((track) => track.stop())
  cameraStream = null
  isCameraReady.value = false

  if (videoElement.value) {
    videoElement.value.srcObject = null
  }
}

const resetCapturedPhoto = () => {
  releaseCapturedPreviewUrl()
  capturedFile.value = null
}

const getCameraErrorMessage = (error: unknown) => {
  if (!(error instanceof DOMException)) {
    return '카메라를 시작하지 못했습니다. 잠시 후 다시 시도해 주세요.'
  }

  if (error.name === 'NotAllowedError' || error.name === 'SecurityError') {
    return '카메라 권한이 필요합니다. 브라우저 주소창에서 카메라 권한을 허용해 주세요.'
  }

  if (error.name === 'NotFoundError' || error.name === 'OverconstrainedError') {
    return '사용 가능한 카메라를 찾을 수 없습니다.'
  }

  if (error.name === 'NotReadableError' || error.name === 'AbortError') {
    return '다른 앱에서 카메라를 사용 중입니다. 다른 앱을 닫고 다시 시도해 주세요.'
  }

  return '카메라를 시작하지 못했습니다. 잠시 후 다시 시도해 주세요.'
}

const startCameraStream = async () => {
  stopCameraStream()

  const requestId = cameraRequestId
  isCameraStarting.value = true
  cameraError.value = ''

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: {
        facingMode: { ideal: 'user' },
        width: { ideal: 1080 },
        height: { ideal: 1920 },
      },
    })

    if (requestId !== cameraRequestId) {
      stream.getTracks().forEach((track) => track.stop())
      return
    }

    cameraStream = stream
    isFrontFacingCamera.value =
      stream.getVideoTracks()[0]?.getSettings().facingMode !== 'environment'

    await nextTick()

    if (!videoElement.value) {
      throw new Error('Camera preview element is unavailable.')
    }

    videoElement.value.srcObject = stream
    await videoElement.value.play()
    isCameraReady.value = true
  } catch (error) {
    if (requestId === cameraRequestId) {
      stopCameraStream()
      cameraError.value = getCameraErrorMessage(error)
      isCameraStarting.value = false
    }
  } finally {
    if (requestId === cameraRequestId) {
      isCameraStarting.value = false
    }
  }
}

const createCapturedFile = (canvas: HTMLCanvasElement) =>
  new Promise<File>((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error('Captured image could not be created.'))
          return
        }

        resolve(
          new File([blob], `full-body-${Date.now()}.jpg`, {
            type: blob.type || 'image/jpeg',
          }),
        )
      },
      'image/jpeg',
      0.92,
    )
  })

const capturePhoto = async () => {
  const video = videoElement.value

  if (!video || !isCameraReady.value || video.videoWidth <= 0 || video.videoHeight <= 0) {
    cameraError.value = '카메라 화면이 준비되지 않았습니다. 잠시 후 다시 시도해 주세요.'
    return
  }

  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight

  const context = canvas.getContext('2d')

  if (!context) {
    cameraError.value = '촬영 결과를 만들지 못했습니다. 다시 시도해 주세요.'
    return
  }

  if (isFrontFacingCamera.value) {
    context.translate(canvas.width, 0)
    context.scale(-1, 1)
  }

  context.drawImage(video, 0, 0, canvas.width, canvas.height)

  try {
    const file = await createCapturedFile(canvas)

    resetCapturedPhoto()
    capturedFile.value = file
    capturedPreviewUrl.value = URL.createObjectURL(file)
    cameraStage.value = 'captured'
    cameraError.value = ''
    stopCameraStream()
  } catch {
    cameraError.value = '촬영 결과를 만들지 못했습니다. 다시 시도해 주세요.'
  }
}

const retakePhoto = async () => {
  resetCapturedPhoto()
  cameraStage.value = 'live'

  await nextTick()
  await startCameraStream()
}

const selectCapturedPhoto = () => {
  if (capturedFile.value) {
    emit('select', capturedFile.value)
  }
}

const retryCamera = async () => {
  cameraStage.value = 'live'
  await startCameraStream()
}

const handleWindowKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Escape') {
    emit('close')
  }
}

onMounted(() => {
  previousBodyOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  window.addEventListener('keydown', handleWindowKeydown)
  dialogElement.value?.focus()
  void startCameraStream()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleWindowKeydown)
  document.body.style.overflow = previousBodyOverflow
  stopCameraStream()
  releaseCapturedPreviewUrl()
})
</script>

<template>
  <Teleport to="body">
    <div
      ref="dialogElement"
      class="camera-capture"
      role="dialog"
      aria-modal="true"
      aria-labelledby="camera-capture-title"
      aria-describedby="camera-capture-description"
      tabindex="-1"
    >
      <section class="camera-capture__panel">
        <header class="camera-capture__header">
          <div>
            <p class="camera-capture__eyebrow">전신 사진 즉시 촬영</p>
            <h2 id="camera-capture-title">
              {{ cameraStage === 'live' ? '카메라 화면을 확인해 주세요' : '이 사진을 사용할까요?' }}
            </h2>
            <p id="camera-capture-description">
              {{
                cameraStage === 'live'
                  ? '머리부터 발끝까지 화면에 들어오도록 위치를 조정한 뒤 촬영해 주세요.'
                  : '사진을 확인하고 다시 촬영하거나 선택해 주세요.'
              }}
            </p>
          </div>

          <button
            class="camera-capture__close"
            type="button"
            aria-label="즉시 촬영 닫기"
            @click="emit('close')"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="m6 6 12 12M18 6 6 18" />
            </svg>
          </button>
        </header>

        <div class="camera-capture__viewport">
          <div v-if="cameraStage === 'live'" class="camera-capture__live">
            <video
              ref="videoElement"
              :class="{ 'camera-capture__video--mirrored': isFrontFacingCamera }"
              autoplay
              muted
              playsinline
              aria-label="전신 사진 카메라 미리보기"
            />

            <div v-if="isCameraStarting" class="camera-capture__state" role="status">
              <span class="camera-capture__spinner" aria-hidden="true" />
              <strong>카메라를 준비하고 있습니다.</strong>
            </div>

            <div v-else-if="cameraError" class="camera-capture__state" role="alert">
              <strong>카메라를 열지 못했습니다.</strong>
              <p>{{ cameraError }}</p>
              <button
                class="camera-capture__button camera-capture__button--secondary"
                type="button"
                @click="retryCamera"
              >
                다시 시도
              </button>
            </div>
          </div>

          <img v-else :src="capturedPreviewUrl" alt="방금 촬영한 전신 사진 미리보기" />
        </div>

        <footer class="camera-capture__actions">
          <template v-if="cameraStage === 'live'">
            <button
              class="camera-capture__button camera-capture__button--secondary"
              type="button"
              @click="emit('close')"
            >
              취소
            </button>
            <button
              class="camera-capture__button camera-capture__button--primary"
              type="button"
              :disabled="!isCameraReady"
              @click="capturePhoto"
            >
              촬영
            </button>
          </template>

          <template v-else>
            <button
              class="camera-capture__button camera-capture__button--secondary"
              type="button"
              @click="retakePhoto"
            >
              다시 촬영
            </button>
            <button
              class="camera-capture__button camera-capture__button--primary"
              type="button"
              @click="selectCapturedPhoto"
            >
              선택
            </button>
          </template>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped lang="scss">
.camera-capture {
  position: fixed;
  inset: 0;
  z-index: calc(var(--z-top) + 10);
  display: grid;
  overflow: auto;
  padding: var(--space-6);
  background: var(--color-page);
  outline: none;
  place-items: center;
}

.camera-capture__panel {
  display: grid;
  overflow: auto;
  width: min(720px, 100%);
  max-height: calc(100dvh - 48px);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-modal);
  background: var(--color-surface);
  box-shadow: 0 24px 80px rgb(0 0 0 / 45%);
}

.camera-capture__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-5);
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.camera-capture__eyebrow {
  color: var(--color-accent);
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  letter-spacing: var(--letter-spacing-label);
  text-transform: uppercase;
}

.camera-capture__header h2 {
  margin-top: var(--space-1);
  color: var(--color-text-primary);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-xl);
}

.camera-capture__header p:last-child {
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-control);
}

.camera-capture__close {
  display: grid;
  width: 40px;
  height: 40px;
  border: 1px solid var(--color-border-input);
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-text-muted);
  flex: 0 0 auto;
  cursor: pointer;
  place-items: center;
}

.camera-capture__close:hover {
  border-color: var(--color-text-primary);
  color: var(--color-text-primary);
}

.camera-capture__close:focus-visible,
.camera-capture__button:focus-visible {
  outline: 1px solid var(--color-primary);
  outline-offset: 2px;
}

.camera-capture__close svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-width: 1.8;
}

.camera-capture__viewport {
  position: relative;
  display: grid;
  min-height: 420px;
  overflow: hidden;
  background: var(--color-chrome);
  place-items: center;
}

.camera-capture__live {
  position: relative;
  display: grid;
  width: 100%;
  height: 100%;
  place-items: center;
}

.camera-capture__viewport video,
.camera-capture__viewport > img {
  width: 100%;
  max-height: 62dvh;
  aspect-ratio: 3 / 4;
  background: var(--color-chrome);
  object-fit: contain;
}

.camera-capture__video--mirrored {
  transform: scaleX(-1);
}

.camera-capture__state {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
  background: var(--color-page);
  color: var(--color-text-secondary);
  flex-direction: column;
  gap: var(--space-3);
  text-align: center;
}

.camera-capture__state strong {
  color: var(--color-text-primary);
  font-size: var(--font-size-md-plus);
}

.camera-capture__state p {
  max-width: 480px;
  line-height: var(--line-height-body);
}

.camera-capture__spinner {
  width: 32px;
  height: 32px;
  border: 2px solid var(--color-border-strong);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: camera-capture-spin 0.8s linear infinite;
}

.camera-capture__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--color-border);
}

.camera-capture__button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 120px;
  height: var(--button-height-standard);
  padding: 0 var(--space-6);
  border: 1px solid transparent;
  border-radius: var(--radius-control);
  font-weight: var(--font-weight-medium);
  line-height: 1;
  cursor: pointer;
}

.camera-capture__button--primary {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.camera-capture__button--primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.camera-capture__button--secondary {
  border-color: var(--color-border-input);
  background: transparent;
  color: var(--color-text-muted);
}

.camera-capture__button--secondary:hover:not(:disabled) {
  border-color: var(--color-text-primary);
  color: var(--color-text-primary);
}

.camera-capture__button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

@keyframes camera-capture-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 560px) {
  .camera-capture {
    padding: 0;
  }

  .camera-capture__panel {
    width: 100%;
    height: 100dvh;
    max-height: 100dvh;
    border: 0;
    border-radius: 0;
    grid-template-rows: auto minmax(0, 1fr) auto;
  }

  .camera-capture__header {
    padding: var(--space-4);
  }

  .camera-capture__viewport {
    min-height: 0;
  }

  .camera-capture__viewport video,
  .camera-capture__viewport > img {
    height: 100%;
    max-height: none;
  }

  .camera-capture__actions {
    display: grid;
    padding: var(--space-4);
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .camera-capture__button {
    width: 100%;
    min-width: 0;
  }
}
</style>
