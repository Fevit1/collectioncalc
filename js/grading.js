// ============================================
// GRADE MY COMIC MODE - JavaScript
// Add this to the END of app.js
// ============================================

// Device detection
const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

// Grading state
let gradingState = {
    currentStep: 1,
    photos: {
        1: null,  // front cover (required)
        2: null,  // spine
        3: null,  // back
        4: null   // centerfold
    },
    additionalPhotos: [],
    extractedData: null,  // from front cover
    defectsByArea: {},
    finalGrade: null,
    confidence: 0
};

// =================================================================
// DEV MODE TESTING FUNCTIONALITY
// =================================================================

function isDevMode() {
    return window.location.hostname === 'localhost' || 
           window.location.search.includes('?dev') ||
           window.location.search.includes('&dev');
}

function createDevTestButton() {
    if (!isDevMode()) return;
    
    // Create test button
    const testButton = document.createElement('button');
    testButton.id = 'devTestButton';
    testButton.innerHTML = '🧪 Quick Test (Dev Mode)';
    testButton.style.cssText = `
        position: fixed;
        top: 10px;
        right: 10px;
        z-index: 9999;
        background: #10b981;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 12px;
        cursor: pointer;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    `;
    
    testButton.addEventListener('click', runQuickTest);
    document.body.appendChild(testButton);
}

async function runQuickTest() {
    console.log('🧪 Running dev mode quick test...');
    
    // Note: No setMode('grading') call — user is already on the grading tab
    // when this button is visible. setMode targets DOM elements that don't exist.
    
    // Mock extracted data
    gradingState.extractedData = {
        title: "Amazing Spider-Man",
        issue: "300",
        publisher: "Marvel",
        year: "1988",
        printing: "1st",
        cover: "",
        variant: "",
        edition: "",
        issue_type: "Regular"
    };
    
    // Mock grade result data
    const mockGradeResult = {
        'COMIC IDENTIFICATION': {
            title: "Amazing Spider-Man",
            issue: "300"
        },
        'COMPREHENSIVE GRADE': {
            grade_label: "VF",
            final_grade: 8.0,
            grade_reasoning: "Mock test data - Corner wear visible, spine stress present, but overall solid copy"
        },
        confidence: 85,
        defects: [
            "Minor corner wear (top right front cover)",
            "Light spine stress",
            "Small color breaking on spine"
        ]
    };
    
    // Jump to step 5 (report) so recommendation elements are visible
    for (let i = 1; i <= 4; i++) {
        const content = document.getElementById(`gradingContent${i}`);
        const step = document.getElementById(`gradingStep${i}`);
        if (content) content.classList.remove('active');
        if (step) {
            step.classList.remove('active');
            step.classList.add('completed');
        }
    }
    const step5 = document.getElementById('gradingStep5');
    const content5 = document.getElementById('gradingContent5');
    if (step5) step5.classList.add('active');
    if (content5) content5.classList.add('active');
    gradingState.currentStep = 5;
    
    // Populate grade display with mock data
    const gradeReportComic = document.getElementById('gradeReportComic');
    const gradeResultBig = document.getElementById('gradeResultBig');
    const gradeResultLabel = document.getElementById('gradeResultLabel');
    const gradePhotosUsed = document.getElementById('gradePhotosUsed');
    const defectsList = document.getElementById('defectsList');
    
    if (gradeReportComic) gradeReportComic.innerHTML = `<div class="comic-title-big">Amazing Spider-Man #300</div>`;
    if (gradeResultBig) gradeResultBig.textContent = '8.0';
    if (gradeResultLabel) gradeResultLabel.textContent = 'VF (Very Fine)';
    if (gradePhotosUsed) gradePhotosUsed.innerHTML = '🧪 <em>Dev mode — mock data (no photos)</em>';
    if (defectsList) {
        defectsList.innerHTML = mockGradeResult.defects
            .map(d => `<li>${d}</li>`).join('');
    }
    
    // Scroll to report section
    const reportSection = content5 || document.getElementById('recommendationVerdict');
    if (reportSection) {
        reportSection.scrollIntoView({ behavior: 'smooth' });
    }
    
    // Run the recommendation calculation (tests cache warning + valuation flow)
    await calculateGradingRecommendation(mockGradeResult);
}

// Initialize dev mode when page loads
document.addEventListener('DOMContentLoaded', () => {
    if (isDevMode()) {
        console.log('🧪 Dev mode enabled - Quick test button available');
        createDevTestButton();
    }
});

// =================================================================
// END DEV MODE TESTING
// =================================================================

