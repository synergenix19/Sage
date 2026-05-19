export function getAdminDemoData() {
  return {
    totalUsers: 128,
    activeToday: 34,
    avgMoodScore: 3.7,
    crisisAlertsThisWeek: 2,
    moodTrend: Array.from({ length: 14 }, (_, i) => ({
      date: `Day ${i + 1}`,
      avg: parseFloat((3.2 + Math.sin(i * 0.7) * 0.6).toFixed(1)),
    })),
    topTopics: [
      { topic: 'Workplace stress', count: 42 },
      { topic: 'Family', count: 31 },
      { topic: 'Sleep', count: 28 },
      { topic: 'Anxiety', count: 24 },
      { topic: 'Relationships', count: 19 },
    ],
    recentAlerts: [
      { id: '1', userId: 'usr_demo_01', timestamp: '2026-05-20T09:14:00Z', severity: 'high' as const },
      { id: '2', userId: 'usr_demo_02', timestamp: '2026-05-19T16:33:00Z', severity: 'medium' as const },
    ],
  }
}
