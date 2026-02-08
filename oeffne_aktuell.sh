#!/bin/bash
cd "$(dirname "$0")"
JAHR=$(date +%Y)
MONAT=$(date +%m)
open "termine_re_${JAHR}_${MONAT}.html"
