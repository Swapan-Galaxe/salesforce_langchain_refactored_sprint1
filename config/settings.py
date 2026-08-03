from pathlib import Path
import os
BASE_DIR=Path(__file__).resolve().parent.parent
USE_MOCK_DATA=os.getenv('USE_MOCK_DATA','True')=='True'
OPENAI_MODEL=os.getenv('OPENAI_MODEL','gpt-4.1')
MAX_AGENT_HOPS=4
MAX_TOOL_CALLS=8
MAX_RECORDS=100
