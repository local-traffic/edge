
from hailo_sdk_client import ClientRunner
import os

def compile_rfdetr(onnx_path, output_hef_path):
    print(f"Compiling {onnx_path} to {output_hef_path}")
    
    model_name = "rfdetr_nano"
    runner = ClientRunner(hw_arch="hailo8l") # Targeting Hailo-8L (RPi 5 AI Kit) or hailo8 depending on HW
    # Note: RPi 5 AI Kit is Hailo-8L. If standard Hailo-8, change to "hailo8"
    
    # 1. Parse ONNX
    # We might need to specify start_node and end_node if the model has post-processing we want to strip
    # or handle specially. For now, assume ONNX is clean.
    runner.translate_onnx_model(
        onnx_path, 
        model_name, 
        # start_node_names=[], 
        # end_node_names=[], 
        net_input_shapes={"images": [1, 3, 640, 640]} # Adjust based on model input
    )
    
    # 2. Optimize
    # We ideally need a calibration dataset (ALS) for quantization.
    # For this script we'll skip providing real data and rely on random/default if possible, 
    # BUT Hailo usually requires calibration images.
    # We'll assume a 'calibration_images' folder exists.
    
    # runner.optimize(calib_dataset) # This requires a dataset loader
    
    # Simplified optimization (might fail without data)
    runner.optimize_full_precision() # Start with full precision or specific precision if possible without calib?
    # Usually we need quantization.
    
    # 3. Compile
    hef = runner.compile()
    
    with open(output_hef_path, "wb") as f:
        f.write(hef)
    print("Compilation complete!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--onnx", default="rfdetr-experiment/rfdetr_nano.onnx")
    parser.add_argument("--out", default="rfdetr-experiment/rfdetr_nano.hef")
    args = parser.parse_args()
    
    compile_rfdetr(args.onnx, args.out)
