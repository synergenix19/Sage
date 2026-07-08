// Split text into progressive-reveal chunks for the typewriter.
// Rules (spec §3.1): word-level (≤2 word-tokens/chunk), and a chunk NEVER
// straddles a text-direction change — so a partial LTR run embedded in RTL
// (or vice-versa) can't reorder already-revealed words as more land.
const RTL = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/
const LTR = /[A-Za-zÀ-ɏ]/

type Dir = 'rtl' | 'ltr' | 'neutral'
function dirOf(token: string): Dir {
  if (RTL.test(token)) return 'rtl'
  if (LTR.test(token)) return 'ltr'
  return 'neutral' // whitespace, digits, punctuation — do not force a boundary
}

const MAX_WORDS_PER_CHUNK = 2

export function chunkForReveal(text: string): string[] {
  if (!text) return []
  // Tokenize into alternating word / whitespace runs, preserving everything.
  const tokens = text.match(/\s+|\S+/g) ?? []
  const chunks: string[] = []
  let cur = ''
  let curDir: Dir = 'neutral'
  let wordCount = 0

  for (const tok of tokens) {
    const isSpace = /^\s+$/.test(tok)
    const d = isSpace ? 'neutral' : dirOf(tok)
    const flips = d !== 'neutral' && curDir !== 'neutral' && d !== curDir
    const full = wordCount >= MAX_WORDS_PER_CHUNK && !isSpace

    if (cur && (flips || full)) {
      chunks.push(cur)
      cur = ''
      curDir = 'neutral'
      wordCount = 0
    }
    cur += tok
    if (!isSpace) {
      wordCount++
      if (curDir === 'neutral') curDir = d
    }
  }
  if (cur) chunks.push(cur)
  return chunks
}
