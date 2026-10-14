# 🌾 Rural Scheme AI

**An AI-powered rural government scheme assistant for Tamil Nadu.**

Rural Scheme AI is a native Python desktop application that helps users explore government welfare schemes, understand eligibility criteria, learn about required documents, and find application instructions in English, Tamil, and Tanglish.

## ✨ Features

- 💬 **Chat Interface** — Interactive chat interface with a dark, WhatsApp-inspired design.
- 🌐 **Multilingual Support** — Access scheme information in English, Tamil, and Tanglish.
- 🏛️ **Government Scheme Information** — Explore information about central and Tamil Nadu government schemes.
- 🔍 **Scheme Search** — Find schemes using scheme names, keywords, and alternative names.
- 📋 **Eligibility Guidance** — Understand eligibility requirements, benefits, and necessary documents.
- 📝 **Application Guidance** — Learn how to apply through official portals and government offices.
- 🎙️ **Voice Input** — Optional local speech recognition using Faster-Whisper.
- 🔊 **Voice Output** — Optional text-to-speech functionality using pyttsx3.
- 💾 **Chat History** — Store and restore conversations using SQLite.
- 🔒 **Privacy-Friendly Design** — Scheme lookup and chat history work locally without requiring API keys.
- 🖥️ **Native Desktop App** — Built with Python and Tkinter, without requiring a web frontend.

## 🏛️ Supported Schemes

The application includes information about schemes and services such as:

- PM-KISAN Samman Nidhi
- Pradhan Mantri Fasal Bima Yojana (PMFBY)
- Chief Minister's Uzhavar Pathukappu Thittam
- Pudhumai Penn Scheme
- Tamil Pudhalvan Scheme
- Kalaignar Magalir Urimai Thittam
- VB-G RAM-G Rural Employment Framework
- Pradhan Mantri Awaas Yojana – Gramin (PMAY-G)
- Pradhan Mantri Jan-Dhan Yojana (PMJDY)
- Tamil Nadu Chief Minister's Breakfast Scheme
- Tamil Nadu Social Security Pension Schemes
- Tamil Nadu e-Sevai Services

*Note: Scheme details, eligibility, benefits, and application procedures may change. Always verify the latest information through official government sources.*

## 🛠️ Technologies Used

- **Python** — Core programming language
- **Tkinter / ttk** — Desktop graphical user interface
- **SQLite** — Local chat-history database
- **JSON** — Embedded scheme database
- **Faster-Whisper** — Optional local speech recognition
- **pyttsx3** — Optional text-to-speech
- **NumPy** — Audio processing for voice input
- **sounddevice** — Microphone input

## 📋 Requirements

- Python 3.10 or later recommended
- Windows, Linux, or macOS with a working Tkinter installation
- Microphone and speakers for voice features (optional)
- Internet access for the initial download of the optional speech-recognition model, if needed

## 🚀 Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/rural-scheme-ai.git
```

### 2. Navigate to the project folder

```bash
cd rural-scheme-ai
```

### 3. Run the application

```bash
python rural_scheme_ai.py
```

The application uses its embedded scheme database and does not require an API key for basic functionality.

### 4. Optional: Install voice dependencies

To enable microphone input and speech output, install the optional packages:

```bash
python -m pip install faster-whisper pyttsx3 sounddevice numpy
```

Voice recognition may download a speech model on first use. Model size affects recognition speed and accuracy.

## 💡 How to Use

1. Launch the application.
2. Choose your preferred language.
3. Search for a government scheme or enter a question in the chat.
4. Read the scheme's benefits, eligibility, required documents, and application instructions.
5. Open the relevant official website or contact the appropriate government office to verify details.
6. Optionally use voice input and spoken responses if the required dependencies are installed.

## 📁 Project Structure

```text
rural-scheme-ai/
│
├── rural_scheme_ai.py    # Main desktop application
└── README.md             # Project documentation
```

The application stores chat history and logs in a local directory under the user's home folder.

## 🔐 Privacy and Disclaimer

- Basic scheme lookup works without an external AI API.
- Chat history is stored locally using SQLite.
- Optional speech recognition runs locally after the required model is available.
- Scheme information is provided for general guidance only.
- The application does not guarantee eligibility, application approval, employment, or benefit payments.
- Do not share Aadhaar OTPs, banking credentials, or other sensitive information with unauthorized persons.

## 🔮 Future Improvements

- Expand the government scheme database.
- Add more regional languages.
- Improve search using natural-language processing.
- Add regularly verified scheme updates.
- Improve accessibility and voice interaction.
- Add official application-status links where available.

## 🤝 Contributing

Contributions, suggestions, and bug reports are welcome.

1. Fork the repository.
2. Create a new branch.
3. Make your changes.
4. Submit a pull request describing your improvements.

## 📄 License

No license has been specified yet. Add a suitable open-source license before permitting others to reuse, modify, or distribute this project.

---

**Built with ❤️ using Python to make government scheme information more accessible.**
