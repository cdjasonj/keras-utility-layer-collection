# Copyright (c) 2018 Roland Zimmermann
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import keras.backend as K
from keras.layers import Layer, Dense, TimeDistributed, Concatenate


class ScaledDotProductAttention(Layer):
    """
        Implementation according to:
            "Attention is all you need" by A Vaswani, N Shazeer, N Parmar (2017)

    """

    def __init__(self, return_attention=False, **kwargs):    
        self._return_attention = return_attention
        super(ScaledDotProductAttention, self).__init__(**kwargs)
    
    def compute_output_shape(self, input_shape):
        self._validate_input_shape(input_shape)
        
        return input_shape
    
    def _validate_input_shape(self, input_shape):
        if len(input_shape) != 3:
            raise ValueError("Layer received an input shape {0} but expected three inputs (Q, V, K).".format(input_shape))
        else:
            if input_shape[0][0] != input_shape[1][0] or input_shape[1][0] != input_shape[2][0]:
                raise ValueError("All three inputs (Q, V, K) have to have the same batch size; received batch sizes: {0}, {1}, {2}".format(input_shape[0][0], input_shape[1][0], input_shape[2][0]))
            if input_shape[0][1] != input_shape[1][1] or input_shape[1][1] != input_shape[2][1]:
                raise ValueError("All three inputs (Q, V, K) have to have the same length; received lengths: {0}, {1}, {2}".format(input_shape[0][0], input_shape[1][0], input_shape[2][0]))
            if input_shape[0][2] != input_shape[1][2]:
                raise ValueError("Input shapes of Q {0} and V {1} do not match.".format(input_shape[0], input_shape[1]))
    
    def build(self, input_shape):
        self._validate_input_shape(input_shape)
        
        super(ScaledDotProductAttention, self).build(input_shape)
    
    def call(self, x):
        q, k, v = x
        d_k = q.shape.as_list()[2]
        
        # in pure tensorflow:
        # weights = tf.matmul(x_batch, tf.transpose(y_batch, perm=[0, 2, 1]))
        # normalized_weights = tf.nn.softmax(weights/scaling)
        # output = tf.matmul(normalized_weights, x_batch)
        
        weights = K.batch_dot(q,  k, axes=[2, 2])
        normalized_weights = K.softmax(weights / np.sqrt(d_k))
        output = K.batch_dot(normalized_weights, v)
        
        if self._return_attention:
            return output, normalized_weights
        else:
            return output


class MultiHeadAttention(Layer):
    """
        Implementation according to:
            "Attention is all you need" by A Vaswani, N Shazeer, N Parmar (2017)

    """

    def __init__(self, h, d_k=None, d_v=None, d_model=None, activation=None, return_attention=False, **kwargs):    
        super(MultiHeadAttention, self).__init__(**kwargs)
        
        if (type(h) is not int or h < 2):
            raise ValueError("You have to set `h` to an int >= 2.")
        self._h = h
        
        if d_model and (type(d_model) is not int or d_model < 1):
                raise ValueError("You have to set `d_model` to an int >= 1.")
        self._d_model = d_model
        
        if d_k and int (type(d_k) is not int or d_k < 1):
            raise ValueError("You have to set `d_k` to an int >= 1.")
        self._d_k = d_k
        
        if d_v and (type(d_v) is not int or d_v < 1):
            raise ValueError("You have to set `d_v` to an int >= 1.")
        self._d_v = d_v
        
        self._activation = None
        self._return_attention = return_attention
    
    def compute_output_shape(self, input_shape):
        self._validate_input_shape(input_shape)
        
        return input_shape
    
    def _validate_input_shape(self, input_shape):
        if len(input_shape) != 3:
            raise ValueError("Layer received an input shape {0} but expected three inputs (Q, V, K).".format(input_shape))
        else:
            if input_shape[0][0] != input_shape[1][0] or input_shape[1][0] != input_shape[2][0]:
                raise ValueError("All three inputs (Q, V, K) have to have the same batch size; received batch sizes: {0}, {1}, {2}".format(input_shape[0][0], input_shape[1][0], input_shape[2][0]))
            if input_shape[0][1] != input_shape[1][1] or input_shape[1][1] != input_shape[2][1]:
                raise ValueError("All three inputs (Q, V, K) have to have the same length; received lengths: {0}, {1}, {2}".format(input_shape[0][0], input_shape[1][0], input_shape[2][0]))
            if input_shape[0][2] != input_shape[1][2]:
                raise ValueError("Input shapes of Q {0} and V {1} do not match.".format(input_shape[0], input_shape[1]))
    
    def build(self, input_shape):
        self._validate_input_shape(input_shape)
        
        d_k = self._d_k if self._d_k else input_shape[1][-1]
        d_model = self._d_model if self._d_model else input_shape[1][-1]
        
        self._q_layers = []
        self._k_layers = []
        self._v_layers = []
        self._sdp_layer = ScaledDotProductAttention(return_attention=self._return_attention)
    
        for _ in range(self._h):
            self._q_layers.append(
                TimeDistributed(
                    Dense(d_k, activation=self._activation, use_bias=False)
                )
            )
            self._k_layers.append(
                TimeDistributed(
                    Dense(d_k, activation=self._activation, use_bias=False)
                )
            )
            self._v_layers.append(
                TimeDistributed(
                    Dense(d_k, activation=self._activation, use_bias=False)
                )
            )
        
        self._output = TimeDistributed(Dense(d_model))
        if self._return_attention:
            self._output = Concatenate()
        
        super(MultiHeadAttention, self).build(input_shape)
    
    def call(self, x):
        q, k, v = x
        
        outputs = []
        attentions = []
        for i in range(self._h):
            qi = self._q_layers[i](q)
            ki = self._k_layers[i](q)
            vi = self._v_layers[i](q)
            
            if self._return_attention:
                output, attention = self._sdp_layer([qi, ki, vi])
                outputs.append(output)
                attentions.append(attention)
            else:
                output = self._sdp_layer([qi, ki, vi])
                outputs.append(output)
            
        concatenated_outputs = Concatenate()(outputs)
        output = self._output(concatenated_outputs)
        
        if self._return_attention:
            attention = Concatenate()(attentions)
       
        if self._return_attention:
            return output, attention
        else:
            return output        


