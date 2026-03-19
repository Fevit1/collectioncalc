// lib/valuator.js - Price lookup engine
// NO require() or module.exports - uses window global

window.Valuator = (function() {
  'use strict';

  // Grade multipliers (relative to NM 9.4 base)
  const GRADE_MULTIPLIERS = {
    10.0: 3.0,
    9.9: 2.5,
    9.8: 2.2,
    9.6: 1.5,
    9.4: 1.0,    // Base NM
    9.2: 0.85,
    9.0: 0.70,
    8.5: 0.55,
    8.0: 0.45,
    7.5: 0.38,
    7.0: 0.32,
    6.5: 0.27,
    6.0: 0.23,
    5.5: 0.20,
    5.0: 0.17,
    4.5: 0.15,
    4.0: 0.13,
    3.5: 0.11,
    3.0: 0.10,
    2.5: 0.08,
    2.0: 0.07,
    1.8: 0.06,
    1.5: 0.05,
    1.0: 0.04,
    0.5: 0.03
  };

  // Get multiplier for any grade (interpolates)
  function getGradeMultiplier(grade) {
    if (!grade) return 1.0;
    
    // Exact match
    if (GRADE_MULTIPLIERS[grade]) {
      return GRADE_MULTIPLIERS[grade];
    }
    
    // Find surrounding grades and interpolate
    const grades = Object.keys(GRADE_MULTIPLIERS)
      .map(Number)
      .sort((a, b) => b - a);
    
    for (let i = 0; i < grades.length - 1; i++) {
      if (grade <= grades[i] && grade >= grades[i + 1]) {
        const high = grades[i];
        const low = grades[i + 1];
        const ratio = (grade - low) / (high - low);
        return GRADE_MULTIPLIERS[low] + ratio * (GRADE_MULTIPLIERS[high] - GRADE_MULTIPLIERS[low]);
      }
    }
    
    return 1.0;
  }

  // Look up comic value
  function lookup(parsed) {
    if (!parsed || !parsed.series || !parsed.issue) {
      return null;
    }

    // Check if database is loaded
    if (typeof window.COMIC_DATABASE === 'undefined') {
      console.log('[Valuator] Database not loaded');
      return null;
    }

    // Try to find in database
    const key = window.ComicNormalizer.makeKey(parsed.series, parsed.issue);
    if (!key) return null;

    const entry = window.COMIC_DATABASE[key];
    if (!entry) {
      // Try alternate volumes
      for (let v = 1; v <= 5; v++) {
        const altKey = window.ComicNormalizer.makeKey(parsed.series, parsed.issue, v);
        if (window.COMIC_DATABASE[altKey]) {
          return calculateValue(window.COMIC_DATABASE[altKey], parsed.grade);
        }
      }
      return null;
    }

    return calculateValue(entry, parsed.grade);
  }

  // Calculate value with grade adjustment
  function calculateValue(entry, grade) {
    const baseNM = entry.nm;
    const multiplier = getGradeMultiplier(grade || 9.4);
    const fmv = Math.round(baseNM * multiplier);

    return {
      fmv: fmv,
      baseNM: baseNM,
      grade: grade,
      multiplier: multiplier,
      note: entry.note || null,
      tier: entry.tier || 2
    };
  }

  // Get all keys for a series
  function getSeriesKeys(series) {
    if (typeof window.COMIC_DATABASE === 'undefined') return [];
    
    const normalizedSeries = series.toLowerCase().replace(/[^a-z0-9]/g, '');
    return Object.keys(window.COMIC_DATABASE)
      .filter(key => key.startsWith(normalizedSeries))
      .map(key => {
        const match = key.match(/^(.+)-(\d+)-v(\d+)$/);
        if (match) {
          return {
            key,
            issue: parseInt(match[2]),
            volume: parseInt(match[3]),
            ...window.COMIC_DATABASE[key]
          };
        }
        return null;
      })
      .filter(Boolean)
      .sort((a, b) => a.issue - b.issue);
  }

  return {
    lookup,
    getGradeMultiplier,
    getSeriesKeys,
    GRADE_MULTIPLIERS
  };
})();
