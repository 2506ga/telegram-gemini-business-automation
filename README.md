# Telegram Gemini Business Automation

An AI-powered operations assistant for service businesses. It uses Telegram as a simple input channel and Gemini to organize operational information into structured, actionable insights.

## The Problem

Businesses often receive critical daily information through scattered messages: sales, reservations, expenses, purchases, payments, and operational updates. This makes reporting slow, inconsistent, and difficult to audit.

## Solution

This MVP centralizes operational updates sent through Telegram and uses generative AI to interpret, classify, and summarize the information. The goal is to reduce manual reporting and give managers clearer visibility into daily business performance.

## Key Capabilities

- Receive business updates through Telegram
- Process natural-language messages with Gemini
- Classify information by operational category
- Extract relevant data from unstructured messages
- Generate structured summaries and management insights
- Support reporting for multiple business units, such as bar, events, and catering
- Provide a management-oriented interface for reviewing submitted information

## Example Use Cases

- Record daily sales and collections
- Track reservations and confirmed payments
- Register purchases, expenses, and refunds
- Consolidate business-unit updates into a daily report
- Identify missing information before closing the day

## Project Status

This repository represents an MVP designed to validate the workflow and user experience before a production deployment.

## Architecture

```text
Team member
    ↓ Telegram message
Telegram Bot
    ↓
Gemini API
    ↓
Structured operational data
    ↓
Management dashboard and reports
```

## Security Notes

- Never commit API keys, Telegram tokens, passwords, or real business data.
- Use environment variables for credentials.
- Use anonymized or sample data when demonstrating the application.

## Author

**Gabriel Coronel**  
AI Solutions Engineer & Automation Lead

- Portfolio: [gabrielcoronel.netlify.app](https://gabrielcoronel.netlify.app)
- LinkedIn: [linkedin.com/in/gycoronel](https://www.linkedin.com/in/gycoronel)
