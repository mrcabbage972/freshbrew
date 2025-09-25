from abc import ABC, abstractmethod

from smolagents import CodeAgent


class Agent(ABC):
    @abstractmethod
    def run(self, prompt: str) -> str:
        return prompt


class SmolCodeAgentWrapper(Agent):
    def __init__(self, agent: CodeAgent):
        self.agent = agent

    def run(self, prompt: str) -> str:
        return self.agent.run(prompt)  # type: ignore
