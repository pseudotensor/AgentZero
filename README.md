# AgentZero

Learnings:
* Model quite bad at picking the python module.  As random name or name matching class/function, picks wrong one.
  * `generate_random_module_name` is worse, so I only use temporarily and remap once can import module: `get_tool_imports`
  * I give it suggestions for what module name it may have meant: `process_stderr`
* Model quite bad at choosing files even if looked up files before
  * So have to have hints for that too: `process_stderr`
* Model sometimes confused by python vs. python_tools task
* Model never does other tasks like patch, rarely does bash.  Does review too much unless heavily prompt.
* Model often thinks it's done, have to tell it to continue.
* Model can't remember what tools it made, and anyways may start out with some tools, so provide it  class/function names and doc strings: `get_custom_classes_and_functions`

TODO:
* Have tools standardized. Need inputs/outputs as part of doc string and consumed for LLM to know what to do.
* Similar ^ to using function tools to manage tools
* `ModuleNotFoundError: No module named 'PyPDF2'` -- auto-install packages and retry

IDEAS:
* Instead of monolithic system prompt for all tasks and letting model choose task, may have to have stricter tasks with well-defined steps
  * E.g. building a tool: python (fix errors), python, etc. python_tools, python_test_tools, repeat testing tool until passes all tests.
  * E.g. editing code.  Force it to edit code, add test of that addition, then restart with that change.  If fails still, then have it fix in parent.
* Give it more information about where it is in path and suggested steps.
  * E.g. if did python, then suggest next to make a tool.
  * if did tool, suggest making test
  * if did test, suggest running the test using the tool
  * if test passes, try using multiple tools together to accomplish novel task
  * 