import subprocess
import time
import sys

if __name__ == '__main__':
    timestr = time.strftime("%m_%d_%Y-%H-%M-%S")

    try:
        subprocess.run(
            ['tar', '-czvf', 'C:\\Users\\Paul\\OneDrive\\LuxAIReplays\\submission.tar.gz',
             '__init__.py', 'agent.py', 'main.py', 'lux'],
            cwd='C:\\Users\\Paul\\PycharmProjects\\Lux-Design-2021\\kits\\python\\simple',
            shell=True
        )

        subprocess.run(
            ['tar', '-czvf', f'C:\\Users\\Paul\\OneDrive\\LuxAIReplays\\past_submissions\\submission_{timestr}.tar.gz',
             '__init__.py', 'agent.py', 'main.py', 'lux'],
            cwd='C:\\Users\\Paul\\PycharmProjects\\Lux-Design-2021\\kits\\python\\simple',
            shell=True
        )

    except subprocess.CalledProcessError as err:
        print(
            'Failed to run algos',
            file=sys.stderr
        )
        raise err
