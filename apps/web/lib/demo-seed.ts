import type { MoodScore, SessionInsight } from '@cdai/types'

function seededRandom(seed: number) {
  let s = seed
  return () => { s = (s * 1664525 + 1013904223) & 0xffffffff; return (s >>> 0) / 0xffffffff }
}

export function getUserDemoData(userId: string) {
  const rand = seededRandom(userId.split('').reduce((a, c) => a + c.charCodeAt(0), 0))
  const today = new Date()

  const moodScores: MoodScore[] = Array.from({ length: 21 }, (_, i) => {
    const d = new Date(today); d.setDate(d.getDate() - (20 - i))
    // Arc: starts ~2.5, rises to ~4.0, dips at day 10-12
    const base = i < 10 ? 2.5 + i * 0.1 : i < 13 ? 3.5 - (i - 10) * 0.2 : 3.2 + (i - 13) * 0.08
    const score = Math.min(5, Math.max(1, parseFloat((base + (rand() - 0.5) * 0.4).toFixed(1))))
    return { id: `demo-mood-${i}`, userId, sessionId: `demo-session-${i}`, score, createdAt: d.toISOString() }
  })

  const topics = ['Parenting', 'Work Stress', 'Relationships', 'Sleep', 'Anxiety']
  const insights: SessionInsight[] = topics.slice(0, 3).map((tag, i) => ({
    id: `demo-insight-${i}`,
    sessionId: `demo-session-${i}`,
    userId,
    content: `You've been exploring ${tag.toLowerCase()} this week. Small steps add up — keep going.`,
    topicTag: tag,
    createdAt: new Date(today.getTime() - i * 86400000).toISOString(),
  }))

  const streak = 12

  return { moodScores, insights, topics, streak }
}
