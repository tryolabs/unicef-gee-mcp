from config import config
from dotenv import load_dotenv
from logging_config import get_logger
from mcp.server.fastmcp import FastMCP

load_dotenv(override=True)

mcp = FastMCP("GEE MCP", port=config.server.port)


logger = get_logger(__name__)


if __name__ == "__main__":
    logger.info("🚀 Starting server... ")

    logger.info(
        'Check "http://localhost:%s/%s" for the server status',
        config.server.port,
        config.server.transport,
    )

    mcp.run(config.server.transport)
