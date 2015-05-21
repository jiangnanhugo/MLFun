from theano.tensor.nnet.conv import conv2d
from theano import tensor

from blocks.bricks import Initializable
from blocks.bricks.base import Brick, lazy, application
from blocks.roles import add_role, FILTER, BIAS
from blocks.utils import shared_floatx_nans

class Conv1D(Initializable):
    """Perform a 1D convolution

    Parameters
    ----------
    filter_length : int
    num_filters : int
    input_dim : int
    """

    @lazy(allocation=['filter_length', 'num_filters', 'input_dim'])
    def __init__(self, filter_length, num_filters, input_dim, **kwargs):
        super(Conv1D, self).__init__(**kwargs)

        self.filter_length = filter_length
        self.num_filters = num_filters
        self.input_dim = input_dim

    def _allocate(self):
        W = shared_floatx_nans((self.num_filters, self.input_dim,
            self.filter_length, 1), name='W')
        add_role(W, FILTER)
        self.params.append(W)

        if self.use_bias:
            b = shared_floatx_nans((self.num_filters, ), name='b')
            add_role(b, BIAS)
            self.params.append(b)

    def _initialize(self):
        W, b = self.params
        self.biases_init.initialize(b, self.rng)
        self.weights_init.initialize(W, self.rng)

    @application(inputs=['input_'], outputs=['output'])
    def apply(self, input_):
        """Perform the convolution.

        Parameters
        ----------
        input_ : :class:`~tensor.TensorVariable`
            A 3D tensor with axes batch size, sequence, features

        Returns
        -------
        output : :class: `~tensor.TensorVariable`
            A 3D tensor of filtered sequences with axes batch size, sequence,
            filter map response
        """
        W, b = self.params
        shuffled = input_.dimshuffle(0, 2, 1, 'x')

        # batch_size, num_filters, x_map, 1
        output = conv2d(
                shuffled, W,
                filter_shape=(self.num_filters, self.input_dim, self.filter_length, 1),
                border_mode='valid')

        sequence_out = output[:, :, :, 0].dimshuffle(0, 2, 1)
        return sequence_out + b.dimshuffle('x', 0)

if __name__ == "__main__":
    from blocks.initialization import Constant
    import numpy as np
    import theano
    conv = Conv1D(filter_length=5, num_filters=32, input_dim=50,
            weights_init = Constant(1.0),
            biases_init = Constant(0.2))
    conv.initialize()

    x = tensor.tensor3('input')
    output = conv.apply(x)

    output_val = output.eval({x : np.ones((3, 11, 50), dtype=theano.config.floatX)})
    print output_val.shape
