import streamlit as st
import openai
import os
import random
from PIL import Image, ImageDraw, ImageFont
import textwrap

# --------------------------
# 1. CONFIGURATION & SETUP
# --------------------------
# Initialize default settings in session_state if not already set
if "mother_tongue" not in st.session_state:
    st.session_state["mother_tongue"] = "English"
if "target_language" not in st.session_state:
    st.session_state["target_language"] = "Polish"
if "language_level" not in st.session_state:
    st.session_state["language_level"] = "B1"
if "user_name" not in st.session_state:
    st.session_state["user_name"] = "Guigs"
if "friend_name" not in st.session_state:
    st.session_state["friend_name"] = "Zak"

# Load OpenAI API key securely from Streamlit Secrets
API_KEY = st.secrets["openai"]["api_key"]
client = openai.Client(api_key=API_KEY)

POSTCARD_FOLDER = "./Postcards"
FONTS_FOLDER = "./Fonts"

# Gather all available random fonts in FONTS_FOLDER (for Latin alphabets)
FONT_FILES = [
    os.path.join(FONTS_FOLDER, f)
    for f in os.listdir(FONTS_FOLDER)
    if f.lower().endswith(".ttf") and f.lower() not in ["cyrillic.ttf", "korean.ttf", "japanese.ttf", "chinese.ttf"]
]

