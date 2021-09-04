import subprocess
import time
import sys

if __name__ == '__main__':

    try:
        subprocess.run(
            ['tar', '-czvf', 'submission.tar.gz',
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
