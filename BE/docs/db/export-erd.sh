#!/usr/bin/env bash
# ERD 다이어그램 이미지 export (S15P11A108-52)
#
# erd.md 안의 mermaid 블록을 그대로 뽑아 SVG·PNG 로 렌더링한다.
# 다이어그램 원본은 어디까지나 erd.md 다 — 이미지는 파생물이므로 직접 편집하지 않는다.
#
# GitLab·Notion 은 mermaid 를 자체 렌더링하므로 문서를 읽는 데는 이미지가 필요 없다.
# 이 스크립트는 발표자료·산출물 페이지처럼 mermaid 를 못 쓰는 곳을 위한 것이다.
#
# 사용법 (레포 루트에서): bash BE/docs/db/export-erd.sh
# 전제: Node.js (mermaid-cli 를 npx 로 내려받는다. 최초 실행 시 Chromium 다운로드로 수 분 소요)

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$DIR/erd.md"
OUT="$DIR/img"
MMDC="@mermaid-js/mermaid-cli@11"

# erd.md 의 mermaid 블록 순서 → 출력 파일명
NAMES=(erd-full erd-bid-core product-status)

mkdir -p "$OUT"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "erd.md 에서 mermaid 블록 추출"
awk -v tmp="$TMP" '
/^```mermaid$/ { n++; inb=1; f=tmp "/block" n ".mmd"; next }
/^```$/ && inb { inb=0; next }
inb { print > f }
' "$SRC"

i=0
for f in "$TMP"/block*.mmd; do
    name="${NAMES[$i]:-diagram$((i+1))}"
    echo "  $name ← $(basename "$f")"
    # PNG 는 폭을 크게 잡아야 글자가 뭉개지지 않는다 (전체 ERD 는 가로가 길다)
    npx -y "$MMDC" -i "$f" -o "$OUT/$name.svg" >/dev/null
    npx -y "$MMDC" -i "$f" -o "$OUT/$name.png" -w 3200 -b white >/dev/null
    i=$((i+1))
done

echo "완료:"
ls -1 "$OUT"
