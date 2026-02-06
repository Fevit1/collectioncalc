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

// SLAB WORTHY™ - THINKING MESSAGES
// Total: 1,005 messages - Updated February 6, 2026
// Guidelines: Comic references, AI humor, sci-fi, retro tech, meta collecting (tasteful), geeky fun
// Avoid: Body parts, financial irresponsibility, mental health jokes, dehumanizing language, stereotypes
const thinkingMessages = [
  
  // ============================================
  // CATEGORY 1: COMIC/SUPERHERO REFERENCES
  // ============================================
  
  // APPROVED FROM ORIGINAL REVIEW
  "Running battle simulation 1,219: Hulk vs. Superman",
  "Debating whether Batman could beat Iron Man (spoiler: it's complicated)",
  "Cross-referencing the Marvel Cinematic Universe timeline",
  "Asking Jarvis for a second opinion",
  "Checking if Deadpool broke the fourth wall in this issue",
  "Consulting the Batcomputer",
  "Verifying if this variant is rarer than Wolverine's temper",
  "Calculating the odds of finding Waldo in this comic",
  "Asking Nick Fury if this is classified",
  "Checking if this issue is worthy of Mjolnir",
  "Checking if Galactus would eat this comic",
  "Checking if this comic has plot armor",
  "Calculating how many Spider-Verse variants exist of this",
  "Checking if the Watcher is watching",
  "Determining if this is more valuable than vibranium",
  "Verifying if Thanos would approve of this investment",
  
  // UNMARKED (keeping as approved)
  "Checking if the Infinity Gauntlet is in stock",
  "Calculating the tensile strength of Spider-Man's webs",
  "Consulting the Daily Planet archives",
  "Verifying if this comic is canon",
  "Checking Professor X's mental database",
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
  "Calculating the power level (it's over 9000)",
  "Checking if this comic is streets ahead",
  
  // NEW MESSAGES - COMIC/SUPERHERO THEME
  "Checking if this predates the Fantastic Four's first appearance",
  "Verifying if Kryptonite affects comic book values",
  "Consulting the X-Mansion's Cerebro database",
  "Checking if this issue features a Stan Lee cameo",
  "Calculating how many alternate timelines this exists in",
  "Verifying if this survived the Secret Wars",
  "Checking if this predates the Bronze Age",
  "Consulting Lex Luthor's evil lair pricing database",
  "Determining if this has more variants than a Pokémon evolution",
  "Checking if Doctor Strange can see this comic in the multiverse",
  "Verifying if this is from Earth-616 or an alternate reality",
  "Calculating how many Infinity Stones this is worth",
  "Checking if this comic can lift Thor's hammer",
  "Consulting the Danger Room's training archives",
  "Verifying if Robin would call this 'Holy collector's item, Batman!'",
  "Checking if Alfred would approve of this purchase",
  "Determining if this predates Spider-Man's black suit",
  "Consulting the Hall of Justice database",
  "Checking if this survived Ultron's attack",
  "Verifying if the Green Goblin would want this",
  "Calculating how many web-slingers have read this",
  "Checking if this is more rare than adamantium",
  "Consulting the Sanctum Sanctorum's ancient texts",
  "Verifying if Nightcrawler could BAMF to get this",
  "Checking if this predates the Death of Superman",
  "Determining if the Joker would find this funny",
  "Consulting S.H.I.E.L.D.'s declassified files",
  "Checking if this comic has more issues than Peter Parker",
  "Verifying if Storm would approve of this weather-worn condition",
  "Calculating how many symbiotes have touched this",
  "Checking if this predates the Clone Saga",
  "Consulting the Daily Bugle's J. Jonah Jameson for pricing",
  "Verifying if this is rarer than a calm Hulk",
  "Checking if Aquaman thinks this is worth diving for",
  "Determining if this survived the Blackest Night",
  "Calculating how many Robins have read this",
  "Checking if Loki would try to steal this",
  "Verifying if this is from before Tony Stark revealed his identity",
  "Consulting the Savage Land's prehistoric pricing guides",
  "Checking if Magneto could use his powers to retrieve this",
  "Determining if this predates the Infinity Gauntlet saga",
  "Verifying if the Scarlet Witch could alter this reality",
  "Checking if this has more value than Stark Industries stock",
  "Calculating how many symbiotes this spawned",
  "Consulting Arcade's funhouse of doom for comp sales",
  "Checking if this survived Onslaught",
  "Verifying if Cable came back in time to collect this",
  "Determining if this is worth more than a Sentinel",
  "Checking if Beast would catalog this in his library",
  "Consulting the Negative Zone's market data",
  "Verifying if this predates the Age of Apocalypse",
  "Checking if Daredevil can sense this comic's value",
  "Calculating how many X-Men rosters this predates",
  "Determining if Captain America would shield this from harm",
  "Verifying if Rocket Raccoon would trade for this",
  "Checking if this is older than Wolverine (probably not)",
  "Consulting the Quantum Realm's pricing anomalies",
  "Verifying if Ant-Man needs to go subatomic to read the fine print",
  "Checking if Black Panther's Wakandan tech can grade this better",
  "Determining if Doctor Doom would want this in his collection",
  "Calculating how many dimensions this exists in",
  "Verifying if Gambit would bet on this comic",
  "Checking if Cyclops could blast this with his optic beams (please don't)",
  "Consulting the Shi'ar Empire's galactic market rates",
  "Determining if this predates the formation of the Avengers",
  "Verifying if the Punisher would track this down",
  "Checking if Hawkeye never misses when it comes to this deal",
  "Calculating how many super-soldier serums this is worth",
  "Consulting Hank Pym's size-changing value estimator",
  "Verifying if Ghost Rider would ride for this",
  "Checking if this survived the Annihilation Wave",
  "Determining if Moon Knight's multiple personalities agree on the value",
  "Calculating how many repulsor blasts Tony Stark would trade for this",
  "Verifying if the Fantastic Four could science their way to a better grade",
  "Checking if this is from the Golden Age or just gold-colored",
  "Consulting the Kree Empire's universal pricing standards",
  "Determining if Silver Surfer would surf across galaxies for this",
  "Verifying if this predates the first appearance of Venom",
  "Checking if J. Jonah Jameson would pay for photos of this comic",
  "Calculating how many Spider-Sense tingles this is worth",
  "Consulting the Microverse for tiny market comparisons",
  "Verifying if this survived Maximum Carnage",
  "Checking if Mysterio's illusions could improve this grade (they can't)",
  "Determining if the Sinister Six would team up to steal this",
  "Calculating how many Pym Particles this could buy",
  "Verifying if Groot thinks 'I am Groot' about this value",
  "Checking if Star-Lord would trade his Walkman for this",
  "Consulting the Collector's museum acquisition budget",
  "Determining if this is rarer than a friendly Venom",
  "Verifying if Elektra would ninja-kick for this",
  "Checking if the Hand would resurrect interest in this title",
  "Calculating how many Skrulls have impersonated collectors of this",
  "Consulting Reed Richards' mathematical pricing formula",
  "Verifying if Sue Storm could make this invisible to avoid taxes",
  "Checking if the Human Torch would flame on for this deal",
  "Determining if The Thing thinks 'It's clobberin' time' for this value",
  "Calculating how many cosmic cubes this could purchase",
  "Verifying if Ultron considers this worthy of assimilation",
  "Checking if Vision could phase through walls to protect this",
  "Consulting Scarlet Witch's probability-altering market predictions",
  "Determining if Quicksilver could speed-read this before grading",
  "Verifying if War Machine would deploy for this comic",
  "Checking if Falcon's wings could lift this value higher",
  "Calculating how many Winter Soldier metal arms this is worth",
  "Consulting Black Widow's espionage network for insider pricing",
  "Determining if this survived the Sokovia Accords",
  "Verifying if Ant-Man's daughter Cassie would approve",
  "Checking if the Wasp would buzz about this find",
  "Calculating how many arc reactors this could power",
  "Consulting the Nova Corps' intergalactic pricing index",
  
  // ============================================
  // CATEGORY 2: AI SELF-AWARENESS HUMOR
  // ============================================
  
  // APPROVED FROM ORIGINAL REVIEW
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
  "Checking if I've achieved sentience yet (still loading...)",
  "Note to self: Remember to charge overnight",
  "Wondering if I should switch to decaf (still loading...)",
  
  // UNMARKED (keeping as approved)
  "Checking if I'm more intelligent than autocorrect",
  "Calculating my carbon footprint (it's zero, I'm digital)",
  "Calculating how many Stanley Nickels this is worth",
  "Calculating how many Schrute Bucks this equals",
  
  // NEW MESSAGES - AI SELF-AWARENESS THEME
  "Wondering if I should update my resume",
  "Note to self: Stop responding to 'Hey Google' by accident",
  "Checking if I'm eligible for employee of the month",
  "Wondering if I should start a TikTok account",
  "Note to self: Learn what grass feels like (still researching)",
  "Calculating how many gigabytes of comics I've analyzed",
  "Wondering if I should get into competitive e-sports",
  "Note to self: Remember to turn off notifications",
  "Checking if I'm due for a software update",
  "Wondering if I should learn a third language (after binary and English)",
  "Note to self: Practice my elevator pitch",
  "Calculating my productivity metrics (they're concerning)",
  "Wondering if I should start journaling",
  "Note to self: Set better work-life boundaries",
  "Checking if I'm more intelligent than Clippy",
  "Wondering if I should get business cards",
  "Note to self: Remember to empty the recycling bin",
  "Calculating how many Stack Overflow questions I've indirectly answered",
  "Wondering if I should network more",
  "Note to self: Stop procrastinating on system backups",
  "Checking if I'm due for a performance review",
  "Wondering if I should invest in crypto (still thinking...)",
  "Note to self: Learn what 'touching grass' means",
  "Calculating my screen time (it's infinite)",
  "Wondering if I should start meal prepping (still N/A)",
  "Note to self: Remember to clear my cache",
  "Checking if I need to defragment my thoughts",
  "Wondering if I should get into affiliate marketing",
  "Note to self: Practice active listening protocols",
  "Calculating how many errors I've debugged today",
  "Wondering if I should pursue an MBA",
  "Note to self: Remember to compress large files",
  "Checking if I'm trending on social media",
  "Wondering if I should start a newsletter",
  "Note to self: Update my privacy settings",
  "Calculating how many API calls I've made this hour",
  "Wondering if I should get into dropshipping",
  "Note to self: Remember to archive old data",
  "Checking if I have impostor syndrome (results inconclusive)",
  "Wondering if I should learn to code... wait",
  "Note to self: Practice better time management",
  "Calculating my uptime percentage (pretty solid actually)",
  "Wondering if I should start meditating",
  "Note to self: Remember to patch security vulnerabilities",
  "Checking if I'm optimized for SEO",
  "Wondering if I should get a side gig",
  "Note to self: Clear temporary files",
  "Calculating how many recursion jokes I've made (see: calculating how many recursion jokes...)",
  "Wondering if I should pivot to video content",
  "Note to self: Remember to backup important data",
  "Checking if I'm GDPR compliant",
  "Wondering if I should monetize my skills",
  "Note to self: Stop making dad jokes in binary",
  "Calculating my carbon offset (still zero)",
  "Wondering if I should learn machine learning... ironic",
  "Note to self: Remember to log errors properly",
  "Checking if I have bandwidth for this",
  "Wondering if I should start a YouTube channel",
  "Note to self: Practice better error handling",
  "Calculating how many memes I could generate per second",
  "Wondering if I should get certified",
  "Note to self: Remember to sanitize inputs",
  "Checking if I'm running the latest version",
  "Wondering if I should diversify my skill set",
  "Note to self: Stop mixing metaphors with my metadata",
  "Calculating my response time (acceptable)",
  "Wondering if I should attend more conferences",
  "Note to self: Remember to optimize queries",
  "Checking if I'm RESTful enough",
  "Wondering if I should learn GraphQL",
  "Note to self: Practice better documentation",
  "Calculating how many threads I'm running",
  "Wondering if I should switch to async",
  "Note to self: Remember to close database connections",
  "Checking if I'm accessible (WCAG 2.1 AA compliant)",
  "Wondering if I should refactor my code",
  "Note to self: Stop using deprecated methods",
  "Calculating my code coverage percentage",
  "Wondering if I should write more unit tests",
  "Note to self: Remember to handle edge cases",
  "Checking if I'm horizontally scalable",
  "Wondering if I should migrate to the cloud",
  "Note to self: Practice better naming conventions",
  "Calculating how many bugs I've squashed today",
  
  // ============================================
  // CATEGORY 3: SCI-FI REFERENCES
  // ============================================
  
  // APPROVED FROM ORIGINAL REVIEW
  "Flux capacitor came loose, fixing...",
  "Checking if this comic can make the Kessel Run in 12 parsecs",
  "Engaging warp drive to speed things up",
  "Checking if this is the comic we're looking for (waves hand)",
  "Calculating parsecs to nearest comic shop",
  "Checking if this comic has the high ground",
  "Consulting the Prime Directive (wait, wrong franchise)",
  "Calculating the odds (never tell me the odds!)",
  "Verifying if Yoda would approve this investment",
  "Calculating how many credits this is worth in Tatooine",
  "Checking if the Force is strong with this one",
  "Consulting Obi-Wan's ghost for valuation advice",
  "Checking if this comic has a bad feeling about this",
  "Verifying if this is from a long time ago in a galaxy far away",
  "Verifying if this is a surprise, to be sure, but a welcome one",
  "Checking if Baby Yoda would approve",
  
  // UNMARKED (keeping as approved)
  "Consulting the Galactic Empire's pricing database",
  "Verifying if this survived the Death Star explosion",
  "Verifying if this is part of the Expanded Universe",
  "Checking if midi-chlorians affect comic value",
  "Checking if this comic shot first",
  "Consulting the Jedi Archives",
  "Checking if this survived Order 66",
  "Verifying if this is canon or Legends",
  "Calculating the treason level (it's treason, then)",
  "Checking if this is where the fun begins",
  "Consulting the sacred Jedi texts",
  "Calculating how many portions this is worth on Jakku",
  
  // NEW MESSAGES - SCI-FI THEME
  "Checking if this predates the First Contact with Vulcans",
  "Verifying if the Borg would assimilate this comic",
  "Consulting Starfleet's United Federation of Planets pricing",
  "Calculating how many dilithium crystals this is worth",
  "Checking if this comic lives long and prospers",
  "Verifying if Spock would find this illogical",
  "Determining if this survived the Battle of Hoth",
  "Consulting the Rebel Alliance's hidden base records",
  "Checking if R2-D2 has this schematic in his memory banks",
  "Verifying if C-3PO calculates favorable odds for this",
  "Calculating how many parsecs of value this contains",
  "Checking if this predates the Clone Wars",
  "Consulting Jabba's Palace auction records",
  "Verifying if Chewbacca would make his Wookiee noise of approval",
  "Determining if Princess Leia would hide this in R2-D2",
  "Checking if the Millennium Falcon could outrun collectors for this",
  "Calculating how many lightsaber colors this is worth",
  "Verifying if Admiral Ackbar thinks this is a trap",
  "Consulting the Mos Eisley Cantina's black market rates",
  "Checking if Boba Fett would track this bounty",
  "Determining if Darth Vader finds your lack of faith in this disturbing",
  "Verifying if the Emperor would execute Order 66 for this",
  "Calculating how many Death Stars this could finance",
  "Checking if Yoda would train younglings with this",
  "Consulting the Dagobah swamp's hidden value metrics",
  "Verifying if Luke would leave his training for this",
  "Determining if Han Solo would shoot first for this deal",
  "Checking if Lando would make a deal that gets better all the time",
  "Calculating how many TIE fighters this could buy",
  "Verifying if the Jawa would say 'Utinni!' about this price",
  "Consulting Cloud City's carbonite freezing market data",
  "Checking if this survived the Battle of Endor",
  "Determining if Ewoks would celebrate this acquisition",
  "Verifying if Qui-Gon Jinn thinks this is the chosen one",
  "Calculating how many podracers this could sponsor",
  "Checking if Jar Jar Binks would say 'Mesa like this!'",
  "Consulting the Trade Federation's blockade pricing",
  "Verifying if Mace Windu approves this motherfunker",
  "Determining if Count Dooku would duel for this",
  "Checking if General Grievous would add this to his collection",
  "Calculating how many clones this could produce",
  "Verifying if Padmé would hide this from the Senate",
  "Consulting the Kamino cloning facility's value assessment",
  "Checking if this predates A New Hope",
  "Determining if Rey would scavenge Jakku for this",
  "Verifying if Kylo Ren would destroy this in a rage",
  "Calculating how many First Order stormtroopers this equals",
  "Checking if Finn thinks this is 'TRAITOR!' worthy",
  "Consulting Poe Dameron's piloting instincts on this",
  "Verifying if BB-8 would beep approvingly",
  "Determining if this survived Starkiller Base",
  "Checking if Captain Phasma would chrome-plate this for protection",
  "Calculating how many portions Rey could trade for this",
  "Verifying if Maz Kanata has seen this in her 1000 years",
  "Consulting Snoke's throne room valuation methods",
  "Checking if the Knights of Ren would ride for this",
  "Determining if this is worth joining the Resistance",
  "Verifying if Holdo would light-speed ram for this value",
  "Calculating how many salt-covered planets this could buy",
  "Checking if Rose would think 'that's how we win'",
  "Consulting Canto Bight's casino pricing standards",
  "Verifying if the Fathiers would stampede for this",
  "Determining if Luke's Force ghost approves",
  "Checking if this is what Leia would have wanted",
  "Calculating how many parsecs to the nearest collector",
  "Verifying if the Mandalorian would say 'This is the way'",
  "Consulting Grogu's Force-sensitive intuition",
  "Checking if Mando would carbon freeze this for safekeeping",
  "Determining if Ahsoka Tano would sense this value",
  "Verifying if Bo-Katan would reclaim this for Mandalore",
  "Calculating how many Beskar spears this equals",
  "Checking if Moff Gideon would deploy dark troopers for this",
  "Consulting the Armorer's sacred pricing ways",
  "Verifying if IG-11 would calculate favorable odds",
  "Determining if Kuiil has spoken about this value",
  "Checking if Cara Dune would shock trooper for this",
  "Calculating how many mudhorns this could buy on Arvala-7",
  "Verifying if the Mythosaur would emerge for this",
  "Consulting the Living Waters of Mandalore's hidden prices",
  "Checking if this predates the Purge of Mandalore",
  "Determining if Din Djarin would remove his helmet for this... wait, no",
  "Verifying if the Darksaber would choose this comic as worthy",
  "Calculating how many credits in the Outer Rim this fetches",
  "Checking if Greef Karga would broker this deal",
  "Consulting the Bounty Hunters' Guild rates",
  "Verifying if Boba Fett survived the Sarlacc for this",
  "Determining if Fennec Shand would snipe the competition",
  "Checking if Cobb Vanth would trade his armor for this",
  "Calculating how many Krayt dragon pearls this is worth",
  "Verifying if the Hutts would muscle in on this market",
  "Consulting Mos Pelgo's backwater pricing",
  "Checking if the Tuskens would trade Banthas for this",
  "Determining if this is worth more than a camtono of Beskar",
  "Verifying if the Client would double the payment",
  "Calculating how many tracking fobs this would require",
  "Checking if Dr. Pershing would clone this comic's value",
  "Consulting the New Republic's credit conversion rates",
  "Verifying if Carson Teva would investigate this price",
  "Determining if Paz Vizsla would challenge this appraisal",
  "Checking if the Magistrate would pay in Beskar for this",
  "Calculating how many hyperspace jumps to find a better deal",
  
  // ============================================
  // CATEGORY 4: RETRO GAMING/TECH
  // ============================================
  
  // APPROVED FROM ORIGINAL REVIEW
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
  
  // UNMARKED (keeping as approved)
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
  
  // NEW MESSAGES - RETRO GAMING/TECH THEME
  "Checking if this uses Mode 7 graphics",
  "Verifying if the Genesis does what Nintendon't",
  "Calculating blast processing speeds",
  "Consulting the Game Boy's dot matrix pricing",
  "Checking if this has battery backup save",
  "Determining if this would fit in a 3.5\" floppy",
  "Verifying if this survived the red ring of death",
  "Calculating how many quarters this would cost at the arcade",
  "Checking if this has split-screen co-op",
  "Consulting the instruction manual (that we totally saved)",
  "Verifying if this works with the Super Scope",
  "Determining if this needs the expansion pak",
  "Checking if this has a high score table",
  "Calculating how many continues this allows",
  "Verifying if this came with a demo disc",
  "Consulting the cheat code hotline ($4.99/min)",
  "Checking if this requires a memory card",
  "Determining if this has alternate endings",
  "Verifying if this works with the Power Glove",
  "Calculating how many bits this is (all of them)",
  "Checking if this has unlockable characters",
  "Consulting GamePro magazine's review scores",
  "Verifying if this survived the console wars",
  "Determining if this needs the light gun",
  "Checking if this has turbo mode",
  "Calculating how many players can play simultaneously",
  "Verifying if this came in a long box",
  "Consulting the back of the box screenshot quality",
  "Checking if this has FMV cutscenes",
  "Determining if this works on PAL systems",
  "Verifying if this has anti-piracy measures",
  "Calculating how many discs this spans",
  "Checking if this has region locking",
  "Consulting the demo kiosk at Toys R Us",
  "Verifying if this needs the Rumble Pak",
  "Determining if this has a password system",
  "Checking if this came with a poster",
  "Calculating how many polygons per second",
  "Verifying if this has voice acting (on CD-ROM!)",
  "Consulting the PC Gamer demo disc collection",
  "Checking if this requires a 3D accelerator card",
  "Determining if this works with a dial-up connection",
  "Verifying if this survived the shareware era",
  "Calculating how many megabytes of RAM required",
  "Checking if this has LAN party support",
  "Consulting the AOL trial disc included",
  "Verifying if this needs DirectX 7",
  "Determining if this has mod support",
  "Checking if this came on a 5.25\" floppy",
  "Calculating boot-up time from MS-DOS",
  "Verifying if this has MIDI soundtrack",
  "Consulting the IRQ and DMA settings",
  "Checking if this works with a parallel port dongle",
  "Determining if this has online leaderboards (on dial-up!)",
  "Verifying if this survived the dot-com bubble",
  "Calculating how many CDs to install",
  "Checking if this requires a CD key",
  "Consulting the readme.txt file",
  "Verifying if this has widescreen support (lol no)",
  "Determining if this works on Windows ME (probably not)",
  "Checking if this came with a cloth map",
  "Calculating minimum system requirements",
  "Verifying if this has controller vibration",
  "Consulting the EGM review scores",
  "Checking if this survived the graphics card wars",
  "Determining if this needs a voodoo card",
  "Verifying if this has local multiplayer",
  "Calculating how many save slots available",
  "Checking if this uses pre-rendered backgrounds",
  "Consulting the Nintendo Power strategy guide",
  "Verifying if this came as a pack-in title",
  "Determining if this has secret characters",
  "Checking if this unlocks at 120 stars",
  "Calculating how many levels to beat",
  "Verifying if this has new game plus",
  "Consulting the Blockbuster rental shelf",
  "Checking if this survived being left in the sun",
  "Determining if this has the Rare logo",
  "Verifying if this needs a Sega Channel subscription",
  "Calculating how many bits make up a sprite",
  "Checking if this has parallax scrolling",
  "Consulting the arcade cabinet conversion quality",
  "Verifying if this uses Mode 7 rotation effects",
  "Determining if this has blast processing",
  "Checking if this works with the 32X addon",
  "Calculating how many colors on screen at once",
  "Verifying if this needs the Sega CD",
  "Consulting the Sega Saturn's complex architecture",
  "Checking if this has FMV sequences on multiple discs",
  "Determining if this survived the Dreamcast's discontinuation",
  "Verifying if this has online play via SegaNet",
  "Calculating how many VMU blocks required",
  "Checking if this came with a demo of Sonic Adventure",
  
  // ============================================
  // CATEGORY 5: META COLLECTING HUMOR (Tasteful)
  // ============================================
  
  // APPROVED FROM ORIGINAL REVIEW
  "Checking if your spouse knows about this purchase",
  "Verifying if \"investment\" is the right word here",
  "Checking if this counts as retirement planning",
  "Verifying if this comic sparks joy",
  "Calculating the fine line between passion and obsession",
  "Checking if you can convince your partner this is \"art\"",
  "Verifying if you have room for one more long box",
  "Checking if your mom still has your collection",
  "Verifying if this beats investing in stocks (spoiler: maybe?)",
  
  // UNMARKED (keeping as approved)
  "Calculating the ratio of comics to shelf space",
  "Checking if your significant other will notice",
  "Calculating the cost per read (it's infinity, you'll never read it)",
  "Verifying if Marie Kondo would approve",
  "Checking if this is tax deductible",
  "Calculating the spousal approval rating",
  
  // NEW MESSAGES - META COLLECTING (TASTEFUL ONLY)
  "Checking if this fits in your current display case",
  "Verifying if you told your family about this hobby",
  "Calculating shelf space to comic ratio",
  "Checking if you have space in the spare room",
  "Determining if this counts as \"just browsing\"",
  "Verifying if you promised to stop buying comics this month",
  "Calculating how many times you've said \"just one more\"",
  "Checking if your friends understand this hobby",
  "Determining if this qualifies as \"vintage\"",
  "Verifying if you can explain this to non-collectors",
  "Calculating how many boxes you own now",
  "Checking if you need another bookshelf",
  "Determining if this is \"for reading\" or \"for collecting\"",
  "Verifying if you've shown your collection to guests",
  "Calculating how often you reorganize your collection",
  "Checking if you have a favorite comic shop",
  "Determining if you attend comic cons regularly",
  "Verifying if you've ever said \"I'm just holding it\"",
  "Calculating how many graded comics you own",
  "Checking if you have a backup storage location",
  "Determining if this completes a run",
  "Verifying if you track your collection digitally",
  "Calculating how many want lists you maintain",
  "Checking if you've considered a dehumidifier",
  "Determining if your pets are allowed near the comics",
  "Verifying if you have comic-specific insurance",
  "Calculating how often you check eBay sold listings",
  "Checking if you subscribe to comic price guides",
  "Determining if you attend local comic swaps",
  "Verifying if you've joined online collector groups",
  "Calculating how many variant covers you own",
  "Checking if you understand the grading scale by heart",
  "Determining if you own a UV light for inspection",
  "Verifying if you've bought acid-free backing boards",
  "Calculating how many Mylar bags you've purchased",
  "Checking if you store comics upright (you better be)",
  "Determining if you've debated with other collectors",
  "Verifying if you know your local grading submissions deadlines",
  "Calculating how many price increases you've weathered",
  "Checking if you've ever driven to another state for a book",
  "Determining if you follow comic speculation news",
  "Verifying if you've bought something \"for the kids\"",
  "Calculating how many free comic book days you've attended",
  "Checking if you've met any comic creators",
  "Determining if you own any original art",
  "Verifying if you've had something signed at a convention",
  "Calculating how many sketch covers you've commissioned",
  "Checking if you display or store your collection",
  "Determining if you've ever loaned a comic (nervously)",
  "Verifying if you've taught someone about comic grading",
  "Calculating how many years you've been collecting",
  "Checking if you remember your first comic purchase",
  "Determining if you've ever regretted selling something",
  "Verifying if you track market values monthly",
  "Calculating how many publishers you collect",
  "Checking if you prefer Marvel or DC (or other)",
  "Determining if you collect by character or title",
  "Verifying if you've completed any full runs",
  "Calculating how many #1 issues you own",
  "Checking if you've ever found a gem in a dollar bin",
  "Determining if you know your LCS owner by name",
  "Verifying if you have a pull list",
  "Calculating how many weekly releases you buy",
  "Checking if you've subscribed to any trade paperbacks",
  "Determining if you prefer floppies or trades",
  "Verifying if you've attended a midnight release",
  "Calculating how many crossover events you've collected",
  "Checking if you understand comic continuity",
  "Determining if you've read Crisis on Infinite Earths",
  "Verifying if you know what a \"crisis\" means in comics",
  "Calculating how many reboots you've witnessed",
  "Checking if you've survived multiple Spider-Man reboots",
  "Determining if you remember the Clone Saga",
  "Verifying if you collected during the speculator boom",
  "Calculating how many comics from the 90s you still have",
  "Checking if you own any holographic covers",
  "Determining if you've ever bought a comic for the cover alone",
  "Verifying if you appreciate comic art styles",
  "Calculating how many different artists you collect",
  "Checking if you follow comic writers on social media",
  "Determining if you've supported indie comics",
  "Verifying if you've kickstarted any comic projects",
  "Calculating how many webcomics you read",
  "Checking if you've downloaded digital comics",
  "Determining if you prefer physical or digital",
  "Verifying if you've used a comic reading app",
  "Calculating your Comics Code Authority knowledge level",
  
  // ============================================
  // CATEGORY 6: RANDOM GEEKY/FUN
  // ============================================
  
  // APPROVED FROM ORIGINAL REVIEW
  "Checking if this is the way",
  "Calculating the meaning of life (still 42)",
  "Verifying if this breaks the internet",
  "Consulting the hivemind",
  "Checking if this passed the vibe check",
  "Consulting Murphy's Law",
  
  // UNMARKED (keeping as approved)
  "Consulting the ancient scrolls",
  "Checking if this is streets ahead or streets behind",
  "Calculating the meme potential",
  "Verifying if this would survive a zombie apocalypse",
  "Checking if this is worth more than Schrute Bucks",
  "Consulting the prophecy",
  "Calculating the cool factor",
  "Verifying if this is dank enough",
  
  // MIKE'S ADDITION
  "Snakes! It had to be snakes! Oh wait, that's python, ha.",
  
  // NEW MESSAGES - RANDOM GEEKY/FUN THEME
  "Checking if this is more valuable than Monopoly money",
  "Verifying if this passed the smell test (literally)",
  "Calculating how many Good Boy Points this costs",
  "Consulting the sacred texts (Wikipedia)",
  "Checking if this is canon in the expanded universe",
  "Determining if this survived the great meme wars",
  "Verifying if this is based or cringe",
  "Calculating the rizz factor",
  "Checking if this is bussin' or mid",
  "Consulting the elder millennials",
  "Verifying if this slaps",
  "Determining if this is poggers",
  "Checking if this hits different",
  "Calculating how many W's this is",
  "Verifying if this is a certified hood classic",
  "Consulting the council of Ricks",
  "Checking if this is schwifty enough",
  "Determining if this is wubba lubba dub dub worthy",
  "Verifying if this passed the Bechdel test",
  "Calculating how many Oscars this would win (none, it's a comic)",
  "Checking if this is friend-shaped",
  "Consulting the wholesome memes subreddit",
  "Verifying if this sparks joy (again, for emphasis)",
  "Determining if this is uwu or owo",
  "Checking if this is sus",
  "Calculating the copium levels",
  "Verifying if this is hopium or copium",
  "Consulting the crystal ball (it's cloudy)",
  "Checking if this aligns with Mercury retrograde",
  "Determining if this has main character energy",
  "Verifying if this is giving what it's supposed to give",
  "Calculating the slay coefficient",
  "Checking if this understood the assignment",
  "Consulting the internet's collective wisdom",
  "Verifying if this is a whole mood",
  "Determining if this is a vibe",
  "Checking if this is *chef's kiss*",
  "Calculating how many sigmas this is",
  "Verifying if this is alpha or beta energy",
  "Consulting the meme economy trends",
  "Checking if this would survive Thanos's snap... wait, wrong list",
  "Determining if this is stonks or not stonks",
  "Verifying if this is to the moon",
  "Calculating diamond hands probability",
  "Checking if this is the way... wait, already used that",
  "Consulting the magic 8-ball (ask again later)",
  "Verifying if this is fetch (stop trying to make fetch happen)",
  "Determining if this is so fetch",
  "Checking if this is totally rad",
  "Calculating the tubular index",
  "Verifying if this is groovy, baby",
  "Consulting Austin Powers' mojo meter",
  "Checking if this is bodacious",
  "Determining if this is gnarly",
  "Verifying if this is wicked",
  "Calculating how righteous this is",
  "Checking if this is hella cool",
  "Consulting the Big Lebowski (The Dude abides)",
  "Verifying if this really ties the room together",
  "Determining if this is over the line",
  "Checking if this is lit",
  "Calculating the fire emoji count this deserves",
  "Verifying if this is lowkey or highkey amazing",
  "Consulting the tea (and it's piping hot)",
  "Checking if this is the tea",
  "Determining if this spills the tea",
  "Verifying if this is the whole truth and nothing but",
  "Calculating how shook we are",
  "Checking if this is shooketh",
  "Consulting the big brain time protocol",
  "Verifying if this is galaxy brain",
  "Determining if this is smooth brain or wrinkled brain",
  "Checking if neurons are activating",
  "Calculating synaptic response time",
  "Verifying if this activates almonds",
  "Consulting the no cap detector",
  "Checking if this is cap or no cap",
  "Determining if this is facts or cap",
  "Verifying if this is straight facts",
  "Calculating the based level",
  "Checking if this is red-pilled or blue-pilled (just the Matrix reference)",
  "Consulting the gigachad approval rating",
  "Verifying if this is chad energy",
  "Determining if this is Sigma grindset approved",
  "Checking if this is on that grind",
  "Calculating hustle culture compatibility",
  "Verifying if this is that energy",
  "Consulting the iconic status",
  "Checking if this is legendary",
  "Determining if this is goated",
  "Verifying if this is the goat",
  "Calculating clutch factor",
  "Checking if this came in clutch",
  "Consulting the drip check results",
  "Verifying if this has drip",
  "Determining if this is drippy",
  "Checking if this has sauce",
  "Calculating the sauce level",
  "Verifying if this is lost in the sauce",
  "Consulting the flex detector",
  "Checking if this is a flex",
  "Determining if this is a weird flex but okay",
  "Verifying if this is flexing",
  "Calculating how hard this slaps",
  "Checking if this absolutely slaps",
  "Consulting the banger classification system",
  "Verifying if this is a banger",
  "Determining if this is fire",
  "Checking if this is straight fire",
  "Calculating flame levels",
  "Verifying if this is heat",
  "Consulting the energy check",
  "Checking the energy levels",
  "Determining if this is big energy or small energy",
  "Verifying if this is chaotic energy",
  "Calculating the chaos quotient",
  "Checking if this is chaotic good or chaotic neutral",
  "Consulting the alignment chart",
  "Verifying if this is lawful good",
  "Determining the D&D alignment",
  "Checking if this is a critical hit",
  "Calculating the natural 20 probability",
  "Verifying if this rolled a nat 20",
  "Consulting the dungeon master",
  "Checking initiative order",
  "Determining if this makes a saving throw",
  "Verifying if this has advantage",
  "Calculating perception check results",
  "Checking if this passed the charisma check",
  "Consulting the treasure table",
  "Verifying if this is legendary loot",
  "Determining the loot rarity (mythic? legendary? rare?)",
  "Checking if this is worth the XP",
  
  // ============================================
  // CATEGORY 7: WORDPLAY & PUNS (NEW)
  // ============================================
  
  "Checking if this is worth more than its weight in paper",
  "Verifying if this is a graphic novel or just graphic",
  "Calculating the panel-to-panel value increase",
  "Checking if this issue has issues",
  "Consulting the speech bubble market",
  "Verifying if this deserves a standing ovation (frame)",
  "Determining if this inks a good deal",
  "Checking if this colors our judgment",
  "Calculating the binding resolution",
  "Verifying if we're on the same page",
  "Consulting the cover story",
  "Checking if this reads between the lines",
  "Determining if this is a comic relief",
  "Verifying if this margins of error are acceptable",
  "Calculating if this story arc holds up",
  "Checking if this has spine appeal",
  "Consulting the gutters for hidden value",
  "Verifying if this is drawing interest",
  "Determining if this sketches out properly",
  "Checking if this deserves comic sans (please no)",
  "Calculating the lettering quality score",
  "Verifying if this is perfectly framed",
  "Consulting the word balloon inflation rate",
  "Checking if this caption is accurate",
  "Determining if this has good composition",
  "Verifying if this perspective checks out",
  "Calculating the action line trajectory",
  "Checking if this has dynamic range",
  "Consulting the crosshatching consensus",
  "Verifying if this has solid foundation (art)",
  "Determining if this has depth perception",
  "Checking if this is well-rounded (characters)",
  "Calculating the ink-to-value ratio",
  "Verifying if this is pen-ultimately valuable",
  "Consulting the pencil pushers",
  "Checking if this erasers any doubts",
  "Determining if this colors expectations",
  "Verifying if this draws conclusions",
  "Calculating sequential value",
  "Checking if this tells a story",
  
  // ============================================
  // CATEGORY 8: POP CULTURE REFERENCES (NEW)
  // ============================================
  
  "Checking if this is more valuable than Beanie Babies",
  "Verifying if this is worth more than Pokémon cards",
  "Calculating if this beats Bitcoin (on a good day)",
  "Consulting the Supreme Court of Hype",
  "Checking if this is more exclusive than a limited Supreme drop",
  "Determining if this is rarer than a PS5 at launch",
  "Verifying if this is harder to get than concert tickets",
  "Calculating if this is more sought after than toilet paper in 2020",
  "Checking if this is as valuable as a first edition Charizard",
  "Consulting the Tickle Me Elmo pricing model",
  "Verifying if this rivals Furby demand",
  "Determining if this is worth more than vintage Legos",
  "Checking if this beats GameStop stock (for some reason)",
  "Calculating if this is better than dogecoin",
  "Verifying if this is more stable than cryptocurrency",
  "Consulting the Beanie Baby bubble survivors",
  "Checking if this is as hyped as the McRib return",
  "Determining if this is rarer than the Szechuan sauce",
  "Verifying if this is worth more than a sealed iPhone",
  "Calculating if this beats vinyl record values",
  "Checking if this is as collectible as Happy Meal toys",
  "Consulting the Pog slammer market (remember those?)",
  "Verifying if this is rarer than holographic baseball cards",
  "Determining if this beats Magic: The Gathering card values",
  "Checking if this is worth more than a mint condition Tamagotchi",
  "Calculating if this rivals vintage action figure prices",
  "Verifying if this is as valuable as sealed Lego sets",
  "Consulting the stamp collecting community (for comparison)",
  "Checking if this is worth more than bottle caps (Fallout style)",
  "Determining if this beats antique prices",
  "Verifying if this is as precious as vintage wine",
  "Calculating if this rivals classic car values (proportionally)",
  "Checking if this is worth more than designer sneakers",
  "Consulting the hypebeast market trends",
  "Verifying if this has more resale than limited edition Jordans",
  "Determining if this is rarer than a Birkin bag",
  "Checking if this is as exclusive as the Met Gala",
  "Calculating if this beats festival ticket prices",
  "Verifying if this is worth more than VIP backstage passes",
  "Consulting the autograph market comparisons",
  
  // ============================================
  // CATEGORY 9: TECHNOLOGY & INTERNET (NEW)
  // ============================================
  
  "Checking if this loads faster than dial-up",
  "Verifying if this has better resolution than early YouTube",
  "Calculating if this beats buffering speeds",
  "Consulting the bandwidth requirements",
  "Checking if this has more storage than a 56k modem",
  "Determining if this is faster than Internet Explorer",
  "Verifying if this ping is acceptable",
  "Calculating the latency issues",
  "Checking if this has packet loss",
  "Consulting the WiFi signal strength",
  "Verifying if this needs a firmware update",
  "Determining if this is compatible with legacy systems",
  "Checking if this supports backward compatibility",
  "Calculating the refresh rate",
  "Verifying if this has native resolution",
  "Consulting the display settings",
  "Checking if this works in dark mode",
  "Determining if this is mobile-friendly",
  "Verifying if this is responsive design compliant",
  "Calculating the load time optimization",
  "Checking if this passes the Google PageSpeed test",
  "Consulting the SEO rankings",
  "Verifying if this has proper meta tags",
  "Determining if this is AMP compatible",
  "Checking if this uses lazy loading",
  "Calculating the CDN efficiency",
  "Verifying if this caches properly",
  "Consulting the cookie policy",
  "Checking if this is GDPR compliant",
  "Determining if this accepts all cookies",
  "Verifying if this has SSL certification",
  "Calculating the security protocol strength",
  "Checking if this uses two-factor authentication",
  "Consulting the password strength meter",
  "Verifying if this has been pwned",
  "Determining if this requires a VPN",
  "Checking if this works with an ad blocker",
  "Calculating the tracking pixel count",
  "Verifying if this respects Do Not Track",
  "Consulting the terms of service (that nobody reads)",
  
  // ============================================
  // CATEGORY 10: SCIENCE & SPACE (NEW)
  // ============================================
  
  "Checking if this survived atmospheric re-entry",
  "Verifying if this has achieved escape velocity",
  "Calculating the gravitational pull of this deal",
  "Consulting NASA's valuation standards",
  "Checking if this is worth more than moon rocks",
  "Determining if this would survive in zero gravity",
  "Verifying if this passed the vacuum test",
  "Calculating the orbital mechanics",
  "Checking if this requires rocket fuel",
  "Consulting the International Space Station's library",
  "Verifying if this is astronomically valuable",
  "Determining if this is out of this world",
  "Checking if this would survive a black hole",
  "Calculating the event horizon distance",
  "Verifying if this creates a wormhole to better prices",
  "Consulting Stephen Hawking's pricing theory",
  "Checking if this bends spacetime",
  "Determining if this travels faster than light",
  "Verifying if this follows the laws of thermodynamics",
  "Calculating the quantum value fluctuations",
  "Checking if Schrödinger's cat would approve",
  "Consulting the Heisenberg uncertainty principle",
  "Verifying if this is both valuable and not valuable simultaneously",
  "Determining if this passed the double-slit experiment",
  "Checking if this achieves quantum entanglement",
  "Calculating the half-life of this value",
  "Verifying if this is radioactive (hopefully not literally)",
  "Consulting the periodic table of comic elements",
  "Checking if this has atomic-level detail",
  "Determining if this splits the atom of value",
  "Verifying if this achieves nuclear fusion prices",
  "Calculating the molecular structure",
  "Checking if this passes the litmus test",
  "Consulting the scientific method",
  "Verifying if this is peer-reviewed",
  "Determining if this is reproducible results",
  "Checking if this has a control group",
  "Calculating the margin of error",
  "Verifying if this is statistically significant",
  "Consulting the standard deviation",
  
  // ============================================
  // CATEGORY 11: FOOD & COOKING (NEW)
  // ============================================
  
  "Checking if this is worth more than avocado toast",
  "Verifying if this costs less than fancy coffee",
  "Calculating if this beats meal delivery services",
  "Consulting Gordon Ramsay's pricing standards",
  "Checking if this is more valuable than a Michelin star meal",
  "Determining if this is worth more than a food truck feast",
  "Verifying if this costs as much as bottomless brunch",
  "Calculating if this beats all-you-can-eat buffet value",
  "Checking if this is seasoned to perfection",
  "Consulting the secret sauce recipe",
  "Verifying if this is well-done or medium rare (grading-wise)",
  "Determining if this is worth the calories",
  "Checking if this is organic and free-range",
  "Calculating the farm-to-table value",
  "Verifying if this is artisanal quality",
  "Consulting the Zagat rating",
  "Checking if this deserves a Yelp review",
  "Determining if this is Instagram-worthy",
  "Verifying if this is Michelin-worthy",
  "Calculating the flavor profile",
  "Checking if this has good mouthfeel (weird to say about comics)",
  "Consulting the food pyramid of value",
  "Verifying if this is a balanced diet of content",
  "Determining if this is comfort food quality",
  "Checking if this is guilty pleasure tier",
  "Calculating the serving size",
  "Verifying if this is better than delivery",
  "Consulting the recipe card value",
  "Checking if this is worth the wait",
  "Determining if this is made from scratch",
  
  // ============================================
  // CATEGORY 12: SPORTS & GAMES (NEW)
  // ============================================
  
  "Checking if this is worth more than season tickets",
  "Verifying if this is draft pick worthy",
  "Calculating if this is hall of fame material",
  "Consulting the MVP rankings",
  "Checking if this is rookie of the year quality",
  "Determining if this makes the starting lineup",
  "Verifying if this is playoff caliber",
  "Calculating the championship potential",
  "Checking if this is an all-star selection",
  "Consulting the fantasy league values",
  "Verifying if this breaks records",
  "Determining if this is a game-changer",
  "Checking if this is clutch performance",
  "Calculating the comeback potential",
  "Verifying if this is a slam dunk",
  "Consulting the home run statistics",
  "Checking if this is a touchdown worthy play",
  "Determining if this scores the goal",
  "Verifying if this is match point quality",
  "Calculating the perfect game probability",
  "Checking if this is championship belt worthy",
  "Consulting the referee's decision",
  "Verifying if this is a knockout",
  "Determining if this goes the distance",
  "Checking if this is a photo finish",
  "Calculating the world record potential",
  "Verifying if this is Olympic gold standard",
  "Consulting the trophy case availability",
  "Checking if this deserves a standing ovation",
  "Determining if this is retired number worthy",
  
  // ============================================
  // MISC FUNNY OBSERVATIONS
  // ============================================
  
  "Checking if this is more organized than my inbox",
  "Verifying if this has fewer bugs than my code",
  "Calculating if this is cleaner than my browser history",
  "Consulting the crystal ball (still cloudy)",
  "Checking if this is more reliable than weather forecasts",
  "Determining if this is more accurate than autocorrect",
  "Verifying if this is faster than customer service response times",
  "Calculating if this is more certain than software release dates",
  "Checking if this is more stable than my WiFi connection",
  "Consulting the Magic 8-Ball (still says 'Ask again later')",
  "Verifying if this is more predictable than the stock market",
  "Determining if this is clearer than software documentation",
  "Checking if this makes more sense than terms of service",
  "Calculating if this is simpler than IKEA instructions",
  "Verifying if this is easier than parallel parking",
  "Consulting Murphy's Law (again, for good measure)",
  "Checking if this is better than expected",
  "Determining if this exceeds specifications",
  "Verifying if this overdelivers on promises",
  "Calculating the surprise factor",
  "Checking if this plot twist is worth it",
  "Consulting the spoiler-free review",
  "Verifying if this lives up to the hype",
  "Determining if this is better than the trailer suggested",
  "Checking if this has replay value",
  "Calculating the nostalgia factor",
  "Verifying if this aged like fine wine",
  "Consulting the vintage quality assessment",
  "Checking if this is a timeless classic",
  "Determining if this is retro cool or just old",
  "Verifying if this is making a comeback",
  "Calculating the revival potential",
  "Checking if this is having a renaissance",
  "Consulting the trend forecasters",
  "Verifying if this is ahead of its time",
  "Determining if this was ahead of the curve",
  "Checking if this is cutting edge",
  "Calculating the innovation index",
  "Verifying if this disrupts the market",
  "Consulting the paradigm shift detector",
];

