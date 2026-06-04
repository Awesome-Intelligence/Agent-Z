#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI for Handsome Agent API server.

Usage:
    python -m api.server --host 0.0.0.0 --port 8001 --api-key your-key
"""

# 🏃 Execution - 🛠️ ToolExec - API Server CLI

import argparse
import asyncio
import signal
import sys
from typing import Optional

from api.api_server import create_api_server, AIOHTTP_AVAILABLE


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Handsome Agent API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8001, help="Port to listen on")
    parser.add_argument("--api-key", default="", help="API key for authentication")
    parser.add_argument(
        "--cors-origins",
        default="",
        help="Comma-separated list of allowed CORS origins",
    )
    parser.add_argument("--model-name", default="handsome-agent", help="Model name to advertise")
    return parser.parse_args()


async def run_server(args):
    """Run the API server."""
    if not AIOHTTP_AVAILABLE:
        print("Error: aiohttp is required. Install with: pip install aiohttp")
        sys.exit(1)

    config = {
        "extra": {
            "host": args.host,
            "port": args.port,
            "key": args.api_key,
            "cors_origins": args.cors_origins,
            "model_name": args.model_name,
        }
    }

    server = create_api_server(config)

    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                  Handsome Agent API Server                      ║
║                  OpenAI-compatible Interface                   ║
╠══════════════════════════════════════════════════════════════════╣
║  URL: http://{args.host}:{args.port}                            ║
║  Auth: {'Enabled' if args.api_key else 'Disabled (local only)'}                     ║
╠══════════════════════════════════════════════════════════════════╣
║  Endpoints:                                                    
║    Health:                                                    
║      GET  /health              - Simple health check           
║      GET  /health/detailed      - Detailed status               
║                                                            
║    Models:                                                  
║      GET  /v1/models           - List available models         
║                                                            
║    Chat Completions (OpenAI compatible):                     
║      POST /v1/chat/completions - Chat completions endpoint    
║                                                            
║    Responses API (OpenAI compatible):                        
║      POST /v1/responses        - Responses endpoint           
║      GET  /v1/responses/{{id}}  - Get stored response         
║      DELETE /v1/responses/{{id}} - Delete response           
║                                                            
║    Runs:                                                    
║      POST /v1/runs            - Start a run                  
║      GET  /v1/runs/{{id}}      - Get run status              
║      GET  /v1/runs/{{id}}/events - SSE events               
║      POST /v1/runs/{{id}}/stop - Stop run                   
║                                                            
║    Capabilities:                                             
║      GET  /v1/capabilities     - API capabilities             
║                                                            
╠══════════════════════════════════════════════════════════════════╣
║  Examples:                                                    
║    curl http://{args.host}:{args.port}/health                     
║    curl http://{args.host}:{args.port}/v1/models                  
║    curl -X POST http://{args.host}:{args.port}/v1/chat/completions \\ 
║      -H "Content-Type: application/json" \\                     
║      -d '{{"model":"handsome-agent","messages":[{{"role":"user","content":"Hello"}}]}}'
╚══════════════════════════════════════════════════════════════════╝
🛑 Press Ctrl+C to stop...
""")

    stop_event = asyncio.Event()

    def signal_handler(sig, frame):
        print("\n👋 Shutting down...")
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await server.start()
        await stop_event.wait()
    finally:
        await server.stop()


def main():
    """Main entry point."""
    args = parse_args()
    try:
        asyncio.run(run_server(args))
    except KeyboardInterrupt:
        print("\n👋 Shutdown complete.")


if __name__ == "__main__":
    main()
