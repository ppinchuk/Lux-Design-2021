import subprocess
import time
import sys

if __name__ == '__main__':

    seed = None  # 812865753 # 183985976 # 727594669 # 69420 # 759738969 # 562124210 # 94876192  # None #  69420
    save_replay = True

    timestr = time.strftime("%m_%d_%Y-%H-%M-%S")
    try:
        if seed:
            subprocess.run(
                ['lux-ai-2021', f'--seed={seed}', 'dev\\main.py', 'mediocre\\main.py']
                # ['lux-ai-2021', f'--seed={seed}', 'dev\\main.py', 'simple\\main.py']
                + ([f'--out=C:\\Users\\Paul\\OneDrive\\LuxAIReplays\\replay_{timestr}-{seed}.json'] if save_replay else []),
                cwd='C:\\Users\\Paul\\PycharmProjects\\Lux-Design-2021\\kits\\python',
                shell=True
            )
        else:
            subprocess.run(
                ['lux-ai-2021', 'dev\\main.py', 'mediocre\\main.py']
                + ([f'--out=C:\\Users\\Paul\\OneDrive\\LuxAIReplays\\replay_{timestr}.json'] if save_replay else []),
                cwd='C:\\Users\\Paul\\PycharmProjects\\Lux-Design-2021\\kits\\python',
                shell=True
            )
    except subprocess.CalledProcessError as err:
        print(
            'Failed to run algos',
            file=sys.stderr
        )
        raise err
