import streamlit as st
import openai
import os
import json
import random
from PIL import Image, ImageDraw, ImageFont
import textwrap

# --------------------------
# 1. CONFIGURATION & SETUP
# --------------------------

# Function to load settings from JSON file
def load_settings():
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r") as f:
                settings = json.load(f)
                # Ensure default values exist for friend_name and user_name
                settings.setdefault("friend_name", "Zak")
                settings.setdefault("user_name", "Guigs")
                return settings
        except json.JSONDecodeError:
            st.warning("Settings file is corrupted. Loading default settings.")
    return {
        "mother_tongue": "English",
        "target_language": "Polish",
        "language_level": "B1",
        "friend_name": "Zak",
        "user_name": "Guigs"
    }


# Function to save settings to JSON file
def save_settings(settings_path, updated_settings):
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(updated_settings, f, indent=4, ensure_ascii=False)

# Define the path to settings.json
SETTINGS_PATH = os.path.join("pages", "settings.json")

# Load OpenAI API key securely from Streamlit Secrets
API_KEY = st.secrets["openai"]["api_key"]

client = openai.Client(api_key=API_KEY)


POSTCARD_FOLDER = "./Postcards"
FONTS_FOLDER = "./Fonts"

# Gather all .ttf font paths in FONTS_FOLDER
FONT_FILES = [
    os.path.join(FONTS_FOLDER, f)
    for f in os.listdir(FONTS_FOLDER)
    if f.lower().endswith(".ttf")
]

# -------------------------
# 2. GPT HELPER FUNCTIONS
# -------------------------
def generate_friend_letter(friend_name, user_name, target_language):
    """
    Generate a short letter in target_language from friend_name to user_name,
    signing off with friend_name.
    """
    prompt = (
        f"Write a short (about 80 words) letter to your friend about a random activity in vacation. Ask a question about something to your friend. Speak in {target_language} from {friend_name} point of view. "
        f"to {user_name}. Sign the letter as {friend_name}."
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are writing to your friend a letter from your holidays in..."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=300,
        temperature=0.9
    )
    return response.choices[0].message.content.strip()

