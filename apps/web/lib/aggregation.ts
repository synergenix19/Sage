// apps/web/lib/aggregation.ts
//
// Shared aggregation helpers for the dashboard query layer (progress-queries.ts,
// admin-queries.ts). Both files independently reimplemented the same two shapes —
// "N days ago as an ISO cutoff" and "tally occurrences, rank by count descending" —
// nine times between them. This collapses those copies into one implementation each.

// ISO-8601 timestamp N days before now — the shared shape behind the SEVEN_DAYS_AGO /
// TWENTY_ONE_DAYS_AGO / THIRTY_DAYS_AGO cutoff constants. Evaluated at call time (not
// memoized), matching the original `() => new Date(...)` thunks.
export function daysAgo(n: number): string {
  return new Date(Date.now() - n * 24 * 60 * 60 * 1000).toISOString()
}

// Tallies `key(item)` occurrences across `items`, maps each distinct key to
// `shape(key, count)`, and sorts the result by count descending. `limit`, if given,
// caps the result to the top N entries. The shared shape behind every
// `Record<string, number>` accumulator + `Object.entries(...).map(...).sort((a, b) =>
// b.count - a.count)` block in progress-queries.ts and admin-queries.ts.
export function countAndRank<T, R>(
  items: T[],
  key: (item: T) => string,
  shape: (key: string, count: number) => R,
  limit?: number,
): R[] {
  const counts: Record<string, number> = {}
  for (const item of items) {
    const k = key(item)
    counts[k] = (counts[k] ?? 0) + 1
  }
  const ranked = Object.entries(counts)
    .sort(([, a], [, b]) => b - a)
    .map(([k, count]) => shape(k, count))
  return limit !== undefined ? ranked.slice(0, limit) : ranked
}
