# skill.completion

Shell completion setup and diagnostics.

### Functions

| [`install_completion`](#skill.completion.install_completion)()       | Register shell completion for `skill` in the user's shell config.   |
|-----------------------------------------------------------------------------|---------------------------------------------------------------------|
| [`is_completion_registered`](#skill.completion.is_completion_registered)() | Check whether shell completion for `skill` appears to be set up.    |
| [`maybe_hint_completion`](#skill.completion.maybe_hint_completion)()    | Print a one-time hint about shell completion if it isn't set up.    |

### skill.completion.install_completion()

Register shell completion for `skill` in the user’s shell config.

Returns a status message describing what was done.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

### skill.completion.is_completion_registered()

Check whether shell completion for `skill` appears to be set up.

Looks for the `register-python-argcomplete skill` line in the
user’s shell config, or checks if argcomplete global activation is present.

* **Return type:**
  [`bool`](https://docs.python.org/3/library/functions.html#bool)

### skill.completion.maybe_hint_completion()

Print a one-time hint about shell completion if it isn’t set up.

Called on first CLI invocation. Writes a marker file so the hint
is only shown once.

* **Return type:**
  [`None`](https://docs.python.org/3/library/constants.html#None)
