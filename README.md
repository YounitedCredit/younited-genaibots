
# GenaiBots Project

## Overview
GenaiBots is a comprehensive framework designed for automating and managing interactions across various digital platforms. It is primarily an enterprise tool for integrating generative AI into operational processes through mediums such as instant messaging, emails, ticketing tools, or internal tools. Utilizing advanced AI and a modular plugin system, it enables the creation of sophisticated operational flows and interaction models tailored for both businesses and developers.

## Key Features
- **AI Enhancements**: Integrate generative AI at the core of interactions. This enables not only custom AI generation through prompts but also the ability to trigger actions and manage processes with a rapid feedback loop.
- **Custom Action Handlers**: Easily create custom actions based on specific triggers and conditions, and invoke them directly through prompts.
- **Extensible Plugin Architecture**: Expand functionality or integrate third-party services through plugins, ensuring flexibility and extensibility.
- **Integration with Enterprise Systems**: Interface generative AI seamlessly within the core IT infrastructure via a web server or Docker container. This allows processing and tracking tasks performed by bots across various contexts (messaging, ticketing tools, emails, custom applications).
- **Dynamic Backend Services**: Integrates with various backend services for data processing and storage, allowing the system to adapt to specific enterprise use cases and requirements.

## System Requirements
- **Operating System**: Compatible with Windows, MacOS, and Linux.
- **Python Version**: 3.8 or later.
- **Additional Libraries and Dependencies**: Listed in the `requirements.txt` file.

## Installation Guide
1. **Clone the Repository**
   ```bash
   git clone https://github.com/YounitedCredit/younited-genaibots
   cd genaibots
   ```
2. **Setup Virtual Environment (Recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration
Configure the application settings by editing the `config.yaml` file in the `config` directory. Ensure all necessary API keys and database configurations are set correctly.

### config.yaml
The `config.yaml` file centralizes the configuration settings for the GenaiBots application. Here are some key sections and their purposes:

- **BOT_CONFIG**: Contains settings related to bot behavior and debugging levels.
    - `LOG_DEBUG_LEVEL`: Defines the debug level for logging.
    - `PROMPTS_FOLDER`, `CORE_PROMPT`, `MAIN_PROMPT`, `SUBPROMPTS_FOLDER`: Specify the directories and files for prompts.
    - `SHOW_COST_IN_THREAD`: Toggle to show cost information in threads.
    - Various plugin default names and behaviors are also configured here.
  
- **UTILS**: Contains utility configurations, such as logging settings.
    - `LOGGING`: Configures logging, including file system paths and Azure settings.

- **PLUGINS**: Defines available plugins and their configurations.
    - Categories include `ACTION_INTERACTIONS`, `BACKEND`, `USER_INTERACTIONS`, `GENAI_INTERACTIONS`, and `USER_INTERACTIONS_BEHAVIORS`.

### Environment Setup
The environment variables are loaded via `python-dotenv`, typically from a `.env` file. This allows the application to securely load sensitive data like API keys and database URLs. Here's a basic overview of how environment setup works in GenaiBots:

1. **Loading Environment Variables**: `load_dotenv()` function is called to load environment variables from a `.env` file into the application.
2. **Accessing Environment Variables**: The configuration settings in `config.yaml` can reference these environment variables using the `$(ENV_VAR_NAME)` syntax.

## Running the Application
Execute the following command in the project root directory:
```bash
python app.py
```
This will start the server and begin handling requests based on configured actions and triggers.

## Debugging in Visual Studio Code
To debug the application in Visual Studio Code, use the following command:

```bash
c:; cd 'c:\repos\Yuc.GenaiBots'; & 'C:\Users\AntoineHABERT\miniconda3\python.exe' 'c:\Users\AntoineHABERT\.vscode\extensions\ms-python.debugpy-2024.6.0-win32-x64\bundled\libs\debugpy\adapter/../..\debugpy\launcher' '64580' '--' '-m' 'uvicorn' 'app:app' '--host' 'localhost' '--port' '7071' '--workers' '1'
```

## Plugin Architecture
GenaiBots employs a modular plugin architecture categorized into several families:

1. **Action Interactions**:
    - **Default Plugins**: Predefined actions for common tasks.
    - **Custom Plugins**: User-defined actions tailored to specific needs.

2. **Backend**:
    - Handles internal data processing and interactions with backend services.

3. **User Interactions**:
    - **Instant Messaging**: Plugins for handling messaging platforms like Slack and Teams.
    - **Custom API**: Plugins to interact with custom APIs.

4. **GenAI Interactions**:
    - **Text**: Plugins for generating and handling text interactions using AI.
    - **Image**: Plugins for generating and handling image interactions using AI.
    - **Vector Search**: Plugins for handling vector search functionalities.

5. **User Interactions Behaviors**:
    - Defines the behavior of user interactions across different messaging platforms and custom APIs.

## Contribution Guidelines
Interested in contributing? Please read through the `CONTRIBUTING.md` file to understand our contribution requirements and code of conduct.

## License
This project is licensed under the MIT License - see the `LICENSE.md` file for more details.

## Support and Contact
For any support queries or to report issues, please visit our GitHub Issues page at:
https://example.com/genaibots/issues
