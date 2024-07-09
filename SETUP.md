# Setup Guide for GenaiBots

## Prerequisites

- **Operating System**: Compatible with Windows, MacOS, and Linux.
- **Python Version**: 3.8 or later.
- **Visual Studio Code**: Latest version recommended.
- **Extensions**:
  - Python (ms-python.python)
  - Pylance (ms-python.vscode-pylance)

## Installation

### 1. Clone the Repository

```bash
git clone https://example.com/genaibots.git
cd genaibots
```

### 2. Setup Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\\Scripts\\activate`
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Configuration

### Environment Variables

Create a `.env` file in the root directory of the project and add the necessary environment variables.

#### Template for Standard Local Configuration

Here is a template for the `.env` file for a standard local configuration:

```
# Logging settings
LOG_DEBUG_LEVEL=DEBUG

# Prompt settings
PROMPTS_FOLDER=./prompts
CORE_PROMPT=core_prompt.txt
MAIN_PROMPT=main_prompt.txt
SUBPROMPTS_FOLDER=./subprompts
FEEDBACK_GENERAL_BEHAVIOR=general_feedback.txt

# Costs settings
SHOW_COST_IN_THREAD=True

# Bot behavior settings
REQUIRE_MENTION_NEW_MESSAGE=False
REQUIRE_MENTION_THREAD_MESSAGE=False
ACKNOWLEDGE_NONPROCESSED_MESSAGE=True
GET_URL_CONTENT=True
LLM_CONVERSION_FORMAT=json
BREAK_KEYWORD=!STOP
START_KEYWORD=!START

# Default plugins
ACTION_INTERACTIONS_DEFAULT_PLUGIN_NAME=main_actions
INTERNAL_DATA_PROCESSING_DEFAULT_PLUGIN_NAME=file_system
USER_INTERACTIONS_INSTANT_MESSAGING_DEFAULT_PLUGIN_NAME=slack
USER_INTERACTIONS_INSTANT_MESSAGING_BEHAVIOR_DEFAULT_PLUGIN_NAME=im_default_behavior
GENAI_TEXT_DEFAULT_PLUGIN_NAME=azure_chatgpt
GENAI_IMAGE_DEFAULT_PLUGIN_NAME=azure_dalle
GENAI_VECTOR_SEARCH_DEFAULT_PLUGIN_NAME=azure_aisearch

# Utils settings
APPLICATIONINSIGHTS_CONNECTION_STRING=your_application_insights_connection_string

# File system backend settings
AZURE_STORAGE_CONNECTION_STRING=your_azure_storage_connection_string

# Slack settings
SLACK_SIGNING_SECRET=your_slack_signing_secret
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_BOT_USER_TOKEN=your_slack_bot_user_token
SLACK_BOT_USER_ID=your_slack_bot_user_id
SLACK_AUTHORIZED_CHANNELS=your_slack_authorized_channels
SLACK_FEEDBACK_CHANNEL=your_slack_feedback_channel
SLACK_FEEDBACK_BOT_ID=your_slack_feedback_bot_id
SLACK_INTERNAL_CHANNEL=your_slack_internal_channel

# Azure settings for various plugins
AZURE_COMMANDR_KEY=your_azure_commandr_key
AZURE_COMMANDR_ENDPOINT=your_azure_commandr_endpoint
AZURE_LLAMA370B_KEY=your_azure_llama370b_key
AZURE_LLAMA370B_ENDPOINT=your_azure_llama370b_endpoint
AZURE_OPENAI_KEY=your_azure_openai_key
AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint
AZURE_MISTRAL_KEY=your_azure_mistral_key
AZURE_MISTRAL_ENDPOINT=your_azure_mistral_endpoint
VERTEXAI_GEMINI_KEY=your_vertexai_gemini_key
VERTEXAI_GEMINI_PROJECTNAME=your_vertexai_gemini_projectname
VERTEXAI_GEMINI_LOCATION=your_vertexai_gemini_location
```

### config.yaml

