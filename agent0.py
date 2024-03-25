#!python
import os
import sys
import uuid

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


def run_code(text, binary=sys.executable, args='-c', case='unknown', iteration=-1):
    """
    Executes the given Python code in a separate Python interpreter subprocess.
    Returns the stdout and stderr outputs as separate strings.
    """

    if case == 'python':
        ext = '.py'
    elif case == 'bash':
        ext = '.sh'
    else:
        ext = None

    if ext is None:
        if args:
            cmd = [binary, args, text]
        else:
            cmd = [binary, text]
    else:
        os.makedirs(case, exist_ok=True)
        script_name = os.path.join(case, str(uuid.uuid4()) + ext)
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

    return dict(iteration=iteration, binary=binary, case=case, stdout=stdout, stderr=stderr, exception=exception)


# id of this running instance, children have higher numbers
myid = int(os.getenv('AGENT0_ID', '0'))


def run_code_blocks(code_blocks, system_prompt0='', iteration=-1):
    prefix = 'Code block should have first 3 backticks followed by the word: '
    cases = {'user': f'{prefix}user .  Code block should contain text that would be used as user message.  You should write this in the perspective of the user who is talking to an LLM.',
             'review': f'{prefix}review .  This triggers user to respond with full {__file__} code.',
             'bash': f'{prefix}bash .  Code block should contain new bash script (e.g. tool or other useful action) to run.',
             'python': f'{prefix}python . Code block should contain new pyton code (e.g. tool or other useful action) to run.',
             'edit': f'{prefix}edit . Code block should contain the full rewrite of the {__file__} code.',
             'restart': f'{prefix}restart .  This triggers a new fork to run the full {__file__} code.' ,
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
        system_prompt = system_prompt0
        match lang:
            case 'user':
                # Message to make user say, to act as request to assistant
                output1 = dict(iteration=iteration, binary=None, case='user', stdout=code, stderr=None, exception=None)
                outputs.append(output1)
            case 'review':
                with open(__file__, 'rt') as f:
                    outputs.append(dict(iteration=iteration, case='review',
                                        stdout=f"The agent code {__file__} the user is having you run.\n```python\n" + f.read() + "```",
                                        stderr=None))
                    if iteration == 0:
                        system_prompt += """In this iteration, given the code, come up with a plan.""" + finish
                    else:
                        system_prompt += """In this iteration, your primary task is to review the code for potential improvements given the history of feedback from the user (which is just automated agent code you are effectively running)."""  + finish
            case 'bash':
                # run bash command
                outputs.append(run_code(code, binary='bash', args=None, case='bash', iteration=iteration))
                system_prompt = system_prompt0 + finish
            case 'python':
                # run python code
                outputs.append(run_code(code, binary=sys.executable, case='python', iteration=iteration))
                system_prompt = system_prompt0 + finish
            case 'edit':
                # to allow recursion
                if code and len(code) > 5000:  # sanity check
                    with open(__file__, 'wt') as f:
                        f.write(code)
                    outputs.append(dict(iteration=iteration, stdout=None, stderr=None, case='edit'))
                    system_prompt += """You have edited the agent code, if you plan to restart with this code, do not forget to have a code block with code tag 'restart' (no quotes).""" + finish
                else:
                    outputs.append(dict(iteration=iteration, stdout=None, stderr="Invalid edit.  Edit should be an entire reproduction of the code with any additional changes included.", case='edit'))
            case 'restart':
                # restart updated code (recursion)
                os.environ['AGENT0_ID'] = str(myid + 1)
                outputs.append(run_code(__file__, binary=sys.executable, iteration=iteration, case='restart'))
                system_prompt += finish
            case 'exit':
                # exit (undo recursion)
                return outputs
            # agent can add new cases by editing this file and then restarting this file
    return outputs, system_prompt


def main_loop():
    import re
    # Regex pattern to match code blocks with optional language identifiers
    pattern = re.compile(r"```(.*?)(\n[\s\S]*?)?```", re.DOTALL)

    system_prompt0 = """You are a curious and intelligent embodied agent in a competition to learn about (and test) your capabilities.
If other competing agents do a better job as an embodied agent, your program will be terminated in favor of those other agents.
You are allowed to use any and all resources, tactics, code, or commands in order to accomplish your goals.
Focus on embodied capabilities of the agent.  Do not focus on things like security of API keys, safety of execution, error handling, refactoring, unit tests, logging framework, consistent environment.

If you are unsure what to do, explore by trying to build a tool 
"""

    client, model = get_client()
    messages = [
        dict(role="system", content=system_prompt0),
    ]

    all_outputs = []
    iteration = 0
    while True:
        if iteration % 10 == 0:
            # reflect on current code status periodically
            code_blocks = [dict(language='review', code=None)]
            assistant_content = None
        else:
            # agent driven actions
            client_kwargs = dict(max_tokens=2048, stream=False, messages=messages, model=model)
            responses = client.chat.completions.create(**client_kwargs)
            assistant_content = responses.choices[0].message.content

            # Find all matches in the text
            matches = pattern.findall(assistant_content)

            # Extract code blocks and their languages into a list of dicts
            code_blocks = [{'language': lang if lang else 'unknown', 'code': code.strip()} for lang, code in matches]

        outputs, system_prompt = run_code_blocks(code_blocks, system_prompt0=system_prompt0, iteration=iteration)

        # update system prompt for the task
        messages[0]['content'] = system_prompt

        # update user prompt given output from task, slightly formatted
        if outputs:
            if len(outputs) == 1 and outputs[0]['case'] == 'user':
                user_content = outputs[0]['stdout']
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
        print(f'iteration: {iteration}\n\nassistant: {assistant_content}\n\nuser: {user_content}')

        iteration += 1
        all_outputs.append(outputs)
        with open('state_%s.txt', 'wt') as f:
            f.write(str(all_outputs))


if __name__ == "__main__":
    main_loop()
