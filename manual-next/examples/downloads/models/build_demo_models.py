"""Create small deterministic ONNX graphs for API examples, not trained models.
Convert each resulting ONNX file to RTen before running the Rust example.
"""
from pathlib import Path
import onnx
from onnx import TensorProto, helper

out = Path(__file__).parent / "models"
out.mkdir(exist_ok=True)
x = helper.make_tensor_value_info("image", TensorProto.FLOAT, [1, 1, 8, 8])
def constant(name, dims, values):
    return helper.make_tensor(name, TensorProto.FLOAT, dims, values)
def emit(name, nodes, initializers, shape):
    graph = helper.make_graph(nodes, "manual_demo_" + name, [x],
        [helper.make_tensor_value_info("output", TensorProto.FLOAT, shape)], initializers)
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)],
                              producer_name="zvision-manual-demo")
    model.ir_version = 8
    onnx.checker.check_model(model)
    onnx.save(model, out / ("demo-" + name + ".onnx"))
one = constant("one", [1], [1.0])
emit("classification", [helper.make_node("ReduceMean", ["image"], ["mean"], axes=[2,3], keepdims=0),
    helper.make_node("Sub", ["one","mean"], ["inverse"]),
    helper.make_node("Concat", ["inverse","mean"], ["output"], axis=1)], [one], [1,2])
emit("segmentation", [helper.make_node("Sub", ["one","image"], ["inverse"]),
    helper.make_node("Concat", ["inverse","image"], ["output"], axis=1)], [one], [1,2,8,8])
emit("anomaly", [helper.make_node("Identity", ["image"], ["output"])], [], [1,1,8,8])
emit("detection", [helper.make_node("ReduceMean", ["image"], ["mean"], axes=[1,2,3], keepdims=1),
    helper.make_node("Mul", ["mean","zero"], ["unused"]),
    helper.make_node("Reshape", ["unused","shape"], ["scalar"]),
    helper.make_node("Add", ["box","scalar"], ["output"])],
    [constant("zero", [1], [0.]), helper.make_tensor("shape", TensorProto.INT64, [1], [1]),
     constant("box", [1,1,6], [1.,1.,6.,6.,0.9,0.])], [1,1,6])
