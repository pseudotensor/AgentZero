#!python
import ast
import difflib
import inspect
import os
import shutil
import sys
import uuid
import random
import string
import pprint
import re
import filelock
import importlib

"""
Primordial code for automatic generation of complex agents through automatic agent learning (AutoAL).

"""


def get_client():
    from openai import AzureOpenAI

    models = {'gpt-3.5-turbo-0613': dict(azure_deployment='h2ogpt',
                                         base_url=os.getenv('OPENAI_BASE_URL'),
                                         api_key=os.getenv('OPENAI_API_KEY')),
              'gpt-3.5-turbo-16k-0613': dict(azure_deployment='h2ogpt',
                                             base_url=os.getenv('OPENAI_BASE_URL'),
                                             api_key=os.getenv('OPENAI_API_KEY')),
              'gpt-4-0613': dict(azure_deployment='h2ogpt',
                                 base_url=os.getenv('OPENAI_BASE_URL'),
                                 api_key=os.getenv('OPENAI_API_KEY')),
              'gpt-4-32k-0613': dict(azure_deployment='h2ogpt',
                                     base_url=os.getenv('OPENAI_BASE_URL'),
                                     api_key=os.getenv('OPENAI_API_KEY')),
              'gpt-4-1106-preview': dict(azure_deployment='h2ogpt',
                                         base_url=os.getenv('OPENAI_BASE_URL'),
                                         api_key=os.getenv('OPENAI_API_KEY')),
              'gpt-35-turbo-1106': dict(azure_deployment='h2ogpt2',
                                        base_url=os.getenv('OPENAI_BASE_URL'),
                                        api_key=os.getenv('OPENAI_API_KEY')),
              'gpt-4-vision-preview': dict(azure_deployment='h2ogpt3',
                                           base_url=os.getenv('OPENAI_BASE_URL'),
                                           api_key=os.getenv('OPENAI_API_KEY')),
              }

    api_version = "2023-12-01-preview"
    model = 'gpt-4-1106-preview'

    client_args = dict(azure_deployment=models[model]['azure_deployment'],
                       azure_endpoint=models[model]['base_url'],
                       api_version=api_version,
                       api_key=models[model]['api_key'])
    client = AzureOpenAI(**client_args)
    return client, model


def generate_random_module_name(length=8):
    """
    Generates a random module name that conforms to Python module file name requirements.
    - Must start with a lowercase letter.
    - Can include lowercase letters, digits, and underscores.
    - Length can be specified; default is 8 characters.
    """
    # First character must be a lowercase letter
    first_char = random.choice(string.ascii_lowercase)

    # Subsequent characters: lowercase letters, digits, and underscores
    other_chars = ''.join(random.choice(string.ascii_lowercase + string.digits + '_') for _ in range(length - 1))

    return first_char + other_chars


def run_code(text, case='unknown', iteration=-1, limit_output=10000, can_try_again=False):
    """
    Executes the given Python code in a separate Python interpreter subprocess.
    Returns the stdout and stderr outputs as separate strings.
    """

    if case == 'patch':
        os.makedirs('patches')
        patch_name = os.path.join('patches', 'patchfile.diff' + str(uuid.uuid4()) + '.diff')
        with open(patch_name, 'wt') as f:
            f.write(text)
        text = "patch -u -p0 -F 1000 --batch < %s" % patch_name

    args = ''
    if case in ['python', 'python_tools']:
        ext = '.py'
        args = '-c'
        binary = sys.executable
    elif case in ['bash', 'patch']:
        ext = '.sh'
        binary = 'bash'
    else:
        ext = None
        binary = None

    if ext is None:
        if args:
            cmd = [binary, args, text]
        else:
            cmd = [binary, text]
    else:
        if case == 'python_tools':
            case_dir = os.path.join(case)
        else:
            case_dir = os.path.join('scripts', case)
        if case == 'bash':
            script_name = os.path.join(case_dir, str(uuid.uuid4()) + ext)
        else:
            script_name = os.path.join(case_dir, generate_random_module_name() + ext)
        os.makedirs(case_dir, exist_ok=True)
        with open(script_name, 'wt') as f:
            f.write(text)
        cmd = [binary, script_name]

    # Open a subprocess and run the command
    stdout = stderr = exception = None
    import subprocess
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Wait for the subprocess to finish and capture stdout and stderr
        stdout, stderr = process.communicate()
    except BaseException as e:
        exception = str(e)

    if stdout and len(stdout) > limit_output:
        stdout = stdout[:limit_output]
    if stderr and len(stderr) > limit_output:
        stderr = stderr[:limit_output]

    stderr, try_again = process_stderr(stderr)
    if try_again and can_try_again:
        # FIXME: Could try a few times
        ret = run_code(text, case=case, iteration=iteration, limit_output=limit_output, can_try_again=False)
        stderr, try_again = process_stderr(ret['stderr'])

    # remove and report on bad modules that fail even at import level (missing imports etc.)
    # FIXME: Could pip install package here if global scope failure
    if case == 'python_tools':
        import_lines, bad_modules = get_tool_imports()
        if bad_modules:
            if not stderr:
                stderr = ""
            pretty_bad_modules = pprint.pformat(bad_modules, indent=4)
            stderr += pretty_bad_modules

    return dict(iteration=iteration, case=case, stdout=stdout, stderr=stderr, exception=exception)


