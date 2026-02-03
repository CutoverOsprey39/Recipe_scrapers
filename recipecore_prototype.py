import tkinter as tk
from tkinter import messagebox, scrolledtext
import requests
from recipe_scrapers import scrape_me, scrape_html, WebsiteNotImplementedError
import os
import sys
import subprocess
import re
from datetime import datetime

# ----------------------------------------------------------------------
# RecipeCore Prototype – HCI Assignment
# ----------------------------------------------------------------------
# Purpose:    Simple desktop tool that takes any recipe blog URL and
#             returns a clean 3-paragraph summary (overview, ingredients,
#             instructions) without blog stories/ads.
#
# HCI alignment:
#  -Visibility of system status: loading message + colored feedback
#  -Error prevention: try/except blocks + safe method checks
#  -User control: real-time input → instant output which can reused and edited for whatever purpose the user desires - stimulation of creativity for their own modified recipe identity.
#  -Aesthetic & minimalist design: clean dark theme, no clutter and typographic hierarchy for improved readablility! - to embrace evocation and reusability.
#
# Features:
#   - Warm cozy dark mode theme
#   - Robust error handling for site-specific scraper inconsistencies
#   - Safe attribute checks to avoid AttributeError on missing methods
#   - Colored feedback messages in output area
#   - Save & open summary for printing/sharing (file named after current title in output)
#   - Supports user edits: saves exactly what’s in the text area (including title changes)
#
# Dependencies:
#   pip install recipe-scrapers requests
#
# To run:
#   python3 recipecore_prototype.py
# ----------------------------------------------------------------------

# ────────────────────────────────────────────────
# COLOR PALETTE
# ────────────────────────────────────────────────
# These constants make it easy to tweak colors globally
BG_MAIN        = "#0D1117"      # Main window background (deep navy-black)
SURFACE        = "#161B22"      # Input fields, output area background
BORDER         = "#21262D"      # Subtle borders and highlights
TEXT_PRIMARY   = "#E6EDF3"      # Main readable text (warm off-white)
TEXT_SECONDARY = "#8B949E"      # Secondary / muted text (labels, notes)
ACCENT         = "#D08770"      # Button color (warm terracotta/peach)
ACCENT_HOVER   = "#E0A07F"      # Button hover state
SUCCESS        = "#A3BE8C"      # Green for success/fallback notes
ERROR          = "#BF616A"      # Red for error/warning messages

