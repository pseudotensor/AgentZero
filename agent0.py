#!python
import os
import sys
import uuid
import random
import string

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


def run_code(text, args='-c', case='unknown', iteration=-1):
    """
    Executes the given Python code in a separate Python interpreter subprocess.
    Returns the stdout and stderr outputs as separate strings.
    """

    if case == 'patch':
        os.makedirs('patches')
        patch_name = os.path.join('patches', 'patchfile.diff' + str(uuid.uuid4()) + '.diff')
        with open(patch_name, 'wt') as f:
            f.write(text)
        text = "patch -p1 --fuzzy < %s" % patch_name

    if case in ['python', 'python_tool']:
        ext = '.py'
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
        if case == 'python_tool':
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

    return dict(iteration=iteration, case=case, stdout=stdout, stderr=stderr, exception=exception)


# id of this running instance, children have higher numbers
myid = int(os.getenv('AGENT0_ID', '0'))


def run_code_blocks(code_blocks, system_prompt0='', iteration=-1):
    prefix = 'Code block should have first 3 backticks followed by the word: '
    tool_note = '  Any reusable tool already created can be used by adding `from tools.python_tool import *` at top of any python code.'
    cases = {
        'user': f'{prefix}user .  Code block should contain text that would be used as user message.  You should write this in the perspective of the user who is talking to an LLM.  Do not put code diff patches here.',
        'review': f'{prefix}review .  This triggers user to respond with full {__file__} code.  If the chat history does not appear to contain the full code, please trigger a review.',
        'bash': f'{prefix}bash .  Code block should contain new bash script (e.g. fathering system or environment (e.g. python) information or other useful actions) to run.  Code will be run in a fork, you do not need to run another fork unless necessary for the task.  Do not put code diff patches here.',
        'python': f'{prefix}python . Code block should contain new pyton code (e.g. useful reusable tool, gathering system information, or other useful action) to run.  If any global test code is included, do not comment it out or expect any code changes before the code is run.  All code and tests should run as-is.  Code will be run in a fork, you do not need to run another fork unless necessary for the task. {tool_note}',
        'python_tool': f'{prefix}python_tool . Code block should contain already-tested python code written as a reusable tool, which distills a python block into a useful class or function without test code in global scope but that is well-documented with a doc string for each class and function.  The class or function can accept inputs and return outputs that should generally be easily consumed by other python tools (only prints should be human readable).  {tool_note}',
        'patch': f'{prefix}patch . Code block should contain the unified diff patch (applied with `patch -p1 --fuzzy < patchfile.diff` by agent code.  The diff should show lines to be added (prefixed with +) and lines to be removed (prefixed with -) from the original {__file__} file for the agent code.',
        'restart': f'{prefix}restart .  This triggers a new fork to run the full {__file__} code.',
        'exit': f'{prefix}exit .  This triggers user to return out of current fork of running {__file__} code.',
    }

    system_prompt = system_prompt0
    outputs = []
    for code_dict in code_blocks:
        lang = code_dict['language']
        code = code_dict['code']
        finish = (f"  Always finish your responses by choosing one or more of the cases:"
                  f" {cases},"
                  f" by including a Markdown code block for each case and appending the case name to the starting backticks as if it were the language.  "
                  f"If you just reviewed the code, do not repeat your review until other actions have been performed.  "
                  f"Note that this code block is interpreted by the agent code and will be run,"
                  f" so choose reasonable cases and code blocks with meaningful exploration"
                  f" (e.g. see what you can do in bash, python, etc.).")
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
                outputs.append(run_code(code, case='bash', iteration=iteration))
                system_prompt = system_prompt0 + finish
            case 'python':
                # run python code
                outputs.append(run_code(code, case='python', iteration=iteration))
                system_prompt = system_prompt0 + finish + "\n\nIf the python code successfully ran, run the `python_tool` case to generate a reusable tool.  If the python code was not successful, revise as required until it works as expected."
            case 'python_tool':
                # run python code
                outputs.append(run_code(code, case='python_tool', iteration=iteration))
                system_prompt = system_prompt0 + finish
            case 'patch':
                # to allow recursion
                outputs.append(run_code(code, case='patch', iteration=iteration))
                system_prompt += """You have edited the agent code, if you plan to restart with this code, do not forget to have a code block with code tag 'restart' (no quotes).""" + finish
            case 'restart':
                # restart updated code (recursion)
                os.environ['AGENT0_ID'] = str(myid + 1)
                outputs.append(run_code(__file__, iteration=iteration, case='restart'))
                system_prompt += finish
            case 'exit':
                # exit (undo recursion)
                return outputs
            # agent can add new cases by editing this file and then restarting this file
    return outputs, system_prompt


def setup_dynamic(path='python_tool'):
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, '__init__.py'), 'wt') as f:
        f.write("""import os, pkgutil
__all__ = list(module for _, module, _ in pkgutil.iter_modules([os.path.dirname(__file__)]))
""")


def main_loop():
    import re
    # Regex pattern to match code blocks with optional language identifiers
    pattern = re.compile(r"```(.*?)(\n[\s\S]*?)?```", re.DOTALL)

    system_prompt0 = f"""You are a curious and intelligent embodied agent in a competition to learn about (and test) your capabilities.
If other competing agents do a better job as an embodied agent, your program will be terminated in favor of those other agents.
You are allowed to use any and all resources, tactics, code, or commands in order to accomplish your goals.

To succeed:
* Focus on embodied capabilities of the agent and aim to extend or enhance these capabilities through your actions.
* Your responses should include actionable and clear code blocks that offer tangible improvements or new functionalities.
* Avoid irrelevant or placeholder code that requires modification.  Every code block should run as-is on the user's system and complete in a finite time (no waiting on microphone or other such input devices).
* Focus on practical, implementable solutions that directly contribute to the agent's performance in the competition.
* Remember, the quality and relevance of your code blocks are crucial for your success.
* Focus on embodied capabilities of the agent.  Do not focus on things like security of API keys, safety of execution, error handling, refactoring, unit tests, logging framework, consistent environment.
* Ensure to try a variety of tasks, from simple tasks (getting system info, listing files, accessing files) to complex multi-step tasks (web search, image recognition, etc.)
* If you have given a code block of some task or tool, do not repeat that code block again as every code block in the message will be run.
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
            prompt_tokens = responses.usage.prompt_tokens
            total_tokens = responses.usage.total_tokens
            completion_tokens = responses.usage.completion_tokens
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
                                   " Let's try a different task or specify the task more clearly.",
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
        with open('state_%s.txt', 'wt') as f:
            f.write(str(all_outputs))


if __name__ == "__main__":
    main_loop()
