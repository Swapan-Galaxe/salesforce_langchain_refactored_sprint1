import asyncio


class BaseAgent:
    def __init__(
        self, llm=None, skill_executor=None, name=None, role=None,
        salesforce_agent=None, llm_client=None, callbacks=None, agent_key=None
    ):
        self.llm = llm_client or llm
        self.llm_client = llm_client or llm
        self.skill_executor = skill_executor
        self.name = name or self.__class__.__name__
        self.role = role or "Sales intelligence agent"
        self.salesforce_agent = salesforce_agent
        self.callbacks = callbacks or []
        self.agent_key = agent_key or self.name.lower().replace(" ", "_")
        self.conversation_history = []
        self.user_context = None
        self.execution_budget = None

    def add_to_history(self, role, content):
        self.conversation_history.append({"role": role, "content": content})

    def get_history(self, limit=None):
        return self.conversation_history[-limit:] if limit else list(self.conversation_history)

    def clear_history(self):
        self.conversation_history.clear()

    def set_request_context(self, user_context, execution_budget):
        self.user_context = user_context
        self.execution_budget = execution_budget

    def execute_skill(self, skill_name, function, **kwargs):
        if not self.skill_executor:
            raise RuntimeError("Skill executor not configured")
        return self.skill_executor.execute(
            agent_key=self.agent_key,
            skill_name=skill_name,
            function=function,
            user_context=self.user_context,
            budget=self.execution_budget,
            arguments=kwargs,
        )

    async def _call_llm_async(self, messages, temperature=0.7):
        """Run the existing OpenAI client without blocking the event loop."""
        if not self.llm_client:
            raise RuntimeError("LLM client not configured")

        loop = asyncio.get_running_loop()

        def call_llm():
            response = self.llm_client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content

        return await loop.run_in_executor(None, call_llm)
