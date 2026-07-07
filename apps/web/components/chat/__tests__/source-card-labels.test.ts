import { describe, it, expect } from 'vitest'
import type { Source } from '@cdai/types'
import { sourceLabelKey, sourceLabel } from '../source-card-labels'

const article = (i = 0): Source => ({ type: 'article', title: `a${i}`, url: `https://kb/a${i}`, citation: 'c' })
const video = (i = 0): Source => ({ type: 'video', title: `v${i}`, url: `https://youtu/v${i}`, citation: 'c' })

describe('source-card label — deterministic, keyed on actual card types', () => {
  it('all articles -> reading', () => {
    expect(sourceLabelKey([article(), article(1)])).toBe('reading')
    expect(sourceLabel([article()], 'en')).toBe('Further reading')
  })

  it('all videos -> watch', () => {
    expect(sourceLabelKey([video(), video(1)])).toBe('watch')
    expect(sourceLabel([video()], 'en')).toBe('Watch')
  })

  it('article + video -> mixed (Learn more)', () => {
    expect(sourceLabelKey([article(), video()])).toBe('mixed')
    expect(sourceLabel([article(), video()], 'en')).toBe('Learn more')
  })

  it('AR returns null (placeholder pending native review — no guessed Arabic)', () => {
    expect(sourceLabel([article()], 'ar')).toBeNull()
    expect(sourceLabel([video()], 'ar')).toBeNull()
    expect(sourceLabel([article(), video()], 'ar')).toBeNull()
  })

  it('empty sources -> null (no label)', () => {
    expect(sourceLabel([], 'en')).toBeNull()
  })
})