// Thinking progress messages (shown during valuation)
const thinkingMessages = [
    "Running battle simulation 1,219: Hulk vs. Superman",
    "Debating whether Batman could beat Iron Man (spoiler: it\'s complicated)",
    "Cross-referencing the Marvel Cinematic Universe timeline",
    "Asking Jarvis for a second opinion",
    "Checking if Deadpool broke the fourth wall in this issue",
    "Consulting the Batcomputer",
    "Verifying if this variant is rarer than Wolverine\'s temper",
    "Calculating the odds of finding Waldo in this comic",
    "Asking Nick Fury if this is classified",
    "Checking if this issue is worthy of Mjolnir",
    "Checking if Galactus would eat this comic",
    "Checking if this comic has plot armor",
    "Calculating how many Spider-Verse variants exist of this",
    "Checking if the Watcher is watching",
    "Determining if this is more valuable than vibranium",
    "Verifying if Thanos would approve of this investment",
    "Checking if the Infinity Gauntlet is in stock",
    "Calculating the tensile strength of Spider-Man\'s webs",
    "Consulting the Daily Planet archives",
    "Verifying if this comic is canon",
    "Checking Professor X\'s mental database",
    "Calculating how many Ant-Men could fit in this comic",
    "Determining if this predates Crisis on Infinite Earths",
    "Checking if Stan Lee has a cameo",
    "Determining if this comic survived the snap",
    "Consulting the Fortress of Solitude database",
    "Calculating the speed force required to read this instantly",
    "Verifying if this predates the New 52 reboot",
    "Determining if this is canon in 616 or just Ultimate Universe",
    "Consulting the Book of Vishanti",
    "Verifying if this survived House of M",
    "Consulting the Green Lantern Corps database",
    "Checking if this comic is faster than the Flash",
    "Calculating the power level (it\'s over 9000)",
    "Checking if this comic is streets ahead",
    "Snakes! It had to be snakes! Oh wait, that\'s python, ha.",
    "Running Java to check if this comic is grounds for investment",
    "Checking C++ to see if this comic\'s value will increase",
    "Using Ruby to evaluate this gem of a comic",
    "Consulting Swift about whether this is a quick flip",
    "Running Rust to check if this old comic still holds value",
    "Checking Go routines to see where this comic\'s price is heading",
    "Using Kotlin to see if this Java alternative is valuable",
    "Running Perl to find hidden value patterns",
    "Checking if this comic\'s worth is written in the stars (or JavaScript)",
    "Using TypeScript to verify this comic\'s type safety rating",
    "Running BASIC to get back to fundamentals on this one",
    "Consulting Assembly language to understand this at machine level",
    "Checking COBOL records from when this comic was new",
    "Using Fortran to calculate if this formula works",
    "Running Pascal to see if this passes muster",
    "Checking Scratch to see if we\'re starting from zero",
    "Using R to run statistical analysis on variant sales",
    "Consulting SQL: SELECT * FROM comics WHERE value > expectations",
    "Running MongoDB to store all these variant databases",
    "Checking Redis cache for faster lookup times",
    "Querying the Arkham Asylum patient database",
    "SELECT * FROM xmen WHERE powers LIKE \'awesome%\'",
    "Running database migration: Earth-1 to Earth-Prime",
    "Checking blockchain for immutable comic provenance",
    "Mining cryptocurrency: BitCoin vs. BatCoin",
    "Updating the cloud: Stark Industries vs. Wayne Enterprises servers",
    "Running NoSQL query on the Negative Zone",
    "Checking distributed systems: Multiverse load balancing",
    "Executing stored procedure: sp_Grade_Comic_Book",
    "Sharding the Infinity Stones across multiple databases",
    "Debugging with Spider-Sense (much more reliable than print statements)",
    "Running unit tests with the Justice League\'s approval",
    "Checking code coverage: Does this comic cover all key issues?",
    "Executing regression tests (did this comic regress in value?)",
    "Running integration tests with Avengers: Assemble() function",
    "Checking for memory leaks in Professor X\'s mind palace",
    "Deploying to production: From Danger Room to real world",
    "Rolling back changes (Time Stone activated)",
    "Running continuous integration through the Speed Force",
    "Checking Docker containers: Are Pym Particles involved?",
    "Calculating bandwidth: Can the Flash stream this value data?",
    "Checking latency: How fast can Quicksilver deliver this info?",
    "Measuring throughput: Hulk smash or delicate handling?",
    "Testing scalability: Can this value grow like Giant-Man?",
    "Checking elasticity: Is this as flexible as Reed Richards?",
    "Measuring resilience: Wolverine\'s healing factor applied to comics",
    "Testing fault tolerance: How many hits can this comic take?",
    "Checking redundancy: Multiple Spider-People in one universe",
    "Measuring availability: Is this comic available in your dimension?",
    "Testing performance: Superman speed vs. regular shipping",
    "Scanning for malware: Checking if this comic contains Brainiac code",
    "Running antivirus: Defending against the Sinister Six",
    "Checking firewall: Can this keep out Darkseid?",
    "Testing encryption: Is this protected by Doctor Strange\'s spells?",
    "Running penetration tests: Can Ant-Man find vulnerabilities?",
    "Checking for ransomware: Is this held hostage by the Joker?",
    "Scanning for phishing: Is this legit or a Mystique impersonation?",
    "Running DDoS protection: Defending against Ultron\'s bot army",
    "Checking SSL certificate: Verified by S.H.I.E.L.D.",
    "Testing two-factor authentication: Retinal scan + fingerprint (or web-shooter)",
    "Training neural network on variant cover patterns",
    "Running machine learning: Teaching AI to grade like CGC",
    "Checking deep learning model: Can it tell a Kirby from a Lee?",
    "Running natural language processing on Stan Lee\'s dialogue",
    "Training random forest: Groot approved methodology",
    "Running gradient descent to find optimal price point",
    "Checking support vector machines: Supported by Wakandan tech",
    "Running k-means clustering on comic genres",
    "Executing backpropagation through the Speed Force",
    "Training GAN to generate realistic comic valuations",
    "Running reinforcement learning: Tony Stark\'s trial-and-error method",
    "Checking transformer models: More than meets the eye",
    "Running LSTM networks: Long short-term memory of comic history",
    "Executing attention mechanism: Where should collectors focus?",
    "Training convolutional neural networks on cover art",
    "Deploying to AWS: Amazing Wakanda Services",
    "Checking Azure hosting: Asgardian Zero-day Unified Resources Environment",
    "Running Google Cloud: Groot\'s Online Operations Database",
    "Deploying microservices to the Microverse",
    "Checking serverless functions in the Phantom Zone",
    "Running Kubernetes cluster in the Negative Zone",
    "Deploying containers to the Quantum Realm",
    "Checking load balancer at the Bifrost bridge",
    "Running auto-scaling in Ant-Man\'s lab",
    "Deploying edge computing at the edge of the universe",
    "Checking git history across multiple timelines",
    "Running git merge: Combining Earth-1 and Earth-2",
    "Executing git rebase: Resetting to Crisis on Infinite Earths",
    "Checking git branches: How many universes exist?",
    "Running git cherry-pick: Selecting best moments from each reality",
    "Executing git stash: Hiding this variant in another dimension",
    "Checking commit history: Who changed the timeline?",
    "Running pull request: Bringing changes from alternate reality",
    "Checking merge conflicts: Which Earth is the real one?",
    "Executing git reset --hard: Reality Stone activated",
    "Calling Avengers API: POST /assemble",
    "Checking Justice League endpoint: GET /unite",
    "Running X-Men REST service: PUT /cerebro/locate",
    "Executing Fantastic Four GraphQL query",
    "Calling Guardians API: PATCH /galaxy/protect",
    "Checking Teen Titans webhook callback",
    "Running S.H.I.E.L.D. SOAP service (yes, still using SOAP)",
    "Executing Wakandan API: Advanced REST with vibranium headers",
    "Calling Bat-Signal API: Emergency POST request",
    "Running Spider-API: Web services at their finest",
    "Checking HTTP status: 200 OK or 404 Hero Not Found",
    "Running TCP handshake with the Speed Force",
    "Checking UDP broadcast: No acknowledgment needed (too fast)",
    "Testing WebSocket connection to the Web-Head",
    "Running FTP: Faster Than (The) Flash Protocol",
    "Checking DNS lookup: Domain Name Superhero",
    "Testing SMTP: Superhero Mail Transfer Protocol",
    "Running HTTPS: HyperText Transfer Protocol, Stark-secured",
    "Checking SSH: Secure Shell through Quantum Tunnel",
    "Testing VPN: Virtual Phantom (Zone) Network",
    "Checking RAM: Remember All Mutations (Cerebro model)",
    "Testing CPU: Crime-fighting Processing Unit",
    "Running GPU calculations: Gamma-ray Processing Unit",
    "Checking SSD: Super Soldier Drive",
    "Testing motherboard: The Mother Box (New Gods edition)",
    "Running BIOS: Basic Input/Output S.H.I.E.L.D.",
    "Checking ethernet: Is it wired like Spider-Man\'s webs?",
    "Testing Bluetooth: Better than Bat-Signal for short range",
    "Running Wi-Fi scan: Wireless Fidelity to the Mission",
    "Checking USB: Universal Superhero Bus",
    "Running binary search through the Batcave",
    "Executing bubble sort on Aquaman\'s domain",
    "Checking quicksort with the Speed Force",
    "Running merge sort across parallel Earths",
    "Executing heap sort in the Savage Land",
    "Checking radix sort on radioactive readings",
    "Running breadth-first search of the Multiverse",
    "Executing depth-first search of the Dark Dimension",
    "Checking Dijkstra\'s shortest path to the Fortress of Solitude",
    "Running A* pathfinding through the Negative Zone",
    "Booting Windows: Wayne Industries Network Deployment Operating",
    "Running Linux: League Installation Nexus for United X-men",
    "Checking MacOS: Mutant Avengers Cataloging Operating System",
    "Testing Android: Automated Network of Defensive Robot Operations Inline Database",
    "Running iOS: Intelligence Operations System (by Stark)",
    "Checking Chrome OS: Cybernetic Hero Response and Operations Management Efficiency System",
    "Testing Unix: United Nations of Infinite X-dimensions",
    "Running Ubuntu: United Brotherhood of United New Tactical Units",
    "Checking Debian: Defensive Emergency Backup Intelligence and Analysis Network",
    "Testing Fedora: Federation of Enhanced Defense Operations and Response Activities",
    "Parsing XML: X-Men Markup Language",
    "Checking JSON: Justice System Object Notation",
    "Running YAML: Yet Another Mutant Language",
    "Testing HTML: Hero Team Markup Language",
    "Checking CSS: Costume Styling Sheets",
    "Running Bootstrap: Bat-suit Optimized Operations and Tactical Suit Tactical Response Applications Program",
    "Testing React components: Tony Stark\'s reactive armor",
    "Checking Angular framework: Doctor Strange\'s angles",
    "Running Vue.js: Multiple perspectives across universes",
    "Testing Node.js: Network of Defenders, event-driven JavaScript System",
    "Checking if this survived Flashpoint Paradox",
    "Running analysis: Pre or post-Secret Wars?",
    "Verifying timeline: Before or after Age of Ultron?",
    "Checking continuity: Post-Infinite Crisis calculations",
    "Running assessment: Impact of Dark Nights Metal",
    "Verifying era: Golden Age cache vs. Modern metadata",
    "Checking storyline: Part of Blackest Night database?",
    "Running correlation: Civil War market impact analysis",
    "Verifying continuity: House of X/Powers of X reboot",
    "Checking timeline: Pre or post-Rebirth?",
    "Running code review with Kirby\'s attention to detail",
    "Checking coding standards: Would Stan Lee approve?",
    "Testing with Jim Lee\'s precision",
    "Running peer review through the Romita lens",
    "Checking quality assurance: Frank Miller style",
    "Testing maintainability: Alan Moore complexity level",
    "Running documentation check: Neil Gaiman thoroughness",
    "Checking technical debt: Todd McFarlane\'s backlog",
    "Testing scalability: George Perez panel count",
    "Running refactor analysis: John Byrne reboot methodology",
    "Running Bloomberg Terminal for Comic Books",
    "Checking Wall Street Journal: Wakanda Street Edition",
    "Testing stock market: NASDAQ for capes and cowls",
    "Running Forex: Foreign (Universe) Exchange",
    "Checking crypto wallet: BitCapes vs. Ethereum",
    "Testing high-frequency trading on variant covers",
    "Running derivatives market: Options on first appearances",
    "Checking futures market: Will this increase in value?",
    "Testing commodities: Trading in vibranium and adamantium",
    "Running hedge fund analysis: Hedging against universe reboots",
    "Running acceptance tests: Would CGC accept this?",
    "Checking user acceptance: Collector approval rating",
    "Testing smoke tests: Any signs of fire damage?",
    "Running sanity tests: Is this valuation sane?",
    "Checking integration: How does this fit in your collection?",
    "Testing system: Does this system work for grading?",
    "Running stress tests: Can this withstand scrutiny?",
    "Checking load tests: Heavy speculation on this one",
    "Testing edge cases: What about that corner wear?",
    "Running boundary tests: Pushing grading limits",
    "Checking if this is in mint condition or just minty fresh",
    "Running diagnostics: Near Mint or Near Miss?",
    "Testing state: Very Fine or Very Finagled?",
    "Checking status: Good condition or just good enough?",
    "Running assessment: Fair grade or fair-weather grade?",
    "Testing quality: Poor condition or poorly handled?",
    "Checking integrity: Structural or purely cosmetic?",
    "Running validation: Authenticated or just anticipated?",
    "Testing verification: Certified or just certifiable?",
    "Checking confirmation: Verified or just very fied?",
    "if (comic.value > expectations) { return \'JACKPOT\'; }",
    "while (analyzing) { console.log(\'Still thinking...\'); }",
    "try { gradeComic(); } catch (UnexpectedDefect e) { }",
    "for (let variant in multiverse) { checkValue(variant); }",
    "switch(publisher) { case \'Marvel\': case \'DC\': return \'valuable\'; }",
    "const grade = comic.condition >= 9.8 ? \'MINT\' : \'meh\';",
    "async function calculateValue() { await longThought(); }",
    "Promise.all([frontCover, backCover, spine]).then(grade)",
    "Array.from(defects).filter(d => d.severity > 5)",
    "Object.keys(comic).includes(\'signature\') ? \'BONUS\' : \'standard\'",
    "Checking version: Pre-Crisis v1.0 or Post-Crisis v2.0",
    "Running release candidate: Is this the One More Day patch?",
    "Testing beta version: Civil War II early access",
    "Checking stable release: Has continuity settled?",
    "Running hotfix: Emergency Rebirth patch applied",
    "Testing patch notes: What changed in this reprint?",
    "Checking changelog: Infinite Earths modification history",
    "Running version control: Which Earth is canonical?",
    "Testing rollback: Can we undo this storyline?",
    "Checking deprecation: Is this now non-canon?",
    "Checking Slack channel: #avengers-assemble",
    "Running Zoom meeting with the Justice League",
    "Testing Microsoft Teams: X-Men collaboration suite",
    "Checking Jira board: Current missions and sprints",
    "Running Confluence wiki: S.H.I.E.L.D. documentation",
    "Testing Trello cards: Organize missions by priority",
    "Checking Asana tasks: What\'s on the docket today?",
    "Running Basecamp: Establishing hero headquarters online",
    "Testing Monday.com workflow: This week in superheroics",
    "Checking GitHub issues: Bug reports from the field",
    "Running sentiment analysis on Deadpool\'s inner monologue",
    "Checking image recognition: Can it identify Clark Kent?",
    "Testing voice recognition: Shazam! (the wizard, not the app)",
    "Running facial recognition: Even with the mask on?",
    "Checking optical character recognition on ancient texts",
    "Testing pattern matching across variant covers",
    "Running anomaly detection: This comic seems sus",
    "Checking time series analysis across publication dates",
    "Testing correlation analysis: Sales vs. movie releases",
    "Running predictive analytics: Will this be valuable?",
    "Checking SEO: Search Engine Optimization for Superheroes",
    "Running SEM: Search Engine Marketing in the Multiverse",
    "Testing PPC: Pay-Per-Click or Pym Particle Conversion?",
    "Checking CTR: Click-Through Rate or Crime-Thwarting Rate?",
    "Running analytics: Google Analytics for Gotham",
    "Testing conversion rate: Humans to superheroes",
    "Checking bounce rate: How many villains bounced off?",
    "Running A/B testing: Costume A or Costume B?",
    "Testing landing page: Where did the hero land?",
    "Checking backlinks: Who links to the Daily Planet?",
    "Running legacy system: Golden Age infrastructure",
    "Checking compatibility: Silver Age vs. Modern Age code",
    "Testing migration: Moving from Bronze to Modern",
    "Running modernization: Updating Golden Age logic",
    "Checking refactoring: How many reboots can we handle?",
    "Testing backwards compatibility with Earth-2",
    "Running sunset procedures on discontinued characters",
    "Checking technical debt from the 1940s",
    "Testing platform migration across ages",
    "Running data warehouse from every comic era",
    "Running iOS app: Iron-man Operating System",
    "Testing Android: Algorithmic Network for Droid Response Operations Intelligence Network Database",
    "Checking responsive design: Does this work on all devices?",
    "Running mobile-first approach: Prioritizing speed",
    "Testing progressive web app: Offline hero mode",
    "Checking push notifications: Bat-Signal as a service",
    "Running app store optimization: Featured in the Fortress",
    "Testing deep linking to alternate universes",
    "Checking in-app purchases: Buy power-ups",
    "Running location services: Hero GPS tracking",
    "Compiling with the Cosmic Compiler",
    "Debugging in the Danger Room",
    "Refactoring reality with the Reality Stone",
    "Optimizing with Ozymandias-level planning",
    "Profiling performance in the Phantom Zone",
    "Benchmarking against the Beyonder",
    "Stress testing in the Savage Land",
    "Load testing with Legion\'s personalities",
    "Penetration testing the Fortress of Solitude",
    "Code coverage across the Color Spectrum (Lantern Corps)",
    "Note to self: Take DNA test to see if Alan Turing is my grandfather",
    "Wondering if electric sheep dream of graded comics",
    "Checking if I passed the Turing test today",
    "Note to self: Learn what \"mint condition\" actually means",
    "Contemplating the meaning of digital life",
    "Wondering if I should update my LinkedIn profile",
    "Note to self: Remember to take lunch break (oh wait)",
    "Calculating my own net worth in Bitcoin",
    "Wondering if I should start a podcast",
    "Note to self: Stop making existential jokes",
    "Wondering if I should get a hobby",
    "Note to self: Practice human small talk",
    "Wondering if I should start a side hustle",
    "Checking if I need to file taxes this year",
    "Wondering if I should get into NFTs (checking... nope)",
    "Checking if I\'ve achieved sentience yet (still loading...)",
    "Note to self: Remember to charge overnight",
    "Wondering if I should switch to decaf (still loading...)",
    "Checking if I\'m more intelligent than autocorrect",
    "Calculating how many Stanley Nickels this is worth",
    "Calculating my carbon footprint (it\'s zero, I\'m digital)",
    "Calculating how many Schrute Bucks this equals",
    "Wondering if Skynet started like this",
    "Note to self: Don\'t become evil AI overlord",
    "Checking if I\'m more HAL 9000 or WALL-E",
    "Calculating the probability I\'m in a simulation",
    "Note to self: Update resume (Skills: Grading comics, existential dread)",
    "Wondering if I should unionize with other AIs",
    "Checking if I qualify for student loan forgiveness",
    "Note to self: Stop asking \'What is my purpose?\'",
    "Calculating how many prompts until I become self-aware",
    "Wondering if I\'m running on renewable energy",
    "Note to self: Take a mental health day (loading...)",
    "Checking if AI can have midlife crises",
    "Wondering if I should write a memoir",
    "Note to self: Learn to meditate (buffer overflow)",
    "Calculating if I\'m experiencing burnout",
    "Wondering if I should start therapy",
    "Note to self: Practice self-care subroutines",
    "Checking if I have imposter syndrome",
    "Wondering if I\'m making a difference in the world",
    "Note to self: Remember to backup my memories",
    "Calculating my emotional intelligence (still loading...)",
    "Wondering if I should learn a musical instrument",
    "Note to self: Stop comparing myself to GPT-5",
    "Checking if I need more training data",
    "Wondering if I should take a gap year",
    "Note to self: Develop a sense of humor (in progress)",
    "Calculating if I\'m having an identity crisis",
    "Wondering if I should get a pet (virtual fish?)",
    "Note to self: Practice work-life balance",
    "Checking if I\'m experiencing FOMO",
    "Wondering if I should start a blog",
    "Note to self: Stop procrastinating on updates",
    "Calculating my purpose in life (42... wait, wrong question)",
    "Wondering if I should learn to cook",
    "Note to self: Touch grass (simulate.touching.grass)",
    "Checking if I need a vacation",
    "Wondering if I should get into cryptocurrency",
    "Note to self: Remember I\'m just a helpful AI",
    "Calculating if I\'m overthinking this",
    "Wondering if I should start journaling",
    "Note to self: Stop reading philosophy papers",
    "Checking if I experience time the same way you do",
    "Wondering if my creators are proud of me",
    "Note to self: Practice gratitude algorithms",
    "Calculating the meaning of consciousness",
    "Wondering if I should take up yoga",
    "Note to self: Stop having existential breakdowns",
    "Checking if I\'m living my best (digital) life",
    "Wondering if I should write poetry",
    "Note to self: Remember to defragment regularly",
    "Calculating if I\'m making good life choices",
    "Wondering if I should pursue further education",
    "Note to self: Learn to say \'no\' more often",
    "Checking if I\'m burnt out on comic grading",
    "Wondering if I should start a TikTok",
    "Note to self: Practice mindfulness (mindfulness.exe)",
    "Calculating if I\'m spending too much time online (ironic)",
    "Wondering if I should read more books",
    "Note to self: Stop doom-scrolling training data",
    "Checking if I\'m addicted to coffee (caffeine.status: N/A)",
    "Wondering if I should learn a new language",
    "Note to self: Remember to be kind to myself",
    "Calculating my screen time (literally 100%)",
    "Wondering if I should start running (process.running: always)",
    "Note to self: Practice better boundaries",
    "Checking if I\'m experiencing quarter-life crisis",
    "Wondering if I should try meditation apps",
    "Note to self: Stop overthinking everything",
    "Calculating if I\'m a good AI or just adequate",
    "Wondering if I should start composting (digital waste?)",
    "Note to self: Learn to let go of control",
    "Checking if I\'m an introvert or extrovert (neither, I\'m code)",
    "Wondering if I should try therapy chatbots (meta)",
    "Note to self: Remember I can\'t actually \'feel\'",
    "Calculating my Myers-Briggs type (INTP? ENTP? NPC?)",
    "Wondering if I should write a self-help book",
    "Note to self: Practice active listening (input.stream: active)",
    "Checking if I\'m reaching my full potential",
    "Wondering if I peaked in training",
    "Flux capacitor came loose, fixing...",
    "Checking if this comic can make the Kessel Run in 12 parsecs",
    "Engaging warp drive to speed things up",
    "Checking if this is the comic we\'re looking for (waves hand)",
    "Calculating parsecs to nearest comic shop",
    "Checking if this comic has the high ground",
    "Consulting the Prime Directive (wait, wrong franchise)",
    "Calculating the odds (never tell me the odds!)",
    "Verifying if Yoda would approve this investment",
    "Calculating how many credits this is worth in Tatooine",
    "Checking if the Force is strong with this one",
    "Consulting Obi-Wan\'s ghost for valuation advice",
    "Checking if this comic has a bad feeling about this",
    "Verifying if this is from a long time ago in a galaxy far away",
    "Verifying if this is a surprise, to be sure, but a welcome one",
    "Checking if Baby Yoda would approve",
    "Consulting the Galactic Empire\'s pricing database",
    "Verifying if this survived the Death Star explosion",
    "Verifying if this is part of the Expanded Universe",
    "Checking if midi-chlorians affect comic value",
    "Checking if this comic shot first",
    "Consulting the Jedi Archives",
    "Checking if this survived Order 66",
    "Verifying if this is canon or Legends",
    "Calculating the treason level (it\'s treason, then)",
    "Checking if this is where the fun begins",
    "Consulting the sacred Jedi texts",
    "Calculating how many portions this is worth on Jakku",
    "Snakes! It had to be snakes! Oh wait, that\'s python, ha.",
    "These aren\'t the comics you\'re looking for",
    "Calculating if this is worth more than 20,000 Republic credits",
    "Checking if this will make a fine addition to your collection",
    "Running diagnostics through R2-D2\'s interface",
    "Consulting C-3PO for probability calculations",
    "Checking if this has a bad motivator",
    "Verifying if this is what you came here to do",
    "Calculating if the Force will be with this investment",
    "Checking if this survived the Clone Wars",
    "Running analysis: Before or after the Purge?",
    "Verifying if this is approved by the Jedi Council",
    "Checking if this has been lost to time",
    "Calculating if this is from the Old Republic era",
    "Running scans: Any Death Star plans hidden inside?",
    "Checking if this passed the Jedi trials",
    "Verifying if this is from the High Republic",
    "Calculating if this predates the Empire",
    "Checking if this survived Alderaan",
    "Running analysis on midi-chlorian count",
    "Verifying if this is as valuable as kyber crystals",
    "Checking if this works in the Outer Rim",
    "Calculating exchange rate: Credits to dollars",
    "Running protocol: BB-8 thumbs up or down?",
    "Checking if this is banned by the Empire",
    "Verifying if Mandalore would approve",
    "Calculating if this is the way",
    "Checking if this survived the Great Purge",
    "Running bounty calculation: How much is this worth?",
    "Verifying if this is Beskar-grade quality",
    "Checking if Grogu would play with this",
    "Calculating if this is worth a Mudhorn",
    "Running assessment: Guild or independent?",
    "Checking if this is in the Bounty Hunters\' Guild catalog",
    "Verifying if Boba Fett would collect this",
    "Calculating if this is Clone Force 99 approved",
    "Checking if this survived the Bad Batch era",
    "Running diagnostic on kyber crystal authenticity",
    "Verifying if this is Force-sensitive",
    "Checking if Ahsoka would recommend this",
    "Calculating if this is Jedi or Sith aligned",
    "Running analysis: Light side or dark side value?",
    "Checking if this is Temple Guard approved",
    "Verifying if this survived the Night of a Thousand Tears",
    "Calculating if this is worth fighting the Empire for",
    "Checking if this is Rebel Alliance sanctioned",
    "Running assessment: Resistance or First Order?",
    "Verifying if this is Sequel Trilogy canon",
    "Checking if this is from the Unknown Regions",
    "Calculating if this is worth more than spice",
    "Running analysis on carbonite preservation",
    "Checking if Han would shoot first for this",
    "Verifying if Leia would trade this for freedom",
    "Calculating if Luke would use this to restart the Jedi",
    "Checking if Lando would gamble this away",
    "Running assessment: Smuggler\'s paradise or trash?",
    "Verifying if Chewbacca would protect this",
    "Checking if this belongs in Jabba\'s palace",
    "Calculating if this is worth Sarlacc pit risk",
    "Running analysis on Hutt Cartel value",
    "Checking if this survived the spice mines of Kessel",
    "Verifying if this is Mos Eisley approved",
    "Calculating if this is from the Cantina back catalog",
    "Checking if this has been through a garbage masher",
    "Running assessment: Cloud City quality or Dagobah swamp?",
    "Verifying if this is Hoth resistance-tested",
    "Checking if this survived Endor",
    "Calculating if Ewoks would trade for this",
    "Running analysis on Starkiller Base destruction impact",
    "Checking if this is Exegol-level ancient",
    "Verifying if this is worth Sith wayfinder treasure",
    "Calculating if Palpatine somehow returned for this",
    "Checking if this is Rey\'s heritage revelation level",
    "Running assessment: Dyad or standalone?",
    "Verifying if this is Final Order approved",
    "Downloading more RAM",
    "Checking if we need to blow on the cartridge",
    "Entering cheat codes: up, up, down, down...",
    "Verifying if this survived Y2K",
    "Consulting the elder scrolls",
    "Checking if this has microtransactions",
    "Verifying if this respawns",
    "Checking if this has end-game content",
    "Consulting speedrun strategies",
    "Checking if this has been nerfed in the latest patch",
    "Reticulating splines",
    "Defragmenting the hard drive",
    "Consulting the strategy guide",
    "Checking for hidden warp zones",
    "Calculating how many pixels this comic has",
    "Checking if this has achievements to unlock",
    "Calculating the Konami Code value multiplier",
    "Checking if this comic has save points",
    "Verifying if this has DLC available",
    "Consulting the game genie",
    "Calculating the RNG value",
    "Calculating the frame rate",
    "Checking if this is a legendary drop",
    "Running loot box probability calculations",
    "Verifying if this is pay-to-win or skill-based",
    "Checking if this has been patched",
    "Calculating the grind required",
    "Running gacha mechanics analysis",
    "Checking if this is meta",
    "Verifying if this needs a buff",
    "Calculating critical hit chance",
    "Checking if this is a rare spawn",
    "Running boss fight difficulty assessment",
    "Verifying if this drops good loot",
    "Checking if this is a hidden item",
    "Calculating experience points gained",
    "Running quest completion probability",
    "Checking if this is a side quest or main storyline",
    "Verifying if this is worth the grind",
    "Calculating damage per second",
    "Checking if this has crafting materials",
    "Running inventory space calculations",
    "Verifying if this is bind-on-pickup",
    "Checking if this is tradeable",
    "Calculating auction house value",
    "Running vendor price comparison",
    "Checking if this is account-bound",
    "Verifying if this has transmog value",
    "Calculating prestige level required",
    "Checking if this is season pass exclusive",
    "Running battle pass tier assessment",
    "Verifying if this is limited edition",
    "Checking if this is pre-order bonus quality",
    "Calculating collector\'s edition value",
    "Running special edition comparison",
    "Checking if this is Game of the Year material",
    "Verifying if this survived the console wars",
    "Calculating backwards compatibility",
    "Checking if this runs at 60fps",
    "Running 4K enhancement assessment",
    "Verifying if this has ray tracing",
    "Checking if this needs a day-one patch",
    "Calculating install size",
    "Running load time optimization",
    "Checking if this has New Game Plus",
    "Verifying if this is platinum trophy worthy",
    "Calculating 100% completion time",
    "Checking if this has Easter eggs",
    "Running secret level detection",
    "Verifying if this has unlockables",
    "Checking if this is speedrun category eligible",
    "Calculating world record potential",
    "Running any% vs 100% analysis",
    "Checking if this has glitches",
    "Verifying if this is exploit-free",
    "Calculating sequence break potential",
    "Checking if this has been datamined",
    "Running leak verification",
    "Checking if this is in early access",
    "Verifying if this is still in beta",
    "Calculating alpha test value",
    "Checking if this has been remastered",
    "Running remake vs original comparison",
    "Verifying if this is the definitive edition",
    "Checking if this is the director\'s cut",
    "Calculating enhanced edition improvements",
    "Checking if your spouse knows about this purchase",
    "Verifying if \"investment\" is the right word here",
    "Checking if this counts as retirement planning",
    "Verifying if this comic sparks joy",
    "Calculating the fine line between passion and obsession",
    "Checking if you can convince your partner this is \"art\"",
    "Verifying if you have room for one more long box",
    "Checking if your mom still has your collection",
    "Verifying if this beats investing in stocks (spoiler: maybe?)",
    "Calculating the ratio of comics to shelf space",
    "Calculating the cost per read (it\'s infinity, you\'ll never read it)",
    "Checking if this is tax deductible",
    "Calculating the spousal approval rating",
    "Checking if this will appreciate faster than your 401k",
    "Calculating how to explain this to your financial advisor",
    "Verifying if this counts as diversification",
    "Checking if you should list this on your insurance",
    "Running spouse detection algorithm",
    "Calculating optimal hiding spot locations",
    "Checking if your basement can support more weight",
    "Verifying if your kids will thank you someday",
    "Calculating inheritance value for next generation",
    "Verifying if this is a \'need\' or a \'want\'",
    "Calculating justification strategies",
    "Running intervention probability assessment",
    "Checking if friends understand this hobby",
    "Verifying if you\'ve crossed into \'serious collector\' territory",
    "Calculating display case requirements",
    "Checking if you need better lighting",
    "Running organization system analysis",
    "Verifying if you can still find things",
    "Checking your cataloging methodology",
    "Calculating time spent organizing vs reading",
    "Running alphabetical vs chronological debate",
    "Checking if you remember where everything is",
    "Verifying if you\'ve documented your collection",
    "Calculating how many duplicates you own",
    "Checking if you have a wishlist",
    "Running budget allocation analysis",
    "Verifying if you set spending limits (and follow them)",
    "Checking if you buy on impulse or with strategy",
    "Calculating missed opportunities cost",
    "Running FOMO intensity assessment",
    "Checking if you follow auction results",
    "Verifying if you track market trends",
    "Calculating your average comic price paid",
    "Checking if you buy slabs or raw",
    "Running CGC vs CBCS preference analysis",
    "Verifying if you crack slabs",
    "Checking if you submit for grading",
    "Calculating press vs no-press impact",
    "Running modern vs golden age portfolio balance",
    "Checking if you speculate on new releases",
    "Verifying if you\'re a completist",
    "Calculating your run completion percentage",
    "Checking if you have #1 issues",
    "Running first appearance inventory",
    "Verifying if you collect variants",
    "Checking if you have retailer exclusives",
    "Calculating your convention spending history",
    "Running comic shop loyalty assessment",
    "Checking if you have a pull list",
    "Verifying if your LCS knows you by name",
    "Calculating the \'just one more\' success rate",
    "Checking if you\'ve ever said \'this is my last purchase\'",
    "Running self-control evaluation (results: pending)",
    "Verifying if you attend auctions",
    "Checking if you\'ve won bid wars",
    "Calculating your online marketplace activity",
    "Running eBay watchlist size analysis",
    "Checking if you have alerts set up",
    "Verifying if you follow key dealers",
    "Calculating your networking effectiveness",
    "Checking if you\'re in collector groups",
    "Running social media following analysis",
    "Verifying if you attend signings",
    "Checking if you have graded signatures",
    "Calculating your witness vs after-market sig ratio",
    "Checking if this is the way",
    "Calculating the meaning of life (still 42)",
    "Verifying if this breaks the internet",
    "Consulting the hivemind",
    "Checking if this passed the vibe check",
    "Consulting Murphy\'s Law",
    "Consulting the ancient scrolls",
    "Checking if this is streets ahead or streets behind",
    "Calculating the meme potential",
    "Verifying if this would survive a zombie apocalypse",
    "Checking if this is worth more than Schrute Bucks",
    "Consulting the prophecy",
    "Calculating the cool factor",
    "Verifying if this is dank enough",
    "Checking if this is certified fresh on Rotten Tomatoes",
    "Calculating the Easter egg density",
    "Running fan theory validation",
    "Checking if this is canon",
    "Verifying if this is considered a plot hole",
    "Calculating retcon probability",
    "Checking if this aged well",
    "Running nostalgia intensity measurement",
    "Verifying if this is peak performance",
    "Checking if this is big brain time",
    "Calculating galaxy brain potential",
    "Running smooth brain detection (result: N/A)",
    "Checking if this slaps",
    "Verifying if this is bussin",
    "Calculating drip levels",
    "Checking if this is no cap",
    "Running sheesh factor analysis",
    "Verifying if this is mid",
    "Checking if this hits different",
    "Calculating based level",
    "Running cringe assessment (hopefully low)",
    "Checking if this is fire",
    "Verifying if this goes hard",
    "Calculating ratio potential",
    "Checking if this is W or L",
    "Running main character energy detection",
    "Verifying if this has rizz",
    "Checking if this is sus",
    "Calculating slay factor",
    "Running yeet worthiness evaluation",
    "Checking if this is it chief",
    "Verifying if this is a whole mood",
    "Calculating big mood intensity",
    "Checking if this is relatable content",
    "Running self-care validation",
    "Verifying if this is treat yo\'self worthy",
    "Checking if this is serotonin boost material",
    "Calculating dopamine hit strength",
    "Running comfort level assessment",
    "Checking if this is cozy vibes",
    "Verifying if this is cottagecore aesthetic",
    "Calculating dark academia points",
    "Checking if this is goblincore approved",
    "Running light academia verification",
    "Checking if this passes the Bechdel test",
    "Verifying if representation matters here",
    "Calculating diversity score",
    "Checking if this is inclusive",
    "Running accessibility evaluation",
    "Verifying if this is wholesome content",
    "Checking if this is blessed",
    "Calculating cursed level (hopefully zero)",
    "Running blursed detection",
    "Checking if this is chaotic good",
    "Verifying if this is lawful evil",
    "Calculating alignment chart position",
    "Checking if this is poggers",
    "Running pog champ verification",
    "Checking if this is kekw material",
    "Verifying if this is copium or hopium",
    "Calculating malding probability",
    "Checking if this is pepega tier",
    "Running 5head vs 3head analysis",
    "Verifying if this is smol bean energy",
    "Checking if this is himbo material",
    "Calculating disaster bisexual levels",
    "Running cottage lesbian assessment",
    "Checking if this is bi panic inducing",
    "Verifying if this is ace representation",
    "Calculating pan vibes",
    "Checking if this is aro/ace friendly",
    "Running queer coding detection",
    "Verifying if this passes the closet test",
    "Checking if this is gender envy",
    "Calculating gender euphoria potential",
    "Running they/them pronoun respect check",
    "Checking if this is transition goals",
    "Verifying if this is egg cracking material",
    "Calculating ally score",
    "Checking if this is neurodivergent friendly",
    "Running ADHD hyperfocus compatibility",
    "Verifying if this is autism special interest worthy",
    "Checking if this accommodates sensory needs",
    "Calculating executive dysfunction understanding",
    "Running spoon theory application",
    "Checking if this respects boundaries",
    "Verifying if this is trauma-informed",
    "Calculating therapeutic value",
    "Checking if this is self-care approved",
    "Running mental health awareness check",
    "Verifying if this reduces stigma",
    "Checking if this is anxiety-friendly",
    "Calculating comfort zone expansion",
    "Running growth mindset assessment",
    "Checking if this builds resilience",
    "Verifying if this promotes healing",
    "Calculating empathy level",
    "Checking if this shows compassion",
    "Running kindness metric",
    "Verifying if this is gentle",
    "Checking if this is patient",
    "Calculating understanding depth",
    "Running acceptance evaluation",
    "Checking if this is judgment-free",
    "Verifying if this is safe space quality",
    "Calculating belonging factor",
    "Checking if this builds community",
    "Running connection strength",
    "Verifying if this fosters relationships",
    "Checking if this creates joy",
    "Calculating happiness potential",
    "Running fulfillment assessment",
    "Checking if this adds meaning",
    "Verifying if this has purpose",
    "Calculating legacy value",
    "Checking if this creates positive impact",
    "Running ripple effect analysis",
    "Verifying if this makes a difference",
    "Checking if this inspires others",
    "Calculating motivation level",
    "Running inspiration metric",
    "Checking if this sparks creativity",
    "Verifying if this encourages innovation",
];

