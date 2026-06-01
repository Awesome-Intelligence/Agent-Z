"""brain.service - Brain Service CLI 入口"""

import asyncio
import argparse
import logging
from agent.service import BrainService, BrainServiceConfig
from agent.agent_loop import AgentConfig
from agent.llm import LLMFactory
from common.logging import setup_logging


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Handsome Agent Brain Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m agent.service_cli                  # Start with default config
  python -m agent.service_cli --port 8002      # Specify port
  python -m agent.service_cli --llm openai --api-key xxx  # Enable OpenAI LLM
  python -m agent.service_cli --debug          # Enable debug mode
        """
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Service listen address (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Service listen port (default: 8001)"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=10,
        help="Agent max iterations (default: 10)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Timeout in seconds (default: 60)"
    )
    parser.add_argument(
        "--llm",
        choices=["openai", "claude", "none"],
        default="none",
        help="LLM provider (default: none)"
    )
    parser.add_argument(
        "--api-key",
        help="LLM API key"
    )
    parser.add_argument(
        "--model",
        help="LLM model name"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--system-prompt",
        default="You are an intelligent assistant that helps users complete various tasks.",
        help="System prompt"
    )
    
    return parser.parse_args()


async def main():
    """Main function"""
    args = parse_args()
    
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level=log_level)
    logger = get_decision_logger(__name__)
    
    logger.info("=" * 50)
    logger.info("Handsome Agent Brain Service")
    logger.info("=" * 50)
    
    config = BrainServiceConfig(
        name="HandsomeAgentBrain",
        host=args.host,
        port=args.port,
        max_iterations=args.max_iterations,
        timeout_seconds=args.timeout,
    )
    
    brain_service = BrainService(config)
    
    if args.llm != "none" and args.api_key:
        logger.info(f"Configuring LLM Provider: {args.llm}")
        try:
            llm_provider = LLMFactory.create(
                provider=args.llm,
                api_key=args.api_key,
                model=args.model,
            )
            
            loop_config = AgentConfig(
                max_iterations=args.max_iterations,
                timeout_seconds=args.timeout,
                system_prompt=args.system_prompt,
            )
            
            brain_service._agent_loop = brain_service._agent_loop or None
            if brain_service._agent_loop:
                brain_service._agent_loop.config = loop_config
                brain_service._agent_loop.set_llm_provider(llm_provider)
            
            logger.info(f"LLM Provider configured: {args.llm}")
        except Exception as e:
            logger.warning(f"LLM Provider configuration failed: {e}")
            logger.info("Using rule-based mode")
    else:
        logger.info("LLM not configured, using rule-based mode")
    
    try:
        await brain_service.start()
        logger.info(f"Brain Service started: http://{args.host}:{args.port}")
        logger.info("Press Ctrl+C to stop service")
        
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received stop signal")
    finally:
        await brain_service.stop()
        logger.info("Brain Service stopped")


if __name__ == "__main__":
    asyncio.run(main())