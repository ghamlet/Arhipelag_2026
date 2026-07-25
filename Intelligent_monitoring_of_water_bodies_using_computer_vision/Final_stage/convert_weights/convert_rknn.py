from rknn.api import RKNN

ONNX_MODEL = '../weights/best.onnx'
RKNN_MODEL = '../weights/best.rknn'
TARGET_PLATFORM = 'rk3588'

rknn = RKNN(verbose=True)
rknn.config(mean_values=[], std_values=[], target_platform=TARGET_PLATFORM)

if rknn.load_onnx(model=ONNX_MODEL) == 0:
    rknn.build(do_quantization=False)
    rknn.export_rknn(RKNN_MODEL)
    print(f"Модель сконвертирована: {RKNN_MODEL}")
rknn.release()