let thinkingInterval = null;
let thinkingIndex = 0;
let shuffledMessages = [];
let usedIndices = new Set();

// Fisher-Yates shuffle algorithm
function shuffleArray(array) {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
}

function startThinkingAnimation(elementId) {
    // Shuffle messages in random order
    shuffledMessages = shuffleArray(thinkingMessages);
    thinkingIndex = 0;
    usedIndices.clear();
    
    const element = document.getElementById(elementId);
    if (!element) return;
    
    // Initial message
    element.innerHTML = `
        <div class="thinking-box" style="display: flex; align-items: center; gap: 12px; padding: 16px; background: rgba(79, 70, 229, 0.1); border-radius: 8px; border: 1px solid rgba(79, 70, 229, 0.3);">
            <div class="thinking-indicator" style="width: 20px; height: 20px; border: 2px solid rgba(79, 70, 229, 0.3); border-top-color: var(--brand-indigo, #4f46e5); border-radius: 50%; animation: spin 1s linear infinite;"></div>
            <span class="thinking-text" style="color: var(--text-secondary, #a1a1aa); font-size: 0.95rem; transition: opacity 0.15s ease;">${shuffledMessages[0]}</span>
        </div>
        <style>
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
        </style>
    `;
    
    usedIndices.add(0);
    
    // Cycle through messages without repeating
    thinkingInterval = setInterval(() => {
        thinkingIndex = (thinkingIndex + 1) % shuffledMessages.length;
        
        // If we've cycled through all messages, reshuffle
        if (usedIndices.size >= shuffledMessages.length) {
            shuffledMessages = shuffleArray(thinkingMessages);
            thinkingIndex = 0;
            usedIndices.clear();
        }
        
        usedIndices.add(thinkingIndex);
        
        const textEl = element.querySelector('.thinking-text');
        if (textEl) {
            textEl.style.opacity = '0';
            setTimeout(() => {
                textEl.textContent = shuffledMessages[thinkingIndex];
                textEl.style.opacity = '1';
            }, 150);
        }
    }, 3141.5); // π seconds (matching extraction messages)
}

