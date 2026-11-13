"""
app.py
------
Streamlit front-end for the Student Performance Predictor.

Run with:
    streamlit run app.py

The model is loaded once at startup via st.cache_resource.
"""

from __future__ import annotations
import io
import os
import sys

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from src.predict import load_model, predict_batch, predict_one
from src.validate import make_csv_template, validate_csv, validate_single

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL_PATH = os.path.join(ROOT, "models", "early_model.joblib")
CATEGORY_COLORS = {
    "Performing Well": "#2ecc71",   # green
    "Needs Improvement": "#f39c12", # orange
    "At-Risk": "#e74c3c",           # red
}
CATEGORY_ICONS = {
    "Performing Well": "✅",
    "Needs Improvement": "⚠️",
    "At-Risk": "🚨",
}

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Student Performance Predictor",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Model loading (cached — happens only once per server start)
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading model…")
def _load_model():
    return load_model(MODEL_PATH)


# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
        .result-card {
            padding: 1.2rem 1.5rem;
            border-radius: 10px;
            margin: 0.8rem 0;
        }
        .disclaimer {
            font-size: 0.82rem;
            color: #888;
            margin-top: 0.5rem;
        }
        .factor-tag {
            display: block;
            background: rgba(128, 128, 128, 0.15);
            color: inherit;
            border-radius: 6px;
            padding: 6px 12px;
            margin: 4px 0;
            font-size: 0.9rem;
            border-left: 3px solid rgba(128, 128, 128, 0.45);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_confidence_pie(cat: str, conf: float) -> None:
    """
    Renders an animated, fluid SVG radial pie/gauge chart with a synchronized
    percentage counter and status assessment card.
    """
    pct = round(conf * 100, 1)

    color_schemes = {
        "Performing Well": {
            "primary": "#10b981",
            "end": "#059669",
            "badge_bg": "rgba(16, 185, 129, 0.14)",
            "badge_border": "rgba(16, 185, 129, 0.35)",
            "icon": "✅",
        },
        "Needs Improvement": {
            "primary": "#f59e0b",
            "end": "#d97706",
            "badge_bg": "rgba(245, 158, 11, 0.14)",
            "badge_border": "rgba(245, 158, 11, 0.35)",
            "icon": "⚠️",
        },
        "At-Risk": {
            "primary": "#ef4444",
            "end": "#b91c1c",
            "badge_bg": "rgba(239, 68, 68, 0.14)",
            "badge_border": "rgba(239, 68, 68, 0.35)",
            "icon": "🚨",
        },
    }

    scheme = color_schemes.get(
        cat,
        {
            "primary": "#3b82f6",
            "end": "#1d4ed8",
            "badge_bg": "rgba(59, 130, 246, 0.14)",
            "badge_border": "rgba(59, 130, 246, 0.35)",
            "icon": "📊",
        },
    )

    primary = scheme["primary"]
    end_color = scheme["end"]
    badge_bg = scheme["badge_bg"]
    badge_border = scheme["badge_border"]
    icon = scheme["icon"]

    # Circumference for r=62 is 2 * pi * 62 = 389.56
    circumference = 389.56
    target_offset = max(0.0, circumference * (1.0 - (pct / 100.0)))

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        * {{
          box-sizing: border-box;
          margin: 0;
          padding: 0;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }}
        body {{
          background: transparent;
          padding: 4px;
          overflow: hidden;
        }}
        .pie-card {{
          display: flex;
          align-items: center;
          gap: 24px;
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0.01) 100%);
          border: 1px solid rgba(128, 128, 128, 0.22);
          border-left: 5px solid {primary};
          border-radius: 14px;
          padding: 18px 22px;
          box-shadow: 0 4px 18px rgba(0, 0, 0, 0.07);
        }}
        @media (prefers-color-scheme: light) {{
          .pie-card {{
            background: #ffffff;
            border-color: rgba(0, 0, 0, 0.08);
            border-left-color: {primary};
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
          }}
          .counter-num {{ color: #0f172a !important; }}
          .center-sub {{ color: #64748b !important; }}
          .card-title {{ color: #0f172a !important; }}
          .card-desc {{ color: #475569 !important; }}
          .bg-ring {{ stroke: rgba(0, 0, 0, 0.07) !important; }}
        }}
        @media (prefers-color-scheme: dark) {{
          .pie-card {{
            background: rgba(30, 41, 59, 0.55);
            border-color: rgba(255, 255, 255, 0.1);
            border-left-color: {primary};
          }}
          .counter-num {{ color: #f8fafc !important; }}
          .center-sub {{ color: #94a3b8 !important; }}
          .card-title {{ color: #f1f5f9 !important; }}
          .card-desc {{ color: #cbd5e1 !important; }}
          .bg-ring {{ stroke: rgba(255, 255, 255, 0.08) !important; }}
        }}
        .pie-container {{
          position: relative;
          width: 140px;
          height: 140px;
          flex-shrink: 0;
          display: flex;
          align-items: center;
          justify-content: center;
        }}
        .pie-svg {{
          width: 140px;
          height: 140px;
          transform: rotate(-90deg);
        }}
        .bg-ring {{
          fill: none;
          stroke: rgba(128, 128, 128, 0.16);
          stroke-width: 12;
        }}
        .progress-ring {{
          fill: none;
          stroke: url(#ringGrad);
          stroke-width: 12;
          stroke-linecap: round;
          stroke-dasharray: {circumference:.2f};
          stroke-dashoffset: {circumference:.2f};
          animation: sweepRing 1.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
          filter: drop-shadow(0 3px 8px {primary}55);
        }}
        @keyframes sweepRing {{
          0% {{
            stroke-dashoffset: {circumference:.2f};
          }}
          100% {{
            stroke-dashoffset: {target_offset:.2f};
          }}
        }}
        .center-content {{
          position: absolute;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          pointer-events: none;
        }}
        .counter-num {{
          font-size: 26px;
          font-weight: 800;
          letter-spacing: -0.5px;
          line-height: 1;
        }}
        .center-sub {{
          font-size: 9px;
          font-weight: 700;
          letter-spacing: 1px;
          text-transform: uppercase;
          margin-top: 4px;
        }}
        .meta-container {{
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 6px;
          min-width: 0;
        }}
        .status-pill {{
          display: inline-flex;
          align-items: center;
          gap: 7px;
          padding: 5px 12px;
          border-radius: 999px;
          font-weight: 700;
          font-size: 14px;
          background: {badge_bg};
          color: {primary};
          border: 1px solid {badge_border};
          width: fit-content;
        }}
        .card-title {{
          font-size: 15px;
          font-weight: 600;
          margin-top: 2px;
        }}
        .card-desc {{
          font-size: 12.5px;
          line-height: 1.4;
        }}
        .mini-bar-bg {{
          width: 100%;
          height: 5px;
          background: rgba(128, 128, 128, 0.15);
          border-radius: 999px;
          overflow: hidden;
          margin-top: 4px;
        }}
        .mini-bar-fill {{
          height: 100%;
          background: linear-gradient(90deg, {primary}, {end_color});
          width: 0%;
          border-radius: 999px;
          animation: fillMiniBar 1.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }}
        @keyframes fillMiniBar {{
          0% {{ width: 0%; }}
          100% {{ width: {pct}%; }}
        }}
      </style>
    </head>
    <body>
      <div class="pie-card">
        <div class="pie-container">
          <svg class="pie-svg" viewBox="0 0 160 160">
            <defs>
              <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="{primary}" />
                <stop offset="100%" stop-color="{end_color}" />
              </linearGradient>
            </defs>
            <circle class="bg-ring" cx="80" cy="80" r="62" />
            <circle class="progress-ring" cx="80" cy="80" r="62" />
          </svg>
          <div class="center-content">
            <div class="counter-num" id="animCount">0%</div>
            <div class="center-sub">CONFIDENCE</div>
          </div>
        </div>
        <div class="meta-container">
          <div class="status-pill">
            <span>{icon}</span>
            <span>{cat}</span>
          </div>
          <div class="card-title">Prediction Result</div>
          <div class="card-desc">
            Model indicates <strong>{pct}%</strong> confidence for <strong>{cat}</strong> based on early semester indicators.
          </div>
          <div class="mini-bar-bg">
            <div class="mini-bar-fill"></div>
          </div>
        </div>
      </div>

      <script>
        (function() {{
          const countEl = document.getElementById('animCount');
          const target = {pct};
          const duration = 1400;
          const start = performance.now();

          function easeOutCubic(t) {{
            return 1 - Math.pow(1 - t, 3);
          }}

          function animate(now) {{
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            const val = (easeOutCubic(progress) * target).toFixed(1);
            countEl.textContent = val + '%';

            if (progress < 1) {{
              requestAnimationFrame(animate);
            }} else {{
              countEl.textContent = target.toFixed(1) + '%';
            }}
          }}

          requestAnimationFrame(animate);
        }})();
      </script>
    </body>
    </html>
    """
    components.html(html_code, height=185)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🎓 Student Performance Predictor")
st.caption(
    "Early-intervention tool — uses first-period data (G1, absences, study time, "
    "past failures) to flag at-risk students."
)
st.divider()

# ---------------------------------------------------------------------------
# Check model availability
# ---------------------------------------------------------------------------
model_available = os.path.exists(MODEL_PATH)

if not model_available:
    st.error(
        "⚠️ **Model not found.**  \n"
        "Please run the following command to train the model first:\n\n"
        "```bash\npython src/train.py\n```",
        icon="🔴",
    )
    st.stop()

model = _load_model()

# ---------------------------------------------------------------------------
# Tab layout
# ---------------------------------------------------------------------------
tab_single, tab_csv = st.tabs(["📋 Single Student", "📁 CSV Upload"])

# ===========================================================================
# TAB 1 — Single student form
# ===========================================================================
with tab_single:
    st.subheader("Enter Student Details")

    with st.form("student_form"):
        col1, col2 = st.columns(2)

        with col1:
            g1 = st.number_input(
                "First Period Grade (G1)",
                min_value=0,
                max_value=20,
                value=None,
                step=1,
                help="Grade scored in the first period (0–20).",
                placeholder="0 – 20",
            )
            absences = st.number_input(
                "Number of Absences",
                min_value=0,
                max_value=93,
                value=None,
                step=1,
                help="Total school days missed (0–93).",
                placeholder="0 – 93",
            )

            assignment_rate = st.slider(
                "Assignment Completion Rate (%)",
                min_value=0,
                max_value=100,
                value=80,
                step=5,
                help="Percentage of coursework/homework assignments submitted (0–100%).",
            )

        with col2:
            studytime = st.selectbox(
                "Weekly Study Time",
                options=[None, 1, 2, 3, 4],
                format_func=lambda x: {
                    None: "— select —",
                    1: "1 — Less than 2 hours",
                    2: "2 — 2 to 5 hours",
                    3: "3 — 5 to 10 hours",
                    4: "4 — More than 10 hours",
                }.get(x, str(x)),
                help="Coded 1–4 per the UCI dataset.",
            )
            failures = st.number_input(
                "Past Class Failures",
                min_value=0,
                max_value=4,
                value=None,
                step=1,
                help="Number of past course failures (0–4).",
                placeholder="0 – 4",
            )
            assessment_trend = st.selectbox(
                "Recent Assessment Trend",
                options=[1, 0, -1],
                index=1,
                format_func=lambda x: {
                    1: "↗️ Improving (scores rising)",
                    0: "➡️ Stable (consistent scores)",
                    -1: "↘️ Declining (scores dropping)",
                }.get(x, str(x)),
                help="Direction of student's scores on recent tests or quizzes.",
            )

        submitted = st.form_submit_button("🔍 Predict", use_container_width=True)

    if submitted:
        raw = {
            "absences": absences,
            "G1": g1,
            "failures": failures,
            "studytime": studytime,
            "assignment_rate": assignment_rate,
            "assessment_trend": assessment_trend,
        }
        cleaned, errors = validate_single(raw, feature_set="early")

        if errors:
            for err in errors:
                st.error(f"❌ {err}")
        else:
            result = predict_one(model, cleaned)
            cat = result["category"]
            conf = result["confidence"]
            factors = result["factors"]

            # Render fluid animated pie chart / radial gauge
            render_confidence_pie(cat, conf)

            st.markdown("**Top contributing factors:**")
            factor_tags = " ".join(
                f'<span class="factor-tag">🔹 {f}</span>' for f in factors
            )
            st.markdown(factor_tags, unsafe_allow_html=True)

            # Recommendations integration
            try:
                from src.recommend import generate_recommendations
                recs = generate_recommendations(cat, cleaned)
                if recs:
                    st.markdown("#### 💡 Recommended Actions & Intervention:")
                    for r in recs:
                        p_color = "#e74c3c" if r["priority"] == "high" else ("#f39c12" if r["priority"] == "medium" else "#27ae60")
                        st.markdown(
                            f"""
                            <div style="border-left: 4px solid {p_color}; padding: 8px 12px; margin-bottom: 8px; background: rgba(128,128,128,0.08); border-radius: 4px;">
                                <strong style="color: {p_color};">[{r['priority'].upper()}] {r['title']}</strong><br/>
                                <span style="font-size: 0.9rem;">{r['description']}</span><br/>
                                <span style="font-size: 0.85rem; font-style: italic;">👉 Action: {r['action']}</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
            except Exception:
                pass

            st.markdown(
                '<p class="disclaimer">⚠️ This prediction is decision support only '
                "and should not replace educator judgment.</p>",
                unsafe_allow_html=True,
            )

# ===========================================================================
# TAB 2 — CSV upload
# ===========================================================================
with tab_csv:
    st.subheader("Batch Prediction via CSV Upload")

    # Template download
    template_df = make_csv_template(feature_set="early")
    csv_bytes = template_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download CSV Template",
        data=csv_bytes,
        file_name="student_template.csv",
        mime="text/csv",
        help="Fill in this template with your student data.",
    )

    st.caption(
        "Required columns: `absences`, `G1`, `failures`, `studytime`  \n"
        "You may add extra columns (e.g. student ID) — they will be preserved in the output."
    )

    uploaded = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded is not None:
        try:
            raw_df = pd.read_csv(uploaded)
        except Exception as exc:
            st.error(f"❌ Could not read the CSV file: {exc}")
            st.stop()

        cleaned_df, errors = validate_csv(raw_df, feature_set="early")

        # Show row-level warnings (non-fatal)
        if errors:
            with st.expander(f"⚠️ {len(errors)} validation issue(s) — click to view"):
                for err in errors:
                    st.warning(err)

        if cleaned_df is None:
            st.error("❌ No valid rows could be processed. Please fix the errors above.")
        else:
            with st.spinner("Running predictions…"):
                results_df = predict_batch(model, cleaned_df)

            st.success(f"✅ Predicted {len(results_df)} student(s).")

            # Color-coded table
            def _style_row(row):
                color = CATEGORY_COLORS.get(row["Prediction"], "#ffffff")
                return [f"background-color: {color}22"] * len(row)

            st.dataframe(
                results_df.style.apply(_style_row, axis=1),
                use_container_width=True,
            )

            # Download results
            out_csv = results_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download Results",
                data=out_csv,
                file_name="predictions.csv",
                mime="text/csv",
            )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.caption(
    "Model: Random Forest or Logistic Regression (best At-Risk recall) trained on "
    "the UCI Student Performance dataset (~1,000 records, one school). "
    "Results reflect first-period data only."
)
