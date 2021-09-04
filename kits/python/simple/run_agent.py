import subprocess
import time
import sys

if __name__ == '__main__':

    seed = 69420

    timestr = time.strftime("%m_%d_%Y-%H-%M-%S")
    try:
        if seed:
            subprocess.run(
                ['lux-ai-2021', f'--seed={seed}',
                 'main.py', 'main_simple.py',
                 f'--out=C:\\Users\\Paul\\OneDrive\\LuxAIReplays\\replay_{timestr}.json'],
                cwd='C:\\Users\\Paul\\PycharmProjects\\Lux-Design-2021\\kits\\python\\simple',
                shell=True
            )
        else:
            subprocess.run(
                ['lux-ai-2021', 'main.py', 'main_simple.py',
                 f'--out=C:\\Users\\Paul\\OneDrive\\LuxAIReplays\\replay_{timestr}.json'],
                cwd='C:\\Users\\Paul\\PycharmProjects\\Lux-Design-2021\\kits\\python\\simple',
                shell=True
            )
    except subprocess.CalledProcessError as err:
        print(
            'Failed to run algos',
            file=sys.stderr
        )
        raise err