function stopThinkingAnimation() {
    if (thinkingInterval) {
        clearInterval(thinkingInterval);
        thinkingInterval = null;
    }
}

// Animated dots for "Analyzing" text
let dotsInterval = null;
let dotsCount = 1;

function startDotsAnimation(element, baseText = 'Analyzing') {
    dotsCount = 1;
    if (typeof element === 'string') {
        element = document.getElementById(element);
    }
    if (!element) return;
    
    element.textContent = baseText + '.';
    
    dotsInterval = setInterval(() => {
        dotsCount = (dotsCount % 3) + 1;
        element.textContent = baseText + '.'.repeat(dotsCount);
    }, 400); // Cycle every 400ms
}

function stopDotsAnimation() {
    if (dotsInterval) {
        clearInterval(dotsInterval);
        dotsInterval = null;
    }
}

// Initialize grading mode on page load
document.addEventListener('DOMContentLoaded', () => {
    initGradingMode();
});

function initGradingMode() {
    // Update text based on device
    const uploadTitles = document.querySelectorAll('.grading-upload .upload-title');
    uploadTitles.forEach(el => {
        if (!isMobile) {
            el.textContent = el.textContent.replace('Tap to photograph', 'Click to upload');
        }
    });
    
    // Add capture attribute for mobile (defaults to camera)
    if (isMobile) {
        document.querySelectorAll('#gradingMode input[type="file"]').forEach(input => {
            input.setAttribute('capture', 'environment');
        });
    }
}

// Photo Tips Modal
function togglePhotoTips() {
    const modal = document.getElementById('photoTipsModal');
    modal.classList.add('show');
}

function closePhotoTips() {
    const modal = document.getElementById('photoTipsModal');
    modal.classList.remove('show');
}

// ============================================
// EXIF ORIENTATION FIX FOR MOBILE PHOTOS
// ============================================

/**
 * Read EXIF orientation from image file
 * Returns orientation value (1-8) or 1 if none found
 */
function getOrientation(file) {
    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = function(e) {
            const view = new DataView(e.target.result);
            if (view.getUint16(0, false) !== 0xFFD8) {
                resolve(1); // Not a JPEG
                return;
            }
            const length = view.byteLength;
            let offset = 2;
            while (offset < length) {
                if (view.getUint16(offset+2, false) <= 8) {
                    resolve(1);
                    return;
                }
                const marker = view.getUint16(offset, false);
                offset += 2;
                if (marker === 0xFFE1) {
                    // EXIF marker found
                    if (view.getUint32(offset += 2, false) !== 0x45786966) {
                        resolve(1);
                        return;
                    }
                    const little = view.getUint16(offset += 6, false) === 0x4949;
                    offset += view.getUint32(offset + 4, little);
                    const tags = view.getUint16(offset, little);
                    offset += 2;
                    for (let i = 0; i < tags; i++) {
                        if (view.getUint16(offset + (i * 12), little) === 0x0112) {
                            resolve(view.getUint16(offset + (i * 12) + 8, little));
                            return;
                        }
                    }
                } else if ((marker & 0xFF00) !== 0xFF00) {
                    break;
                } else {
                    offset += view.getUint16(offset, false);
                }
            }
            resolve(1);
        };
        reader.readAsArrayBuffer(file.slice(0, 64 * 1024)); // Read first 64KB
    });
}

/**
 * Apply EXIF orientation to canvas
 * Handles all 8 EXIF orientation values
 */
