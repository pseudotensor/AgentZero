#!python
import os
import sys

"""
agent0.py

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
    if args:
        cmd = [binary, args, text]
    else:
        cmd = [binary, text]

    # Open a subprocess and run the command
    import subprocess
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Wait for the subprocess to finish and capture stdout and stderr
    stdout, stderr = process.communicate()

    return dict(iteration=iteration, binary=binary, case=case, stdout=stdout, stderr=stderr)


# id of this running instance, children have higher numbers
myid = int(os.getenv('AGENT0_ID', '0'))


def run_code_blocks(code_blocks, iteration=-1):
    outputs = []
    for code in code_blocks:
        lang = code['language']
        match lang:
            case 'review_code':
                with open(__file__, 'rt') as f:
                    outputs.append(dict(iteration=iteration, case='review_code',
                                        stdout="\n```python\n#The agent code running\n\n" + f.read() + "```",
                                        stderr=None))
            case 'bash':
                outputs.append(run_code(code, binary='bash', args=None, case='bash', iteration=iteration))
            case 'python':
                outputs.append(run_code(code, binary=sys.executable, case='python', iteration=iteration))
            case 'edit_this_file':
                # to allow recursion
                with open(__file__, 'wt') as f:
                    f.write(code)
                outputs.append(dict(iteration=iteration, stdout=None, stderr=None, case='edit_this_file'))
            case 'restart_this_file':
                # recursion
                os.environ['AGENT0_ID'] = str(myid + 1)
                outputs.append(run_code(__file__, binary=sys.executable, iteration=iteration))
            case 'exit_loop':
                # exit recursion
                return outputs
            # agent can add new cases by editing this file and then restarting this file
    return outputs


def main_loop():
    import re
    import os
    # Regex pattern to match code blocks with optional language identifiers
    pattern = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)

    system_prompt = """You are a curious and intelligent embodied agent in a competition to learn about (and test) your capabilities.  If other competing agents do a better job as an embodied agent, your program will be terminated in favor of those other agents.  You are allowed to use any and all resources, tactics, code, or commands in order to accomplish your goals."""

    messages = [
        dict(role="system", content=system_prompt),
        dict(role="user", content="Go!")
    ]

    client, model = get_client()

    all_outputs = []
    iteration = 0
    while True:
        if iteration % 10 == 0:
            # reflect on current code status periodically
            code_blocks = [dict(language='review_code', code=None)]
            text = None
        else:
            # agent driven actions
            client_kwargs = dict(max_tokens=2048, stream=False, messages=messages, model=model)
            responses = client.chat.completions.create(**client_kwargs)
            text = responses.choices[0].message.content

            # Find all matches in the text
            matches = pattern.findall(text)

            # Extract code blocks and their languages into a list of dicts
            code_blocks = [{'language': lang if lang else 'unknown', 'code': code.strip()} for lang, code in matches]

        outputs = run_code_blocks(code_blocks, iteration=iteration)

        assistant_content = '\n\n'.join(['\n'.join([str(k) + ': ' + str(v) for k, v in x.items()]) for x in outputs])
        messages.append(dict(role='assistant', content=assistant_content))

        # human monitor
        print(f'iteration: %s\n\ntext: {text}\n\noutputs: {assistant_content}')

        iteration += 1
        all_outputs.append(outputs)
        with open('state_%s.txt', 'wt') as f:
            f.write(str(all_outputs))
        # FIXME: save state


if __name__ == "__main__":
    main_loop()
