# space_news/config.py
"""
Configuration for space news filtering.
Contains keyword lists, domain filters, and other constants used across views.
"""

# ==============================================================================
# SPACE-RELATED KEYWORDS
# ==============================================================================

# General space exploration terms
SPACE_KEYWORDS_GENERAL = [
    "nasa", "spacex", "space", "rocket", "satellite", "astronaut", 
    "spacecraft", "launch", "mars", "moon", "orbit", "iss", 
    "international space station", "telescope", "galaxy", "planet",
    "asteroid", "comet", "solar system", "mission", "starship",
    "falcon", "dragon", "crew", "apollo", "artemis", "hubble",
    "webb", "jwst", "esa", "jaxa", "boeing starliner", "blue origin",
]

# Space Domain Awareness (SDA) specific terms
SPACE_KEYWORDS_SDA = [
    "space domain awareness", "space debris", "space junk", 
    "orbital debris", "space collision", "satellite collision",
    "space tracking", "space surveillance", "space traffic",
    "space traffic management", "conjunction", "close approach",
    "kessler syndrome", "anti-satellite", "asat", "space situational awareness",
    "ssa", "sst", "space sustainability", "mega constellation",
    "starlink debris", "satellite reentry", "deorbit", "space safety"
]

# Combined list for easy access
SPACE_KEYWORDS_ALL = SPACE_KEYWORDS_GENERAL + SPACE_KEYWORDS_SDA


# ==============================================================================
# EXCLUDED TOPICS (Non-space content to filter out)
# ==============================================================================

EXCLUDED_TOPICS = {
    # Elon Musk's other companies
    "companies": [
        "tesla", "twitter", "x corp", "boring company", "neuralink",
    ],
    
    # Finance/Business (non-space)
    "finance": [
        "cryptocurrency", "bitcoin", "dogecoin", "ethereum", "crypto",
        "stock price", "stock market", "shares", "investor", "wall street",
        "nasdaq", "dow jones", "s&p 500", "earnings report", "ipo",
    ],
    
    # Legal issues (personal)
    "legal": [
        "court", "lawsuit", "trial", "divorce", "girlfriend", "dating",
        "settlement", "sued", "litigation", "custody",
    ],
    
    # Politics (non-space policy)
    "politics": [
        "election", "campaign", "vote", "ballot", "midterm",
        "democrat", "republican", "trump", "biden", "congress",
    ],
    
    # Consumer Tech (non-space)
    "tech": [
        "ai chatbot", "artificial intelligence model", "grok", 
        "chatgpt", "openai", "facebook", "instagram", "tiktok",
        "iphone", "android", "app store", "video game", "gaming console",
        "metaverse", "virtual reality headset", "cryptocurrency exchange",
    ],
    
    # Weather/Natural disasters
    "weather": [
        "hurricane", "tropical storm", "tornado", "earthquake", "wildfire",
        "flood", "tsunami", "cyclone", "blizzard", "heatwave",
    ],
    
    # Entertainment/Celebrity
    "entertainment": [
        "celebrity", "actor", "actress", "movie premiere", "red carpet",
        "awards show", "kardashian", "influencer", "reality tv",
        "concert", "music festival", "album release",
    ],
    
    # Sports
    "sports": [
        "football game", "basketball game", "baseball game", "soccer match",
        "nfl", "nba", "mlb", "nhl", "world cup", "super bowl",
        "championship game", "playoffs",
    ],
    
    # Crime/Violence
    "crime": [
        "murder", "shooting", "arrest", "police investigation",
        "robbery", "theft", "protest", "riot",
    ],
    
    # Health (non-space)
    "health": [
        "covid", "pandemic", "vaccine rollout", "virus outbreak",
        "hospital", "clinical trial", "diet", "weight loss", "fitness",
    ],
    
    # Real estate/Lifestyle
    "lifestyle": [
        "real estate", "housing market", "property sale",
        "restaurant", "hotel", "vacation", "travel destination",
        "fashion", "beauty",
    ],
    
    # Automotive (non-space)
    "automotive": [
        "car accident", "traffic", "vehicle recall", "auto show",
    ],
}

# Flatten all excluded topics into a single list
EXCLUDED_TOPICS_ALL = [topic for category in EXCLUDED_TOPICS.values() for topic in category]

# ==============================================================================
# INAPPROPRIATE CONTENT KEYWORDS
# ==============================================================================

INAPPROPRIATE_KEYWORDS = [
    "adult", "porn", "xxx", "celebrity gossip", "dating", "sexy", "erotic",
]

# ==============================================================================
# DOMAIN FILTERS
# ==============================================================================

# Domains to exclude from NewsAPI queries
EXCLUDED_DOMAINS = [
    "adult-sites.com",
    "inappropriate-domain.com",
    "reddit.com",           # Often text-only or low quality
    "twitter.com",          # Inconsistent images
    "facebook.com",         # Privacy/access issues
    "yahoo.com",            # Often missing images
    "msn.com",              # Aggregator with inconsistent quality
    "news.google.com",      # Aggregator
    "flipboard.com",        # Aggregator
    "ladbible.com",         # Low quality clickbait
    "unilad.com",           # Low quality clickbait
    "dailymail.co.uk",      # Tabloid quality
    "techpowerup.com",
    "siliconangle.com",
    "Biztoc.com",
    "newser.com"
]

# Reliable sources with consistent high-quality images and content
RELIABLE_IMAGE_SOURCES = [
    'nasa.gov',                    # NASA - US Space Agency
    'esa.int',                     # ESA - European Space Agency
    'jaxa.jp',                     # JAXA - Japan Space Agency
    'stsci.edu',                   # Space Telescope Science Institute
    'spacex.com',                  # SpaceX Official
    'blueorigin.com',              # Blue Origin Official
    'ulalaunch.com',               # United Launch Alliance
    'spacenews.com',               # Space Industry News
    'space.com',                   # General Space News
    'spaceflightnow.com',          # Launch Tracking & Updates
    'spacepolicyonline.com',       # Space Policy Analysis
    'astronomy.com',               # Astronomy Magazine
    'skyandtelescope.org',         # Sky & Telescope
    'planetary.org',               # The Planetary Society
    'earthsky.org',                # EarthSky
    'scientificamerican.com',      # Scientific American
    'smithsonianmag.com',          # Smithsonian Magazine
    'nytimes.com',                 # New York Times
    'washingtonpost.com',          # Washington Post
    'bbc.co.uk',                   # BBC News
]

# ==============================================================================
# NEWS API CONFIGURATION
# ==============================================================================

# Default NewsAPI query parameters for space news
NEWS_API_QUERY = (
    '(NASA OR SpaceX OR "space exploration" OR "space mission" OR '
    '"space domain awareness" OR "space debris" OR "space traffic") '
    'AND '
    '(rocket OR satellite OR astronaut OR spacecraft OR launch OR debris OR '
    'collision OR tracking OR "space junk" OR orbit OR SSA OR SST)'
)
NEWS_API_TITLE_QUERY = "space OR NASA OR SpaceX OR satellite OR debris OR collision OR tracking"

# Maximum articles per source for diversity
MAX_ARTICLES_PER_SOURCE = 3

# Total articles to display
TOTAL_ARTICLES_LIMIT = 20