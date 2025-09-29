#!/usr/bin/env python3
"""
Minimal HTTP proxy for ChatGPT MCP connector compatibility.
Forwards requests from ChatGPT desktop to your existing FastAPI MCP server.
"""

import asyncio
import json
import logging
from aiohttp import web, ClientSession

# Configuration
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 9000
TARGET_SERVER = "http://127.0.0.1:8000/mcp"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def proxy_mcp_request(request):
    """Forward MCP requests to the target server with full logging."""
    try:
        # Log incoming request
        body = await request.read()
        logger.info(f"Received request from ChatGPT:")
        logger.info(f"  Method: {request.method}")
        logger.info(f"  Headers: {dict(request.headers)}")
        logger.info(f"  Body: {body.decode('utf-8') if body else 'Empty'}")

        # Forward to target server
        async with ClientSession() as session:
            async with session.post(
                TARGET_SERVER,
                data=body,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            ) as response:
                response_body = await response.text()

                # Log response
                logger.info(f"Response from target server:")
                logger.info(f"  Status: {response.status}")
                logger.info(f"  Headers: {dict(response.headers)}")
                logger.info(f"  Body: {response_body}")

                # Return response to ChatGPT
                return web.Response(
                    text=response_body,
                    status=response.status,
                    content_type='application/json',
                    headers={
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'POST, OPTIONS',
                        'Access-Control-Allow-Headers': '*'
                    }
                )

    except Exception as e:
        logger.error(f"Proxy error: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": f"Proxy error: {str(e)}"},
            "id": None
        }
        return web.Response(
            text=json.dumps(error_response),
            status=500,
            content_type='application/json'
        )

async def handle_options(request):
    """Handle CORS preflight requests."""
    return web.Response(
        status=200,
        headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': '*'
        }
    )

async def health_check(request):
    """Health check endpoint."""
    return web.json_response({
        "status": "healthy",
        "proxy_port": PROXY_PORT,
        "target_server": TARGET_SERVER
    })

def create_app():
    """Create the proxy web application."""
    app = web.Application()

    # Routes
    app.router.add_post('/mcp', proxy_mcp_request)
    app.router.add_options('/mcp', handle_options)
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)  # Root endpoint

    return app

if __name__ == '__main__':
    app = create_app()
    logger.info(f"Starting ChatGPT MCP Proxy on {PROXY_HOST}:{PROXY_PORT}")
    logger.info(f"Forwarding requests to: {TARGET_SERVER}")
    logger.info(f"Use this URL in ChatGPT: http://{PROXY_HOST}:{PROXY_PORT}/mcp")

    web.run_app(app, host=PROXY_HOST, port=PROXY_PORT)