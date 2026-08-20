import { describe, it, expect } from 'vitest'
import { extractSageMetadata } from '../sage-headers'

describe('extractSageMetadata', () => {
  it('parses the basic scalar/JSON headers', () => {
    const headers = new Headers({
      'X-Sage-Intent': 'emotional',
      'X-Sage-Model': 'claude-sonnet-4-6',
      'X-Sage-Emotional-Intensity': '4',
      'X-Sage-Semantic-Score': '0.72',
      'X-Sage-Turn-Number': '3',
      'X-Sage-Token-Usage': JSON.stringify({ input: 100, output: 50 }),
    })
    const metadata = extractSageMetadata(headers)
    expect(metadata.intentClassification).toBe('emotional')
    expect(metadata.sageModel).toBe('claude-sonnet-4-6')
    expect(metadata.emotionalIntensity).toBe(4)
    expect(metadata.semanticScore).toBe(0.72)
    expect(metadata.turnNumber).toBe(3)
    expect(metadata.tokenUsage).toEqual({ input: 100, output: 50 })
  })

  it('merges a valid array X-Sage-Sources with skill-delivered media', () => {
    const kbSources = [{ type: 'article', title: 'Understanding Anxiety', url: 'https://kb/a', citation: 'c' }]
    const headers = new Headers({
      'X-Sage-Sources': JSON.stringify(kbSources),
      'X-Sage-Skill-Media': JSON.stringify({ type: 'video', title: 'Breathing', url: 'https://vid/1', provider: 'yt' }),
    })
    const metadata = extractSageMetadata(headers)
    expect(metadata.sources).toEqual([
      ...kbSources,
      { type: 'video', title: 'Breathing', url: 'https://vid/1', citation: 'yt' },
    ])
  })

  // Fix round 1 pinning test: the extraction unified the persist and render copies of the
  // X-Sage-Sources + X-Sage-Skill-Media merge, which had silently diverged — the persist
  // copy guarded the merge with `Array.isArray(parsedSources) ? parsedSources : []`, the
  // render copy had no such guard. This extraction adopted the render copy's (unguarded)
  // behavior for BOTH call sites (disclosed in the PR body): a non-array-but-valid-JSON
  // X-Sage-Sources value is left completely untouched, and the skill media entry is
  // silently NOT merged into it — no throw escapes extractSageMetadata, no crash.
  it('leaves a non-array X-Sage-Sources value untouched when skill media is also present', () => {
    const nonArraySources = { unexpected: 'shape' }
    const headers = new Headers({
      'X-Sage-Sources': JSON.stringify(nonArraySources),
      'X-Sage-Skill-Media': JSON.stringify({ type: 'video', title: 'Breathing', url: 'https://vid/1', provider: 'yt' }),
    })
    const metadata = extractSageMetadata(headers)
    expect(metadata.sources).toEqual(nonArraySources)
  })

  it('falls back to no sources when X-Sage-Sources is malformed JSON', () => {
    const headers = new Headers({ 'X-Sage-Sources': '{not valid json' })
    const metadata = extractSageMetadata(headers)
    expect(metadata.sources).toBeNull()
  })

  it('produces only the media entry when X-Sage-Sources is absent but skill media is present', () => {
    const headers = new Headers({
      'X-Sage-Skill-Media': JSON.stringify({ type: 'video', title: 'Breathing', url: 'https://vid/1', provider: 'yt' }),
    })
    const metadata = extractSageMetadata(headers)
    expect(metadata.sources).toEqual([{ type: 'video', title: 'Breathing', url: 'https://vid/1', citation: 'yt' }])
  })
})
