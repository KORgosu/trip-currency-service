import { describe, it, expect } from 'vitest';
import { applyIncrementsAndRerank } from '../rankingUtils';

describe('applyIncrementsAndRerank', () => {
  it('increments counts, reorders and computes deltas correctly', () => {
    const initial = [
      { country_code: 'JP', selection_count: 19, rank: 1 },
      { country_code: 'GB', selection_count: 18, rank: 2 },
      { country_code: 'US', selection_count: 15, rank: 3 }
    ];
    const prevPositions = { JP: 2, GB: 1, US: 3 }; // previous ranks

    const result = applyIncrementsAndRerank(initial, ['JP'], prevPositions);

    // JP should be incremented to 20 and remain rank 1
    expect(result[0].country_code).toBe('JP');
    expect(result[0].selection_count).toBe(20);
    expect(result[0].rank).toBe(1);
    // delta: prev JP was 2 -> now 1 => change = 1
    expect(result[0].change).toBe(1);
    expect(result[0].trend).toBe('up');

    // GB should be rank 2 with unchanged count
    expect(result[1].country_code).toBe('GB');
    expect(result[1].rank).toBe(2);

    // US stays rank 3
    expect(result[2].country_code).toBe('US');
    expect(result[2].rank).toBe(3);
  });
});
