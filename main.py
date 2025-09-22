import asyncio
import hashlib
import hmac
import json
import os
from typing import Dict, Any

import httpx
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import JSONResponse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Cameo Webhook Listener", version="1.0.0")

# Configuration - these should be set as environment variables
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", "your-secret-token-here")
RELAY_URL_1 = os.getenv("RELAY_URL_1", "https://your-destination-url-1.com/webhook")
RELAY_URL_2 = os.getenv("RELAY_URL_2", "https://your-destination-url-2.com/webhook")
RELAY_URL_3 = os.getenv("RELAY_URL_3", "https://your-destination-url-3.com/webhook")
RELAY_TIMEOUT = int(os.getenv("RELAY_TIMEOUT", "30"))

# Collect all relay URLs
RELAY_URLS = [RELAY_URL_1, RELAY_URL_2, RELAY_URL_3]

@app.get("/")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "message": "Cameo Webhook Listener is running"}

@app.get("/webhook")
async def webhook_verification(msg: str = Query(..., description="Verification message from drchrono")):
    """
    Webhook verification endpoint for drchrono webhooks.
    
    This endpoint handles the GET request sent during webhook verification.
    It uses HMAC-SHA256 to hash the provided message with the secret token.
    """
    try:
        logger.info(f"Webhook verification requested with msg: {msg}")
        
        # Generate HMAC-SHA256 hash of the message using the secret token
        secret_token = hmac.new(
            WEBHOOK_SECRET_TOKEN.encode('utf-8'), 
            msg.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()
        
        logger.info("Webhook verification successful")
        
        return JSONResponse(
            status_code=200,
            content={"secret_token": secret_token}
        )
        
    except Exception as e:
        logger.error(f"Webhook verification failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Verification failed")

@app.post("/webhook")
async def webhook_handler(request: Request):
    """
    Webhook handler that receives POST requests and relays them to another URL.
    
    This endpoint:
    1. Receives webhook data from drchrono
    2. Extracts headers and body
    3. Relays the data to the configured destination URL
    4. Returns appropriate response
    """
    try:
        # Extract headers
        headers = dict(request.headers)
        
        # Log webhook details
        drchrono_event = headers.get("x-drchrono-event", "unknown")
        drchrono_signature = headers.get("x-drchrono-signature", "")
        drchrono_delivery = headers.get("x-drchrono-delivery", "")
        
        logger.info(f"Received webhook - Event: {drchrono_event}, Delivery: {drchrono_delivery}")
        
        # Get the request body
        body = await request.body()
        
        # Parse JSON body if it exists
        try:
            json_body = await request.json() if body else {}
        except json.JSONDecodeError:
            json_body = {}
            logger.warning("Failed to parse JSON body")
        
        # Prepare relay data
        relay_data = {
            "headers": {
                "X-drchrono-event": drchrono_event,
                "X-drchrono-signature": drchrono_signature,
                "X-drchrono-delivery": drchrono_delivery,
                "Content-Type": "application/json"
            },
            "body": json_body
        }
        
        # Relay the webhook data to all destination URLs
        async with httpx.AsyncClient(timeout=RELAY_TIMEOUT) as client:
            relay_results = []
            
            # Send to all relay URLs concurrently
            tasks = []
            for i, relay_url in enumerate(RELAY_URLS, 1):
                logger.info(f"Preparing to relay webhook data to URL {i}: {relay_url}")
                task = client.post(
                    relay_url,
                    json=relay_data,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "Cameo-Webhook-Relay/1.0"
                    }
                )
                tasks.append(task)
            
            # Wait for all relay requests to complete
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, response in enumerate(responses, 1):
                if isinstance(response, Exception):
                    logger.error(f"Relay to URL {i} failed: {str(response)}")
                    relay_results.append({
                        "url_index": i,
                        "url": RELAY_URLS[i-1],
                        "status": "error",
                        "error": str(response)
                    })
                else:
                    logger.info(f"Relay to URL {i} response status: {response.status_code}")
                    relay_results.append({
                        "url_index": i,
                        "url": RELAY_URLS[i-1],
                        "status": "success",
                        "status_code": response.status_code
                    })
            
            # Return success response to drchrono with all relay statuses
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Webhook received and relayed to all destinations",
                    "relay_results": relay_results,
                    "event": drchrono_event,
                    "delivery_id": drchrono_delivery
                }
            )
            
    except httpx.TimeoutException:
        logger.error(f"Timeout while relaying to one or more URLs")
        # Still return 200 to drchrono to avoid retries
        return JSONResponse(
            status_code=200,
            content={
                "status": "timeout",
                "message": "Webhook received but relay timed out"
            }
        )
        
    except httpx.RequestError as e:
        logger.error(f"Request error while relaying: {str(e)}")
        # Still return 200 to drchrono to avoid retries
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": "Webhook received but relay failed"
            }
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in webhook handler: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/webhook/status")
async def webhook_status():
    """
    Status endpoint to check webhook configuration
    """
    return {
        "webhook_secret_configured": bool(WEBHOOK_SECRET_TOKEN and WEBHOOK_SECRET_TOKEN != "your-secret-token-here"),
        "relay_urls": {
            "url_1": {
                "configured": bool(RELAY_URL_1 and RELAY_URL_1 != "https://your-destination-url-1.com/webhook"),
                "url": RELAY_URL_1
            },
            "url_2": {
                "configured": bool(RELAY_URL_2 and RELAY_URL_2 != "https://your-destination-url-2.com/webhook"),
                "url": RELAY_URL_2
            },
            "url_3": {
                "configured": bool(RELAY_URL_3 and RELAY_URL_3 != "https://your-destination-url-3.com/webhook"),
                "url": RELAY_URL_3
            }
        },
        "relay_timeout": RELAY_TIMEOUT
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port) 