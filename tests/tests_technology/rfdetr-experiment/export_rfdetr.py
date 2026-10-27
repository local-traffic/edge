
import torch
import os
from rfdetr import RFDETRNano

def main():
    print("Initializing RF-DETR Nano...")
    # Initialize with default config
    model = RFDETRNano()
    
    # Create output directory
    os.makedirs("rfdetr-experiment", exist_ok=True)
    output_path = "rfdetr-experiment/rfdetr_nano.onnx"
    
    print(f"Exporting to ONNX: {output_path}")
    
    # The export method in RFDETR class calls self.model.export()
    # We need to see what arguments it accepts.
    # Based on code it seems to use default export logic.
    
    # We might need to ensure weights are loaded. RFDETR __init__ calls maybe_download_pretrain_weights()
    
    # Export
    try:
        # Note: 'export' might need specific args, but let's try default
        # Looking at detr.py: export(**kwargs) -> self.model.export(**kwargs)
        # We might need to specify opset_version or input definitions if not handled by library
        model.export(path=output_path)
        print("Export successful!")
    except Exception as e:
        print(f"Export failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
