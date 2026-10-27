import numpy as np
import cv2
import argparse
import time
import os
import sys

# Try to import HailoRT Python API
try:
    from hailo_platform import (HEF, VDevice, HailoStreamInterface, InferVStreams,
                                ConfigureParams, InputVStreamParams, OutputVStreamParams,
                                FormatType)
except ImportError:
    print("Error: hailo_platform not found. Please ensure HailoRT Python API is installed.")
    sys.exit(1)

def parse_args():
    parser = argparse.ArgumentParser(description="Test Hailo YOLO Inference")
    parser.add_argument("--hef", type=str, default="yolov8n.hef", help="Path to HEF model file")
    parser.add_argument("--image", type=str, default=None, help="Path to test image")
    parser.add_argument("--input_shape", type=str, default="640x640", help="Input shape WxH")
    return parser.parse_args()

def get_input_shape(shape_str):
    try:
        w, h = map(int, shape_str.lower().split('x'))
        return (w, h)
    except:
        return (640, 640)

def main():
    args = parse_args()
    
    if not os.path.exists(args.hef):
        print(f"Error: Model file '{args.hef}' not found.")
        print("Please download a compiled YOLOv8 HEF model from the Hailo Model Zoo.")
        return

    print(f"Loading HEF: {args.hef}")
    target = VDevice()
    
    # Load HEF
    hef = HEF(args.hef)
    
    # Configure Network Group
    configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
    network_groups = target.configure(hef, configure_params)
    network_group = network_groups[0]
    
    network_group_params = network_group.create_params()
    
    # Create Input/Output Stream Params
    input_vstreams_params = InputVStreamParams.make(network_group, format_type=FormatType.UINT8)
    output_vstreams_params = OutputVStreamParams.make(network_group, format_type=FormatType.FLOAT32)
    
    # Prepare Input Data
    width, height = get_input_shape(args.input_shape)
    
    if args.image and os.path.exists(args.image):
        print(f"Loading image: {args.image}")
        image = cv2.imread(args.image)
        image = cv2.resize(image, (width, height))
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    else:
        print(f"Using dummy image ({width}x{height})")
        image = np.zeros((height, width, 3), dtype=np.uint8)
        # Add some patterns
        cv2.circle(image, (width//2, height//2), 50, (255, 0, 0), -1)
    
    # Add batch dimension
    input_data = np.expand_dims(image, axis=0)
    
    print("Starting inference...")
    
    # Activate the network group before inference
    with network_group.activate(network_group_params):
        with InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as infer_pipeline:
            start_time = time.time()
            
            # Run inference
            # The infer method returns a dictionary of output_name -> numpy array
            outputs = infer_pipeline.infer(input_data)
            
            end_time = time.time()
            print(f"Inference time: {(end_time - start_time)*1000:.2f} ms")
            
            # Print output shapes
            print("\nOutputs:")
            for name, data in outputs.items():
                try:
                    if isinstance(data, list):
                         print(f"  {name}: List of length {len(data)}")
                         if len(data) > 0:
                             print(f"    Element 0 type: {type(data[0])}")
                             if hasattr(data[0], 'shape'):
                                 print(f"    Element 0 shape: {data[0].shape}")
                             elif isinstance(data[0], list):
                                 print(f"    Element 0 list len: {len(data[0])}")
                    elif hasattr(data, 'shape'):
                        print(f"  {name}: {data.shape} - Range: [{data.min():.2f}, {data.max():.2f}]")
                    else:
                        print(f"  {name}: Type {type(data)}")
                except Exception as e:
                    print(f"  {name}: Error printing details: {e}")
            
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main()