The `config.yaml` file centralizes the configuration settings for the GenaiBots application. Users can either directly input their information into this file or use environment variables by utilizing the `$(VAR_NAME)` syntax, which is useful for different types of deployments.

Here is a detailed explanation of each section and parameter in the `config.yaml` file:

#### Full Configuration with Comments

```yaml
BOT_CONFIG:

  # DEBUG
  LOG_DEBUG_LEVEL: "$(LOG_DEBUG_LEVEL)"  # Sets the logging debug level.

  # PROMPT
  PROMPTS_FOLDER: "$(PROMPTS_FOLDER)"  # Directory for prompt files.
  CORE_PROMPT: "$(CORE_PROMPT)"  # Core prompt file.
  MAIN_PROMPT: "$(MAIN_PROMPT)"  # Main prompt file.
  SUBPROMPTS_FOLDER: "$(SUBPROMPTS_FOLDER)"  # Directory for sub-prompt files.
  FEEDBACK_GENERAL_BEHAVIOR: "$(FEEDBACK_GENERAL_BEHAVIOR)"  # General feedback prompt file.

  # COSTS
  SHOW_COST_IN_THREAD: "$(SHOW_COST_IN_THREAD)"  # Display cost information in threads.

  # BOT BEHAVIOR
  REQUIRE_MENTION_NEW_MESSAGE: "$(REQUIRE_MENTION_NEW_MESSAGE)"  # Require mention for new messages.
  REQUIRE_MENTION_THREAD_MESSAGE: "$(REQUIRE_MENTION_THREAD_MESSAGE)"  # Require mention for thread messages.
  BEGIN_MARKER: "[BEGINIMDETECT]"  # Marker for the beginning of IM detection.
  END_MARKER: "[ENDIMDETECT]"  # Marker for the end of IM detection.
  ACKNOWLEDGE_NONPROCESSED_MESSAGE: "$(ACKNOWLEDGE_NONPROCESSED_MESSAGE)"  # Acknowledge non-processed messages.
  GET_URL_CONTENT: "$(GET_URL_CONTENT)"  # Enable URL content fetching.
  LLM_CONVERSION_FORMAT: "$(LLM_CONVERSION_FORMAT)"  # Format for LLM conversion.
  BREAK_KEYWORD: "!STOP"  # Keyword to break the conversation.
  START_KEYWORD: "!START"  # Keyword to start the conversation.

  # BOT DEFAULT PLUGINS
  ACTION_INTERACTIONS_DEFAULT_PLUGIN_NAME: "$(ACTION_INTERACTIONS_DEFAULT_PLUGIN_NAME)"  # Default plugin for action interactions.
  INTERNAL_DATA_PROCESSING_DEFAULT_PLUGIN_NAME: "$(INTERNAL_DATA_PROCESSING_DEFAULT_PLUGIN_NAME)"  # Default plugin for internal data processing.
  USER_INTERACTIONS_INSTANT_MESSAGING_BEHAVIOR_DEFAULT_PLUGIN_NAME: "$(USER_INTERACTIONS_INSTANT_MESSAGING_BEHAVIOR_DEFAULT_PLUGIN_NAME)"  # Default plugin for IM behavior.
  GENAI_TEXT_DEFAULT_PLUGIN_NAME: "$(GENAI_TEXT_DEFAULT_PLUGIN_NAME)"  # Default plugin for text generation.
  GENAI_IMAGE_DEFAULT_PLUGIN_NAME: "$(GENAI_IMAGE_DEFAULT_PLUGIN_NAME)"  # Default plugin for image generation.
  GENAI_VECTOR_SEARCH_DEFAULT_PLUGIN_NAME: "$(GENAI_VECTOR_SEARCH_DEFAULT_PLUGIN_NAME)"  # Default plugin for vector search.

UTILS:
  LOGGING:
    FILE_SYSTEM:
      PLUGIN_NAME: 'file_system'  # Plugin name for file system logging.
      FILE_PATH: 'C:\\LOGS\\GENAI_BOT.log'  # File path for the log file.

PLUGINS:
  ACTION_INTERACTIONS:
    DEFAULT:
      MAIN_ACTIONS:
        PLUGIN_NAME: "main_actions"  # Main actions plugin name.
    CUSTOM: {}  # Custom actions can be added here.

  BACKEND:
    INTERNAL_DATA_PROCESSING:
      FILE_SYSTEM:
        PLUGIN_NAME: "file_system"  # Plugin name for file system backend.
        DIRECTORY: "C:\\GenAI"  # Directory for the file system backend.
        SESSIONS_CONTAINER: "sessions"  # Directory for sessions.
        MESSAGES_CONTAINER: "messages"  # Directory for messages.
        FEEDBACKS_CONTAINER: "feedbacks"  # Directory for feedbacks.
        CONCATENATE_CONTAINER: "concatenate"  # Directory for concatenated data.
        PROMPTS_CONTAINER: "prompts"  # Directory for prompts.
        COSTS_CONTAINER: "costs"  # Directory for cost information.
        PROCESSING_CONTAINER: "processing"  # Directory for processing data.
        ABORT_CONTAINER: "abort"  # Directory for abort data.
        VECTORS_CONTAINER: "vectors"  # Directory for vector data.

  USER_INTERACTIONS:
    INSTANT_MESSAGING:
      SLACK:
        PLUGIN_NAME: "slack"  # Plugin name for Slack integration.
        BEHAVIOR_PLUGIN_NAME: "im_default_behavior"  # Default behavior plugin for Slack.
        ROUTE_PATH: "/api/get_slacknotification"  # API route path for Slack notifications.
        ROUTE_METHODS: ["POST"]  # HTTP methods for the Slack API route.
        PLUGIN_DIRECTORY: "plugins.user_interactions.plugins"  # Directory for plugins.
        SLACK_MESSAGE_TTL: 3600  # Time-to-live for Slack messages.
        SLACK_SIGNING_SECRET: "$(SLACK_SIGNING_SECRET)"  # Signing secret for Slack.
        SLACK_BOT_TOKEN: "$(SLACK_BOT_TOKEN)"  # Bot token for Slack.
        SLACK_BOT_USER_TOKEN: "$(SLACK_BOT_USER_TOKEN)"  # User token for Slack bot.
        SLACK_BOT_USER_ID: "$(SLACK_BOT_USER_ID)"  # User ID for Slack bot.
        SLACK_API_URL: "https://slack.com/api/"  # API URL for Slack.
        SLACK_AUTHORIZED_CHANNELS: "$(SLACK_AUTHORIZED_CHANNELS)"  # Authorized channels for Slack bot.
        SLACK_FEEDBACK_CHANNEL: "$(SLACK_FEEDBACK_CHANNEL)"  # Feedback channel for Slack bot.
        SLACK_FEEDBACK_BOT_ID: "$(SLACK_FEEDBACK_BOT_ID)"  # Feedback bot ID for Slack.
        MAX_MESSAGE_LENGTH: 2900  # Maximum message length for Slack.
        INTERNAL_CHANNEL: "$(SLACK_INTERNAL_CHANNEL)"  # Internal channel for Slack bot.
        WORKSPACE_NAME: "pretdunion"
```

