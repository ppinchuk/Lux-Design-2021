from kaggle_environments import make
from agent import agent
from simple_agent import agent as simple_agent
from random import seed


if __name__ == '__main__':

    seed_ = 183985976  # 69420  # 562124210 # 812865753 # 759738969 # 94876192 # 69420

    conf = {
        "loglevel": 2,
        "annotations": True
    }

    if seed_ is not None:
        conf['seed'] = seed_

    env = make("lux_ai_2021", configuration=conf, debug=True)
    seed(69420)
    steps = env.run([agent, simple_agent])

