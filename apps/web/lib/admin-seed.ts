export function getAdminDemoData() {
  return {
    totalUsers: 847,
    activeToday: 312,
    avgMoodScore: 3.6,
    crisisAlertsThisWeek: 2,
    moodTrend: Array.from({ length: 14 }, (_, i) => ({
      date: `Day ${i + 1}`,
      avg: parseFloat((3.2 + Math.sin(i * 0.7) * 0.6).toFixed(1)),
    })),
    topTopics: [
      { topic: 'Workplace stress', count: 187 },
      { topic: 'Family', count: 143 },
      { topic: 'Sleep', count: 121 },
      { topic: 'Anxiety', count: 98 },
      { topic: 'Relationships', count: 76 },
    ],
    districtStress: [
      { district: 'Al Quoz',       index: 78 },
      { district: 'Deira',         index: 62 },
      { district: 'Karama',        index: 58 },
      { district: 'Bur Dubai',     index: 51 },
      { district: 'Al Nahda',      index: 48 },
      { district: 'Mirdif',        index: 44 },
      { district: 'Business Bay',  index: 41 },
      { district: 'Dubai Marina',  index: 38 },
      { district: 'Al Barsha',     index: 35 },
      { district: 'Jumeirah',      index: 33 },
      { district: 'Downtown',      index: 31 },
      { district: 'Nad Al Sheba',  index: 28 },
    ],
    recentAlerts: [
      { id: '1', userId: 'usr_demo_01', district: 'Al Quoz',   timestamp: '2026-05-20T09:14:00Z', severity: 'high'   as const },
      { id: '2', userId: 'usr_demo_02', district: 'Deira',     timestamp: '2026-05-19T16:33:00Z', severity: 'medium' as const },
    ],
  }
}
