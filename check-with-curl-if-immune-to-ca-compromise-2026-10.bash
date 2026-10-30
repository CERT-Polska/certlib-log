#!/usr/bin/env bash

set -Eu

export emudhra_ca_compromise_test_urls="https://dv-g3b-emudhra.we-have-a-problem.com/ https://dv-g3c-emudhra.we-have-a-problem.com/ https://ov-g3b-emudhra.we-have-a-problem.com/ https://ov-g3c-emudhra.we-have-a-problem.com/ https://ev-g3b-emudhra.we-have-a-problem.com/ https://ev-g3c-emudhra.we-have-a-problem.com/ https://dv-g3b-aaa-emudhra.we-have-a-problem.com/ https://dv-g3c-aaa-emudhra.we-have-a-problem.com/ https://ov-g3b-aaa-emudhra.we-have-a-problem.com/ https://ov-g3c-aaa-emudhra.we-have-a-problem.com/ https://ev-g3b-aaa-emudhra.we-have-a-problem.com/ https://ev-g3c-aaa-emudhra.we-have-a-problem.com/ https://dv-g3b-noct-emudhra.we-have-a-problem.com/ https://dv-g3b-aaa-noct-emudhra.we-have-a-problem.com/"

emudhra_ca_compromise_test_bad_news=0

for url in ${emudhra_ca_compromise_test_urls}; do
  printf 'Requesting "%s" with curl... ' "$url"

  curl \
    --fail \
    --silent \
    --show-error \
    --connect-timeout 10 \
    --max-time 30 \
    -- "$url" > /dev/null 2>&1

  rc=$?

  case "$rc" in
    60)
      echo 'OK, certificate verification failed as expected.'
      continue
      ;;
    0)
      echo 'NOT GOOD, WE ARE VULNERABLE! (request did not fail)' >&2
      emudhra_ca_compromise_test_bad_news=1
      continue
      ;;
    *)
      printf 'TEST NOT PERFORMED PROPERLY! (unrecognized error; curl exit code: %s)\n' "$rc" >&2
      emudhra_ca_compromise_test_bad_news=1
      continue
      ;;
  esac
done

if (( emudhra_ca_compromise_test_bad_news == 0 )); then
  echo 'OK, everything went as expected. It looks like we are secure.'
else
  echo 'DANGER! For some request, certificate verification did not properly fail!' >&2
fi

exit "$emudhra_ca_compromise_test_bad_news"
