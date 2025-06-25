# Cameo Webhook Listener

A FastAPI application that listens to drchrono webhooks, verifies them, and relays the data to another URL.

## Features

- **Webhook Verification**: Handles GET requests for drchrono webhook verification using HMAC-SHA256
- **Webhook Relay**: Receives POST webhook data and forwards it to a configured destination URL
- **Error Handling**: Robust error handling with proper logging
- **Health Check**: Simple health check endpoint
- **Status Check**: Configuration status endpoint

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**
   
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and set your values:
   ```env
   WEBHOOK_SECRET_TOKEN=your-drchrono-webhook-secret-token-here
   RELAY_URL=https://your-destination-url.com/webhook
   RELAY_TIMEOUT=30
   PORT=8000
   ```

3. **Run the Application**
   ```bash
   python main.py
   ```
   
   Or using uvicorn directly:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

## API Endpoints

### GET `/`
Health check endpoint that returns the service status.

### GET `/webhook?msg=<verification_message>`
Webhook verification endpoint for drchrono. This endpoint:
- Receives a verification message via the `msg` query parameter
- Generates an HMAC-SHA256 hash using your webhook secret token
- Returns the hash as `secret_token` in the JSON response

### POST `/webhook`
Main webhook handler that:
- Receives webhook data from drchrono
- Extracts important headers (X-drchrono-event, X-drchrono-signature, X-drchrono-delivery)
- Relays the data to your configured destination URL
- Returns appropriate response to drchrono

### GET `/webhook/status`
Configuration status endpoint that shows whether your webhook is properly configured.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WEBHOOK_SECRET_TOKEN` | Your drchrono webhook secret token | `your-secret-token-here` |
| `RELAY_URL` | Destination URL to relay webhook data | `https://your-destination-url.com/webhook` |
| `RELAY_TIMEOUT` | Timeout for relay requests in seconds | `30` |
| `PORT` | Port to run the application on | `8000` |

## Webhook Data Format

When relaying webhook data, the application sends a POST request with the following structure:

```json
{
  "headers": {
    "X-drchrono-event": "event_type",
    "X-drchrono-signature": "signature",
    "X-drchrono-delivery": "delivery_id",
    "Content-Type": "application/json"
  },
  "body": {
    "receiver": "webhook_object",
    "object": "related_object_data"
  }
}
```

## Usage

1. Set up your environment variables with your drchrono webhook secret and destination URL
2. Run the application
3. Configure your drchrono webhook to point to `http://your-domain.com/webhook`
4. Use the verification endpoint to verify your webhook
5. The application will automatically relay incoming webhook data to your configured destination

## Logging

The application logs important events including:
- Webhook verification requests
- Incoming webhook events
- Relay attempts and responses
- Errors and timeouts

## Error Handling

The application handles various error scenarios:
- Relay timeouts: Returns success to drchrono but logs the timeout
- Relay failures: Returns success to drchrono but logs the error
- Verification failures: Returns 500 error for verification issues 