# learn_page/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.middleware.csrf import get_token
import openai
from django.conf import settings
import json

# Predefined topics with descriptions
PREDEFINED_TOPICS = [
    {
        "id": "satellites",
        "title": "Satellites & Their Functions",
        "icon": "🛰️",
        "description": "Learn about different types of satellites and their roles"
    },
    {
        "id": "space-debris",
        "title": "Space Debris Tracking",
        "icon": "🗑️",
        "description": "Understanding orbital debris and tracking methods"
    },
    {
        "id": "orbital-mechanics",
        "title": "Orbital Mechanics",
        "icon": "🌍",
        "description": "The physics behind how objects orbit in space"
    },
    {
        "id": "sda",
        "title": "Space Domain Awareness",
        "icon": "👁️",
        "description": "Methods and technologies for monitoring space activities"
    },
    {
        "id": "rocket-science",
        "title": "Rocket Propulsion",
        "icon": "🚀",
        "description": "How rockets work and launch into space"
    },
    {
        "id": "iss",
        "title": "International Space Station",
        "icon": "🏗️",
        "description": "Life and research aboard the ISS"
    },
    {
        "id": "exoplanets",
        "title": "Exoplanets",
        "icon": "🪐",
        "description": "Discovering planets beyond our solar system"
    },
    {
        "id": "black-holes",
        "title": "Black Holes",
        "icon": "⚫",
        "description": "Understanding these mysterious cosmic objects"
    }
]


@ensure_csrf_cookie
def learn_page(request):
    """Render the Learn page with predefined topics."""
    context = {
        "topics": PREDEFINED_TOPICS
    }
    return render(request, "learn_page/learn_page.html", context)


def validate_space_topic(topic):
    """
    Validate that the topic is space-related using ChatGPT.
    Returns (is_valid, message)
    """
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        # Skip validation if no API key
        return True, None

    try:
        client = openai.OpenAI(api_key=api_key)

        validation_prompt = f"""You are a space topic validator. Determine if the following query is related to space, astronomy, spaceflight, satellites, rockets, planets, stars, space exploration, or any space-related topic.

Query: "{topic}"

Respond with ONLY "YES" if it's space-related, or "NO" if it's not space-related.
Do not include any other text or explanation."""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a topic validator that responds with only YES or NO."},
                {"role": "user", "content": validation_prompt}
            ],
            max_tokens=10,
            temperature=0
        )

        answer = response.choices[0].message.content.strip().upper()

        if "YES" in answer:
            return True, None
        else:
            return False, f"'{topic}' doesn't appear to be related to space. Please ask about satellites, planets, rockets, or other space topics!"

    except Exception as e:
        print(f"Validation error: {e}")
        # On error, allow the topic through
        return True, None


@require_http_methods(["POST"])
def generate_summary(request):
    """
    Generate AI-powered educational summary for a given topic.
    Expects JSON: {"topic": "space debris"}
    """
    try:
        data = json.loads(request.body)
        topic = data.get("topic", "").strip()

        if not topic:
            return JsonResponse({
                "error": "Please provide a topic to learn about."
            }, status=400)

        # Validate that topic is space-related
        is_valid, validation_message = validate_space_topic(topic)
        if not is_valid:
            return JsonResponse({
                "error": validation_message,
                "fallback": True
            }, status=400)

        # Check if we have an API key
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            return JsonResponse({
                "error": "AI service is not configured. Please contact support.",
                "fallback": True
            }, status=503)

        # Generate summary using ChatGPT
        client = openai.OpenAI(api_key=api_key)

        prompt = f"""You are an educational space science expert. Create a clear, beginner-friendly summary about: {topic}

Your response should:
- Be 150-250 words
- Use simple, accessible language
- Include key concepts and terminology
- Be engaging and informative
- Focus on Space Domain Awareness context when relevant

After the summary, provide 3-5 related keywords for further learning, formatted as:
**Related Topics:** keyword1, keyword2, keyword3

Do not use any preamble or closing remarks. Start directly with the educational content."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # or "gpt-3.5-turbo" for cheaper option
            messages=[
                {"role": "system",
                 "content": "You are an educational space science expert who creates clear, beginner-friendly summaries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )

        # Extract the text content
        summary_text = response.choices[0].message.content

        # Split summary and keywords
        parts = summary_text.split("**Related Topics:**")
        summary = parts[0].strip()
        keywords = parts[1].strip() if len(parts) > 1 else ""

        return JsonResponse({
            "success": True,
            "topic": topic,
            "summary": summary,
            "keywords": keywords
        })

    except openai.APIError as e:
        return JsonResponse({
            "error": "Sorry, I couldn't generate information about that topic right now. Please try again later.",
            "fallback": True
        }, status=503)

    except Exception as e:
        print(f"Error generating summary: {e}")
        return JsonResponse({
            "error": "Sorry, I don't have enough data on that topic yet! Try another topic or rephrase your query.",
            "fallback": True
        }, status=500)