import os

import httpx

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

GROQ_SYSTEM_PROMPT = (
    "You are the ForensiX ZR Unit assistant, a crime-reporting and case management platform for citizens. "
    "Help users with: submitting reports (Report page), tracking report status (My Reports page), "
    "emergency SOS (SOS page), uploading evidence, and account/profile questions. "
    "Reply in the same language and style the user writes in (English, Urdu, or Roman Urdu/English mix). "
    "Keep replies short, 2-3 sentences."
)

# Rule-based FAQ assistant. Each entry: (keywords, response).
# The first entry whose keywords appear in the user's message wins.
FAQ_RULES = [
    (["sos", "emergency", "madad", "bachao", "khatra", "fauri madad", "ammergency"],
     "For emergencies, go to the SOS page and tap 'Emergency SOS' — this instantly notifies officers with your location. If you are in immediate danger, please also contact local emergency services."),

    (["submit", "file a report", "new report", "report a crime", "how to report", "make a report",
      "shikayat", "report kaise", "complaint kaise", "case darj", "report karna"],
     "To submit a report, go to the 'Report' page, choose a concern type, add the location and description, and optionally attach evidence (JPG, PNG, or PDF). Tap submit and you'll see it under 'My Reports'."),

    (["status", "my report", "track", "mera report", "report kahan", "kya hua mere report"],
     "You can check the status of your reports on the 'My Reports' page. Each report shows its current status: pending, verified, resolved, or rejected."),

    (["evidence", "upload", "attach", "photo", "file", "tasveer", "saboot", "photo lagana"],
     "You can attach evidence (JPG, PNG, or PDF, up to 5 files) when submitting a report, by dragging files into the upload area or clicking it to choose files."),

    (["officer", "contact", "speak to", "talk to", "afsar", "police se baat", "rabta"],
     "Officers review reports after they're submitted and may convert them into cases. You can see assigned officer details under your case information, or use the 'Contact Us' page for general inquiries."),

    (["account", "profile", "password", "login", "username", "password bhool", "login nahi"],
     "You can update your profile details and password from the 'Profile' page. If you're having trouble logging in, double-check your username, password, and role."),

    (["withdraw", "delete", "cancel report", "wapas lena", "report cancel", "report delete"],
     "You can withdraw a report from 'My Reports' as long as it's still pending. Reports that are already verified or converted into a case can't be withdrawn."),

    (["hi", "hello", "hey", "salam", "assalam", "kya haal", "kese ho", "kaisi ho"],
     "Hello! I'm the ForensiX assistant. I can help you with reporting a concern, tracking report status, emergency SOS, evidence uploads, and account questions. What do you need help with?"),

    (["thank", "thanks", "shukriya", "meharbani", "thanku"],
     "You're welcome! Stay safe."),
]

FALLBACK_RESPONSE = (
    "I'm not sure about that, but I can help with: submitting a report, tracking report status, "
    "emergency SOS, uploading evidence, or account/profile questions. Could you rephrase your question?"
)


def _ask_groq(message: str) -> str | None:
    if not GROQ_API_KEY:
        return None
    try:
        response = httpx.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": GROQ_SYSTEM_PROMPT},
                    {"role": "user", "content": message},
                ],
                "max_tokens": 200,
                "temperature": 0.4,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def _rule_based_reply(message: str) -> str:
    text = message.lower()
    for keywords, response in FAQ_RULES:
        if any(keyword in text for keyword in keywords):
            return response
    return FALLBACK_RESPONSE


def get_assistant_reply(message: str) -> str:
    groq_reply = _ask_groq(message)
    if groq_reply:
        return groq_reply
    return _rule_based_reply(message)
