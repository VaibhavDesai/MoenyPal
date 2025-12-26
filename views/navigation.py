"""Bottom navigation component."""
import streamlit as st
from utils.constants import TABS


def render_bottom_nav(active: str) -> None:
    """Render fixed bottom navigation bar."""
    st.markdown(
        """
<style>
/* Mobile-first layout tweaks */
main .block-container {
  padding-bottom: 92px;
  padding-top: 16px;
  max-width: 520px;
}

/* Hide Streamlit default menu/footer */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 8px;
}
::-webkit-scrollbar-track {
  background: rgba(0,0,0,0.05);
}
::-webkit-scrollbar-thumb {
  background: rgba(59,130,246,0.3);
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(59,130,246,0.5);
}

.mp-bottom-nav {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 10px 14px calc(10px + env(safe-area-inset-bottom, 0px));
  background: linear-gradient(to top, rgba(255,255,255,0.98), rgba(255,255,255,0.95));
  backdrop-filter: blur(20px) saturate(180%);
  border-top: 2px solid transparent;
  border-image: linear-gradient(to right, #667eea, #764ba2, #f093fb, #4facfe, #43e97b) 1;
  box-shadow: 
    0 -4px 20px rgba(0,0,0,0.08),
    0 -1px 3px rgba(102,126,234,0.1);
  z-index: 9999;
  animation: navGlow 8s ease-in-out infinite;
}

@keyframes navGlow {
  0%, 100% {
    box-shadow: 
      0 -4px 20px rgba(0,0,0,0.08),
      0 -1px 3px rgba(102,126,234,0.1);
  }
  50% {
    box-shadow: 
      0 -4px 24px rgba(0,0,0,0.1),
      0 -2px 8px rgba(102,126,234,0.2);
  }
}

.mp-bottom-nav .inner {
  max-width: 520px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr 1fr;
  align-items: end;
  gap: 8px;
}

.mp-tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 6px 4px;
  border-radius: 12px;
  text-decoration: none;
  color: rgba(0,0,0,0.5);
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.mp-tab::before {
  content: '';
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 2px;
  background: linear-gradient(to right, #667eea, #764ba2);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.mp-tab:hover {
  color: rgba(0,0,0,0.7);
  background: linear-gradient(135deg, rgba(102,126,234,0.08), rgba(118,75,162,0.08));
  transform: translateY(-2px);
}

.mp-tab:hover::before {
  width: 60%;
}

.mp-tab .icon {
  font-size: 18px;
  line-height: 18px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  filter: drop-shadow(0 0 0 transparent);
}

.mp-tab:hover .icon {
  transform: scale(1.15) rotate(5deg);
  filter: drop-shadow(0 2px 4px rgba(102,126,234,0.3));
}

.mp-tab .label {
  margin-top: 4px;
  font-size: 11px;
  line-height: 12px;
  transition: all 0.2s ease;
}

.mp-tab:hover .label {
  font-weight: 500;
}

.mp-tab.active {
  color: #2563eb;
  font-weight: 600;
  background: linear-gradient(135deg, rgba(102,126,234,0.12), rgba(118,75,162,0.12));
  box-shadow: 0 2px 8px rgba(102,126,234,0.15);
}

.mp-tab.active::before {
  width: 70%;
  background: linear-gradient(to right, #2563eb, #667eea);
}

.mp-tab.active .icon {
  filter: drop-shadow(0 2px 6px rgba(37,99,235,0.4));
}

/* Center + button */
.mp-tab-add {
  transform: translateY(-14px);
}

.mp-tab-add .pill {
  width: 52px;
  height: 52px;
  border-radius: 26px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
  background-size: 200% 200%;
  color: white;
  box-shadow: 
    0 10px 24px rgba(102,126,234,0.4), 
    0 4px 8px rgba(118,75,162,0.3),
    inset 0 1px 0 rgba(255,255,255,0.3);
  font-size: 28px;
  line-height: 28px;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  animation: gradientShift 6s ease infinite;
  position: relative;
  overflow: hidden;
}

@keyframes gradientShift {
  0%, 100% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
}

.mp-tab-add .pill::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 100%;
  height: 100%;
  background: radial-gradient(circle, rgba(255,255,255,0.3) 0%, transparent 70%);
  transform: translate(-50%, -50%) scale(0);
  transition: transform 0.4s ease;
  border-radius: 50%;
}

.mp-tab-add:hover .pill {
  transform: scale(1.08) rotate(90deg);
  box-shadow: 
    0 14px 32px rgba(102,126,234,0.5), 
    0 8px 16px rgba(118,75,162,0.4),
    inset 0 1px 0 rgba(255,255,255,0.4),
    0 0 20px rgba(240,147,251,0.3);
}

.mp-tab-add:hover .pill::before {
  transform: translate(-50%, -50%) scale(1);
}

.mp-tab-add.active .pill {
  background: linear-gradient(135deg, #2563eb 0%, #667eea 50%, #764ba2 100%);
  transform: scale(0.95) rotate(45deg);
  animation: none;
}

/* Make sure links don't show underline on mobile Safari */
a.mp-tab, a.mp-tab:visited, a.mp-tab:hover, a.mp-tab:active {
  text-decoration: none !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )

    items_html = []
    for tab_id, label, icon in TABS:
        is_active = tab_id == active
        href = f"?tab={tab_id}"

        if tab_id == "add":
            items_html.append(
                f"""
<a class="mp-tab mp-tab-add {'active' if is_active else ''}" href="{href}" target="_self">
  <div class="pill">+</div>
</a>
"""
            )
        else:
            items_html.append(
                f"""
<a class="mp-tab {'active' if is_active else ''}" href="{href}" target="_self">
  <div class="icon">{icon}</div>
  <div class="label">{label}</div>
</a>
"""
            )

    st.markdown(
        """
<div class="mp-bottom-nav">
  <div class="inner">
    {items}
  </div>
</div>
        """.format(items="\n".join(items_html)),
        unsafe_allow_html=True,
    )
