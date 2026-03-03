from jinja2 import Template

class BasePrompt:
    template: str = ""

    @classmethod
    def render(cls, **kwargs) -> str:
        return Template(cls.template).render(**kwargs)