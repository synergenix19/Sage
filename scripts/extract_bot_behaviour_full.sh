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
# Equivalence check vs the 2026-07-17 fingerprint: DEFAULT-wrap gfm must be exactly 4661 lines.
# (The record's 4661 was default wrap; canonical output below uses --wrap=none. See
#  2026-07-28-source-fingerprint-erratum.md for the full reconciliation.)
TMP=$(mktemp)
pandoc "$SRC" -f docx -t gfm -o "$TMP"
DW=$(wc -l < "$TMP"); rm -f "$TMP"
[ "$DW" -eq 4661 ] || { echo "FATAL: default-wrap fingerprint $DW != 4661 — chain-root drift, STOP"; exit 1; }
pandoc "$SRC" -f docx -t gfm --wrap=none -o "$OUT"
# Table population (erratum-verified): 61 pipe tables + 1 raw-HTML table (§6b merged-cell
# recognition-phrase table) = 62 total; 26 Skill/Format pipe headers (+ the §6b HTML table
# = the 07-17 record's probable 27 — inference, recorded in the erratum).
PIPE=$(grep -cE '^\|[-| ]+\|$' "$OUT"); HTML=$(grep -c '<table' "$OUT")
[ "$PIPE" -eq 61 ] && [ "$HTML" -eq 1 ] || { echo "FATAL: table population ${PIPE}pipe+${HTML}html != 61+1"; exit 1; }
SF=$(grep -c 'Skill\*\*.*Format\*\*' "$OUT")
[ "$SF" -eq 26 ] || { echo "FATAL: Skill/Format headers $SF != 26"; exit 1; }
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
