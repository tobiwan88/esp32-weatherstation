#!/usr/bin/env bash
# Scan tracked files and the staged diff for private data (public repositories).
# Extra patterns: .privacy-patterns (gitignored, one regex per line; put names, hosts and ids there).
# Paths to skip: .privacy-ignore (committed, one git pathspec per line, e.g. vendored code or CAD files; # comments).
set -u
cd "$(dirname "$0")/.."
pat=(
  '([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}'                 # MAC address
  '192\.168\.[0-9]+\.[0-9]+|10\.[0-9]+\.[0-9]+\.[0-9]+' # LAN IP
  '/Users/[A-Za-z0-9._-]+|/home/[A-Za-z0-9._-]+'       # home path
  '/dev/cu\.usb[a-z]+-?[0-9]+'                         # serial port
  '(ssid|password|passwd|secret|api[_-]?key|token)[" ]*[:=][" ]*"[^"]{4,}"'  # credential-looking literals
  'BEGIN [A-Z ]*PRIVATE KEY'
)
[ -f .privacy-patterns ] && while IFS= read -r l; do [ -n "$l" ] && pat+=("$l"); done < .privacy-patterns
skip=(':!uv.lock' ':!scripts/privacy-check.sh' ':!hw-kit/tooling/scripts/privacy-check.sh')
[ -f .privacy-ignore ] && while IFS= read -r l; do
  case "$l" in ''|'#'*) ;; *) skip+=(":!$l") ;; esac
done < .privacy-ignore
rc=0
for p in "${pat[@]}"; do
  hits=$( { git grep -n -I -E -e "$p" -- . "${skip[@]}" ; git diff --cached -U0 | grep -E -e "^\+[^+]" | grep -E -e "$p" ; } 2>/dev/null | grep -v 'testtoken' | head -5)
  [ -n "$hits" ] && { echo "privacy: pattern /$p/"; echo "$hits" | cut -c1-160 | sed 's/^/  /'; rc=1; }
done
[ $rc -eq 0 ] && echo "privacy-check: clean" || echo "privacy-check: FINDINGS (review above)"
exit $rc
