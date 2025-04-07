from dotenv import load_dotenv
from smolagents import CodeAgent, DuckDuckGoSearchTool
from smolagents.models import LiteLLMModel

from java_migration.smol_tools import ListDir, MavenTest, ReadFile, WriteFile

load_dotenv()


repo_root = "/Users/mayvic/Documents/git/springboot-jwt"
model = LiteLLMModel(model_id="gemini/gemini-1.5-pro")
tools = [DuckDuckGoSearchTool(), ReadFile(repo_root), ListDir(repo_root), MavenTest(repo_root), WriteFile(repo_root)]
agent = CodeAgent(tools=tools, model=model, max_steps=100)

result = agent.run("Upgrade the project to use JDK 17. Ensure that the build and the tests pass.")
pass
