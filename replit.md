# Overview

This is a Mastra-based agentic automation framework built on Replit. Mastra is a TypeScript framework for building AI-powered applications with agents, tools, and workflows. The project supports both time-based (cron) and webhook-based triggers to orchestrate AI automations.

The repository includes a legacy Python implementation (PayLog AI) for expense tracking via Telegram, alongside the main TypeScript Mastra implementation.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Framework: Mastra

**Purpose**: Mastra serves as the foundational framework for building AI agents and workflows with durability, observability, and multi-step orchestration.

**Design Pattern**: The architecture follows a modular, event-driven pattern where:
- **Agents** handle LLM reasoning and tool execution
- **Workflows** orchestrate deterministic multi-step processes
- **Tools** extend agent capabilities with external APIs and custom logic
- **Triggers** activate workflows via cron schedules or webhooks

**Key Architectural Decisions**:
- Uses Inngest for durable workflow execution and step memoization
- Separates concerns between agents (non-deterministic) and workflows (deterministic)
- Employs a two-tier memory scoping system (thread-scoped and resource-scoped)
- Supports suspend/resume patterns for human-in-the-loop interactions

## Agent System

**Architecture**: Agents use LLMs with tool calling capabilities to solve open-ended tasks. They reason about goals, decide which tools to use, and maintain conversation memory.

**Memory Management**:
- **Working Memory**: Persistent user data and preferences stored as structured Markdown or Zod schemas
- **Conversation History**: Recent messages (default: last 10) from current thread
- **Semantic Recall**: RAG-based vector search for retrieving relevant past conversations

**Model Routing**: Supports 600+ models through unified interface (OpenAI, Anthropic, Gemini, etc.) with automatic API key detection.

**Guardrails**: Input/output processors for content moderation, prompt injection prevention, and response sanitization.

## Workflow Orchestration

**Pattern**: Graph-based workflow engine with explicit step definitions and data flow control.

**Control Flow Primitives**:
- `.then()`: Sequential execution
- `.parallel()`: Concurrent execution
- `.branch()`: Conditional branching
- `.map()`: Data transformation between steps
- `.dountil()`: Loop until condition met

**Durability**: Inngest provides step-level memoization, retry logic, and snapshot-based suspend/resume. Workflows can pause for human approval or external resources, then resume from exact state.

**Error Handling**: Configurable retries at workflow or step level with exponential backoff.

## Trigger System

**Time-Based (Cron)**: Standard 5-field cron expressions registered via `registerCronTrigger()`. Triggers fire workflows without external input.

**Webhook-Based**: HTTP endpoints created via `registerApiRoute()` that forward payloads to workflows. Examples include:
- Slack message events
- Telegram bot updates  
- Linear issue webhooks
- Custom connector integrations

**Routing Flow**:
1. External service → Webhook endpoint
2. Inngest event (`event/api.webhooks.{provider}.action`)
3. Forwarding function validates payload
4. Workflow starts with `workflow.createRunAsync()` and `run.start()`

## Data Storage

**Storage Adapters**: Pluggable storage via `@mastra/libsql`, `@mastra/pg`, or `@mastra/upstash` for:
- Conversation threads and messages
- Working memory persistence
- Workflow snapshots (for suspend/resume)
- Vector embeddings (for semantic recall)

**Database Flexibility**: While the codebase references PostgreSQL adapters (`@mastra/pg`), it primarily uses LibSQL for in-memory or file-based storage during development. The system is designed to support multiple backends interchangeably.

## Playground UI

**Replit-Specific**: Custom Mastra Playground UI for Replit environment (user-facing only, not accessible to code agents).

**Features**:
- Chat interface for testing agent interactions
- Workflow graph visualization with plain English node descriptions
- Real-time SSE connection for hot reloading

**Important Constraints**:
- Requires `generateLegacy()` for backwards compatibility (not AI SDK v5)
- All workflow nodes must have clear descriptions for visual graph

## Legacy Python Implementation

**PayLog AI**: Telegram-based expense tracking bot with multi-agent capabilities (Parser, Analyst, Advisor, Query agents).

**Architecture**:
- Google Sheets integration for data persistence
- Multi-provider LLM support (Google AI, Groq, OpenRouter)
- Pandas-based analytics and goal tracking
- HTTP health check server for deployment

**Status**: Separate from main Mastra implementation; included for reference.

# External Dependencies

## AI/ML Services

- **AI SDK (Vercel)**: Model abstraction layer (`ai` package, `@ai-sdk/openai`)
- **OpenRouter**: Multi-provider LLM routing (`@openrouter/ai-sdk-provider`)
- **OpenAI**: Primary LLM provider (requires `OPENAI_API_KEY`)
- **Anthropic**: Alternative LLM provider
- **Google AI**: Gemini models via AI Studio
- **Exa**: Search API integration (`exa-js`)

## Orchestration & Durability

- **Inngest**: Durable workflow execution with step memoization (`inngest`, `@inngest/realtime`)
- **Mastra Inngest Adapter**: Custom integration layer (`@mastra/inngest`)

## Data Storage & Vectors

- **LibSQL**: Primary development storage (`@mastra/libsql`)
- **PostgreSQL**: Production storage option (`@mastra/pg`, `@types/pg`)
- **Upstash**: Redis and vector storage alternative (`@mastra/upstash` - inferred from memory docs)
- **pgvector**: PostgreSQL extension for vector embeddings (when using Postgres)

## Communication Platforms

- **Slack**: Webhook and API integration (`@slack/web-api`)
- **Telegram**: Bot API (Python implementation only)
- **WhatsApp**: Business API (referenced in examples)

## Development Tools

- **TypeScript**: Core language (`typescript`, `ts-node`, `tsx`)
- **Zod**: Schema validation (`zod`)
- **Pino**: Structured logging (`pino`)
- **Prettier**: Code formatting
- **dotenv**: Environment variable management

## Python Dependencies (Legacy)

- **python-telegram-bot**: Telegram bot framework
- **gspread**: Google Sheets API client
- **pandas**: Data analytics
- **requests**: HTTP client

## Infrastructure

- **Node.js**: >=20.9.0 required
- **Mastra CLI**: Project scaffolding and dev server (`mastra`)
- **Replit**: Deployment platform with custom integrations