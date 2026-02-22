# Gemini Voice-to-Voice

## Project Overview
Gemini Voice-to-Voice is an experimental project that enables AI agents to communicate using mobile phones. The project leverages Microsoft's Phone Link app to redirect input and output sound, creating a seamless voice interaction experience.

## Features
- AI-driven voice communication over mobile phones.
- Integration with Microsoft's Phone Link app.
- Experimental setup for exploring voice-to-voice AI interactions.

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- Microsoft's Phone Link app installed and connected to your mobile phone

### Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```bash
   cd gemini-voice-to-voice
   ```
3. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
4. Activate the virtual environment:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
1. Run the main script:
   ```bash
   python simpleVoiceAgentLive.py
   ```
2. Follow the prompts to interact with the AI agent.

## Project Structure
```
Gemini Voice-to-Voice/
├── src/                # Source code
├── tests/              # Test cases
├── requirements.txt    # Project dependencies
├── README.md           # Project documentation
├── .gitignore          # Git ignore file
```

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request.

## License
This project is licensed under the MIT License.