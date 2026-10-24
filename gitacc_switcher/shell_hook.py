"""Shell hook snippets for directory-based auto-switching.

These are opt-in: nothing in gitacc installs them automatically. A user adds
the output of `gitacc rule hook <shell>` to their shell profile, which then
calls `gitacc rule check` whenever the prompt is rendered (bash) or the
working directory changes (zsh), so the active account follows whatever
rules were registered with `gitacc rule add`.
"""

from typing import Optional

_BASH_HOOK = """\
_gitacc_hook() {
  local previous_exit_status=$?
  command gitacc rule check
  return $previous_exit_status
}
if [[ ";${PROMPT_COMMAND:-};" != *";_gitacc_hook;"* ]]; then
  PROMPT_COMMAND="_gitacc_hook${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
fi"""

_ZSH_HOOK = """\
_gitacc_hook() {
  command gitacc rule check
}
if [[ -z "${chpwd_functions[(r)_gitacc_hook]}" ]]; then
  chpwd_functions+=(_gitacc_hook)
fi
_gitacc_hook"""

_HOOKS = {
    "bash": _BASH_HOOK,
    "zsh": _ZSH_HOOK,
}


def get_hook_script(shell: str) -> Optional[str]:
    """Get the shell hook snippet for a given shell.

    Args:
        shell: Shell name ("bash" or "zsh")

    Returns:
        Hook script text, or None if the shell isn't supported
    """
    return _HOOKS.get(shell.lower())


def get_supported_shells() -> list:
    """Get the list of shells a hook script can be generated for."""
    return list(_HOOKS.keys())
