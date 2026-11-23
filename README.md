---
title: Always Together Backend
emoji: 🤝
colorFrom: purple
colorTo: blue
sdk: docker
pinned: true
app_port: 7860
---

# Always Together Backend 🤝

FastAPI backend for the **Always Together** chat application.

## Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Root info |
| GET | `/ping` | Keep-alive (self-pinged every 5 min) |
| GET | `/docs` | Swagger UI |
| WS | `/ws/{user_id}?token=JWT` | Real-time WebSocket |
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login |
| GET | `/auth/me` | Current user |
| GET | `/users/search?tag=@x` | Search users by tag |
| GET | `/conversations` | List conversations |
| POST | `/conversations/create` | Start conversation |
| GET | `/messages/{conv_id}` | Get messages |
| POST | `/messages/send` | Send message |
| DELETE | `/messages/{id}` | Soft-delete message |
| POST | `/messages/{id}/undo-delete` | Undo delete (24h window) |
| POST | `/messages/{id}/react` | Emoji reaction |
| GET | `/messages/{id}/translate?lang=ur` | Translate message |

## Required Secrets (HF Space Settings)
- `MONGODB_URI`
- `JWT_SECRET`
- `FCB_SERVER_KEY`
- `SPACE_URL`