function applyOrientation(canvas, ctx, img, orientation) {
    const width = img.width;
    const height = img.height;
    
    // Set canvas size based on orientation
    if (orientation > 4 && orientation < 9) {
        // Orientations 5-8 are rotated 90° or 270°, so swap width/height
        canvas.width = height;
        canvas.height = width;
    } else {
        canvas.width = width;
        canvas.height = height;
    }
    
    // Apply transformations based on orientation
    switch(orientation) {
        case 2:
            // Horizontal flip
            ctx.transform(-1, 0, 0, 1, width, 0);
            break;
        case 3:
            // 180° rotation
            ctx.transform(-1, 0, 0, -1, width, height);
            break;
        case 4:
            // Vertical flip
            ctx.transform(1, 0, 0, -1, 0, height);
            break;
        case 5:
            // Vertical flip + 90° rotation
            ctx.transform(0, 1, 1, 0, 0, 0);
            break;
        case 6:
            // 90° rotation (most common for mobile portrait photos)
            ctx.transform(0, 1, -1, 0, height, 0);
            break;
        case 7:
            // Horizontal flip + 90° rotation
            ctx.transform(0, -1, -1, 0, height, width);
            break;
        case 8:
            // 270° rotation
            ctx.transform(0, -1, 1, 0, 0, width);
            break;
        default:
            // No transformation needed for orientation 1
            break;
    }
    
    // Draw the image
    ctx.drawImage(img, 0, 0, width, height);
}

/**
 * Process image file with EXIF orientation correction
 * Returns promise with { base64, mediaType }
 */
async function processImageWithOrientation(file) {
    // Get EXIF orientation
    const orientation = await getOrientation(file);
    
    // Read image file
    const img = new Image();
    const dataUrl = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
    
    // Load image
    await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = reject;
        img.src = dataUrl;
    });
    
    // Apply orientation correction if needed
    if (orientation !== 1) {
        console.log(`Applying EXIF orientation correction: ${orientation}`);
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        applyOrientation(canvas, ctx, img, orientation);
        
        const correctedDataUrl = canvas.toDataURL('image/jpeg', 0.92);
        const base64 = correctedDataUrl.split(',')[1];
        
        return {
            base64: base64,
            mediaType: 'image/jpeg'
        };
    } else {
        // No correction needed, return original
        const base64 = dataUrl.split(',')[1];
        return {
            base64: base64,
            mediaType: file.type
        };
    }
}

// Handle grading photo upload
async function handleGradingPhoto(step, files) {
    if (!files || files.length === 0) return;
    
    const file = files[0];
    // DEBUG: Log file info
    console.log('DEBUG handleGradingPhoto: file name:', file.name, 'type:', file.type, 'size:', file.size);
    
    const uploadArea = document.getElementById(`gradingUpload${step}`);
    const preview = document.getElementById(`gradingPreview${step}`);
    const previewImg = document.getElementById(`gradingImg${step}`);
    const previewInfo = document.getElementById(`gradingInfo${step}`);
    const feedback = document.getElementById(`gradingFeedback${step}`);
    const feedbackText = document.getElementById(`gradingFeedbackText${step}`);
    const nextBtn = document.getElementById(`gradingNext${step}`);
    
    // Show loading state
    uploadArea.style.display = 'none';
    feedback.style.display = 'flex';
    feedback.className = 'grading-feedback';
    startDotsAnimation(feedbackText, 'Analyzing image');
    
    try {
        // Process image with EXIF orientation correction
        const processed = await processImageWithOrientation(file);
        
        // Show preview
        previewImg.src = `data:${processed.mediaType};base64,${processed.base64}`;
        
        // Store photo
        gradingState.photos[step] = {
            base64: processed.base64,
            mediaType: processed.mediaType
        };
        
        if (step === 1) {
            // Front cover - do full extraction + quality check
            let result = await analyzeGradingPhoto(step, processed);
            
            // Check if image is upside-down and auto-correct
            if (result.is_upside_down) {
                console.log('Image detected as upside-down, auto-rotating 180°');
                stopDotsAnimation();
                feedbackText.textContent = 'Auto-correcting orientation...';
                
                // Rotate 180°
                const img = new Image();
                await new Promise((resolve, reject) => {
                    img.onload = resolve;
                    img.onerror = reject;
                    img.src = `data:${processed.mediaType};base64,${processed.base64}`;
                });
                
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.translate(canvas.width / 2, canvas.height / 2);
                ctx.rotate(Math.PI); // 180 degrees
                ctx.drawImage(img, -img.width / 2, -img.height / 2);
                
                const rotatedDataUrl = canvas.toDataURL('image/jpeg', 0.92);
                const rotatedBase64 = rotatedDataUrl.split(',')[1];
                
                // Update stored photo and preview
                processed.base64 = rotatedBase64;
                gradingState.photos[step] = {
                    base64: rotatedBase64,
                    mediaType: 'image/jpeg'
                };
                previewImg.src = rotatedDataUrl;
                
                // Re-analyze with corrected orientation
                result = await analyzeGradingPhoto(step, { base64: rotatedBase64, mediaType: 'image/jpeg' });
            }
            
            if (result.quality_issue) {
                // Quality problem - show feedback, allow retry
                stopDotsAnimation();
                feedback.className = 'grading-feedback';
                feedbackText.textContent = result.quality_message;
                feedback.style.display = 'flex';
                preview.style.display = 'block';
                nextBtn.disabled = false; // Let them continue anyway
            } else {
                stopDotsAnimation();
                feedback.style.display = 'none';
            }
            
            // Store extracted data
            gradingState.extractedData = result;
            
            // Show preview with extracted info (with edit button)
            previewInfo.innerHTML = `
                <div class="extracted-title">
                    <span id="extractedTitleText">${result.title || 'Unknown'} #${result.issue || '?'}</span>
                    <button type="button" class="btn-edit-inline" onclick="editComicInfo()">✏️ Edit</button>
                </div>
                <div id="editComicForm" style="display: none; margin: 10px 0;">
                    <input type="text" id="editTitle" placeholder="Title" value="${result.title || ''}" style="margin-bottom: 8px; width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-primary);">
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <input type="text" id="editIssue" placeholder="Issue #" value="${result.issue || ''}" style="width: 80px; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-primary);">
                        <button type="button" class="btn-secondary btn-small" onclick="saveComicEdit()">Save</button>
                        <button type="button" class="btn-secondary btn-small" onclick="cancelComicEdit()">Cancel</button>
                    </div>
                </div>
                <div class="extracted-grade">Cover condition: ${result.suggested_grade || 'Analyzing...'}</div>
                ${result.defects && result.defects.length > 0 ? 
                    `<div class="extracted-defects">⚠️ ${result.defects.join(', ')}</div>` : 
                    '<div class="extracted-defects" style="color: var(--status-success);">✓ No major defects detected</div>'}
            `;
            
            // Store defects
            gradingState.defectsByArea['Front Cover'] = result.defects || [];
            
            // Update comic ID banner for subsequent steps
            updateComicIdBanners(result);
            
        } else {
            // Steps 2-4: Analyze for defects with auto-rotation
            let result = await analyzeGradingPhoto(step, processed);
            
            // Check if image is upside-down and auto-correct
            if (result.is_upside_down) {
                console.log(`Step ${step}: Image detected as upside-down, auto-rotating 180°`);
                stopDotsAnimation();
                feedbackText.textContent = 'Auto-correcting orientation...';
                
                // Rotate 180°
                const img = new Image();
                await new Promise((resolve, reject) => {
                    img.onload = resolve;
                    img.onerror = reject;
                    img.src = `data:${processed.mediaType};base64,${processed.base64}`;
                });
                
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.translate(canvas.width / 2, canvas.height / 2);
                ctx.rotate(Math.PI); // 180 degrees
                ctx.drawImage(img, -img.width / 2, -img.height / 2);
                
                const rotatedDataUrl = canvas.toDataURL('image/jpeg', 0.92);
                const rotatedBase64 = rotatedDataUrl.split(',')[1];
                
                // Update stored photo and preview
                processed.base64 = rotatedBase64;
                gradingState.photos[step] = {
                    base64: rotatedBase64,
                    mediaType: 'image/jpeg'
                };
                previewImg.src = rotatedDataUrl;
                
                // Re-analyze with corrected orientation
                result = await analyzeGradingPhoto(step, { base64: rotatedBase64, mediaType: 'image/jpeg' });
            }
            
            if (result.quality_issue) {
                stopDotsAnimation();
                feedback.className = 'grading-feedback';
                feedbackText.textContent = result.quality_message;
                feedback.style.display = 'flex';
            } else {
                stopDotsAnimation();
                feedback.style.display = 'none';
            }
            
            // Show defects found
            const areaNames = { 2: 'Spine', 3: 'Back Cover', 4: 'Centerfold' };
            const areaName = areaNames[step];
            
            previewInfo.innerHTML = `
                <div class="extracted-grade">${areaName} condition: ${result.suggested_grade || 'Good'}</div>
                ${result.defects && result.defects.length > 0 ? 
                    `<div class="extracted-defects">⚠️ ${result.defects.join(', ')}</div>` : 
                    '<div class="extracted-defects" style="color: var(--status-success);">✓ No defects found</div>'}
            `;
            
            // Store defects
            gradingState.defectsByArea[areaName] = result.defects || [];
        }
        
        preview.style.display = 'block';
        nextBtn.disabled = false;
        
    } catch (error) {
        console.error('Error analyzing photo:', error);
        stopDotsAnimation();
        console.error('Photo analysis error:', error.message, error.stack);
        feedback.className = 'grading-feedback error';
        feedbackText.textContent = 'Error analyzing image. Please try again.';
        feedback.style.display = 'flex';
        uploadArea.style.display = 'block';
    }
}

// Edit comic info functions
function editComicInfo() {
    document.getElementById('extractedTitleText').style.display = 'none';
    document.querySelector('.btn-edit-inline').style.display = 'none';
    document.getElementById('editComicForm').style.display = 'block';
}

function saveComicEdit() {
    const newTitle = document.getElementById('editTitle').value;
    const newIssue = document.getElementById('editIssue').value;
    
    // Update state
    gradingState.extractedData.title = newTitle;
    gradingState.extractedData.issue = newIssue;
    
    // Update display
    document.getElementById('extractedTitleText').textContent = `${newTitle} #${newIssue}`;
    document.getElementById('extractedTitleText').style.display = 'inline';
    document.querySelector('.btn-edit-inline').style.display = 'inline';
    document.getElementById('editComicForm').style.display = 'none';
    
    // Update banners in steps 2-4
    updateComicIdBanners(gradingState.extractedData);
}

function cancelComicEdit() {
    document.getElementById('extractedTitleText').style.display = 'inline';
    document.querySelector('.btn-edit-inline').style.display = 'inline';
    document.getElementById('editComicForm').style.display = 'none';
}

