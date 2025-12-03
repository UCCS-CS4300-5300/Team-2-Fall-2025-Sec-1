Group 2 Project
# Team-2-Fall-2025-Sec-1

# OrbitStream

## Overview

**OrbitStream** is a comprehensive Space Domain Awareness (SDA) platform designed to unify and streamline access to critical space-related information. As the space industry rapidly expands with hundreds of observations and developments occurring every moment, OrbitStream serves as your centralized hub for staying informed about the latest developments in this vital field.

The platform provides users with real-time access to:
- Recent global satellite launches and mission updates
- Advanced satellite tracking methodologies
- Public space domain information relevant to government and commercial operations
- Personalized saved content with automatic updates

Whether you're a space industry professional, researcher, or enthusiast, OrbitStream ensures you remain current with the most important SDA developments through its intuitive interface and automatic update system.

## Installation

Follow these steps to set up OrbitStream on your local machine:

### 1. Clone the Repository

```bash
git clone <repository-url>
cd orbitstream
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

### 3. Activate the Virtual Environment

**On macOS/Linux:**
```bash
source venv/bin/activate
```

**On Windows:**
```bash
venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements.dev.txt
```

## API Configuration

OrbitStream requires API keys to function properly. You'll need to obtain an API key from the following service:

### NewsAPI
- **Documentation:** https://newsapi.org/docs
- **Purpose:** Provides access to space-related news and updates
- **Setup:** Register for a free API key and configure it in your application settings

### NASA APOD API
- **Documentation:** [https://api.nasa.gov/](https://api.nasa.gov/)
- **Purpose:** Fetches NASA’s “Astronomy Picture of the Day,” including images, videos, titles, and explanations, featured   at the top of the *Space News* page.
- **Setup:** Sign up for a free API key at [https://api.nasa.gov/](https://api.nasa.gov/) then add it to your environment or Django settings.

### NASA Image & Video Library API
- **Documentation:** https://images.nasa.gov/docs/images.nasa.gov_api_docs.pdf
- **Purpose:** Powers the *Gallery* page by providing curated NASA images and videos based on user search queries.
- **Setup:** Does **not** require an API key. Requests are made directly using query parameters (keywords, media type, page, etc.).

### SpaceDevs Launch Library API
- **Documentation:** https://thespacedevs.com/llapi
- **Purpose:** Supplies real-time and historical launch data for the *Launches* section, including upcoming and recent launches, mission details, countdown timers, and rocket metadata.
- **Setup:** Accessible through public endpoints. If using the authenticated tier, configure the API key through an environment variable.

### N2YO Satellite Tracking API

- **Documentation:** https://www.n2yo.com/api/
- **Purpose:** Provides real-time satellite tracking data including positions, passes, visual passes, and TLE (Two-Line Element) data for satellites. Used for tracking satellite trajectories and predicting visibility windows.
- **Setup:** Requires API key registration at N2YO. Configure the API key as an environment variable (e.g., N2YO_API_KEY) in your project settings.

## AI Usage

During the development of OrbitStream, AI tools were utilized to assist with:

1. **HTML Formatting** - Structuring and optimizing markup
2. **CSS Styling** - Designing and refining visual elements
3. **Testing** - Generating and improving test coverage

## Attributions

OrbitStream features background videos from Pixabay. Special thanks to the following creators:

- **Caelan** - [Earth Space India Himalayas](https://pixabay.com/videos/earth-space-india-himalayas-53109/)
- **NASA-Imagery** - [Rocket Launch Cape Canaveral](https://pixabay.com/videos/rocket-launch-cape-caneveral-nasa-228/)
- **Matthias_Groeneveld** - [Radio Telescope](https://pixabay.com/videos/radio-telescope-telescope-bluesky-26968/)
- **AiVreaSaStii** - [Technology Space Bar](https://pixabay.com/videos/technology-space-bar-march-143020/)

---
