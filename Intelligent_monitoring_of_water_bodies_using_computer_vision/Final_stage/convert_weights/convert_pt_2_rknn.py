from ultralytics import YOLO

# Load your custom trained model
model = YOLO("Final_stage/weights/best.pt")

# Export directly to the RKNN format for your specific Rockchip chip
model.export(format="rknn", name="rk3576")
