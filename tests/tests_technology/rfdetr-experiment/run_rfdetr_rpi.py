
import numpy as np
import cv2
import time
from hailo_platform import (HEF, VDevice, HailoStreamInterface, InferVStreams, ConfigureParams, InputVStreamParams, OutputVStreamParams, FormatType)

class HailoInference:
    def __init__(self, hef_path):
        self.hef = HEF(hef_path)
        self.target = VDevice()
        
        # Configure
        configure_params = ConfigureParams.create_from_hef(hef=self.hef, interface=HailoStreamInterface.PCIe)
        self.network_group = self.target.configure(self.hef, configure_params)[0]
        self.network_group_params = self.network_group.create_params()
        
        self.input_vstreams_params = InputVStreamParams.make(self.network_group, format_type=FormatType.FLOAT32)
        self.output_vstreams_params = OutputVStreamParams.make(self.network_group, format_type=FormatType.FLOAT32)
        
        self.input_vstream_info = self.hef.get_input_vstream_infos()[0]
        self.output_vstream_info = self.hef.get_output_vstream_infos()[0]
        
        self.height = self.input_vstream_info.shape[0]
        self.width = self.input_vstream_info.shape[1]

    def infer(self, image):
        # Preprocess
        resized = cv2.resize(image, (self.width, self.height))
        # Ensure BCHW or BHWC based on model expectation. 
        # Usually Hailo DFC handles layout, but inputs usually expected in NHWC or NCHW.
        # rfdetr might expect NCHW.
        input_data = np.expand_dims(resized, axis=0).astype(np.float32)
        
        # Normalize if needed (depends on if normalization was added in DFC)
        input_data /= 255.0 
        
        with InferVStreams(self.network_group, self.input_vstreams_params, self.output_vstreams_params) as infer_pipeline:
            # Inference
            output_data = infer_pipeline.infer({self.input_vstream_info.name: input_data})
            
            # Postprocess output_data (Decoder)
            # This depends entirely on the output layers of RF-DETR export
            # We print raw output shape for debug
            for k, v in output_data.items():
                print(f"Output {k}: {v.shape}")
                
            return output_data

def main():
    import sys
    hef_path = sys.argv[1] if len(sys.argv) > 1 else "rfdetr_nano.hef"
    
    print(f"Loading {hef_path}...")
    try:
        runner = HailoInference(hef_path)
        
        # Test with dummy image
        img = np.zeros((640, 640, 3), dtype=np.uint8)
        print("Running inference...")
        res = runner.infer(img)
        print("Done.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
