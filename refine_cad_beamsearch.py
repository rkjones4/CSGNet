"""
This script does the post processing optimization on the programs retrieved
expression after beam search based decoding from CSGNet. So if the output expressions 
(of size test_size x beam_width) from the network are already calculated, then you can 
use this script.
"""
import argparse
import json
import os
import sys

import numpy as np

from src.utils import read_config
from src.utils.generators.shapenet_generater import Generator
from src.utils.refine import optimize_expression
from src.utils.reinforce import Reinforce

parser = argparse.ArgumentParser()
parser.add_argument("opt_exp_path", type=str, help="path to the expressions being "
                                                   "optmized")
parser.add_argument("opt_exp_save_path", type=str, help="path to the directory where "
                                                        "optmized expressions to be "
                                                        "saved.")
args = parser.parse_args()

if len(sys.argv) > 1:
    config = read_config.Config(sys.argv[1])
else:
    config = read_config.Config("config_synthetic.yml")

print(config.config)

# Load the terminals symbols of the grammar
with open("terminals.txt", "r") as file:
    unique_draw = file.readlines()
for index, e in enumerate(unique_draw):
    unique_draw[index] = e[0:-1]

test_size = 3000
max_len = 13
max_iter = 1

###############
beam_width = 10

# path to load the expressions to be optimized.
# path where results will be stored
save_optimized_exp_path = args.opt_exp_save_path

# path to load the expressions to be optimized.
expressions_to_optmize = args.opt_exp_path
os.makedirs(os.path.dirname(expressions_to_optmize), exist_ok=True)

generator = Generator()
reinforce = Reinforce(unique_draws=unique_draw)
data_set_path = "data/cad/cad.h5"

test_gen = generator.test_gen(
    batch_size=config.batch_size, path=data_set_path, if_augment=False)

target_images = []
for i in range(test_size // config.batch_size):
    data_ = next(test_gen)
    target_images.append(data_[-1, :, 0, :, :])
with open(expressions_to_optmize, "r") as file:
    Predicted_expressions = file.readlines()

# remove dollars and "\n"
for index, e in enumerate(Predicted_expressions):
    Predicted_expressions[index] = e[0:-1].split("$")[0]

print("let us start the optimization party!!")
Target_images = np.concatenate(target_images, 0)
refined_expressions = []
scores = 0
b = 0
distances = 0
beam_scores = []
for index, value in enumerate(Predicted_expressions):

    optimized_expression, score = optimize_expression(
        value,
        Target_images[index // beam_width],
        metric="chamfer",
        stack_size=max_len // 2 + 1,
        steps=max_len,
        max_iter=max_iter)
    refined_expressions.append(optimized_expression)
    beam_scores.append(score)
    if b == (beam_width - 1):
        scores += np.min(beam_scores)
        beam_scores = []
        b = 0
    else:
        b += 1
    print(
        index,
        score,
        scores / ((index + beam_width) // beam_width),
        flush=True)

print(
    "chamfer scores for max_iterm {}: ".format(max_iter),
    scores / (len(refined_expressions) // beam_width),
    flush=True)
results = {
    "chamfer scores for max_iterm {}:".format(max_iter):
        scores / (len(refined_expressions) // beam_width)
}

with open(save_optimized_exp_path +
                  "optmized_expressions_beam_{}_maxiter_{}.txt".format(
                      beam_width, max_iter), "w") as file:
    for index, value in enumerate(refined_expressions):
        file.write(value + "\n")

with open(save_optimized_exp_path + "results_beam_{}_max_iter_{}.org".format(
        beam_width, max_iter), 'w') as outfile:
    json.dump(results, outfile)