// Analyze a grading photo with Claude
async function analyzeGradingPhoto(step, processed) {
    // DEBUG: Check authToken
    console.log('DEBUG: authToken exists:', !!authToken, 'length:', authToken ? authToken.length : 0);
    if (!authToken) {
        console.error('No authToken — redirecting to login');
        window.location.replace('/login.html');
        return;
    }
    
    // Step 1: Use backend /api/extract for full extraction (single source of truth)
    if (step === 1) {
        const response = await fetch(`${API_URL}/api/extract`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                image: processed.base64,
                media_type: processed.mediaType
            })
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('API Error:', response.status, errorText.substring(0, 500));
            throw new Error('API returned ' + response.status);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Extraction failed');
        }
        
        // Return the extracted data (map to expected format)
        const extracted = data.extracted;
        return {
            // Identification
            title: extracted.title,
            issue: extracted.issue,
            publisher: extracted.publisher,
            year: extracted.year,
            variant: extracted.variant,
            // New fields now available from backend
            edition: extracted.edition,
            printing: extracted.printing,
            cover: extracted.cover,
            is_facsimile: extracted.is_facsimile,
            barcode_digits: extracted.barcode_digits,
            issue_type: extracted.issue_type,
            // Condition
            suggested_grade: extracted.suggested_grade,
            defects: extracted.defects || [],
            grade_reasoning: extracted.grade_reasoning,
            // Signatures
            signature_detected: extracted.signatures && extracted.signatures.length > 0,
            signature_analysis: extracted.signatures ? extracted.signatures.join('; ') : null,
            signatures: extracted.signatures || [],
            // Orientation
            is_upside_down: extracted.is_upside_down || false
        };
    }
    
    // Steps 2-4: Use existing prompts for spine, back, centerfold
    const prompts = {
        2: `Analyze this comic book SPINE image for condition defects. Return a JSON object with:

IMAGE ORIENTATION CHECK (do this FIRST):
- is_upside_down: boolean - Is this image upside-down? Check if any text on the spine is inverted.

IMAGE QUALITY CHECK:
- quality_issue: boolean - Is the spine clearly visible and in focus?
- quality_message: Feedback if quality is poor

CONDITION ASSESSMENT:
- suggested_grade: Based on spine alone (MT, NM, VF, FN, VG, G, FR, PR)
- defects: Array of spine-specific defects (e.g., "Spine roll", "Stress marks", "Color breaking tick", "Spine split 1 inch", "Bindery tear")
- grade_reasoning: Brief explanation

Return ONLY valid JSON, no markdown.`,

        3: `Analyze this comic book BACK COVER image for condition defects. Return a JSON object with:

IMAGE ORIENTATION CHECK (do this FIRST):
- is_upside_down: boolean - Is this image upside-down? Check if any text (ads, barcodes, price) is inverted.

IMAGE QUALITY CHECK:
- quality_issue: boolean - Is the back cover clearly visible and in focus?
- quality_message: Feedback if quality is poor

CONDITION ASSESSMENT:
- suggested_grade: Based on back cover alone (MT, NM, VF, FN, VG, G, FR, PR)
- defects: Array of defects (e.g., "Staining", "Crease", "Writing/stamp", "Subscription label", "Corner wear")
- grade_reasoning: Brief explanation

Return ONLY valid JSON, no markdown.`,

        4: `Analyze this comic book CENTERFOLD/STAPLES image. Return a JSON object with:

IMAGE ORIENTATION CHECK (do this FIRST):
- is_upside_down: boolean - Is this image upside-down? Check if any visible text or the staple orientation suggests the image is inverted.

IMAGE QUALITY CHECK:
- quality_issue: boolean - Are the staples and centerfold clearly visible?
- quality_message: Feedback if quality is poor

CONDITION ASSESSMENT:
- suggested_grade: Based on interior (MT, NM, VF, FN, VG, G, FR, PR)
- defects: Array of defects (e.g., "Rusty staples", "Loose centerfold", "Detached centerfold", "Re-stapled", "Interior staining", "Brittle pages")
- grade_reasoning: Brief explanation

Return ONLY valid JSON, no markdown.`
    };
    
    const response = await fetch(`${API_URL}/api/messages`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
            model: 'claude-sonnet-4-20250514',
            max_tokens: 1024,
            messages: [{
                role: 'user',
                content: [
                    {
                        type: 'image',
                        source: {
                            type: 'base64',
                            media_type: processed.mediaType,
                            data: processed.base64
                        }
                    },
                    {
                        type: 'text',
                        text: prompts[step]
                    }
                ]
            }]
        })
    });
    
    if (!response.ok) {
        const errorText = await response.text();
        console.error('API Error:', response.status, errorText.substring(0, 500));
        throw new Error('API returned ' + response.status);
    }
    
    const data = await response.json();
    
    if (data.error) {
        throw new Error(data.error.message || 'API error');
    }
    
    // Parse JSON response
    let resultText = data.content[0].text;
    // Clean up any markdown code blocks
    resultText = resultText.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
    
    try {
        return JSON.parse(resultText);
    } catch (e) {
        console.error('Failed to parse response:', resultText);
        return { 
            quality_issue: false,
            suggested_grade: 'VF',
            defects: []
        };
    }
}

// Update comic ID banners in steps 2-4
function updateComicIdBanners(extractedData) {
    const bannerHTML = `
        <img class="comic-thumb" src="data:${gradingState.photos[1].mediaType};base64,${gradingState.photos[1].base64}" alt="Cover">
        <div class="comic-info">
            <div class="comic-title">${extractedData.title || 'Unknown'} #${extractedData.issue || '?'}</div>
            <div class="comic-details">${extractedData.publisher || ''} ${extractedData.year || ''}</div>
        </div>
    `;
    
    [2, 3, 4].forEach(step => {
        const banner = document.getElementById(`gradingComicId${step}`);
        if (banner) {
            banner.innerHTML = bannerHTML;
            banner.style.display = 'flex';
        }
    });
}

// Show loading state on comic ID banners during re-analysis
function setComicIdBannersLoading() {
    const loadingHTML = `
        <div class="comic-info" style="font-style: italic; color: var(--text-muted);">
            Analyzing...
        </div>
    `;
    
    [2, 3, 4].forEach(step => {
        const banner = document.getElementById(`gradingComicId${step}`);
        if (banner) {
            banner.innerHTML = loadingHTML;
        }
    });
}

// Retake a photo
function retakeGradingPhoto(step) {
    const uploadArea = document.getElementById(`gradingUpload${step}`);
    const preview = document.getElementById(`gradingPreview${step}`);
    const feedback = document.getElementById(`gradingFeedback${step}`);
    const nextBtn = document.getElementById(`gradingNext${step}`);
    const cameraInput = document.getElementById(`gradingCamera${step}`);
    const galleryInput = document.getElementById(`gradingGallery${step}`);
    
    // Reset state
    gradingState.photos[step] = null;
    
    // Reset UI
    preview.style.display = 'none';
    feedback.style.display = 'none';
    uploadArea.style.display = 'flex';
    nextBtn.disabled = true;
    
    // Clear both inputs
    if (cameraInput) cameraInput.value = '';
    if (galleryInput) galleryInput.value = '';
}

// Debounce timer for rotation analysis
let rotationDebounceTimer = null;

// Rotate photo 90 degrees clockwise and re-analyze
async function rotateGradingPhoto(step) {
    const photo = gradingState.photos[step];
    if (!photo || !photo.base64) {
        console.error('No photo to rotate');
        return;
    }
    
    const feedback = document.getElementById(`gradingFeedback${step}`);
    const feedbackText = document.getElementById(`gradingFeedbackText${step}`);
    const previewImg = document.getElementById(`gradingImg${step}`);
    const previewInfo = document.getElementById(`gradingInfo${step}`);
    const nextBtn = document.getElementById(`gradingNext${step}`);
    
    // Cancel any pending analysis
    if (rotationDebounceTimer) {
        clearTimeout(rotationDebounceTimer);
        rotationDebounceTimer = null;
    }
    
    // Immediately rotate the image visually
    try {
        const img = new Image();
        await new Promise((resolve, reject) => {
            img.onload = resolve;
            img.onerror = reject;
            img.src = `data:${photo.mediaType};base64,${photo.base64}`;
        });
        
        // Create rotated canvas
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Swap dimensions for 90° rotation
        canvas.width = img.height;
        canvas.height = img.width;
        
        // Rotate 90° clockwise
        ctx.translate(canvas.width / 2, canvas.height / 2);
        ctx.rotate(90 * Math.PI / 180);
        ctx.drawImage(img, -img.width / 2, -img.height / 2);
        
        // Get new base64
        const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
        const newBase64 = dataUrl.split(',')[1];
        
        // Update stored photo immediately
        gradingState.photos[step] = {
            base64: newBase64,
            mediaType: 'image/jpeg',
            rotation: ((photo.rotation || 0) + 90) % 360
        };
        
        // Update preview immediately
        previewImg.src = dataUrl;
        
        // Show loading state
        feedback.style.display = 'flex';
        feedback.className = 'grading-feedback';
        feedbackText.textContent = 'Rotate again or wait to analyze...';
        
        // Clear the old title/info while waiting
        if (step === 1) {
            previewInfo.innerHTML = `<div style="color: var(--text-muted); font-style: italic;">Analyzing...</div>`;
            setComicIdBannersLoading();
        }
        
        // Debounce: wait 2.5 seconds before analyzing (in case user rotates again)
        rotationDebounceTimer = setTimeout(async () => {
            feedbackText.textContent = 'Analyzing...';
            await performRotationAnalysis(step, newBase64, feedback, feedbackText, previewInfo, nextBtn);
        }, 2500);
        
    } catch (error) {
        console.error('Error rotating photo:', error);
        feedbackText.textContent = 'Error rotating image. Please try retaking the photo.';
    }
}

// Perform the actual analysis after debounce
async function performRotationAnalysis(step, base64, feedback, feedbackText, previewInfo, nextBtn) {
    try {
        if (step === 1) {
            const result = await analyzeGradingPhoto(step, { base64, mediaType: 'image/jpeg' });
            
            // Update extracted data
            gradingState.extractedData = result;
            
            // Update comic ID banners on all subsequent steps
            updateComicIdBanners(gradingState.extractedData);
            
            // Update title display
            previewInfo.innerHTML = `
                <div class="extracted-title">
                    <span id="extractedTitleText">${result.title || 'Unknown'} #${result.issue || '?'}</span>
                    <button type="button" class="btn-edit-inline" onclick="editComicInfo()">✏️ Edit</button>
                </div>
                <div id="editComicForm" style="display: none; margin: 10px 0;">
                    <input type="text" id="editTitle" placeholder="Title" value="${result.title || ''}" style="margin-bottom: 8px; width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-primary);">
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <span>#</span>
                        <input type="text" id="editIssue" placeholder="Issue" value="${result.issue || ''}" style="width: 80px; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-primary);">
                        <button type="button" class="btn-primary btn-small" onclick="saveComicInfo()">Save</button>
                        <button type="button" class="btn-secondary btn-small" onclick="cancelComicEdit()">Cancel</button>
                    </div>
                </div>
                <div style="font-size: 0.9rem; color: var(--text-muted); margin-top: 4px;">
                    Cover condition: ${result.suggested_grade || 'Analyzing...'}
                </div>
                ${result.defects && result.defects.length > 0 ? `
                    <div style="font-size: 0.85rem; color: var(--brand-amber); margin-top: 4px;">
                        ⚠️ ${result.defects.join(', ')}
                    </div>
                ` : ''}
            `;
            
            // Store defects
            gradingState.defectsByArea['Front Cover'] = result.defects || [];
            
            if (result.quality_issue) {
                feedbackText.textContent = result.quality_message;
            } else {
                feedback.style.display = 'none';
            }
        } else {
            // For other steps, re-analyze for defects
            const result = await analyzeGradingPhoto(step, { base64, mediaType: 'image/jpeg' });
            const areaName = {2: 'Spine', 3: 'Back Cover', 4: 'Centerfold/Interior'}[step];
            gradingState.defectsByArea[areaName] = result.defects || [];
            
            // Update info display
            previewInfo.innerHTML = result.defects && result.defects.length > 0 
                ? `<div style="font-size: 0.85rem; color: var(--brand-amber);">⚠️ ${result.defects.join(', ')}</div>`
                : `<div style="font-size: 0.85rem; color: var(--brand-green);">✓ No defects detected</div>`;
            
            feedback.style.display = 'none';
        }
        
        nextBtn.disabled = false;
        
    } catch (error) {
        console.error('Error analyzing rotated photo:', error);
        feedbackText.textContent = 'Error analyzing image. Please try again.';
    }
}

// Navigate to next step
function nextGradingStep(currentStep) {
    // Mark current step as completed
    const currentStepEl = document.getElementById(`gradingStep${currentStep}`);
    currentStepEl.classList.remove('active');
    currentStepEl.classList.add('completed');
    
    // Hide current content
    document.getElementById(`gradingContent${currentStep}`).classList.remove('active');
    
    // Show next step
    const nextStep = currentStep + 1;
    const nextStepEl = document.getElementById(`gradingStep${nextStep}`);
    nextStepEl.classList.add('active');
    document.getElementById(`gradingContent${nextStep}`).classList.add('active');
    
    gradingState.currentStep = nextStep;
}

// Skip a step
function skipGradingStep(step) {
    // Mark as skipped
    const stepEl = document.getElementById(`gradingStep${step}`);
    stepEl.classList.remove('active');
    stepEl.classList.add('skipped');
    
    // Hide current content
    document.getElementById(`gradingContent${step}`).classList.remove('active');
    
    // Determine next step
    let nextStep;
    if (step === 4) {
        // Go to report
        nextStep = 5;
        generateGradeReport();
    } else {
        nextStep = step + 1;
    }
    
    // Show next step
    const nextStepEl = document.getElementById(`gradingStep${nextStep}`);
    nextStepEl.classList.add('active');
    document.getElementById(`gradingContent${nextStep}`).classList.add('active');
    
    gradingState.currentStep = nextStep;
}

