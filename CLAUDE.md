# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based RSS to Mastodon bot that automatically posts security news from RSS feeds to Mastodon. The bot runs on a schedule via GitHub Actions and posts to multiple Mastodon instances.

## Core Architecture

The application consists of:
- `rss-reader.py` - Main application logic with RSS parsing and Mastodon posting
- `config.yaml` - Configuration file defining RSS feeds organized by section
- `requirements.txt` - Python dependencies
- GitHub Actions workflow for scheduled execution

## Key Components

### Main Script (`rss-reader.py`)
- `RSSReader` - Handles RSS feed fetching with retry logic and robust error handling
- `MastodonClient` - Manages Mastodon API interactions with authentication and rate limiting
- `MessageFormatter` - Formats individual posts and digest messages with emoji support
- `RSSMastodonBot` - Main orchestration class with in-memory deduplication and configuration management
- `FeedItem` - Data class representing processed RSS items

### Configuration Structure
The `config.yaml` file organizes RSS feeds by section (e.g., "security"). Each section maps to a Mastodon account via environment variables:
- `{section}_ENDPOINT` - Mastodon instance URL
- `{section}_ACCESS_TOKEN` - Authentication token

### Posting Logic
- Posts individual items if fewer than 5 new items
- Creates digest posts with HTML links if 5+ items
- Checks last post timestamp to avoid duplicates
- Limits posts to 10,000 characters

## Common Commands

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run in test mode (prints messages without posting)
python rss-reader.py test

# Run normally
python rss-reader.py
```

### Environment Setup
Required environment variables for each config section:
- `{section}_ENDPOINT` - Mastodon instance URL
- `{section}_ACCESS_TOKEN` - Access token from Mastodon app

### GitHub Actions
The bot runs automatically every 4 hours via scheduled GitHub Actions workflow. Manual runs can be triggered via workflow_dispatch.

## Development Notes

- The application uses a class-based architecture for better maintainability
- RSS feeds have retry logic with exponential backoff for resilience
- In-memory deduplication prevents duplicate posts within the same run
- Enhanced message formatting with emoji support and smart truncation
- Robust error handling with detailed logging throughout the pipeline
- Environment variable configuration for digest thresholds and fallback timeframes
- Posts are rate-limited to avoid overwhelming Mastodon APIs

### New Environment Variables
- `RSS_DIGEST_THRESHOLD` - Number of items before switching to digest format (default: 5)
- `RSS_FALLBACK_HOURS` - Hours to look back when no previous posts exist (default: 6)

## Security Considerations

- Access tokens are stored as GitHub secrets
- The `_run.sh` file contains hardcoded tokens and should not be used in production
- Use environment variables or `.env` files for local development