import os
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_DIR = os.path.join(BASE_DIR, '..', 'weights')

ONNX_MODEL = os.path.join(WEIGHTS_DIR, 'best_split.onnx')
RKNN_MODEL = os.path.join(WEIGHTS_DIR, 'best.rknn')
TARGET_PLATFORM = 'rk3576'

from rknn.api import RKNN

rknn = RKNN(verbose=True)
rknn.config(
    mean_values=[[0, 0, 0]],
    std_values=[[255, 255, 255]],
    target_platform=TARGET_PLATFORM,
)

print('--> Loading model')
ret = rknn.load_onnx(model=ONNX_MODEL)
if ret != 0:
    print('Load model failed!')
    exit(ret)
print('done')

print('--> Building model')
ret = rknn.build(do_quantization=False)
if ret != 0:
    print('Build model failed!')
    exit(ret)
print('done')

print('--> Export rknn model')
ret = rknn.export_rknn(RKNN_MODEL)
if ret != 0:
    print('Export rknn model failed!')
    exit(ret)
print(f"done: {RKNN_MODEL}")

print('--> Init runtime')
ret = rknn.init_runtime()
if ret != 0:
    print('Init runtime failed!')
    exit(ret)
print('done')

print('--> Testing inference with dummy input')
dummy = np.random.randint(0, 255, (1, 640, 640, 3), dtype=np.uint8)
outputs = rknn.inference(inputs=[dummy])
for i, o in enumerate(outputs):
    print(f"  output {i}: shape={o.shape}")
print('done')

rknn.release()