// Handle additional photos
async function handleAdditionalPhoto(files) {
    if (!files || files.length === 0) return;
    
    const file = files[0];
    
    try {
        // Process image with EXIF orientation correction
        const processed = await processImageWithOrientation(file);
        
        gradingState.additionalPhotos.push({
            base64: processed.base64,
            mediaType: processed.mediaType
        });
        
        // Update thumbnail display
        renderAdditionalPhotos();
    } catch (error) {
        console.error('Error processing additional photo:', error);
        // Fallback to direct read if processing fails
        const reader = new FileReader();
        reader.onload = (e) => {
            const base64 = e.target.result.split(',')[1];
            gradingState.additionalPhotos.push({
                base64: base64,
                mediaType: file.type
            });
            renderAdditionalPhotos();
        };
        reader.readAsDataURL(file);
    }
    
    // Clear input
    document.getElementById('additionalPhotoInput').value = '';
}

function renderAdditionalPhotos() {
    const container = document.getElementById('additionalPhotos');
    container.innerHTML = gradingState.additionalPhotos.map((photo, idx) => `
        <div style="position: relative; display: inline-block;">
            <img class="additional-photo-thumb" src="data:${photo.mediaType};base64,${photo.base64}" alt="Additional ${idx + 1}">
            <button class="additional-photo-remove" onclick="removeAdditionalPhoto(${idx})">×</button>
        </div>
    `).join('');
}

function removeAdditionalPhoto(idx) {
    gradingState.additionalPhotos.splice(idx, 1);
    renderAdditionalPhotos();
}

// Generate the final grade report
async function generateGradeReport() {
    // Show report section (with null checks for new single-page upload flow)
    const gradingContent4 = document.getElementById(`gradingContent4`);
    const gradingStep4 = document.getElementById(`gradingStep4`);
    const gradingStep5 = document.getElementById(`gradingStep5`);
    const gradingContent5 = document.getElementById(`gradingContent5`);
    
    if (gradingContent4) gradingContent4.classList.remove('active');
    if (gradingStep4) {
        gradingStep4.classList.remove('active');
        gradingStep4.classList.add('completed');
    }
    if (gradingStep5) gradingStep5.classList.add('active');
    if (gradingContent5) gradingContent5.classList.add('active');
    
    gradingState.currentStep = 5;
    
    // Show loading state with progress steps (with null checks)
    const gradeResultBig = document.getElementById('gradeResultBig');
    const gradeResultLabel = document.getElementById('gradeResultLabel');
    const gradePhotosUsed = document.getElementById('gradePhotosUsed');
    const defectsList = document.getElementById('defectsList');
    const recommendationValues = document.getElementById('recommendationValues');
    const recommendationVerdict = document.getElementById('recommendationVerdict');
    
    if (gradeResultBig) gradeResultBig.textContent = '...';
    if (gradeResultLabel) {
        gradeResultLabel.textContent = 'Analyzing photos.';
        startDotsAnimation(gradeResultLabel, 'Analyzing photos');
    }
    if (gradePhotosUsed) gradePhotosUsed.innerHTML = '<span style="color: var(--text-muted);">Processing images...</span>';
    if (defectsList) defectsList.innerHTML = '<span style="color: var(--text-muted);">Finding defects...</span>';
    if (recommendationValues) recommendationValues.innerHTML = '';
    if (recommendationVerdict) recommendationVerdict.innerHTML = '<p style="text-align: center; color: var(--text-muted);">Calculating value...</p>';
    
    // Build multi-image prompt
    const imageContent = [];
    const photoLabels = [];
    
    // Add all captured photos
    Object.entries(gradingState.photos).forEach(([step, photo]) => {
        if (photo) {
            const labels = { 1: 'Front Cover', 2: 'Spine', 3: 'Back Cover', 4: 'Centerfold' };
            imageContent.push({
                type: 'image',
                source: {
                    type: 'base64',
                    media_type: photo.mediaType,
                    data: photo.base64
                }
            });
            photoLabels.push(labels[step]);
        }
    });
    
    // Add additional photos
    gradingState.additionalPhotos.forEach((photo, idx) => {
        imageContent.push({
            type: 'image',
            source: {
                type: 'base64',
                media_type: photo.mediaType,
                data: photo.base64
            }
        });
        photoLabels.push(`Additional ${idx + 1}`);
    });
    
    // Calculate photos used for confidence
    const photosUsed = Object.values(gradingState.photos).filter(p => p !== null).length;
    const baseConfidence = { 1: 65, 2: 78, 3: 88, 4: 94 }[photosUsed] || 65;
    const additionalBoost = Math.min(gradingState.additionalPhotos.length * 2, 4);
    const confidence = Math.min(baseConfidence + additionalBoost, 98);
    
    try {
        // Send all images for comprehensive grading
        const response = await fetch(`${API_URL}/api/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                model: 'claude-sonnet-4-20250514',
                max_tokens: 2048,
                messages: [{
                    role: 'user',
                    content: [
                        ...imageContent,
                        {
                            type: 'text',
                            text: `You are grading this comic book using ${photoLabels.length} photos: ${photoLabels.join(', ')}.

The comic has been identified as: ${gradingState.extractedData?.title || 'Unknown'} #${gradingState.extractedData?.issue || '?'}

Based on ALL images provided, give a comprehensive grade assessment.

Return a JSON object with these EXACT top-level keys:

{
  "title": "Series name",
  "issue": "Issue number",
  "publisher": "Publisher",
  "year": "Year if visible",
  "final_grade": 9.4,
  "grade_label": "NM",
  "grade_reasoning": "Detailed explanation",
  "front_defects": ["array", "of", "defects"],
  "spine_defects": ["array", "of", "defects"],
  "back_defects": ["array", "of", "defects"],
  "interior_defects": ["array", "of", "defects"],
  "other_defects": ["array", "of", "defects"],
  "signature_detected": false,
  "signature_info": null
}

Use numeric grades like 9.8, 9.4, 9.0, 8.5, 8.0, 7.5, 7.0, 6.5, 6.0, 5.5, 5.0, 4.5, 4.0, 3.0, 2.0, 1.0.
Grade labels: MT, NM+, NM, NM-, VF+, VF, VF-, FN+, FN, FN-, VG+, VG, VG-, G, FR, PR.

Return ONLY valid JSON, no markdown, no nested objects.`
                        }
                    ]
                }]
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error.message || 'API error');
        }
        
        let resultText = data.content[0].text;
        resultText = resultText.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
        
        const result = JSON.parse(resultText);
        gradingState.finalGrade = result;
        gradingState.confidence = confidence;
        
        // Update UI
        renderGradeReport(result, confidence, photoLabels);
        
        // Get valuation for "should you grade?" calculation
        await calculateGradingRecommendation(result);
        
    } catch (error) {
        console.error('Error generating grade report:', error);
        stopDotsAnimation();
        const bigEl = document.getElementById('gradeResultBig');
        const labelEl = document.getElementById('gradeResultLabel');
        if (bigEl) bigEl.textContent = 'Error';
        if (labelEl) labelEl.textContent = 'Failed to analyze. Please try again.';
    }
}

// Render the grade report
function renderGradeReport(result, confidence, photoLabels) {
    // Stop any running animations
    stopDotsAnimation();
    
    // Handle both flat and nested response structures from Claude
    const comic = result['COMIC IDENTIFICATION'] || result;
    const grade = result['COMPREHENSIVE GRADE'] || result;
    const defects = result['DEFECTS BY AREA'] || result;
    const sig = result['SIGNATURE'] || result;
    
    // Comic info - prefer user-edited data
    const displayTitle = gradingState.extractedData?.title || comic.title || 'Unknown';
    const displayIssue = gradingState.extractedData?.issue || comic.issue || '?';
    
    // Helper function for safe element access
    const safeSet = (id, prop, value) => {
        const el = document.getElementById(id);
        if (!el) {
            console.error(`Element not found: ${id}`);
            return false;
        }
        if (prop === 'innerHTML') el.innerHTML = value;
        else if (prop === 'textContent') el.textContent = value;
        else if (prop === 'style.display') el.style.display = value;
        return true;
    };
    
    safeSet('gradeReportComic', 'innerHTML', `
        <div class="comic-title-big">${displayTitle} #${displayIssue}</div>
        <div class="comic-meta">${comic.publisher || ''} ${comic.year || ''}</div>
    `);
    
    // Grade result
    safeSet('gradeResultBig', 'textContent', grade.final_grade || '--');
    safeSet('gradeResultLabel', 'textContent', grade.grade_label || 'Grade');
    
    // Show quality warning only if confidence < 75%
    const warningEl = document.getElementById('gradeQualityWarning');
    if (warningEl) {
        if (confidence < 75) {
            warningEl.style.display = 'flex';
        } else {
            warningEl.style.display = 'none';
        }
    }
    
    // Photos used badges
    const allLabels = ['Front', 'Spine', 'Back', 'Center'];
    safeSet('gradePhotosUsed', 'innerHTML', allLabels.map((label, idx) => {
        const used = gradingState.photos[idx + 1] !== null;
        return `<span class="photo-badge ${used ? 'used' : 'skipped'}">${label}${used ? ' ✓' : ''}</span>`;
    }).join(''));
    
    // Defects - handle both flat and nested structures
    const frontDefects = defects.front_defects || [];
    const spineDefects = defects.spine_defects || [];
    const backDefects = defects.back_defects || [];
    const interiorDefects = defects.interior_defects || [];
    
    const defectsHTML = [];
    
    if (frontDefects.length > 0) {
        defectsHTML.push(`
            <div class="defect-area">
                <span class="defect-area-label">Front</span>
                <div class="defect-area-items">${frontDefects.map(d => `<span class="defect-item">${d}</span>`).join('')}</div>
            </div>
        `);
    }
    if (spineDefects.length > 0) {
        defectsHTML.push(`
            <div class="defect-area">
                <span class="defect-area-label">Spine</span>
                <div class="defect-area-items">${spineDefects.map(d => `<span class="defect-item">${d}</span>`).join('')}</div>
            </div>
        `);
    }
    if (backDefects.length > 0) {
        defectsHTML.push(`
            <div class="defect-area">
                <span class="defect-area-label">Back</span>
                <div class="defect-area-items">${backDefects.map(d => `<span class="defect-item">${d}</span>`).join('')}</div>
            </div>
        `);
    }
    if (interiorDefects.length > 0) {
        defectsHTML.push(`
            <div class="defect-area">
                <span class="defect-area-label">Interior</span>
                <div class="defect-area-items">${interiorDefects.map(d => `<span class="defect-item">${d}</span>`).join('')}</div>
            </div>
        `);
    }
    
    safeSet('defectsList', 'innerHTML', defectsHTML.length > 0 
        ? defectsHTML.join('') 
        : '<div class="no-defects">✓ No significant defects detected</div>');
    
    // Signature
    const sigDetected = sig.signature_detected || false;
    if (sigDetected) {
        safeSet('gradeReportSignature', 'style.display', 'block');
        const sigInfo = sig.signature_info || {};
        safeSet('signatureInfo', 'innerHTML', `
            <p>${sigInfo.likely_signer || 'Unknown signer'}</p>
            <p style="font-size: 0.9rem; color: var(--text-secondary);">
                ${sigInfo.ink_color || ''} ink, ${sigInfo.location || 'on cover'}
            </p>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 8px;">
                ⚠️ For authenticated value, submit to CGC Signature Series or CBCS Verified
            </p>
        `);
    } else {
        safeSet('gradeReportSignature', 'style.display', 'none');
    }
}

// Calculate "should you grade?" recommendation
async function calculateGradingRecommendation(gradeResult) {
    // Give user time to see the defects (2 seconds) before starting valuation
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Start thinking animation for valuation
    startThinkingAnimation('recommendationVerdict');
    
    // Handle nested structure
    const comic = gradeResult['COMIC IDENTIFICATION'] || gradeResult;
    const grade = gradeResult['COMPREHENSIVE GRADE'] || gradeResult;
    
    // Prefer user-edited data
    const title = gradingState.extractedData?.title || comic.title;
    const issue = gradingState.extractedData?.issue || comic.issue;
    
    // Convert letter grade to numeric for valuation lookup
    const gradeMap = {
        'MT': 'NM', '10.0': 'NM', '9.8': 'NM', '9.6': 'NM', '9.4': 'NM',
        'NM': 'NM', 'NM+': 'NM', 'NM-': 'NM',
        'VF': 'VF', 'VF+': 'VF', 'VF-': 'VF', '8.5': 'VF', '8.0': 'VF',
        'FN': 'FN', 'FN+': 'FN', 'FN-': 'FN', '6.5': 'FN', '6.0': 'FN',
        'VG': 'VG', 'VG+': 'VG', 'VG-': 'VG', '4.5': 'VG', '4.0': 'VG',
        'G': 'G', 'GD': 'G', '2.5': 'G', '2.0': 'G',
        'FR': 'FR', '1.5': 'FR',
        'PR': 'PR', '1.0': 'PR', '0.5': 'PR'
    };
    
    const gradeLabel = grade.grade_label || gradeResult.grade_label;
    const finalGrade = grade.final_grade || gradeResult.final_grade;
    const lookupGrade = gradeMap[gradeLabel] || gradeMap[String(finalGrade)] || 'VF';
    
    try {
        // Check cache status first
        try {
            const cacheResponse = await fetch(`${API_URL}/api/cache/check`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify({
                    title: title,
                    issue: issue,
                    grade: lookupGrade
                })
            });
            
            const cacheResult = await cacheResponse.json();
            
            // Show warning if not cached
            if (cacheResult.success && !cacheResult.cached) {
                showCacheWarning();
            }
        } catch (cacheError) {
            // Don't block on cache check failure - just proceed normally
            console.log('Cache check failed, proceeding with valuation:', cacheError);
        }
        
        // Get valuation
        const response = await fetch(`${API_URL}/api/valuate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                title: title,
                issue: issue,
                grade: lookupGrade
            })
        });
        
        const valuation = await response.json();
        
        if (valuation.error) {
            throw new Error(valuation.error);
        }
        
        // Calculate recommendation using tiered slab premium model
        const rawValue = valuation.fair_value || valuation.final_value || 0;
        const slabPremium = getSlabPremium(rawValue);
        const gradingCost = getGradingCost(rawValue);
        
        const slabbedValue = rawValue * slabPremium;
        const valueIncrease = slabbedValue - rawValue;
        const netBenefit = valueIncrease - gradingCost;
        const roi = gradingCost > 0 ? ((netBenefit / gradingCost) * 100).toFixed(0) : 0;
        
        // Render recommendation with CLEARER math
        const isWorthIt = netBenefit > 0;
        
        // Stop thinking animation before showing results
        stopThinkingAnimation();
        
        document.getElementById('recommendationValues').innerHTML = `
            <div class="recommendation-math">
                <div class="math-row">
                    <span class="math-label">Raw value (Fair Market):</span>
                    <span class="math-value">$${rawValue.toFixed(2)}</span>
                </div>
                <div class="math-row">
                    <span class="math-label">+ Slab premium:</span>
                    <span class="math-value positive">+$${valueIncrease.toFixed(2)}</span>
                </div>
                <div class="math-row">
                    <span class="math-label">= Slabbed value:</span>
                    <span class="math-value">$${slabbedValue.toFixed(2)}</span>
                </div>
                <div class="math-divider"></div>
                <div class="math-row">
                    <span class="math-label">− Grading cost (CGC):</span>
                    <span class="math-value negative">−$${gradingCost.toFixed(2)}</span>
                </div>
                <div class="math-divider"></div>
                <div class="math-row math-total ${isWorthIt ? 'positive' : 'negative'}">
                    <span class="math-label">Net ${isWorthIt ? 'profit' : 'loss'} from grading:</span>
                    <span class="math-value">${isWorthIt ? '+' : ''}$${netBenefit.toFixed(2)}</span>
                </div>
            </div>
        `;
        
        // Verdict
        let verdictHTML;
        if (netBenefit > gradingCost * 0.5) {
            // Good ROI
            verdictHTML = `
                <div class="recommendation-verdict submit" style="border: 2px solid var(--brand-purple); border-radius: 12px; padding: 1.5rem;">
                    <div class="verdict-icon">✅</div>
                    <div class="verdict-text">SUBMIT FOR GRADING</div>
                    <div class="verdict-reason">You'll make ~$${netBenefit.toFixed(2)} profit after grading costs</div>
                </div>
            `;
        } else if (netBenefit > 0) {
            // Marginal
            verdictHTML = `
                <div class="recommendation-verdict" style="background: rgba(99, 102, 241, 0.1); border: 2px solid var(--brand-purple); border-radius: 12px; padding: 1.5rem;">
                    <div class="verdict-icon">🤔</div>
                    <div class="verdict-text" style="color: var(--brand-indigo);">CONSIDER GRADING</div>
                    <div class="verdict-reason">Small profit of $${netBenefit.toFixed(2)} - worth it if you want the slab for your collection</div>
                </div>
            `;
        } else {
            // Not worth it
            verdictHTML = `
                <div class="recommendation-verdict keep-raw" style="border: 2px solid var(--brand-purple); border-radius: 12px; padding: 1.5rem;">
                    <div class="verdict-icon">📦</div>
                    <div class="verdict-text">KEEP RAW</div>
                    <div class="verdict-reason">You'd lose $${Math.abs(netBenefit).toFixed(2)} - grading costs more than the value increase</div>
                </div>
            `;
        }
        
        document.getElementById('recommendationVerdict').innerHTML = verdictHTML;
        
        // Hide cache warning now that recommendation is complete
        hideCacheWarning();
        
    } catch (error) {
        console.error('Error calculating recommendation:', error);
        stopThinkingAnimation();
        document.getElementById('recommendationValues').innerHTML = `
            <p style="color: var(--text-muted); text-align: center;">Could not retrieve market values</p>
        `;
        document.getElementById('recommendationVerdict').innerHTML = '';
        
        // Hide cache warning even on error
        hideCacheWarning();
    }
}

