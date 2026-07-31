#!/usr/bin/env bash
# EC2 UDP 수신/송신 버퍼 확대 (S15P11A108-448)
#
# LiveKit 이 기동 시 이렇게 경고한다.
#   WARN  UDP receive buffer is too small for a production set-up
#         {"current": 425984, "suggested": 5000000}
#
# 커널 UDP 버퍼가 작으면 트래픽이 몰릴 때 **커널이 패킷을 버린다.** WebRTC 는 UDP 로
# 미디어를 나르므로 그대로 영상 끊김·깨짐으로 드러난다. 시청자가 늘수록 심해지고,
# 애플리케이션 로그에는 아무것도 안 남아 원인을 찾기 어렵다.
#
# 호스트 커널 설정이라 컨테이너 안에서는 바꿀 수 없다. 그래서 별도 스크립트로 둔다.
#
# 멱등: 여러 번 실행해도 같은 값으로 덮어쓴다.
# 사용법: bash infra/ec2/setup-udp-buffer.sh
set -euo pipefail

TARGET=5000000
CONF=/etc/sysctl.d/99-livekit.conf

echo "=== 변경 전 ==="
sysctl net.core.rmem_max net.core.wmem_max

echo
echo "=== 즉시 적용 ==="
sudo sysctl -w net.core.rmem_max=$TARGET -w net.core.wmem_max=$TARGET

echo
echo "=== 재부팅 후에도 유지되도록 저장 ($CONF) ==="
printf 'net.core.rmem_max=%s\nnet.core.wmem_max=%s\n' "$TARGET" "$TARGET" | sudo tee "$CONF" >/dev/null
sudo sysctl --system >/dev/null
echo "  저장 완료"

echo
echo "=== 변경 후 ==="
sysctl net.core.rmem_max net.core.wmem_max

echo
echo "다음 단계: LiveKit 을 재시작해야 새 버퍼를 잡는다."
echo "  sudo docker restart vintib-livekit"
echo "  sudo docker logs vintib-livekit --tail 20 | grep -i 'buffer\\|nodeIP'"
echo "  → 'UDP receive buffer' 경고가 사라지고 nodeIP 가 공인 IP 면 정상"
