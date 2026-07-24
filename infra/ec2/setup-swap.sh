#!/usr/bin/env bash
# EC2 swap 4GB 생성 (S15P11A108-297)
#
# 단일 인스턴스에 Spring·FastAPI·PostgreSQL·Redis·(2주차)OpenVidu·GitLab Runner가
# 동거한다. 물리 메모리는 15Gi로 여유가 있으나, 러너 빌드 잡이 버스트하는 순간이나
# 예기치 못한 누수 시 OOM Killer가 컨테이너를 죽이는 것을 막는 안전망이다.
#
# 멱등: 이미 swap이 있으면 아무 것도 하지 않는다.
# 사용법: bash infra/ec2/setup-swap.sh
set -euo pipefail

SWAPFILE=/swapfile
SIZE_GB=4

if sudo swapon --show | grep -q "$SWAPFILE"; then
    echo "이미 활성화된 swap이 있습니다. 변경하지 않습니다."
    sudo swapon --show
    free -h
    exit 0
fi

echo "[1/5] ${SIZE_GB}GB swapfile 생성 ($SWAPFILE)"
# fallocate가 일부 파일시스템에서 swap에 부적합한 경우가 있어 dd로 실할당한다.
sudo dd if=/dev/zero of="$SWAPFILE" bs=1M count=$((SIZE_GB * 1024)) status=progress

echo "[2/5] 권한 600"
sudo chmod 600 "$SWAPFILE"

echo "[3/5] mkswap"
sudo mkswap "$SWAPFILE"

echo "[4/5] swapon"
sudo swapon "$SWAPFILE"

echo "[5/5] 영구 등록"
# fstab 재부팅 유지 (중복 등록 방지)
if ! grep -q "^$SWAPFILE " /etc/fstab; then
    echo "$SWAPFILE none swap sw 0 0" | sudo tee -a /etc/fstab
fi
# swappiness=10: 물리 메모리를 우선 쓰고 swap은 압박 시에만
sudo sysctl -w vm.swappiness=10
if ! grep -q "^vm.swappiness" /etc/sysctl.conf; then
    echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf
fi

echo "완료:"
sudo swapon --show
free -h