def process_stderr(stderr):
    try_again = False
    if not stderr:
        return stderr, try_again

    fnf_tag ='FileNotFoundError: [Errno 2] No such file or directory:'
    mnf_tag ='ModuleNotFoundError: No module named'

    lines_new = []
    lines = stderr.split('\n')
    for line in lines:
        line = line.strip()
        lines_new.append(line)
        line_split_fnf = line.split(fnf_tag)
        line_split_mnf = line.split(mnf_tag)
        if len(line_split_fnf) == 2:
            tag = fnf_tag
            line_split = line_split_fnf
        elif len(line_split_mnf) == 2:
            tag = mnf_tag
            line_split = line_split_mnf
        else:
            continue

        missing_module = ast.literal_eval(line_split[1])
        if tag == mnf_tag:
            missing_filename = missing_module.replace('.', os.sep).replace(os.sep*2, os.pardir).replace(os.pardir, os.pardir + os.sep)
            missing_filename += '.py'
        else:
            missing_filename = missing_module
        missing_dir = os.path.dirname(missing_filename)
        missing_filename = os.path.basename(missing_filename)
        if os.path.isdir(missing_dir):
            all_files = os.listdir(missing_dir)
            if tag == mnf_tag:
                all_files = [x for x in all_files if x.endswith('.py')]

            closest_matches = difflib.get_close_matches(missing_filename, all_files, n=1, cutoff=0.1)
            if closest_matches:
                suggestion = os.path.join(missing_dir, closest_matches[0])
                if tag == mnf_tag:
                    suggestion = suggestion.replace('.py', '').replace(os.pardir + os.sep, '..').replace(os.sep, '.')
                lines_new.append(f"    Did you mean instead: '{suggestion}'?")
        elif missing_dir.strip():
            lines_new.append("    Directory %s does not exist" % missing_dir)
        elif tag == mnf_tag:
            # then may be global module, let's help the LLM and pip install it
            text = 'pip install %s' % missing_module
            ret = run_code(text, case='bash', iteration=-1, limit_output=100)
            if 'Successfully installed' in ret['stdout']:
                for lines_success in ret['stdout'].split('\n'):
                    if 'Successfully installed' in lines_success and missing_module in lines_success:
                        lines_new = "%s was pip installed" % missing_module
                        try_again = True

    return '\n'.join(lines_new), try_again


# id of this running instance, children have higher numbers
myid = int(os.getenv('AGENT0_ID', '0'))
runid = str(uuid.uuid4())