def summarize_recipe():
    """
    Main function called when user clicks the "Summarize" button.
    1. Gets URL from entry field
    2. Tries site-specific scraper first
    3. Falls back to raw schema.org parsing if needed
    4. Builds clean 3-paragraph output for the provided recipe/blog URL
    """
    url = url_entry.get().strip()
    if not url:
        messagebox.showwarning("Input Error", "Please enter a recipe URL.")
        return

    # Auto-prefix https:// if user forgot protocol (common mistake)
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Clear previous output and show loading message
    output_text.delete(1.0, tk.END)
    output_text.insert(tk.END, "Fetching and summarizing recipe...\n\n")
    window.update_idletasks()  # Force UI to refresh immediately

    scraper = None
    fallback_used = False

    # ── Step 1: Try preferred site-specific scraper ─────────────────────
    try:
        scraper = scrape_me(url)
    except WebsiteNotImplementedError:
        # Site not fully supported → go to fallback
        fallback_used = True
        try:
            headers = {"User-Agent": "Mozilla/5.0 RecipeCore HCI Prototype"}
            response = requests.get(url, headers=headers, timeout=12)
            response.raise_for_status()  # Raise if HTTP error (404, etc.)
            scraper = scrape_html(html=response.text, org_url=url)
            output_text.insert(tk.END, "Note: Using fallback schema.org parsing (may miss some details).\n\n", "note")
        except requests.RequestException as req_err:
            output_text.insert(tk.END, f"Could not load page: {str(req_err)}\nTry another URL.\n", "error")
            return
        except Exception as fb_err:
            output_text.insert(tk.END, f"Fallback failed: {str(fb_err)}\n", "error")
            return
    except Exception as e:
        output_text.insert(tk.END, f"Parsing error: {str(e)}\nTry a different recipe site.\n", "error")
        return

    # ── Step 2: Build the clean 3-paragraph output ───────────────────────
    try:
        # Clear loading message **just before** inserting real content
        # This ensures the first line is always the title
        output_text.delete(1.0, tk.END)  # Remove loading text now that we have data

        # Overview paragraph – title is first
        title = scraper.title() or "Recipe (title not found)"
        servings = scraper.yields() or "N/A"

        # Allow full description (up to 600 chars) for richer notes section
        description = scraper.description() or "No description available."
        if len(description) > 600:
            description = description[:597] + "..."

        # Time extraction – very defensive to avoid AttributeError
        times = []
        time_methods = [
            ('total_time', "Total"),
            ('preptime',   "Prep"),
            ('cooktime',   "Cook")
        ]

        for method_name, label in time_methods:
            if hasattr(scraper, method_name):
                getter = getattr(scraper, method_name)
                try:
                    value = getter()
                    if value is not None:
                        if isinstance(value, (int, float)):
                            times.append(f"{label}: {int(value)} min")
                        else:
                            times.append(f"{label}: {value}")
                except (TypeError, ValueError):
                    pass

        time_str = " | ".join(times) if times else "Times not available"
        if fallback_used and not times:
            time_str += " (check original page)"

        # Build overview with tagged sections
        output_text.insert(tk.END, f"{title}\n\n", "title")
        output_text.insert(tk.END, f"Servings: {servings}\n", "heading")
        output_text.insert(tk.END, f"{time_str}\n", "heading")
        output_text.insert(tk.END, f"Notes: {description}\n\n", "heading")

        # Ingredients paragraph
        ing_list = scraper.ingredients()
        if ing_list:
            output_text.insert(tk.END, "Ingredients:\n", "heading")
            for item in ing_list:
                output_text.insert(tk.END, f"• {item.strip()}\n", "body")
            output_text.insert(tk.END, "\n")
        else:
            output_text.insert(tk.END, "Ingredients: (not found)\n\n", "heading")

        # Instructions paragraph
        instr_text = scraper.instructions()
        if instr_text:
            output_text.insert(tk.END, "Instructions:\n", "heading")
            steps = [s.strip() for s in instr_text.splitlines() if s.strip()]
            for i, step in enumerate(steps, 1):
                output_text.insert(tk.END, f"{i}. {step}\n", "body")
            output_text.insert(tk.END, "\n")
        else:
            output_text.insert(tk.END, "Instructions: (not extracted – see original site)\n", "heading")

    except Exception as parse_err:
        output_text.insert(tk.END, f"\nUnexpected parsing issue: {str(parse_err)}\n"
                                  f"Partial data shown above.", "error")


def save_and_open():
    """
    Save the current summary (including any user edits) to a text file named after the current title in the output area.
    Opens the file with the default app for printing/editing.
    Adds timestamp if file already exists to avoid overwriting.
    """
    text = output_text.get("1.0", tk.END).strip()

    # Improved check: block only if it's basically still the loading state
    loading_marker = "Fetching and summarizing recipe..."
    if len(text) < 100 or (loading_marker in text and len(text.splitlines()) < 5):
        messagebox.showwarning("Nothing to save", "Run a summary first.")
        return

    # Extract title from the first non-empty line (user-editable)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = lines[0] if lines else "Recipe"

    # Clean title for filename: remove invalid chars, replace spaces
    clean_title = re.sub(r'[^\w\s-]', '', title)      # remove special chars
    clean_title = re.sub(r'\s+', '_', clean_title)    # spaces → underscores
    clean_title = clean_title.strip('_')              # trim extra _

    if not clean_title:
        clean_title = "edited_recipe"

    base_name = f"{clean_title}.txt"
    file_path = base_name

    # Add timestamp if file already exists
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        file_path = f"{clean_title}_{timestamp}.txt"

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"RecipeCore Summary – {title}\n" + "="*50 + "\n\n")
            f.write(f"Source URL: {url_entry.get().strip()}\n\n")
            f.write(text)

        # Open file with default application (cross-platform)
        if sys.platform == "darwin":  # macOS
            subprocess.run(['open', file_path])
        elif sys.platform == "win32":
            os.startfile(file_path)
        else:  # Linux
            subprocess.run(['xdg-open', file_path])

        messagebox.showinfo("Saved & Opened", f"Saved as:\n{file_path}\nOpened in default app (TextEdit on Mac) for printing/editing.")
    except Exception as e:
        messagebox.showerror("Save Error", f"Could not save/open file:\n{str(e)}")


