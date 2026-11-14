class ToolError(Exception):
    """A user-correctable problem (ambiguous product, missing info, validation). Its message is shown to the model."""
class LLMError(Exception): pass
class LLMNotConfigured(LLMError): pass
