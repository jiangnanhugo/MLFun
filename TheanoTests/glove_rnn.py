# Baseline / first draft heavily inspired by
# https://github.com/laurent-dinh/dl_tutorials/blob/master/part_4_rnn/imdb_main.py


# PassageGatedRecurrent: 53 seconds
# CustomBlocksGatedRecurrent: 411 seconds
# vanillaBlocksGatedRecurrent: 539 seconds
# MyPortOfPassageToBlocks: 363 -- c linker 361
# Direct passage with params: 445
# NoOtherthings, c linker 357

import ipdb
import theano
print "done import"
from theano import tensor as T
import numpy as np


from blocks.initialization import Uniform, Constant, IsotropicGaussian, NdarrayInitialization, Identity, Orthogonal
from blocks.bricks.recurrent import LSTM, SimpleRecurrent, GatedRecurrent
from blocks.bricks.parallel import Fork

from blocks.bricks import Linear, Sigmoid, Tanh, Rectifier
from blocks import bricks

from blocks.extensions import Printing, Timing
from blocks.extensions.monitoring import (DataStreamMonitoring,
        TrainingDataMonitoring)

from blocks.extensions.plot import Plot

from blocks.algorithms import GradientDescent, Adam, Scale, StepClipping, CompositeRule, AdaDelta
from blocks.graph import ComputationGraph, apply_dropout
from blocks.main_loop import MainLoop
from blocks.model import Model

from cuboid.algorithms import AdaM, NAG
from cuboid.extensions import EpochProgress

from fuel.streams import DataStream, ServerDataStream
from fuel.transformers import Padding

from fuel.schemes import ShuffledScheme
from bricks import WeightedSigmoid, GatedRecurrentFull

from multiprocessing import Process
import fuel
import logging

def main():
    x = T.tensor3('features')
    #m = T.matrix('features_mask')
    y = T.imatrix('targets')

    #x = x+m.mean()*0

    embedding_size = 300
    glove_version = "glove.6B.300d.txt"
    #embedding_size = 50
    #glove_version = "vectors.6B.50d.txt"
    wstd = 0.02

    #vaguely normalize
    x = x / 3.0 - .5

    #gloveMapping = Linear(
            #input_dim = embedding_size,
            #output_dim = 128,
            #weights_init = Orthogonal(),
            #biases_init = Constant(0.0),
            #name="gloveMapping"
            #)
    #gloveMapping.initialize()
    #o = gloveMapping.apply(x)
    #o = Rectifier(name="gloveRec").apply(o)
    o = x
    input_dim = 300

    gru = GatedRecurrentFull(
            hidden_dim = input_dim,
            activation=Tanh(),
            #activation=bricks.Identity(),
            gate_activation=Sigmoid(),
            state_to_state_init=IsotropicGaussian(0.02),
            state_to_reset_init=IsotropicGaussian(0.02),
            state_to_update_init=IsotropicGaussian(0.02),
            input_to_state_transform = Linear(
                input_dim=input_dim,
                output_dim=input_dim,
                weights_init=IsotropicGaussian(0.02),
                biases_init=Constant(0.0)),
            input_to_update_transform = Linear(
                input_dim=input_dim,
                output_dim=input_dim,
                weights_init=IsotropicGaussian(0.02),
                biases_init=Constant(0.0)),
            input_to_reset_transform = Linear(
                input_dim=input_dim,
                output_dim=input_dim,
                weights_init=IsotropicGaussian(0.02),
                biases_init=Constant(0.0))
            )
    gru.initialize()
    rnn_in = o.dimshuffle(1, 0, 2)
    #rnn_in = o
    #rnn_out = gru.apply(rnn_in, mask=m.T)
    rnn_out = gru.apply(rnn_in)
    state_to_state = gru.rnn.state_to_state
    state_to_state.name = "state_to_state"
    #o = rnn_out[-1, :, :]
    o = rnn_out[-1]

    #o = rnn_out[:, -1, :]
    #o = rnn_out.mean(axis=1)

    #print rnn_last_out.eval({
        #x: np.ones((3, 101, 300), dtype=theano.config.floatX), 
        #m: np.ones((3, 101), dtype=theano.config.floatX)})
    #raw_input()
    #o = rnn_out.mean(axis=1)

    score_layer = Linear(
            input_dim = 300,
            output_dim = 1,
            weights_init = IsotropicGaussian(std=wstd),
            biases_init = Constant(0.),
            use_bias=True,
            name="linear_score")
    score_layer.initialize()
    o = score_layer.apply(o)
    probs = Sigmoid().apply(o)

    cost = - (y * T.log(probs) + (1-y) * T.log(1 - probs)).mean()
    cost.name = 'cost'
    misclassification = (y * (probs < 0.5) + (1-y) * (probs > 0.5)).mean()
    misclassification.name = 'misclassification'

    #print rnn_in.shape.eval(
            #{x : np.ones((45, 111, embedding_size), dtype=theano.config.floatX),
                #})
    #print rnn_out.shape.eval(
            #{x : np.ones((45, 111, embedding_size), dtype=theano.config.floatX),
                #m : np.ones((45, 111), dtype=theano.config.floatX)})
    #print (m).sum(axis=1).shape.eval({
                #m : np.ones((45, 111), dtype=theano.config.floatX)})
    #print (m).shape.eval({
                #m : np.ones((45, 111), dtype=theano.config.floatX)})
    #raw_input()


    # =================

    cg = ComputationGraph([cost])
    #cg = apply_dropout(cg, variables=dropout_variables, drop_prob=0.5)
    params = cg.parameters
    for p in params:
        p.name += "___" + p.tag.annotations[0].name

    algorithm = GradientDescent(
            cost = cg.outputs[0],
            params=params,
            step_rule = CompositeRule([
                StepClipping(threshold=4),
                AdaM(),
                #NAG(lr=0.1, momentum=0.9),
                #AdaDelta(),
                ])

            )

    #algorithm.initialize()
    print params
    f = theano.function([x, y], algorithm.cost)
    ipdb.set_trace()

    print "making plots"
    #theano.printing.pydotprint(algorithm.cost, outfile='unopt.png')
    theano.printing.pydotprint(f , outfile='opt.png', scan_graphs=True)
    #theano.printing.pydotprint(algorithm._function, outfile='opt.png')

main()
