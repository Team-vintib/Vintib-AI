#!/usr/bin/env bash
# EC2 UFW WebRTC 미디어 포트 개방 (S15P11A108-448)
#
# LiveKit(OpenVidu v3 미디어 코어)이 브라우저와 직접 주고받는 스트림용 포트다.
# 시그널링(7880)은 열지 않는다 — Caddy 가 443 에서 /rtc·/twirp 로 프록시한다.
#
#   7885/udp  미디어 (UDP mux). 기본 50000-60000 범위 대신 단일 포트로 묶었다
#   7881/tcp  미디어 TCP 폴백. UDP 가 막힌 망의 시청자용
#
# ⚠️ Docker 는 포트 publish 시 iptables 를 직접 조작해 UFW 를 우회한다.
#    즉 compose 가 뜨면 이 두 포트는 UFW 규칙과 무관하게 이미 외부에 열린다.
#    그래도 규칙을 넣는 이유는 **UFW status 가 서버의 실제 개방 상태를 보여주게** 하기
#    위해서다. 여기 없으면 나중에 "왜 이 포트가 열려 있지?" 하고 원인을 못 찾는다.
#
# ⚠️ 이 서버에는 SSAFY Gerrit(8988/8989/29418)이 함께 돈다.
#    기존 규칙(22 / 80 / 443 / 8989)은 절대 건드리지 않는다.
#
# 멱등: 이미 열려 있으면 ufw 가 중복 추가를 skip 한다.
# 사용법: bash infra/ec2/setup-ufw-media.sh
set -euo pipefail

echo "=== 변경 전 상태 ==="
sudo ufw status verbose

echo
echo "=== WebRTC 미디어 포트 추가 ==="
sudo ufw allow 7885/udp comment 'WebRTC media UDP mux - LiveKit (448)'
sudo ufw allow 7881/tcp comment 'WebRTC media TCP fallback - LiveKit (448)'

echo
echo "=== 변경 후 상태 ==="
sudo ufw status verbose

# 안전 확인: 기존 규칙이 그대로인지
echo
echo "=== 필수 규칙 보존 확인 ==="
for p in 22 80 443 8989; do
    if sudo ufw status | grep -qE "^$p[[:space:]/]"; then
        echo "  OK  $p 유지됨"
    else
        echo "  !!  $p 규칙이 보이지 않음 — 확인 필요"
    fi
done

echo
echo "=== 미디어 포트 확인 ==="
for p in 7885 7881; do
    if sudo ufw status | grep -qE "^$p[[:space:]/]"; then
        echo "  OK  $p 추가됨"
    else
        echo "  !!  $p 추가 실패"
    fi
done

echo
echo "다음 단계: 컨테이너를 띄운 뒤 실제로 열렸는지 확인한다."
echo "  sudo ss -ulnp | grep 7885"
echo "  sudo ss -tlnp | grep 7881"
