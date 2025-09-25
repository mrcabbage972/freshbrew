from java_migration.eval.agent import Agent


class DummyAgent(Agent):
    def run(self, prompt: str) -> str:
        return prompt
