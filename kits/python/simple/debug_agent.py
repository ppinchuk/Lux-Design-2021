from kaggle_environments import make
from agent import agent
from simple_agent import agent as simple_agent


if __name__ == '__main__':

    seed = None  # 69420  # 562124210 # 812865753 # 759738969 # 94876192 # 69420

    conf = {
        "loglevel": 2,
        "annotations": True
    }

    if seed is not None:
        conf['seed'] = seed

    env = make("lux_ai_2021", configuration=conf, debug=True)
    steps = env.run([agent, simple_agent])

