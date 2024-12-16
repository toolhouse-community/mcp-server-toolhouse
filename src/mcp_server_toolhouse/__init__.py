from . import server
import asyncio


def main():
    """Main entry point for the package."""
    asyncio.run(server.main())