##

 Explanation of Parameters

### BOT_CONFIG

- **LOG_DEBUG_LEVEL**: Sets the logging debug level.
- **PROMPTS_FOLDER**: Directory for prompt files.
- **CORE_PROMPT**: Core prompt file.
- **MAIN_PROMPT**: Main prompt file.
- **SUBPROMPTS_FOLDER**: Directory for sub-prompt files.
- **FEEDBACK_GENERAL_BEHAVIOR**: General feedback prompt file.
- **SHOW_COST_IN_THREAD**: Display cost information in threads.
- **REQUIRE_MENTION_NEW_MESSAGE**: Require mention for new messages.
- **REQUIRE_MENTION_THREAD_MESSAGE**: Require mention for thread messages.
- **BEGIN_MARKER**: Marker for the beginning of IM detection.
- **END_MARKER**: Marker for the end of IM detection.
- **ACKNOWLEDGE_NONPROCESSED_MESSAGE**: Acknowledge non-processed messages.
- **GET_URL_CONTENT**: Enable URL content fetching.
- **LLM_CONVERSION_FORMAT**: Format for LLM conversion.
- **BREAK_KEYWORD**: Keyword to break the conversation.
- **START_KEYWORD**: Keyword to start the conversation.
- **ACTION_INTERACTIONS_DEFAULT_PLUGIN_NAME**: Default plugin for action interactions.
- **INTERNAL_DATA_PROCESSING_DEFAULT_PLUGIN_NAME**: Default plugin for internal data processing.
- **USER_INTERACTIONS_INSTANT_MESSAGING_BEHAVIOR_DEFAULT_PLUGIN_NAME**: Default plugin for IM behavior.
- **GENAI_TEXT_DEFAULT_PLUGIN_NAME**: Default plugin for text generation.
- **GENAI_IMAGE_DEFAULT_PLUGIN_NAME**: Default plugin for image generation.
- **GENAI_VECTOR_SEARCH_DEFAULT_PLUGIN_NAME**: Default plugin for vector search.