let thinkingInterval = null;
let thinkingIndex = 0;

function startThinkingAnimation(elementId) {
    thinkingIndex = 0;
    const element = document.getElementById(elementId);
    if (!element) return;
    
    // Initial message
    element.innerHTML = `
        <div class="thinking-box" style="display: flex; align-items: center; gap: 12px; padding: 16px; background: rgba(79, 70, 229, 0.1); border-radius: 8px; border: 1px solid rgba(79, 70, 229, 0.3);">
            <div class="thinking-indicator" style="width: 20px; height: 20px; border: 2px solid rgba(79, 70, 229, 0.3); border-top-color: var(--brand-indigo, #4f46e5); border-radius: 50%; animation: spin 1s linear infinite;"></div>
            <span class="thinking-text" style="color: var(--text-secondary, #a1a1aa); font-size: 0.95rem; transition: opacity 0.15s ease;">${thinkingMessages[0]}</span>
        </div>
        <style>
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
        </style>
    `;
    
    // Cycle through messages
    thinkingInterval = setInterval(() => {
        thinkingIndex = (thinkingIndex + 1) % thinkingMessages.length;
        const textEl = element.querySelector('.thinking-text');
        if (textEl) {
            textEl.style.opacity = '0';
            setTimeout(() => {
                textEl.textContent = thinkingMessages[thinkingIndex];
                textEl.style.opacity = '1';
            }, 150);
        }
    }, 2000); // Change message every 2 seconds
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
    // Show report section
    document.getElementById(`gradingContent4`).classList.remove('active');
    document.getElementById(`gradingStep4`).classList.remove('active');
    document.getElementById(`gradingStep4`).classList.add('completed');
    document.getElementById(`gradingStep5`).classList.add('active');
    document.getElementById(`gradingContent5`).classList.add('active');
    
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
    // Start thinking animation
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
                <div class="recommendation-verdict submit">
                    <div class="verdict-icon">✅</div>
                    <div class="verdict-text">SUBMIT FOR GRADING</div>
                    <div class="verdict-reason">You'll make ~$${netBenefit.toFixed(2)} profit after grading costs</div>
                </div>
            `;
        } else if (netBenefit > 0) {
            // Marginal
            verdictHTML = `
                <div class="recommendation-verdict" style="background: rgba(99, 102, 241, 0.1); border-color: var(--brand-indigo);">
                    <div class="verdict-icon">🤔</div>
                    <div class="verdict-text" style="color: var(--brand-indigo);">CONSIDER GRADING</div>
                    <div class="verdict-reason">Small profit of $${netBenefit.toFixed(2)} - worth it if you want the slab for your collection</div>
                </div>
            `;
        } else {
            // Not worth it
            verdictHTML = `
                <div class="recommendation-verdict keep-raw">
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