# https://wanasit.github.io/attention-based-sequence-to-sequence-in-keras.html
# https://arxiv.org/pdf/1508.04025.pdf
class SequenceAttention(Layer):
    def __init__(self, similarity, units, kernel_initializer="glorot_uniform", **kwargs):
        super(SequenceAttention, self).__init__(**kwargs)
        if isinstance(similarity, str):
            ALLOWED_SIMILARITIES = ["additive", ]
            if similarity not in ALLOWED_SIMILARITIES:
                raise ValueError("`similarity` has to be either a callable or one of the following: {0}".format(ALLOWED_SIMILARITIES))
            else:
                self._similarity = getattr(self, "_" + similarity + "_similarity")
        elif callable(similarity):
            self._similarity = similarity
        else:
            raise ValueError("`similarity` has to be either a callable or one of the following: {0}".format(ALLOWED_SIMILARITIES))
            
        self._units = units
        self._kernel_initializer = kernel_initializer
            
    def build(self, input_shape):
        super(SequenceAttention, self).build(input_shape)
        self._validate_input_shape(input_shape)
        
        self._weights = {}
        if self._similarity == self._additive_similarity:
            self._weights["w_a"] = self.add_weight(
                name='w_a', 
                shape=(input_shape[0][-1] + input_shape[1][-1], self._units),
                initializer=self._kernel_initializer,
                trainable=True
            )
            
            self._weights["v_a"] = self.add_weight(
                name='v_a', 
                shape=(self._units, 1),
                initializer=self._kernel_initializer,
                trainable=True
            )
        self.built = True
        
    def compute_output_shape(self, input_shape):
        self._validate_input_shape(input_shape)
        
        return (input_shape[0][0], input_shape[0][2])
            
    def _validate_input_shape(self, input_shape):
        if len(input_shape) != 2:
            raise ValueError("Layer received an input shape {0} but expected two inputs (source, query).".format(input_shape))
        else:
            if input_shape[0][0] != input_shape[1][0]:
                raise ValueError("Both two inputs (source, query) have to have the same batch size; received batch sizes: {0}, {1}".format(input_shape[0][0], input_shape[1][0]))
            if input_shape[0][1] != input_shape[1][1]:
                raise ValueError("Both inputs (source, query) have to have the same length; received lengths: {0}, {1}, {2}".format(input_shape[0][0], input_shape[1][0]))
        
    def call(self, x):
        source, query = x
        
        similarity = self._similarity(source, query)
        expected_similarity_shape = [source.shape.as_list()[0], source.shape.as_list()[2]]
        #if similarity.shape.as_list()[:2] != expected_similarity_shape:
        #    raise RuntimeError("The similarity function has returned a similarity with shape {0}, but expected {1}".format(similarity.shape.as_list()[:2], expected_similarity_shape))
        
        score = K.softmax(similarity)
        
        output = K.batch_dot(score, source)
        
        return output
    
    def _additive_similarity(self, source, query):
        concatenation = K.concatenate([source, query], axis=2)

        nonlinearity = K.tanh(K.dot(concatenation, self._weights["w_a"]) )

        similarity = K.dot(nonlinearity, self._weights["v_a"])
        similarity = K.squeeze(similarity, 2)
        
        return similarity