# Copyright 2018, The TensorFlow Federated Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Dependency imports
from absl.testing import parameterized
import numpy as np
import tensorflow as tf

from tensorflow_federated.python.tensorflow_libs.model_compression.core import encoding_stage


class TFStyleEncodeDecodeTest(tf.test.TestCase, parameterized.TestCase):
  """Tests for `tf_style_encode` and `tf_style_decode` decorators."""

  _DEFAULT_SCOPE = 'test_variable_scope'

  def _test_encode_fn(self, default_scope):
    """Returns decorated test encode method."""
    return encoding_stage.tf_style_encode(default_scope)(
        lambda _, x, p, name: x + p['param'])

  def _test_decode_fn(self, default_scope):
    """Returns decorated test decode method."""
    return encoding_stage.tf_style_decode(default_scope)(
        lambda _, x, p, shape, name: tf.reshape(x['val'] + p['param'], shape))

  @parameterized.parameters(None, 'different_test_variable_scope')
  def test_encode_decorator(self, name):
    """Test encode decorator works as expected."""
    test_encode_fn = self._test_encode_fn(self._DEFAULT_SCOPE)
    encoded_x = self.evaluate(test_encode_fn(None, 2.5, {'param': 10.0}, name))

    # The graph should contain three nodes. The two above Python constants
    # converted to a Tensor object, and the resulting sum.
    self.assertLen(tf.get_default_graph().as_graph_def().node, 3)
    for node in tf.get_default_graph().as_graph_def().node:
      # All nodes should be enclosed in appropriate scope.
      self.assertIn(self._DEFAULT_SCOPE if name is None else name, node.name)
    # The functionality (sum) is not modified.
    self.assertEqual(12.5, encoded_x)

  def test_encode_decorator_different_graphs(self):
    """Input Tensors from different tf.Graph instances should raise an error."""
    # The test method should not actually use the input valueas, to ensure the
    # error is not raised in a different way.
    test_encode_fn = encoding_stage.tf_style_encode(self._DEFAULT_SCOPE)(
        lambda _, x, p, name: tf.constant(0.0))
    graph_1, graph_2 = tf.Graph(), tf.Graph()
    with graph_1.as_default():
      x = tf.constant(2.5)
    with graph_2.as_default():
      params = {'param': tf.constant(10.0)}
    with self.assertRaises(ValueError):
      self.evaluate(test_encode_fn(None, x, params, None))

  @parameterized.parameters(None, 'different_test_variable_scope')
  def test_decode_decorator(self, name):
    """Test decode decorator works as expected."""
    test_decode_fn = self._test_decode_fn(self._DEFAULT_SCOPE)
    decoded_x = self.evaluate(test_decode_fn(
        None,
        {'val': np.array([[1.0, 2.0], [3.0, 4.0]], np.float32)},
        {'param': 1.0},
        [4],
        name))

    # The graph should contain five nodes. The three above Python constants
    # converted to a Tensor object, the subtraction, and the final reshape.
    self.assertLen(tf.get_default_graph().as_graph_def().node, 5)
    for node in tf.get_default_graph().as_graph_def().node:
      # All nodes should be enclosed in appropriate scope.
      self.assertIn(self._DEFAULT_SCOPE if name is None else name, node.name)
    # The functionality (sum + reshape) is not modified.
    self.assertAllEqual(np.array([2.0, 3.0, 4.0, 5.0]), decoded_x)

  def test_decode_decorator_different_graphs(self):
    """Input Tensors from different tf.Graph instances should raise an error."""
    # The test method should not actually use the input valueas, to ensure the
    # error is not raised in a different way.
    test_decode_fn = encoding_stage.tf_style_decode(self._DEFAULT_SCOPE)(
        lambda _, x, p, shape, name: tf.constant(0.0))
    graph_1, graph_2 = tf.Graph(), tf.Graph()
    with graph_1.as_default():
      x = {'val': tf.constant(2.5)}
    with graph_2.as_default():
      params = {'param': tf.constant(10.0)}
    with self.assertRaises(ValueError):
      self.evaluate(test_decode_fn(None, x, params, [], None))


if __name__ == '__main__':
  tf.test.main()