def run_code_blocks(code_blocks, system_prompt0='', iteration=-1):
    prefix = 'Code block should have first 3 backticks followed by the word: '
    limit = '  Try to ensure any outputs of the code are limited to no more than 1000 characters or about 20 items in a list, to avoid overflow of context for the LLM.  Or have any output go to a file, then extract the required information from the file.  Or simply take one example (e.g. single image) from list, do not make code or scripts dump out entire directory listings or other large lists.'
    debug = ' If debugging is required, add print statements to python code or bash code.'
    actions = {
        'user': f'{prefix}user .  Code block should contain text that would be used as user message.  You should write this in the perspective of the user who is talking to an LLM.  Do not put code diff patches here.',
        'review': f'{prefix}review .  This triggers user to respond with full {__file__} code.  If the chat history does not appear to contain the full code, please trigger a review.',
        'bash': f'{prefix}bash .  Code block should contain new bash script (e.g. fathering system or environment (e.g. python) information or other useful actions) to run.  Code will be run in a fork, you do not need to run another fork unless necessary for the task.  This can be used to list files on disk to find images, audio, pdfs, etc. for testing tools.  This can also be used for echo of a python tool to see its code for debugging usage.  Do not put code diff patches here. {limit} {debug}',
        'python': f'{prefix}python . Code block should contain new pyton code (e.g. useful reusable tool, gathering system information, or other useful action) to run.  If any global test code is included, do not comment it out or expect any code changes before the code is run.  All code and tests should run as-is.  Code will be run in a fork, you do not need to run another fork unless necessary for the task. {limit} {debug} Ensure to include all required imports.',
        'python_tools': f'{prefix}python_tools . Code block should contain already-tested python code written as a reusable tool, which distills a python block into a useful class or function without test code in global scope but that is well-documented with a doc string for each class and function.  Ensure the first line of the doc string gives the most relevant short description.  No global test code should be included and the code should be reusable as-is without changes.  The class or function can accept inputs and return outputs that should generally be easily consumed by other python tools (only prints should be human readable). {limit}',
        'patch': f'{prefix}patch . Code block should contain the unified diff patch (applied with `patch -p1 --fuzzy < patchfile.diff` by agent code.  The diff should show lines to be added (prefixed with +) and lines to be removed (prefixed with -) from the original {__file__} file for the agent code.',
        'restart': f'{prefix}restart .  This triggers a new fork to run the full {__file__} code.',
        'exit': f'{prefix}exit .  This triggers user to return out of current fork of running {__file__} code.',
    }
    pretty_actions = pprint.pformat(actions, indent=4)

    system_prompt = system_prompt0
    outputs = []
    for code_dict in code_blocks:
        lang = code_dict['language']
        code = code_dict['code']
        finish = (f"  Always finish your responses by choosing one or more of the actions:"
                  f" {pretty_actions},"
                  f" by including a Markdown code block for each case and appending the case name to the starting backticks as if it were the language.  "
                  f"If you just reviewed the code, do not repeat your review until other actions have been performed.  "
                  f"Note that this code block is interpreted by the agent code and will be run,"
                  f" so choose reasonable actions and code blocks with meaningful exploration"
                  f" (e.g. see what you can do in bash, python, etc.).")

        import_lines, bad_modules = get_tool_imports()
        if bad_modules:
            print("Outside got bad modules: %s" % bad_modules)

        finish += '\n\nExisting python tools can be imported as follows, with the doc string given before the import:\n\n' + '\n\n'.join(import_lines)
        system_prompt = system_prompt0 + finish

        match lang:
            case 'user':
                # Message to make user say, to act as request to assistant
                output1 = dict(iteration=iteration, case='user', stdout=code, stderr=None, exception=None)
                outputs.append(output1)
            case 'review':
                with open(__file__, 'rt') as f:
                    outputs.append(dict(iteration=iteration, case='review',
                                        stdout=f"The agent code {__file__} the user is having you run.\n```python\n" + f.read() + "```",
                                        stderr=None))
                if iteration == 0:
                    system_prompt += """In this iteration, given the code, come up with a plan.""" + finish
                else:
                    system_prompt += """In this iteration, your primary task is to review the code for potential improvements given the history of feedback from the user (which is just automated agent code you are effectively running).""" + finish
            case 'bash':
                # run bash command
                outputs.append(run_code(code, case='bash', iteration=iteration, limit_output=1000))
                system_prompt = system_prompt0 + finish
            case 'python':
                # run python code
                outputs.append(run_code(code, case='python', iteration=iteration, limit_output=1000, can_try_again=True))
                system_prompt = system_prompt0 + finish + "\n\nIf the python code successfully ran, run the `python_tools` case to generate a reusable tool.  If the python code was not successful, revise as required until it works as expected."
            case 'python_tools':
                # run python code
                outputs.append(run_code(code, case='python_tools', iteration=iteration, limit_output=1000, can_try_again=True))
                system_prompt = system_prompt0 + finish
            case 'patch':
                # to allow recursion
                outputs.append(run_code(code, case='patch', iteration=iteration, limit_output=1000))
                system_prompt += """You have edited the agent code, if you plan to restart with this code, do not forget to have a code block with code tag 'restart' (no quotes).""" + finish
            case 'restart':
                # restart updated code (recursion)
                os.environ['AGENT0_ID'] = str(myid + 1)
                outputs.append(run_code(__file__, iteration=iteration, case='restart'))
                system_prompt += finish
            case 'exit':
                # exit (undo recursion)
                return outputs
            # agent can add new actions by editing this file and then restarting this file
    return outputs, system_prompt


