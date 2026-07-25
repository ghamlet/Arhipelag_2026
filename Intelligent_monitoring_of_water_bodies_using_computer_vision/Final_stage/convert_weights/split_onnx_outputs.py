import os
import onnx
from onnx import helper, TensorProto, shape_inference

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ONNX_IN = os.path.join(BASE_DIR, '..', 'weights', 'best.onnx')
ONNX_OUT = os.path.join(BASE_DIR, '..', 'weights', 'best_split.onnx')

model = onnx.load(ONNX_IN)

old_output = model.graph.output[0]
old_name = old_output.name
print(f"Original output: {old_name} shape={[d.dim_value for d in old_output.type.tensor_type.shape.dim]}")

old_node = None
for node in model.graph.node:
    for o in node.output:
        if o == old_name:
            old_node = node
            break
    if old_node:
        break
print(f"Producing node: {old_node.op_type} name={old_node.name}")

split_sizes = [6400, 1600, 400]
target_shapes = [[1, 6, 80, 80], [1, 6, 40, 40], [1, 6, 20, 20]]
output_names = ['output_80', 'output_40', 'output_20']

new_nodes = []
new_outputs = []

prev_output = old_name

split_node = helper.make_node(
    'Split',
    inputs=[prev_output],
    outputs=output_names,
    axis=2,
    split=split_sizes,
    name='split_heads'
)
new_nodes.append(split_node)

for i, (name, shape) in enumerate(zip(output_names, target_shapes)):
    reshape_name = f'reshape_{name}'
    reshape_node = helper.make_node(
        'Reshape',
        inputs=[name, f'const_shape_{i}'],
        outputs=[reshape_name],
        name=reshape_name
    )
    new_nodes.append(reshape_node)

    const_tensor = helper.make_tensor(
        name=f'const_shape_{i}',
        data_type=TensorProto.INT64,
        dims=[len(shape)],
        vals=shape
    )
    model.graph.initializer.append(const_tensor)

    new_outputs.append(helper.make_tensor_value_info(reshape_name, TensorProto.FLOAT, None))

model.graph.node.append(split_node)
model.graph.node.extend(new_nodes[1:])

while len(model.graph.output) > 0:
    model.graph.output.pop()
for o in new_outputs:
    model.graph.output.append(o)

model = shape_inference.infer_shapes(model)

onnx.checker.check_model(model)
onnx.save(model, ONNX_OUT)

print(f"Saved split ONNX: {ONNX_OUT}")
for out in model.graph.output:
    print(f"  {out.name} shape={[d.dim_value for d in out.type.tensor_type.shape.dim]}")