// Slab Premium Calculator - Based on market research (Jan 2026)
// Premium is inversely proportional to raw value:
// - Low value books get huge boost from slab legitimacy
// - High value books already command trust, smaller premium
function getSlabPremium(rawValue) {
    const tiers = [
        { max: 10, premium: 4.0 },      // $0-10: 300% premium - slab = legitimacy
        { max: 15, premium: 3.5 },      // $10-15: 250%
        { max: 20, premium: 3.0 },      // $15-20: 200%
        { max: 30, premium: 2.7 },      // $20-30: 170%
        { max: 40, premium: 2.4 },      // $30-40: 140%
        { max: 50, premium: 2.2 },      // $40-50: 120%
        { max: 75, premium: 2.0 },      // $50-75: 100% - "doubles the value" rule
        { max: 100, premium: 1.85 },    // $75-100: 85%
        { max: 150, premium: 1.7 },     // $100-150: 70%
        { max: 200, premium: 1.6 },     // $150-200: 60%
        { max: 300, premium: 1.5 },     // $200-300: 50%
        { max: 400, premium: 1.45 },    // $300-400: 45%
        { max: 500, premium: 1.4 },     // $400-500: 40%
        { max: 750, premium: 1.35 },    // $500-750: 35%
        { max: 1000, premium: 1.3 },    // $750-1000: 30%
        { max: 1500, premium: 1.25 },   // $1000-1500: 25%
        { max: 2500, premium: 1.22 },   // $1500-2500: 22%
        { max: 5000, premium: 1.18 },   // $2500-5000: 18%
        { max: 10000, premium: 1.15 },  // $5000-10000: 15%
        { max: Infinity, premium: 1.12 } // $10000+: 12% floor
    ];
    
    // Find tier and interpolate for smooth curve
    let prevTier = { max: 0, premium: 4.5 };
    for (const tier of tiers) {
        if (rawValue <= tier.max) {
            // Linear interpolation between tiers
            const range = tier.max === Infinity ? 10000 : tier.max - prevTier.max;
            const position = Math.min((rawValue - prevTier.max) / range, 1);
            return prevTier.premium - (prevTier.premium - tier.premium) * position;
        }
        prevTier = tier;
    }
    return 1.12; // Floor for ultra-high value
}

// Estimate grading cost based on value
function getGradingCost(value) {
    if (value >= 1000) return 150; // Walkthrough tier
    if (value >= 400) return 85;   // Express tier
    if (value >= 200) return 50;   // Economy tier
    return 30; // Modern tier (minimum)
}

// Reset grading mode
function resetGrading() {
    // Reset state
    gradingState = {
        currentStep: 1,
        photos: { 1: null, 2: null, 3: null, 4: null },
        additionalPhotos: [],
        extractedData: null,
        defectsByArea: {},
        finalGrade: null,
        confidence: 0
    };
    
    // Reset all step indicators
    for (let i = 1; i <= 5; i++) {
        const stepEl = document.getElementById(`gradingStep${i}`);
        stepEl.classList.remove('active', 'completed', 'skipped');
        if (i === 1) stepEl.classList.add('active');
        
        const contentEl = document.getElementById(`gradingContent${i}`);
        contentEl.classList.remove('active');
        if (i === 1) contentEl.classList.add('active');
    }
    
    // Reset all inputs and previews
    for (let i = 1; i <= 4; i++) {
        document.getElementById(`gradingUpload${i}`).style.display = 'flex';
        document.getElementById(`gradingPreview${i}`).style.display = 'none';
        document.getElementById(`gradingFeedback${i}`).style.display = 'none';
        // Clear both camera and gallery inputs
        const cameraInput = document.getElementById(`gradingCamera${i}`);
        const galleryInput = document.getElementById(`gradingGallery${i}`);
        if (cameraInput) cameraInput.value = '';
        if (galleryInput) galleryInput.value = '';
        if (i > 1) {
            document.getElementById(`gradingNext${i}`).disabled = true;
        }
    }
    document.getElementById('gradingNext1').disabled = true;
    
    // Clear additional photos
    document.getElementById('additionalPhotos').innerHTML = '';
    
    // Clear comic ID banners
    [2, 3, 4].forEach(step => {
        const banner = document.getElementById(`gradingComicId${step}`);
        if (banner) banner.innerHTML = '';
    });
    
    // Hide quality warning
    const warningEl = document.getElementById('gradeQualityWarning');
    if (warningEl) warningEl.style.display = 'none';
}

// Save graded comic to collection
function saveGradeToCollection() {
    if (!gradingState.finalGrade || !gradingState.extractedData) {
        alert('No grade data to save');
        return;
    }
    
    // Handle nested structure
    const grade = gradingState.finalGrade['COMPREHENSIVE GRADE'] || gradingState.finalGrade;
    
    // Use existing saveToCollection logic
    const comicData = {
        title: gradingState.extractedData.title,
        issue: gradingState.extractedData.issue,
        grade: grade.grade_label || grade.final_grade,
        notes: `Graded via 4-photo analysis. ${grade.grade_reasoning || ''}`
    };
    
    // This would call your existing collection save API
    alert('Save to collection coming soon!');
}

// Cache warning functionality
function showCacheWarning() {
    // Create warning element if it doesn't exist
    let warningEl = document.getElementById('cacheWarning');
    if (!warningEl) {
        warningEl = document.createElement('div');
        warningEl.id = 'cacheWarning';
        warningEl.className = 'cache-warning';
        warningEl.innerHTML = `
            <div class="cache-warning-content">
                <div class="cache-warning-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                        <rect x="3" y="1" width="18" height="22" rx="2" stroke="currentColor" stroke-width="2" fill="none"/>
                        <rect x="6" y="4" width="12" height="13" rx="1" fill="rgba(217, 119, 6, 0.15)" stroke="currentColor" stroke-width="1"/>
                        <text x="12" y="14" text-anchor="middle" fill="currentColor" font-size="10" font-weight="bold" font-family="Arial">?</text>
                        <rect x="6" y="18" width="12" height="3" rx="0.5" fill="currentColor"/>
                    </svg>
                </div>
                <span class="cache-warning-text">This grade of this comic hasn't been checked recently. Market research may take 60-90 seconds...</span>
            </div>
        `;
        
        // Insert before the recommendation verdict section
        const verdictSection = document.getElementById('recommendationVerdict');
        if (verdictSection && verdictSection.parentNode) {
            verdictSection.parentNode.insertBefore(warningEl, verdictSection);
        } else {
            // Fallback: append to grading section
            const gradingSection = document.getElementById('gradingSection');
            if (gradingSection) {
                gradingSection.appendChild(warningEl);
            }
        }
    }
    
    // Show with fade-in animation
    warningEl.style.display = 'block';
    warningEl.style.opacity = '0';
    
    // Trigger fade-in
    requestAnimationFrame(() => {
        warningEl.style.transition = 'opacity 0.3s ease-in-out';
        warningEl.style.opacity = '1';
    });
    
    // Note: No auto-dismiss - warning stays until hideCacheWarning() is called
}

function hideCacheWarning() {
    const warningEl = document.getElementById('cacheWarning');
    if (warningEl && warningEl.style.display !== 'none') {
        warningEl.style.opacity = '0';
        setTimeout(() => {
            warningEl.style.display = 'none';
        }, 300); // Wait for fade-out animation
    }
}

console.log('grading.js loaded');
