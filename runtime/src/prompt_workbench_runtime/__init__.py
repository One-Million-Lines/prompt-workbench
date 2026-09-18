"""Prompt Workbench portable runtime.

Load and render release bundles produced by the workbench, in any environment, with no
database, no network access and no required third-party dependencies.

    from prompt_workbench_runtime import Bundle
    bundle = Bundle.load("./release-dir", verify=True)
    request = bundle.render("extract-actions", {"email_text": "..."})
    # request.messages, request.output, request.tools, request.model, request.provenance
"""

from .bundle import Bundle, BundleError
from .canonical import canonical_json, content_digest
from .renderer import RenderedRequest, TemplateError, render_prompt, render_string

__version__ = "1.0.0"

__all__ = [
    "Bundle",
    "BundleError",
    "render_prompt",
    "render_string",
    "RenderedRequest",
    "TemplateError",
    "canonical_json",
    "content_digest",
]
