// Pure utilities for ranking computations used by hook and tests
export function applyIncrementsAndRerank(rankingItems, countryCodes = [], prevPositions = {}) {
  if (!Array.isArray(rankingItems)) return [];
  const cloned = rankingItems.map((r) => ({ ...r, selection_count: Number(r.selection_count || 0) }));
  cloned.forEach((r) => {
    if (countryCodes.includes(r.country_code)) {
      r.selection_count = (r.selection_count || 0) + 1;
    }
  });
  cloned.sort((a, b) => (b.selection_count || 0) - (a.selection_count || 0));
  return cloned.map((r, idx) => {
    const newRank = idx + 1;
    const prevPos = prevPositions[r.country_code];
    const change = prevPos ? prevPos - newRank : 0;
    const trend = prevPos ? (change > 0 ? 'up' : (change < 0 ? 'down' : 'same')) : 'same';
    return { ...r, rank: newRank, change, trend };
  });
}