# ────────────────────────────────────────────────
# GUI CONSTRUCTION
# ────────────────────────────────────────────────

window = tk.Tk()
window.title("RecipeCore – Clean Recipe Summary")
window.geometry("680x760")
window.configure(bg=BG_MAIN)

# Tag configurations for colors and typography hierarchy
output_text_tags = {
    "title":    {"foreground": TEXT_PRIMARY, "font": ("Helvetica", 14, "bold")},
    "heading":  {"foreground": TEXT_PRIMARY, "font": ("Helvetica", 12, "bold")},
    "body":     {"foreground": TEXT_PRIMARY, "font": ("Helvetica", 11)},
    "note":     {"foreground": SUCCESS,      "font": ("Helvetica", 11)},
    "error":    {"foreground": ERROR,        "font": ("Helvetica", 11)}
}

# ── Header label ────────────────────────────────────────────────────────
tk.Label(
    window,
    text="Paste any recipe URL:",
    font=("Helvetica", 12, "bold"),
    bg=BG_MAIN,
    fg=TEXT_PRIMARY
).pack(pady=(20, 5))

# ── URL input field ─────────────────────────────────────────────────────
url_entry = tk.Entry(
    window,
    width=75,
    font=("Helvetica", 11),
    bg=SURFACE,
    fg=TEXT_PRIMARY,
    insertbackground=ACCENT,
    relief="flat",
    highlightthickness=1,
    highlightbackground=BORDER,
    highlightcolor=ACCENT
)
url_entry.pack(pady=5, padx=20)

# ── Summarize button ────────────────────────────────────────────────────
tk.Button(
    window,
    text="Get Clean 3-Paragraph Summary",
    command=summarize_recipe,
    font=("Helvetica", 11, "bold"),
    bg=ACCENT,
    fg="#010101",
    activebackground=ACCENT_HOVER,
    activeforeground="#FFFFFF",
    padx=12,
    pady=8,
    relief="flat",
    borderwidth=0
).pack(pady=10)

# ── Save & Open for Print button ───────────────────────────────────────
tk.Button(
    window,
    text="Save & Open for Print",
    command=save_and_open,
    font=("Helvetica", 11),
    bg="#50C878",
    fg="#010101",
    activebackground="#3DAE61",
    activeforeground="#FFFFFF",
    padx=12,
    pady=8,
    relief="flat",
    borderwidth=0
).pack(pady=5)

# ── Scrollable output area with 1.5× line spacing ───────────────────────
output_text = scrolledtext.ScrolledText(
    window,
    wrap=tk.WORD,
    width=78,
    height=32,
    font=("Helvetica", 11),
    bg=SURFACE,
    fg=TEXT_PRIMARY,
    relief="flat",
    borderwidth=1,
    highlightthickness=1,
    highlightbackground=BORDER,
    insertbackground=ACCENT,
    spacing1=6,
    spacing3=4
)
output_text.pack(padx=20, pady=(10, 20), fill=tk.BOTH, expand=True)

# Apply all text tags (colors + fonts)
for tag, cfg in output_text_tags.items():
    output_text.tag_configure(tag, **cfg)

# Initial placeholder/help text
output_text.insert(tk.END, "Paste a cooking recipe URL above and click the button.\n\n")
output_text.insert(tk.END, "Compatible with many recipe blogs such as, but not limited to:\n"
                          "• allrecipes.com\n"
                          "• loveandlemons.com\n"
                          "• bbcgoodfood.com\n"
                          "• foodnetwork.com\n\n", "note")
output_text.insert(tk.END, "Recipes provided without the extra unneeded details!\n\n")

# Start the Tkinter event loop
window.mainloop()