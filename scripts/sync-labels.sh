#!/usr/bin/env bash
#
# 레포 라벨을 종류 라벨 + 영역 라벨 세트로 맞춘다.
#
# 사용법:
#   ./scripts/sync-labels.sh <OWNER>/<REPO>           # 라벨 생성 · 갱신
#   ./scripts/sync-labels.sh --prune <OWNER>/<REPO>   # GitHub 기본 라벨도 정리
#
# 요구사항: gh CLI 로그인 (`gh auth status`)

set -euo pipefail

PRUNE=false
if [[ "${1:-}" == "--prune" ]]; then
  PRUNE=true
  shift
fi

REPO="${1:?레포를 지정하세요. 예: ./scripts/sync-labels.sh my-org/my-repo}"

# name|color|description
LABELS=(
  "bug|d73a4a|버그"
  "enhancement|a2eeef|기능 추가 · 개선"
  "task|c5def5|리팩터링 · 설정 · 문서 등 일반 작업"
  "docs|0075ca|문서"
  "fe|fbca04|프론트엔드 (apps/fe)"
  "be|5319e7|백엔드 (apps/be)"
  "infra|bfd4f2|인프라 · CI"
)

# 안 쓰는 GitHub 기본 라벨 (--prune 옵션일 때만 삭제)
STALE_LABELS=(
  "documentation" "duplicate" "good first issue"
  "help wanted" "invalid" "question" "wontfix"
)

command -v gh >/dev/null || { echo "gh CLI가 필요합니다: https://cli.github.com"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh 로그인이 필요합니다: gh auth login"; exit 1; }

echo "→ $REPO"
for entry in "${LABELS[@]}"; do
  IFS='|' read -r name color desc <<< "$entry"
  gh label create "$name" -R "$REPO" -c "$color" -d "$desc" --force >/dev/null
  echo "   + $name"
done

if [[ "$PRUNE" == true ]]; then
  for name in "${STALE_LABELS[@]}"; do
    if gh label delete "$name" -R "$REPO" --yes >/dev/null 2>&1; then
      echo "   - $name"
    fi
  done
fi

echo "완료."