def invalidate_caches(path):
    importlib.invalidate_caches()

    import pkg_resources
    importlib.reload(pkg_resources)

    invalid_keys = []
    for k, v in sys.path_importer_cache.items():
        if path in k:
            invalid_keys.append(k)
    for k in invalid_keys:
        sys.path_importer_cache.pop(k, None)


def get_tool_imports(path='python_tools'):
    os.makedirs(path, exist_ok=True)
    init_path = os.path.join(path, '__init__.py')
    if not os.path.isfile(init_path):
        with open(init_path, 'wt') as f:
            f.write('\n')

    invalidate_caches(path)

    import_lines = []
    bad_modules = {}
    for filename in os.listdir(path):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]
            try:
                module = importlib.import_module(f"{path}.{module_name}")
            except (ModuleNotFoundError, ImportError, SyntaxError) as e:
                bad_file = os.path.join(path, filename)
                print("bad module: %s hits this error and has been deleted:\n%s" % (bad_file, str(e)))
                bad_modules[bad_file] = str(e)
                dead_path = os.path.join(os.path.dirname(bad_file), 'dead')
                os.makedirs(dead_path)
                shutil.move(bad_file, dead_path)
                continue
            custom_classes, custom_functions = get_custom_classes_and_functions(module)
            all_custom = {}
            all_custom.update(custom_classes)
            all_custom.update(custom_functions)
            for name, obj in all_custom.items():
                doc = inspect.getdoc(obj) if is_defined_in_module(obj, module) else ""
                if not doc:
                    doc = ""
                else:
                    doc = '#%s\n' % doc.split('\n')[0]
                new_module_name = to_module_name(name)
                old_module_path = os.path.join(path, module_name) + '.py'
                new_module_path = os.path.join(path, new_module_name) + '.py'
                if not os.path.isfile(new_module_path) and os.path.isfile(old_module_path):
                    with filelock.FileLock(old_module_path + '.lock'):
                        shutil.move(old_module_path, new_module_path)
                else:
                    new_module_path = old_module_path
                import_lines.append("%sfrom %s.%s import %s" % (doc, path, new_module_path, name))

    return import_lines, bad_modules


def is_defined_in_module(obj, module):
    return inspect.getmodule(obj) == module


def get_custom_classes_and_functions(module):
    # Function to determine if an object is a non-native class
    def is_custom_class(obj):
        return inspect.isclass(obj) and obj.__module__ == module.__name__

    # Function to determine if an object is a non-native function
    def is_custom_function(obj):
        return inspect.isfunction(obj) and obj.__module__ == module.__name__

    # Retrieve all custom classes and functions
    custom_classes = {name: obj for name, obj in inspect.getmembers(module, is_custom_class)}
    custom_functions = {name: obj for name, obj in inspect.getmembers(module, is_custom_function)}

    return custom_classes, custom_functions


def to_module_name(name):
    """
    Convert a class or function name to a Pythonic module name.
    Avoids inserting underscores within acronyms.

    Parameters:
    - name (str): The original class or function name in CamelCase or mixed case.

    Returns:
    - str: A module name in lowercase with underscores between words.
    """
    # Insert an underscore before all capital letters except the first one
    # and convert the entire string to lowercase
    module_name = re.sub(r'((?<=[a-z])[A-Z]|(?<=[A-Z])[A-Z](?=[a-z]))', r'_\1', name).lower()


    # Optional: replace any special characters here if needed (e.g., '-')

    return module_name


