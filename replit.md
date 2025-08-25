# Overview

This project is a Telegram bot that analyzes group communication patterns using AI. The bot monitors messages in Telegram chats, caches them in memory, and provides AI-powered analysis reports when requested by chat administrators. The system uses OpenAI's GPT-5 model to analyze communication patterns, sentiment, and provide insights about group dynamics.

# Recent Changes

## August 25, 2025
- Added `/analyze_user_all` command for cross-chat user analysis
- Implemented new MessageCache methods for retrieving user data across all chats
- Enhanced user analysis to include statistics from multiple chat groups
- Fixed "name 'analyzer' is not defined" error in analyze_user command
- Extended `/analyze_user_all` to work in private messages with the bot
- Added support for numeric user_id in `/analyze_user_all` command

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Bot Framework Architecture
- **Telegram Integration**: Built on the aiogram framework for handling Telegram Bot API interactions
- **Asynchronous Design**: Uses Python's asyncio for non-blocking operations and efficient message handling
- **Message Processing Pipeline**: Real-time message capture → in-memory caching → AI analysis on demand

## Data Management
- **In-Memory Caching**: Uses Python deques with configurable size limits for storing recent messages per chat
- **Cross-Chat Analytics**: Supports retrieving and analyzing user data across all monitored chats
- **No Persistent Storage**: All data is stored in memory only, with automatic cleanup when cache limits are reached
- **Message Structure**: Standardized message format with chat_id, user_id, username, text, and timestamp fields
- **User Interaction Tracking**: Captures conversation contexts and user interaction patterns within and across chats

## AI Analysis Engine
- **OpenAI Integration**: Uses AsyncOpenAI client for non-blocking API calls
- **Model Configuration**: Currently configured to use GPT-4o for communication analysis
- **Analysis Pipeline**: Formats cached messages → creates analysis prompts → processes AI responses → returns formatted reports

## Security and Access Control
- **Authorized User System**: Analysis commands restricted to pre-configured authorized users only
- **Main Admin Role**: First user in authorized list has full management rights (add/remove users)
- **Rate Limiting**: Built-in rate limiting system to prevent API abuse (10 seconds between commands)
- **Permission Validation**: Real-time verification of user permissions before executing sensitive operations

## Configuration Management
- **Environment-Based Config**: All sensitive data and settings loaded from environment variables
- **Configuration Validation**: Startup validation ensures all required API keys and settings are present
- **Flexible Settings**: Configurable cache sizes, rate limits, and logging levels

# External Dependencies

## Core APIs
- **OpenAI API**: Primary AI service for communication analysis using GPT-5 model
- **Telegram Bot API**: Message handling, user interaction, and bot management via aiogram framework

## Python Libraries
- **aiogram**: Modern Telegram Bot framework for Python with async support
- **openai**: Official OpenAI Python client library
- **python-dotenv**: Environment variable management for configuration

## Development Tools
- **Logging**: Built-in Python logging for debugging and monitoring
- **Type Hints**: Python typing module for better code maintainability
- **Asyncio**: Python's asynchronous I/O framework for concurrent operations