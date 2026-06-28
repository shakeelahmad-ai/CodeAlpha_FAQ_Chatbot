from __future__ import annotations
import os
APP_NAME        = "AI FAQ Chatbot"
APP_SUBTITLE    = "Intelligent Support Assistant"
APP_VERSION     = "2.0.0"
COMPANY_NAME    = "CodeAlpha"
COMPANY_TAGLINE = "Empowering Developers with AI"

BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
FAQ_CSV_PATH      = os.path.join(BASE_DIR, "faq.csv")
CHAT_HISTORY_PATH = os.path.join(BASE_DIR, "chat_history.json")
DATA_DIR          = os.path.join(BASE_DIR, "data")
HISTORY_JSON      = os.path.join(DATA_DIR, "history.json")
ASSETS_DIR        = os.path.join(BASE_DIR, "assets")
LOGO_PATH         = os.path.join(ASSETS_DIR, "logo.png")
CSS_PATH          = os.path.join(ASSETS_DIR, "style.css")


SIMILARITY_HIGH   = 75   # >= 75 → return exact answer
SIMILARITY_MEDIUM = 55   # 55-74 → return closest answer with disclaimer
# < 55 → fallback

FALLBACK_RESPONSE = (
    "I'm sorry, I couldn't find a suitable answer to your question. "
    "Please try rephrasing it, or browse the FAQ list in the sidebar. "
    "You can also contact our support team at support@codealpha.tech."
)

GREETING_MESSAGES = [
    "Hello! 👋 How can I assist you today?",
    "Hi there! 😊 I'm your AI FAQ assistant. Ask me anything!",
    "Welcome! 🤖 I'm here to help. What would you like to know?",
]


PAGE_ICON        = "🤖"
LAYOUT           = "wide"
INITIAL_SIDEBAR  = "expanded"

MAX_HISTORY_ENTRIES = 200
EXPORT_FILENAME     = "chat_export.txt"

COLOR_PRIMARY    = "#7C3AED"
COLOR_SECONDARY  = "#4F46E5"
COLOR_ACCENT     = "#06B6D4"
COLOR_SUCCESS    = "#10B981"
COLOR_WARNING    = "#F59E0B"
COLOR_DANGER     = "#EF4444"
COLOR_BG_DARK    = "#0F0F1A"
COLOR_SURFACE    = "#1A1A2E"
COLOR_SURFACE2   = "#16213E"
COLOR_TEXT       = "#E2E8F0"
COLOR_MUTED      = "#64748B"

CONFIDENCE_LABELS: dict[str, tuple[str, str]] = {
    "high":   ("High Confidence",   "✅"),
    "medium": ("Medium Confidence", "⚠️"),
    "low":    ("Low Confidence",    "❌"),
}

def get_confidence_label(score: float) -> tuple[str, str]:
    """Return (label, emoji) based on similarity score 0–100."""
    if score >= SIMILARITY_HIGH:
        return CONFIDENCE_LABELS["high"]
    if score >= SIMILARITY_MEDIUM:
        return CONFIDENCE_LABELS["medium"]
    return CONFIDENCE_LABELS["low"]