### UTILS

- **LOGGING.FILE_SYSTEM**: Configuration for file system logging.
  - **PLUGIN_NAME**: Plugin name for file system logging.
  - **FILE_PATH**: File path for the log file.

### PLUGINS

#### ACTION_INTERACTIONS

- **DEFAULT.MAIN_ACTIONS**: Main actions plugin configuration.
  - **PLUGIN_NAME**: Main actions plugin name.
- **CUSTOM**: Custom actions can be added here.

#### BACKEND

- **INTERNAL_DATA_PROCESSING.FILE_SYSTEM**: File system backend configuration.
  - **PLUGIN_NAME**: Plugin name for file system backend.
  - **DIRECTORY**: Directory for the file system backend.
  - **SESSIONS_CONTAINER**: Directory for sessions.
  - **MESSAGES_CONTAINER**: Directory for messages.
  - **FEEDBACKS_CONTAINER**: Directory for feedbacks.
  - **CONCATENATE_CONTAINER**: Directory for concatenated data.
  - **PROMPTS_CONTAINER**: Directory for prompts.
  - **COSTS_CONTAINER**: Directory for cost information.
  - **PROCESSING_CONTAINER**: Directory for processing data.
  - **ABORT_CONTAINER**: Directory for abort data.
  - **VECTORS_CONTAINER**: Directory for vector data.

#### USER_INTERACTIONS

- **INSTANT_MESSAGING.SLACK**: Slack integration configuration.
  - **PLUGIN_NAME**: Plugin name for Slack integration.
  - **BEHAVIOR_PLUGIN_NAME**: Default behavior plugin for Slack.
  - **ROUTE_PATH**: API route path for Slack notifications.
  - **ROUTE_METHODS**: HTTP methods for the Slack API route.
  - **PLUGIN_DIRECTORY**: Directory for plugins.
  - **SLACK_MESSAGE_TTL**: Time-to-live for Slack messages.
  - **SLACK_SIGNING_SECRET**: Signing secret for Slack.
  - **SLACK_BOT_TOKEN**: Bot token for Slack.
  - **SLACK_BOT_USER_TOKEN**: User token for Slack bot.
  - **SLACK_BOT_USER_ID**: User ID for Slack bot.
  - **SLACK_API_URL**: API URL for Slack.
  - **SLACK_AUTHORIZED_CHANNELS**: Authorized channels for Slack bot.
  - **SLACK_FEEDBACK_CHANNEL**: Feedback channel for Slack bot.
  - **SLACK_FEEDBACK_BOT_ID**: Feedback bot ID for Slack.
  - **MAX_MESSAGE_LENGTH**: Maximum message length for Slack.
  - **INTERNAL_CHANNEL**: Internal channel for Slack bot.
  - **WORKSPACE_NAME**: Workspace name.

This setup guide should help you get started with configuring and using the GenaiBots application. If you have any questions or need further assistance, please refer to the project's documentation or contact the support team.