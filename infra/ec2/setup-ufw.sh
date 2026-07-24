#!/usr/bin/env bash
# EC2 UFW 80/tcp 개방 (S15P11A108-297)
#
# Caddy가 Let's Encrypt HTTP-01 챌린지를 받고 HTTP→HTTPS 리다이렉트를 하려면
# 80이 필요하다. 443은 이미 열려 있다.
#
# ⚠️ 이 서버에는 SSAFY Gerrit(8988/8989/29418)이 함께 돈다.
#    기존 규칙(22 / 443 / 8989)은 절대 건드리지 않는다. 이 스크립트는 80만 추가한다.
#
# 멱등: 이미 80이 열려 있으면 중복 추가하지 않는다(ufw가 자체적으로 skip).
# 사용법: bash infra/ec2/setup-ufw.sh
set -euo pipefail

echo "=== 변경 전 상태 ==="
sudo ufw status verbose

echo
echo "=== 80/tcp 추가 ==="
sudo ufw allow 80/tcp comment 'HTTP - Caddy ACME + redirect (297)'

echo
echo "=== 변경 후 상태 ==="
sudo ufw status verbose

# 안전 확인: 22/443/8989가 그대로 있는지
echo
echo "=== 필수 규칙 보존 확인 ==="
for p in 22 443 8989; do
    if sudo ufw status | grep -qE "^$p[[:space:]/]"; then
        echo "  OK  $p 유지됨"
    else
        echo "  !!  $p 규칙이 보이지 않음 — 확인 필요"
    fi
done