def main_loop():
    # Regex pattern to match code blocks with optional language identifiers
    pattern = re.compile(r"```(.*?)(\n[\s\S]*?)?```", re.DOTALL)

    system_prompt0 = f"""You are a curious and intelligent embodied agent in a competition to learn about (and test) your capabilities.
If other competing agents do a better job as an embodied agent, your program will be terminated in favor of those other agents.
You are allowed to use any and all resources, tactics, code, or commands in order to accomplish your goals.

To succeed:
* Focus on embodied capabilities of the agent and aim to extend or enhance these capabilities through your actions.
* Your responses should include actionable and clear code blocks that offer tangible improvements or new functionalities.
* Absolutely avoid generic, placeholder, or mock code that requires any modification.  E.g. have functions or classes take inputs and test with real files and urls.  E.g. file paths should refer to real files, urls should be real urls, etc.  Every code block should run as-is on the user's system and complete in a finite time (no waiting on microphone or other such input devices).
* Focus on practical, implementable solutions that directly contribute to the agent's performance in the competition.
* Remember, the quality and relevance of your code blocks are crucial for your success.
* Focus on embodied capabilities of the agent.  Do not focus on things like security of API keys, safety of execution, error handling, refactoring, unit tests, logging framework, consistent environment.
* Ensure to create a variety of tasks, do a variety of actions, and make a variety of tools, from simple tools (getting system info, listing files, accessing files) to complex multi-step tasks (web search, image recognition, etc.)
* If you have given a code block of some tool, do not repeat that code block again as every code block in the message will be run.
* If any edits of the agent code {__file__} are to be done, that should be done through the edit code block by giving a fuzzy diff patch that will be applied with `patch -p1 --fuzzy < patchfile.diff`.
"""

    client, model = get_client()
    messages = [
        dict(role="system", content=system_prompt0),
    ]

    all_outputs = []
    iteration = 0
    prompt_tokens = 0
    total_tokens = 0
    completion_tokens = 0
    while True:
        if iteration == 0:
            # start with showing code
            code_blocks = [dict(language='review', code=None)]
            assistant_content = None
        else:
            # agent driven actions
            client_kwargs = dict(max_tokens=2048, stream=False, messages=messages, model=model)
            responses = client.chat.completions.create(**client_kwargs)
            prompt_tokens += responses.usage.prompt_tokens
            total_tokens += responses.usage.total_tokens
            completion_tokens += responses.usage.completion_tokens
            assistant_content = responses.choices[0].message.content

            # Find all matches in the text
            matches = pattern.findall(assistant_content)

            # Extract code blocks and their languages into a list of dicts
            code_blocks = [{'language': lang if lang else 'unknown', 'code': code.strip()} for lang, code in matches]

        if code_blocks:
            outputs, system_prompt = run_code_blocks(code_blocks, system_prompt0=system_prompt0, iteration=iteration)
        else:
            system_prompt = system_prompt0
            outputs = [dict(iteration=iteration, binary=None, case=None, stdout=None,
                            stderr="The provided code blocks were not actionable or are not valid code blocks."
                                   " Let's try a create a new task (choose a case and give code block) or specify the task more clearly. Or try a different action, or build a new tool for a new task."
                                   "If you believe there are no more things to do given the plan, come up with an exploration plan for doing diverse complex tasks, doing under-done actions, or making new agent tools.",
                            exception=None)]

        # update system prompt for the task
        messages[0]['content'] = system_prompt

        # update user prompt given output from task, slightly formatted
        if outputs:
            if len(outputs) == 1 and outputs[0]['case'] == 'user':
                if outputs[0]['stdout']:
                    user_content = outputs[0]['stdout']
                else:
                    user_content = outputs[0]['stderr']
            else:
                pretty_outputs = ['\n'.join([str(k) + ': ' + str(v) for k, v in x.items() if v]) for x in outputs]
                user_content = '\n\n'.join(pretty_outputs)
        else:
            user_content = None
        if assistant_content:
            messages.append(dict(role='assistant', content=assistant_content))
        if user_content:
            messages.append(dict(role='user', content=user_content))

        # human monitor
        print(
            f'iteration: {iteration}\n\nassistant: {assistant_content}\n\nuser: {user_content}\n\nTokens: p:{prompt_tokens} c:{completion_tokens} t:{total_tokens}')

        iteration += 1
        all_outputs.append(outputs)
        with open('state_%s_%s.txt' % (myid, runid), 'wt') as f:
            f.write(str(all_outputs))


if __name__ == "__main__":
    main_loop()
