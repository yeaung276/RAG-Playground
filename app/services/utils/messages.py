from langchain_core.messages import BaseMessage


def thinking(message: BaseMessage) -> str:
    if not isinstance(message.content, list):
        return ""
    return "".join(
        block.get("thinking", "")
        for block in message.content
        if isinstance(block, dict) and block.get("type") == "thinking"
    )
