#!/usr/bin/env bash
# scripts/extract_bot_behaviour_full.sh — full-fidelity extraction of the BOT BEHAVIOUR clinician doc.
# Source: the PINNED repo docx (never ~/Downloads — the integrity chain terminates here).
# Fingerprint (2026-07-17 source-integrity record): pandoc -f docx -t gfm => 4,661 lines,
# all 27 Skill/Format tables intact, plus a §0 trigger table per psychoed category.
# Material deviation = version drift at the chain root or a changed extraction path: STOP, reconcile.
set -euo pipefail
SRC="docs/superpowers/specs/bot-behaviour-oracle/BOT_BEHAVIOUR_ratified_source.docx"
OUT="docs/superpowers/specs/bot-behaviour-oracle/bot_behaviour_full.md"
shasum -a 256 -c docs/superpowers/specs/bot-behaviour-oracle/BOT_BEHAVIOUR_ratified_source.sha256 \
  || { echo "FATAL: pinned docx hash mismatch — chain root moved"; exit 1; }
pandoc "$SRC" -f docx -t gfm --wrap=none -o "$OUT"
LINES=$(wc -l < "$OUT")
echo "lines: $LINES (expected ~4661; hundreds off = STOP)"
SKILL_TABLES=$(grep -c 'Skill.*Format\|Format.*Offer' "$OUT" || true)
echo "skill/format table headers: $SKILL_TABLES (expected 27; wrong = STOP)"
for probe in 'Why does grief come in waves' 'Trigger Words / Recognition'; do
  grep -q "$probe" "$OUT" || { echo "FATAL: probe missing: $probe"; exit 1; }
done
# §0 trigger tables must be pipe tables for each psychoed category section.
for sec in '1f – UNDERSTANDING ANXIETY' '3c – UNDERSTANDING DEPRESSION' '4b – UNDERSTANDING EMOTIONS' \
           '6d – UNDERSTANDING ASSERTIVENESS' '7c – HOW DO I CONNECT' 'S2c – UNDERSTANDING GRIEF'; do
  awk -v s="$sec" 'index($0,s){f=1} f&&/\|/{found=1; exit} f&&/^# /{exit} END{exit !found}' "$OUT" \
    || { echo "FATAL: no pipe table after section: $sec"; exit 1; }
done
shasum -a 256 "$OUT"
