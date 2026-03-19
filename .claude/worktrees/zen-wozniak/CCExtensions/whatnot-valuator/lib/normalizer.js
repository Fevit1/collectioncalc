// lib/normalizer.js - Comic title parsing
// NO require() or module.exports - uses window global

window.ComicNormalizer = (function() {
  'use strict';

  // Series name mappings (abbreviations to full names)
  const SERIES_MAP = {
    // Spider-Man
    'asm': 'Amazing Spider-Man',
    'amazing spider-man': 'Amazing Spider-Man',
    'amazing spiderman': 'Amazing Spider-Man',
    'tasm': 'Amazing Spider-Man',
    'spectacular spider-man': 'Spectacular Spider-Man',
    'ssm': 'Spectacular Spider-Man',
    'web of spider-man': 'Web of Spider-Man',
    'wsm': 'Web of Spider-Man',
    'usm': 'Ultimate Spider-Man',
    'ultimate spider-man': 'Ultimate Spider-Man',
    'miles morales': 'Miles Morales Spider-Man',
    
    // X-Men
    'uxm': 'Uncanny X-Men',
    'uncanny x-men': 'Uncanny X-Men',
    'x-men': 'X-Men',
    'xmen': 'X-Men',
    'gsxm': 'Giant-Size X-Men',
    'giant size x-men': 'Giant-Size X-Men',
    'giant-size x-men': 'Giant-Size X-Men',
    'new mutants': 'New Mutants',
    'nm': 'New Mutants',
    'wolverine': 'Wolverine',
    'wolvie': 'Wolverine',
    
    // Avengers
    'avengers': 'Avengers',
    'avngrs': 'Avengers',
    'new avengers': 'New Avengers',
    'west coast avengers': 'West Coast Avengers',
    'wca': 'West Coast Avengers',
    
    // Fantastic Four
    'ff': 'Fantastic Four',
    'fantastic four': 'Fantastic Four',
    'fantastic 4': 'Fantastic Four',
    
    // Hulk
    'ih': 'Incredible Hulk',
    'incredible hulk': 'Incredible Hulk',
    'hulk': 'Incredible Hulk',
    
    // Iron Man
    'im': 'Iron Man',
    'iron man': 'Iron Man',
    'invincible iron man': 'Invincible Iron Man',
    'iim': 'Invincible Iron Man',
    'tales of suspense': 'Tales of Suspense',
    'tos': 'Tales of Suspense',
    
    // Captain America
    'cap': 'Captain America',
    'captain america': 'Captain America',
    'ca': 'Captain America',
    
    // Thor
    'thor': 'Thor',
    'journey into mystery': 'Journey Into Mystery',
    'jim': 'Journey Into Mystery',
    'mighty thor': 'Mighty Thor',
    
    // Daredevil
    'dd': 'Daredevil',
    'daredevil': 'Daredevil',
    
    // DC
    'batman': 'Batman',
    'detective comics': 'Detective Comics',
    'tec': 'Detective Comics',
    'detective': 'Detective Comics',
    'action comics': 'Action Comics',
    'action': 'Action Comics',
    'superman': 'Superman',
    'wonder woman': 'Wonder Woman',
    'ww': 'Wonder Woman',
    'flash': 'Flash',
    'green lantern': 'Green Lantern',
    'gl': 'Green Lantern',
    'justice league': 'Justice League',
    'jla': 'Justice League',
    'aquaman': 'Aquaman',
    'swamp thing': 'Swamp Thing',
    'teen titans': 'Teen Titans',
    'new teen titans': 'New Teen Titans',
    'ntt': 'New Teen Titans',
    
    // Indie
    'spawn': 'Spawn',
    'tmnt': 'Teenage Mutant Ninja Turtles',
    'teenage mutant ninja turtles': 'Teenage Mutant Ninja Turtles',
    'walking dead': 'Walking Dead',
    'twd': 'Walking Dead',
    'invincible': 'Invincible',
    'saga': 'Saga',
    'preacher': 'Preacher',
    
    // Graphic Novels
    'killing joke': 'Batman The Killing Joke',
    'the killing joke': 'Batman The Killing Joke',
    'batman killing joke': 'Batman The Killing Joke',
    'dark knight returns': 'Batman The Dark Knight Returns',
    'dkr': 'Batman The Dark Knight Returns',
    'tdkr': 'Batman The Dark Knight Returns',
    'long halloween': 'Batman The Long Halloween',
    'year one': 'Batman Year One',
    'arkham asylum': 'Arkham Asylum',
    'watchmen': 'Watchmen',
    'v for vendetta': 'V For Vendetta',
    'kingdom come': 'Kingdom Come',
    'sandman': 'Sandman',
    'civil war': 'Civil War',
    'infinity gauntlet': 'Infinity Gauntlet',
    'old man logan': 'Old Man Logan',
    'sin city': 'Sin City',
    'maus': 'Maus',
    'scott pilgrim': 'Scott Pilgrim',
    'locke & key': 'Locke & Key',
    'locke and key': 'Locke And Key',
    '300': '300',
    'akira': 'Akira',
    'dragon ball': 'Dragon Ball',
    'dragonball': 'Dragon Ball',
    'naruto': 'Naruto',
    'one piece': 'One Piece',
    'onepiece': 'One Piece',
    'attack on titan': 'Attack On Titan',
    'something is killing the children': 'Something Is KillIng The Children',
    'siktc': 'SIKTC'
  };

  // Grade patterns
  const GRADE_PATTERNS = [
    /(\d+\.?\d*)\s*(cgc|cbcs|pgx)/i,           // 9.8 CGC
    /(cgc|cbcs|pgx)\s*(\d+\.?\d*)/i,           // CGC 9.8
    /grade[d]?\s*(\d+\.?\d*)/i,                // Graded 9.8
    /\b(10|9\.\d|8\.\d|7\.\d|6\.\d|5\.\d|4\.\d|3\.\d|2\.\d|1\.\d|0\.\d)\b/  // Raw grade
  ];

  // Issue number patterns
  const ISSUE_PATTERNS = [
    /#\s*(\d+)/,                               // #300
    /issue\s*#?\s*(\d+)/i,                     // Issue 300
    /\bno\.?\s*(\d+)/i,                        // No. 300
    /\bvol\.?\s*\d+\s*#?\s*(\d+)/i,           // Vol 1 #300
    /\b(\d+)\s*(?:cgc|cbcs|pgx|1st|key)/i     // 300 CGC or 300 1st
  ];

  function parse(title, subtitle = '') {
    const combined = `${title} ${subtitle}`.toLowerCase();
    const result = {
      raw: title,
      series: null,
      issue: null,
      grade: null,
      variant: null,
      slabbed: false,
      publisher: null
    };

    // Check if slabbed
    result.slabbed = /cgc|cbcs|pgx/i.test(combined);

    // Extract grade
    for (const pattern of GRADE_PATTERNS) {
      const match = combined.match(pattern);
      if (match) {
        const gradeStr = match[1].match(/\d+\.?\d*/) ? match[1] : match[2];
        const grade = parseFloat(gradeStr);
        if (grade >= 0.5 && grade <= 10) {
          result.grade = grade;
          break;
        }
      }
    }

    // Extract issue number
    for (const pattern of ISSUE_PATTERNS) {
      const match = combined.match(pattern);
      if (match) {
        result.issue = parseInt(match[1]);
        break;
      }
    }

    // Match series name
    for (const [key, fullName] of Object.entries(SERIES_MAP)) {
      if (combined.includes(key)) {
        result.series = fullName;
        break;
      }
    }

    // Detect publisher
    if (result.series) {
      const marvelSeries = ['Amazing Spider-Man', 'X-Men', 'Uncanny X-Men', 'Avengers', 
        'Fantastic Four', 'Incredible Hulk', 'Iron Man', 'Captain America', 'Thor',
        'Daredevil', 'New Mutants', 'Wolverine'];
      const dcSeries = ['Batman', 'Detective Comics', 'Action Comics', 'Superman',
        'Wonder Woman', 'Flash', 'Green Lantern', 'Justice League', 'Aquaman', 'Swamp Thing'];
      
      if (marvelSeries.some(s => result.series.includes(s))) {
        result.publisher = 'Marvel';
      } else if (dcSeries.some(s => result.series.includes(s))) {
        result.publisher = 'DC';
      } else {
        result.publisher = 'Indie';
      }
    }

    // Check for variant
    if (/variant|newsstand|direct|2nd print|second print|reprint/i.test(combined)) {
      result.variant = true;
    }

    return result;
  }

  // Generate lookup key
  function makeKey(series, issue, volume = 1) {
    if (!series || !issue) return null;
    const normalized = series.toLowerCase().replace(/[^a-z0-9]/g, '');
    return `${normalized}-${issue}-v${volume}`;
  }

  return {
    parse,
    makeKey,
    SERIES_MAP
  };
})();