# -------------------------
# 2. GPT HELPER FUNCTIONS
# -------------------------
def generate_friend_letter(friend_name, user_name, target_language):
    """
    Generate a short letter (≈80 words) in target_language from friend_name to user_name.
    """
    prompt = (
        f"Write a short (about 80 words) letter to your friend about a random activity on vacation. "
        f"Ask a question to your friend. Write in {target_language} from {friend_name}'s point of view to {user_name} "
        f"and sign the letter as {friend_name}."
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are writing a letter from your holidays."},
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
            {"role": "system", "content": "You are a translator who preserves the original meaning."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=300,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def correct_text_in_target_language(user_text, target_language, mother_tongue):
    """
    Ask ChatGPT to correct and explain mistakes in user_text written in target_language.
    """
    prompt = (
        f"You are a language teacher. Correct the mistakes using {target_language} and then explain the mistakes in {mother_tongue}. "
        f"First provide the corrected text in {target_language}, then a bullet list with explanations in {mother_tongue}.\n\n"
        f"Text written in {target_language}:\n\n{user_text}"
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

# -------------------------
# 2a. Caching for Translations
# -------------------------
@st.cache_data(show_spinner=False)
def cached_translation(text, target_language):
    return translate_to_language(text, target_language)

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

def overlay_text_on_postcard(image_path, text, target_language):
    """
    Overlays the provided text on the postcard image.
    - The postcard is first resized to a consistent size (600×400 pixels).
    - The text area extends up to 60% of the postcard's width.
    - A language-specific font is chosen if applicable.
    - The font size is dynamically adjusted so that text appears at a consistent visual size.
    """
    # Open and resize the postcard image to a constant size (600x400)
    postcard = Image.open(image_path).convert("RGBA")
    target_size = (600, 400)
    postcard = postcard.resize(target_size)
    width, height = postcard.size

    text_overlay = Image.new("RGBA", postcard.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(text_overlay)

    # Define letter area (left side)
    margin_left = int(width * 0.03)
    margin_top = int(height * 0.18)
    max_text_width = int(width * 0.60)  # up to 60% of the postcard horizontally

    # Determine font path based on target language (use specific fonts for non-Latin alphabets)
    tl_lower = target_language.lower()
    if tl_lower in ["russian", "ukrainian", "bulgarian", "serbian", "macedonian"]:
        font_path = os.path.join(FONTS_FOLDER, "cyrillic.ttf")
    elif tl_lower == "korean":
        font_path = os.path.join(FONTS_FOLDER, "korean.ttf")
    elif tl_lower == "japanese":
        font_path = os.path.join(FONTS_FOLDER, "japanese.ttf")
    elif tl_lower == "chinese":
        font_path = os.path.join(FONTS_FOLDER, "chinese.ttf")
    else:
        font_path = random.choice(FONT_FILES) if FONT_FILES else None

    # Define a baseline target for the character height (in pixels)
    target_char_height = 14

    # Start with an initial font size
    init_font_size = 14
    try:
        # Attempt to load the font at the initial size
        font = ImageFont.truetype(font_path, init_font_size) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    # Function to measure text size safely
    def measure_text(font_obj, text):
        try:
            return font_obj.getsize(text)
        except AttributeError:
            # Fallback to getbbox if getsize is not available
            bbox = font_obj.getbbox(text)
            return (bbox[2] - bbox[0], bbox[3] - bbox[1])

    # If using a TrueType font, adjust the font size so that the rendered character "A" is close to target_char_height.
    if font_path is not None:
        ref_char = "A"
        measured_width, measured_height = measure_text(font, ref_char)
        # Avoid division by zero
        if measured_height > 0:
            adjusted_font_size = int(init_font_size * target_char_height / measured_height)
            if adjusted_font_size != init_font_size:
                try:
                    font = ImageFont.truetype(font_path, adjusted_font_size)
                except Exception:
                    font = ImageFont.load_default()

    # Compute an approximate maximum number of characters per line based on the average character width.
    avg_char_width, _ = measure_text(font, "A")
    max_chars = max(1, int(max_text_width // avg_char_width))

    # Wrap text so that each line does not exceed the designated area.
    wrapped_lines = []
    for paragraph in text.split("\n"):
        wrapped_lines.extend(
            textwrap.wrap(paragraph, width=max_chars, break_long_words=True, break_on_hyphens=False)
        )

    # Draw each line on the overlay using a random dark color (RGB values between 0 and 100)
    line_height = measure_text(font, "A")[1] + 6  # based on the adjusted font size with extra spacing
    y_offset = margin_top
    r, g, b = [random.randint(0, 100) for _ in range(3)]
    color = (r, g, b, 255)

    for line in wrapped_lines:
        draw.text((margin_left, y_offset), line, font=font, fill=color)
        y_offset += line_height

    return Image.alpha_composite(postcard, text_overlay)

# --------------------
# 4. CONVERSATION MODE FUNCTIONS
# --------------------
def simulate_friend_response():
    """
    Uses the current conversation history stored in session_state to generate a friend reply.
    The conversation context is maintained over multiple exchanges.
    """
    conversation_history = st.session_state["conversation_history"]
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=conversation_history,
        max_tokens=300,
        temperature=0.9
    )
    friend_reply = response.choices[0].message.content.strip()
    st.session_state["conversation_history"].append({"role": "assistant", "content": friend_reply})
    return friend_reply

def init_conversation():
    """
    Initializes a new conversation by setting the conversation history with a system prompt.
    Then, an initial greeting from the friend is generated.
    """
    friend_name = st.session_state["friend_name"]
    user_name = st.session_state["user_name"]
    target_language = st.session_state["target_language"]
    language_level = st.session_state["language_level"]
    st.session_state["conversation_history"] = [
        {"role": "system", "content": (
            f"You are {friend_name}, a friendly language partner conversing in {target_language}. "
            f"Engage in a lively, realistic conversation with your friend {user_name} while keeping your language level at {language_level}."
        )}
    ]
    simulate_friend_response()

# --------------------
# 5. STREAMLIT APP FUNCTIONS
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

    # ---------------------------
    # Sidebar: Names and Settings
    # ---------------------------
    st.sidebar.header("🔧 Settings")

    # Editable fields for recipient and sender names
    edited_user_name = st.sidebar.text_input("🖊️ Your Name (Recipient):", value=st.session_state["user_name"])
    edited_friend_name = st.sidebar.text_input("🖊️ Friend’s Name (Sender):", value=st.session_state["friend_name"])
    if edited_user_name != st.session_state["user_name"] or edited_friend_name != st.session_state["friend_name"]:
        st.session_state["user_name"] = edited_user_name
        st.session_state["friend_name"] = edited_friend_name
        st.sidebar.success("✅ Names updated successfully!")

    # Editable Language Settings with a Save button
    st.sidebar.subheader("Language Settings")
    edited_mother_tongue = st.sidebar.text_input("Mother Tongue:", value=st.session_state["mother_tongue"])
    edited_target_language = st.sidebar.text_input("Target Language:", value=st.session_state["target_language"])
    edited_language_level = st.sidebar.text_input("Language Level:", value=st.session_state["language_level"])
    if st.sidebar.button("💾 Save Language Settings"):
        st.session_state["mother_tongue"] = edited_mother_tongue
        st.session_state["target_language"] = edited_target_language
        st.session_state["language_level"] = edited_language_level
        st.sidebar.success("✅ Language settings saved!")

    # Retrieve current settings from session_state
    mother_tongue = st.session_state["mother_tongue"]
    target_language = st.session_state["target_language"]
    language_level = st.session_state["language_level"]
    user_name = st.session_state["user_name"]
    friend_name = st.session_state["friend_name"]

    # ---------------------------
    # Main Page: Generate Postcard Letter
    # ---------------------------
    if "postcard_path" not in st.session_state:
        st.session_state["postcard_path"] = pick_random_postcard()

    if st.button("✉️ Generate Letter"):
        if not st.session_state["postcard_path"]:
            st.error("❌ No postcard images found. Please check your POSTCARD_FOLDER path.")
        else:
            with st.spinner("Generating your personalized letter..."):
                # Generate the letter in the target language
                letter_text = generate_friend_letter(friend_name, user_name, target_language)
                st.session_state["letter_text"] = letter_text

                # Create the final postcard with the overlaid letter text
                final_postcard = overlay_text_on_postcard(st.session_state["postcard_path"], letter_text, target_language)
                st.session_state["final_postcard"] = final_postcard

                # Also store the translation (from target language to mother tongue)
                st.session_state["letter_translation"] = translate_to_language(letter_text, mother_tongue)
            st.success("✅ Letter generated successfully!")

    if "final_postcard" in st.session_state:
        st.image(
            st.session_state["final_postcard"],
            caption=f"✉️ Letter from {friend_name} to {user_name}",
            use_container_width=True
        )

        st.subheader("🧐 Guess the Translation")
        guess = st.text_area(f"Your guess in {mother_tongue}:")

        if st.button("🔍 Reveal ChatGPT Translation"):
            if "letter_translation" in st.session_state:
                st.write(st.session_state["letter_translation"])
            else:
                st.info("ℹ️ You have not generated a letter yet.")

        st.subheader(f"💬 Reply to the Letter in {target_language}")
        user_reply = st.text_area(f"Write your reply in {target_language}:")

        if st.button("✅ Correct My Reply"):
            if user_reply.strip():
                with st.spinner("🔧 Correcting your reply..."):
                    corrected = correct_text_in_target_language(user_reply, target_language, mother_tongue)
                    st.write(corrected)
            else:
                st.info("ℹ️ Please enter some text to correct.")

    # ---------------------------
    # Conversation Mode Section
    # ---------------------------
    st.header("💬 Simulated Conversation Mode")
    st.write("Engage in a natural, back-and-forth chat with your AI friend to practice your target language. "
             "Your conversation history is maintained to provide context across multiple exchanges.")

    # Option to reset or start a new conversation
    if st.button("🔄 Reset Conversation"):
        init_conversation()
        st.experimental_rerun()

    # Initialize conversation if not already started
    if "conversation_history" not in st.session_state or st.session_state.get("conversation_history") is None:
        if st.button("▶️ Start New Conversation"):
            init_conversation()
            st.experimental_rerun()

    # Display conversation history (excluding the system message)
    if "conversation_history" in st.session_state and st.session_state["conversation_history"]:
        st.subheader("Conversation History")
        for i, msg in enumerate(st.session_state["conversation_history"]):
            if msg["role"] == "system":
                continue  # Skip system messages
            if msg["role"] == "assistant":
                st.markdown(f"**{friend_name}:** {msg['content']}")
            elif msg["role"] == "user":
                st.markdown(f"**{user_name}:** {msg['content']}")
            with st.expander("Show Translation"):
                translation = cached_translation(msg["content"], mother_tongue)
                st.markdown(translation)

        # Form for user to send a new message
        with st.form("conversation_form", clear_on_submit=True):
            user_message = st.text_area("Your Message:", height=100)
            submitted = st.form_submit_button("Send")
            if submitted and user_message.strip():
                st.session_state["conversation_history"].append({"role": "user", "content": user_message})
                with st.spinner("Waiting for friend response..."):
                    simulate_friend_response()
                st.experimental_rerun()

if __name__ == "__main__":
    main()