def translate_to_language(text, target_language):
    """
    Ask ChatGPT to translate text into target_language.
    """
    prompt = f"Please translate the following text into {target_language}:\n\n{text}."
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a translator emphasizing on keeping original meaning."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=300,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def correct_text_in_target_language(user_text, target_language, mother_tongue):
    """
    Ask ChatGPT to correct and explain mistakes in user_text 
    which is written in target_language.
    """
    prompt = (
        f"You are a language teacher. Correct mistakes using {target_language} then explain any mistakes done in {mother_tongue}. Remember, first part of your message is in {target_language} and second (correction in bullet list with explanations in this precise context) in {mother_tongue}"
        f"text written in {target_language}:\n\n{user_text}"
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a language teacher."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=300,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

# --------------------------------
# 3. IMAGE & TEXT RENDERING LOGIC
# --------------------------------
def pick_random_postcard():
    """
    Pick a random image from POSTCARD_FOLDER.
    """
    image_files = [
        os.path.join(POSTCARD_FOLDER, f)
        for f in os.listdir(POSTCARD_FOLDER)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]
    return random.choice(image_files) if image_files else None

def overlay_text_on_postcard(image_path, text):
    """
    1) Makes the text bigger (larger font size).
    2) Restricts the text to the left side (~40-42% width) of the postcard 
       by manually wrapping lines with textwrap.
    """
    postcard = Image.open(image_path).convert("RGBA")
    width, height = postcard.size

    text_overlay = Image.new("RGBA", postcard.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(text_overlay)

    # Pick a random font from the folder and set a bigger font size (5% of height)
    font_path = random.choice(FONT_FILES) if FONT_FILES else None
    font_size = int(height * 0.05)  # 5% of image height
    font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()

    # Random color with slight transparency
    r, g, b = (random.randint(0, 255) for _ in range(3))
    alpha = random.randint(160, 220)
    color = (r, g, b, alpha)

    # Define margins & max text width for left half
    margin_left = int(width * 0.03)
    margin_top = int(height * 0.18)
    max_text_width = int(width * 0.42)

    # Word-wrap: break text into lines so it doesn't exceed ~40-42% of the width
    wrapped_lines = []
    for paragraph in text.split("\n"):
        # This 'width=40' is an approximation; tweak as needed.
        for line in textwrap.wrap(paragraph, width=40):
            wrapped_lines.append(line)

    # Draw each line
    line_height = font_size + 6  # extra spacing between lines
    y_offset = margin_top
    for line in wrapped_lines:
        # (Optional) measure to ensure we stay within max_text_width
        line_width_pixels = draw.textlength(line, font=font)
        # If needed, you can do further checks to re-wrap or scale text.

        draw.text((margin_left, y_offset), line, font=font, fill=color)
        y_offset += line_height

    return Image.alpha_composite(postcard, text_overlay)

# --------------------
# 4. STREAMLIT APP FUNCTIONS
# --------------------
def load_css(css_file_path):
    """
    Load and inject the CSS file into the Streamlit app.
    """
    if os.path.exists(css_file_path):
        with open(css_file_path) as f:
            css = f.read()
            st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)
    else:
        st.warning(f"CSS file not found at {css_file_path}. Skipping custom styles.")

def main():
    # Load custom CSS
    load_css("static/styles.css")

    st.title("📬 Custom Postcard Generator")

    # Load settings
    settings = load_settings()


    # Initialize session_state for user_name and friend_name if not already
    if "user_name" not in st.session_state:
        st.session_state["user_name"] = settings.get("user_name", "Jan")
    if "friend_name" not in st.session_state:
        st.session_state["friend_name"] = settings.get("friend_name", "Piotr")

    # Sidebar for Settings
    st.sidebar.header("🔧 Settings")

    # Editable fields for user_name and friend_name
    edited_user_name = st.sidebar.text_input("🖊️ Your Name (Recipient):", value=st.session_state["user_name"])
    edited_friend_name = st.sidebar.text_input("🖊️ Friend’s Name (Sender):", value=st.session_state["friend_name"])

    # If names have changed, update the settings.json and session_state
    if edited_user_name != st.session_state["user_name"] or edited_friend_name != st.session_state["friend_name"]:
        settings["user_name"] = edited_user_name
        settings["friend_name"] = edited_friend_name
        save_settings(SETTINGS_PATH, settings) 
        st.sidebar.success("✅ Names updated successfully!")
        # Update session_state
        st.session_state["user_name"] = edited_user_name
        st.session_state["friend_name"] = edited_friend_name

    # Display current language settings
    mother_tongue = settings.get("mother_tongue", "French")
    target_language = settings.get("target_language", "Polish")
    language_level = settings.get("language_level", "A2")

    st.sidebar.write("### Language Settings")
    st.sidebar.write(f"**Mother Tongue:** {mother_tongue}")
    st.sidebar.write(f"**Target Language:** {target_language}")
    st.sidebar.write(f"**Language Level:** {language_level}")

    # Main page inputs
    user_name = st.session_state["user_name"]
    friend_name = st.session_state["friend_name"]

    if "postcard_path" not in st.session_state:
        st.session_state["postcard_path"] = pick_random_postcard()

    # Generate the letter if the user clicks the button
    if st.button("✉️ Generate Letter"):
        if not st.session_state["postcard_path"]:
            st.error("❌ No postcard images found. Please check your POSTCARD_FOLDER path.")
        else:
            with st.spinner("Generating your personalized letter..."):
                # 2) Ask ChatGPT to write a short letter in the target language
                letter_text = generate_friend_letter(friend_name, user_name, target_language)
                st.session_state["letter_text"] = letter_text

                # 3) Create final postcard
                final_postcard = overlay_text_on_postcard(st.session_state["postcard_path"], letter_text)
                st.session_state["final_postcard"] = final_postcard

                # 4) Also store translation in session (from target_lang -> mother_lang)
                st.session_state["letter_translation"] = translate_to_language(letter_text, mother_tongue)

            st.success("✅ Letter generated successfully!")

    # Display postcard if generated
    if "final_postcard" in st.session_state:
        st.image(
            st.session_state["final_postcard"],
            caption=f"✉️ Letter from {friend_name} to {user_name}",
            use_container_width=True
        )

        st.subheader("🧐 Guess the Translation")
        # Let user guess the translation in their native language
        guess = st.text_area(f"Your guess in {mother_tongue}:")

        # Reveal actual translation
        if st.button("🔍 Reveal ChatGPT Translation"):
            if "letter_translation" in st.session_state:
                st.write(st.session_state["letter_translation"])
            else:
                st.info("ℹ️ You have not generated a letter yet.")

        # Reply to the letter in the target language
        st.subheader(f"💬 Reply to the Letter in {target_language}")
        user_reply = st.text_area(f"Write your reply in {target_language}:")

        # Correct the user's reply in target_language
        if st.button("✅ Correct My Reply"):
            if user_reply.strip():
                with st.spinner("🔧 Correcting your reply..."):
                    corrected = correct_text_in_target_language(user_reply, target_language, mother_tongue)
                    st.write(corrected)
            else:
                st.info("ℹ️ Please enter some text to correct.")

if __name__ == "__main__":
    main() 