from __future__ import annotations

import base64
import html
import os
import time
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from chatbot import FAQEngine
from config import (
    APP_NAME,
    APP_SUBTITLE,
    APP_VERSION,
    COMPANY_NAME,
    COMPANY_TAGLINE,
    CSS_PATH,
    EXPORT_FILENAME,
    LOGO_PATH,
    PAGE_ICON,
    SIMILARITY_HIGH,
    SIMILARITY_MEDIUM,
)
from utils import (
    append_message,
    clear_history,
    compute_statistics,
    date_for_header,
    ensure_directories,
    export_chat_as_txt,
    filter_suggestions,
    short_timestamp,
)

ensure_directories()

st.set_page_config(
    page_title=f"{APP_NAME} | {COMPANY_NAME}",
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

def _load_css(path: str) -> None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

_load_css(CSS_PATH)


def _init_state() -> None:
    defaults: dict[str, Any] = {
        "messages":       [],
        "faq_search_q":   "",
        "voice_enabled":  False,
        "search_history": [],
        "top_questions":  {},
        "initialized":    False,
        "nav":            "💬 Chat"
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

@st.cache_resource(show_spinner=False)
def _get_engine() -> FAQEngine:
    return FAQEngine()

try:
    engine = _get_engine()
except FileNotFoundError as exc:
    st.error(f"❌ {exc}")
    st.stop()


if not st.session_state.initialized:
    greeting_entry: dict[str, Any] = {
        "role":     "assistant",
        "content":  engine.greeting(),
        "short_ts": short_timestamp(),
        "score":    None,
        "category": None,
    }
    st.session_state.messages.append(greeting_entry)
    st.session_state.initialized = True


def _render_logo() -> None:
    if Path(LOGO_PATH).exists():
        with open(LOGO_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        st.sidebar.markdown(
            f'<div class="logo-wrap">'
            f'<img src="data:image/png;base64,{b64}" width="28"/>'
            f'<span>{COMPANY_NAME}</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            f'<div class="logo-wrap"><span>🤖 {COMPANY_NAME}</span></div>',
            unsafe_allow_html=True,
        )


def _badge_cls(score: float | None) -> str:
    if score is None:
        return ""
    if score >= SIMILARITY_HIGH:
        return "badge-high"
    if score >= SIMILARITY_MEDIUM:
        return "badge-medium"
    return "badge-low"

def _badge_txt(score: float | None) -> str:
    if score is None:
        return ""
    if score >= SIMILARITY_HIGH:
        return f"✅ {score:.0f}%"
    if score >= SIMILARITY_MEDIUM:
        return f"⚠️ {score:.0f}%"
    return f"❌ {score:.0f}%"

def _render_message(msg: dict[str, Any]) -> None:
    role     = msg.get("role", "user")
    content  = msg.get("content", "")
    short_ts = msg.get("short_ts", "")
    score    = msg.get("score")
    category = msg.get("category")

    safe = html.escape(content).replace("\n", "<br>")

    if role == "user":
        bubble_html = f"""
        <div class="msg-row user">
          <div class="avatar user">👤</div>
          <div class="bubble-wrap">
            <div class="bubble user-bubble">{safe}</div>
            <div class="bubble-meta">
              <span>{short_ts}</span>
            </div>
          </div>
        </div>
        """
    else:
        badge_html = ""
        if score is not None:
            badge_html = (
                f'<span class="badge {_badge_cls(score)}">'
                f'{_badge_txt(score)}</span>'
            )
        cat_html = (
            f'<span>📂 {html.escape(category)}</span>'
            if category and category not in ("N/A", "General", None) else ""
        )
        bubble_html = f"""
        <div class="msg-row bot">
          <div class="avatar bot">🤖</div>
          <div class="bubble-wrap">
            <div class="bubble bot-bubble">{safe}</div>
            <div class="bubble-meta">
              <span>{short_ts}</span>
              {badge_html}
              {cat_html}
            </div>
          </div>
        </div>
        """

    st.markdown(bubble_html, unsafe_allow_html=True)


def _typing_indicator_html() -> str:
    return """
    <div class="typing-wrap">
      <div class="avatar bot">🤖</div>
      <div class="typing-bubble">
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
      </div>
    </div>
    """


def _handle_query(query: str) -> None:
    query = query.strip()
    if not query:
        return

    u_entry: dict[str, Any] = {
        "role":     "user",
        "content":  query,
        "short_ts": short_timestamp(),
        "score":    None,
        "category": None,
    }
    st.session_state.messages.append(u_entry)
    append_message("user", query)

    if query not in st.session_state.search_history:
        st.session_state.search_history.insert(0, query)
        st.session_state.search_history = st.session_state.search_history[:20]
    st.session_state.top_questions[query] = (
        st.session_state.top_questions.get(query, 0) + 1
    )

    result = engine.match(query)
    b_entry: dict[str, Any] = {
        "role":     "assistant",
        "content":  result.answer,
        "short_ts": short_timestamp(),
        "score":    result.score,
        "category": result.category,
    }
    st.session_state.messages.append(b_entry)
    append_message("assistant", result.answer, score=result.score, category=result.category)

def _on_suggestion_click(query: str) -> None:
    _handle_query(query)

def _on_ask_from_search(query: str) -> None:
    _handle_query(query)
    st.session_state["nav"] = "💬 Chat"

def _on_clear_click() -> None:
    st.session_state.messages = []
    clear_history()
    st.session_state.initialized = False


with st.sidebar:
    _render_logo()
    st.markdown(f"**{APP_NAME}** `v{APP_VERSION}`")
    st.caption(COMPANY_TAGLINE)
    st.divider()

    st.radio(
        "nav",
        options=["💬 Chat", "🔍 FAQ Search", "📊 Statistics", "ℹ️ About"],
        label_visibility="collapsed",
        key="nav",
    )
    st.divider()

    st.markdown("#### ⚡ Quick Actions")
    col_a, col_b = st.columns(2)
    with col_a:
        st.button(
            "🗑️ Clear", 
            use_container_width=True, 
            help="Clear chat", 
            on_click=_on_clear_click
        )
    with col_b:
        txt = export_chat_as_txt(st.session_state.messages)
        st.download_button(
            "💾 Export", data=txt,
            file_name=EXPORT_FILENAME, mime="text/plain",
            use_container_width=True, help="Download chat as TXT",
        )

    st.divider()

    st.session_state.voice_enabled = st.toggle(
        "🔊 Voice Output", value=st.session_state.voice_enabled,
        help="Bot responses spoken aloud via browser TTS",
    )
    st.divider()

    st.markdown(
        f'<div style="font-size:0.71rem;color:#64748B;text-align:center;padding-top:0.3rem;">'
        f'📅 {date_for_header()}<br>'
        f'FAQ entries: <strong>{engine.entry_count}</strong> &nbsp;|&nbsp; '
        f'Messages: <strong>{len(st.session_state.messages)}</strong>'
        f'</div>',
        unsafe_allow_html=True,
    )


active = st.session_state["nav"]

if active == "💬 Chat":
    st.markdown(
        f'<div class="chat-header"><h1>🤖 {APP_NAME}</h1><p>{APP_SUBTITLE} · RapidFuzz Semantic Matching</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="date-divider">{date_for_header()}</div>',
        unsafe_allow_html=True,
    )

    for msg in st.session_state.messages:
        _render_message(msg)

    last_user_input = ""
    for m in reversed(st.session_state.messages):
        if m["role"] == "user":
            last_user_input = m["content"]
            break

    suggestions = filter_suggestions(last_user_input, engine.raw_questions, max_results=4)
    if suggestions:
        st.markdown(
            '<p style="font-size:0.76rem;color:#94A3B8;margin:0.6rem 0 0.2rem;">💡 You might also ask:</p>',
            unsafe_allow_html=True,
        )
        s_cols = st.columns(len(suggestions))
        for i, sug in enumerate(suggestions):
            with s_cols[i]:
                label = sug[:40] + ("…" if len(sug) > 40 else "")
                st.button(
                    label, 
                    key=f"sug_{i}", 
                    use_container_width=True, 
                    on_click=_on_suggestion_click, 
                    args=(sug,)
                )

    components.html("""
    <script>
    (function(){
      if (document.getElementById('_mic_btn')) return;
      var btn = document.createElement('button');
      btn.id = '_mic_btn'; btn.title = 'Click to speak your question'; btn.innerHTML = '🎙️';
      btn.style.cssText = 'position:fixed;bottom:92px;right:24px;z-index:9999;border:none;background:linear-gradient(135deg,#7C3AED,#06B6D4);color:#fff;border-radius:50%;width:44px;height:44px;font-size:1.1rem;cursor:pointer;box-shadow:0 4px 14px rgba(124,58,237,0.45);transition:all .2s ease';
      btn.onmouseenter = function(){ btn.style.opacity='0.85'; btn.style.transform='scale(1.07)'; };
      btn.onmouseleave = function(){ btn.style.opacity='1';    btn.style.transform='scale(1)';    };
      btn.addEventListener('click', function(){
        var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR){ alert('Voice input requires Chrome browser.'); return; }
        var rec = new SR(); rec.lang='en-US'; rec.interimResults=false; rec.maxAlternatives=1;
        btn.innerHTML='🔴'; btn.title='Listening…'; rec.start();
        rec.onresult = function(e){
          var t = e.results[0][0].transcript;
          var ta = document.querySelector('[data-testid="stChatInput"] textarea');
          if (ta){
            Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set.call(ta, t);
            ta.dispatchEvent(new Event('input',{bubbles:true}));
          }
          btn.innerHTML='🎙️'; btn.title='Click to speak';
        };
        rec.onerror = rec.onend = function(){ btn.innerHTML='🎙️'; btn.title='Click to speak'; };
      });
      document.body.appendChild(btn);
    })();
    </script>
    """, height=0)

    if st.session_state.voice_enabled and st.session_state.messages:
        last_bot = next((m for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None)
        if last_bot:
            safe_txt = last_bot["content"].replace('"', '\\"').replace("\n", " ").replace("'", "\\'")
            tts_key = str(hash(last_bot["content"]))
            components.html(f"""
            <script>
            (function(){{
              if (window._spokenKey === '{tts_key}') return;
              window._spokenKey = '{tts_key}';
              var u = new SpeechSynthesisUtterance("{safe_txt}");
              u.rate=0.95; u.pitch=1.0;
              window.speechSynthesis.cancel(); window.speechSynthesis.speak(u);
            }})();
            </script>
            """, height=0)

    user_input = st.chat_input(placeholder="Type your question here… e.g. How do I reset my password?")
    if user_input and user_input.strip():
        typing_ph = st.empty()
        typing_ph.markdown(_typing_indicator_html(), unsafe_allow_html=True)
        time.sleep(0.4)
        typing_ph.empty()
        
        _handle_query(user_input)
        st.rerun()

    st.markdown(
        f'<div class="app-footer">🤖 {APP_NAME} v{APP_VERSION} · {COMPANY_NAME} AI Internship · Powered by RapidFuzz</div>',
        unsafe_allow_html=True,
    )

elif active == "🔍 FAQ Search":
    st.markdown("## 🔍 Browse FAQ Database")
    st.caption(f"{engine.entry_count} questions across {len(engine.categories)} categories.")

    search_q = st.text_input("Search by keyword", placeholder="e.g. password, billing, internship…")
    categories = ["All"] + engine.categories
    sel_cat = st.selectbox("Filter by Category", options=categories)
    st.divider()

    if search_q.strip():
        results = engine.search_faq(search_q, limit=20)
        if sel_cat != "All":
            results = [r for r in results if r["category"] == sel_cat]
        
        if not results:
            st.info("No matching FAQs found. Try different keywords.")
        else:
            st.success(f"Found **{len(results)}** result(s):")
            for r in results:
                with st.expander(f"❓ {r['question']}"):
                    st.markdown(r["answer"])
                    c1, c2, c3 = st.columns(3)
                    c1.caption(f"📂 {r['category']}")
                    c2.caption(f"🎯 Match: {r['score']:.0f}%")
                    with c3:
                        st.button(
                            "💬 Ask in Chat", 
                            key=f"s_{hash(r['question'])}", 
                            on_click=_on_ask_from_search, 
                            args=(r['question'],)
                        )
    else:
        all_entries = engine.get_all_entries()
        if sel_cat != "All":
            all_entries = [e for e in all_entries if e["category"] == sel_cat]
        st.markdown(f"Showing **{len(all_entries)}** entries:")
        for entry in all_entries:
            with st.expander(f"❓ {entry['question']}"):
                st.markdown(entry["answer"])
                c1, c2 = st.columns([4, 1])
                c1.caption(f"📂 {entry['category']}")
                with c2:
                    st.button(
                        "💬 Ask", 
                        key=f"b_{hash(entry['question'])}", 
                        on_click=_on_ask_from_search, 
                        args=(entry['question'],)
                    )

elif active == "📊 Statistics":
    st.markdown("## 📊 Chat Statistics")
    st.caption("Analytics for the current session.")

    stats = compute_statistics(st.session_state.messages)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💬 Total Messages",  stats["total_messages"])
    c2.metric("🙋 Your Messages",   stats["user_messages"])
    c3.metric("🤖 Bot Responses",   stats["bot_messages"])
    avg = stats["avg_confidence"]
    c4.metric("🎯 Avg Confidence",  f"{avg:.1f}%" if avg else "N/A")

    st.divider()
    st.markdown("### 🎯 Confidence Breakdown")

    if stats["bot_messages"] > 0:
        hi, me, lo = stats["high_conf_count"], stats["medium_conf_count"], stats["low_conf_count"]
        total_bot  = stats["bot_messages"]

        ca, cb, cc = st.columns(3)
        with ca:
            st.markdown(f'<div class="stat-card"><div class="stat-val">{hi}</div><div class="stat-lbl">✅ High (≥75%)</div></div>', unsafe_allow_html=True)
        with cb:
            st.markdown(f'<div class="stat-card"><div class="stat-val">{me}</div><div class="stat-lbl">⚠️ Medium (55–74%)</div></div>', unsafe_allow_html=True)
        with cc:
            st.markdown(f'<div class="stat-card"><div class="stat-val">{lo}</div><div class="stat-lbl">❌ Low (&lt;55%)</div></div>', unsafe_allow_html=True)

        acc = (hi + me) / total_bot if total_bot else 0
        st.markdown("<br>**Overall Accuracy**", unsafe_allow_html=True)
        st.progress(acc, text=f"{acc*100:.0f}% of questions received an answer")
    else:
        st.info("No bot responses yet. Start chatting to see statistics!")

    st.divider()
    st.markdown("### 🏆 Top Asked Questions")
    top_q = sorted(st.session_state.top_questions.items(), key=lambda x: x[1], reverse=True)[:5]
    if top_q:
        for rank, (q, cnt) in enumerate(top_q, 1):
            r1, r2, r3 = st.columns([0.5, 7, 1.5])
            r1.markdown(f"**#{rank}**")
            r2.markdown(q[:80] + ("…" if len(q) > 80 else ""))
            r3.markdown(f"`{cnt}x`")
    else:
        st.info("No questions asked yet.")

    st.divider()
    st.markdown("### 📂 Top Categories")
    if stats["top_categories"]:
        for cat, cnt in stats["top_categories"]:
            cl, cr = st.columns([5, 1])
            with cl:
                st.progress(cnt / stats["bot_messages"] if stats["bot_messages"] else 0, text=cat)
            with cr:
                st.markdown(f"`{cnt}`")
    else:
        st.info("No category data yet.")

    st.divider()
    st.markdown("### 🕒 Recent Searches")
    if st.session_state.search_history:
        for i, q in enumerate(st.session_state.search_history[:10], 1):
            st.markdown(f"**{i}.** {q}")
    else:
        st.info("No searches yet.")

elif active == "ℹ️ About":
    st.markdown(
        f'<div class="chat-header"><h1>🤖 {APP_NAME}</h1><p>{APP_SUBTITLE} — {COMPANY_NAME} AI Internship v{APP_VERSION}</p></div>',
        unsafe_allow_html=True,
    )
    col_l, col_r = st.columns([1.5, 1])
    with col_l:
        st.markdown(
            f"""
            ## About This Project
            **{APP_NAME}** is built for the **{COMPANY_NAME} AI Internship (Task 2)**.
            It answers user questions from a pre-defined FAQ database using
            intelligent fuzzy string matching — no heavy AI frameworks needed.

            ### 🚀 Tech Stack
            | Component | Technology |
            |-----------|------------|
            | Language  | Python 3.14 |
            | UI        | Streamlit   |
            | Matching  | RapidFuzz   |
            | Data      | CSV / JSON  |
            | Theme     | Custom CSS  |

            ### 🧠 How the Matching Works (v2.0)
            1. Your question is **normalised** (lowercase, stripped punctuation).
            2. **WRatio** scorer compares it against all {engine.entry_count} FAQ entries.
            3. **Keyword Overlap Guard** — if no meaningful words from your query
               appear in the matched question, it's rejected as a false positive.
            4. **Length Guard** — very short queries require ≥ 85% score.
            5. Score ≥ 75% → exact answer · 55–74% → closest match · < 55% → fallback.

            ### ✨ Features
            - User bubbles RIGHT · Bot bubbles LEFT (proper chat layout)
            - Confidence badge on every bot response
            - Voice input (Chrome Speech API) and voice output (TTS)
            - FAQ search browser with category filter
            - Chat export as TXT · Session statistics · Smart suggestions
            """
        )
    with col_r:
        st.markdown(
            f"""
            ## Project Info
            **Version:** `{APP_VERSION}`\n
            **Company:** {COMPANY_NAME}\n
            **Program:** AI Internship — Task 2\n
            **FAQ Entries:** `{engine.entry_count}`\n
            **Categories:** `{len(engine.categories)}`\n
            ---
            ### Confidence Thresholds
            | Level  | Score   |
            |--------|---------|
            | ✅ High   | ≥ 75%   |
            | ⚠️ Medium | 55–74%  |
            | ❌ Low    | < 55%   |
            ---
            ### Contact
            support@codealpha.tech
            """
        )
    st.markdown(
        f'<div class="app-footer">Built with ❤️ by Shakeel · <a href="https://codealpha.tech">{COMPANY_NAME}</a> AI Internship · {APP_NAME} v{APP_VERSION}</div>',
        unsafe_allow_html=True,
    )