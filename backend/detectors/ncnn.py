"""
NCNN detector implementation for CPU-optimized inference.
"""

import numpy as np
import supervision as sv
from .base import BaseDetector, translate_class_ids_to_coco


class NCNNDetector(BaseDetector):
    """
    NCNN based detector for YOLOv8 models.

    Requires an NCNN exported model directory (containing .param and .bin files).
    To export a YOLOv8 model to NCNN format:
        yolo export model=yolov8n.pt format=ncnn

    This creates a directory `yolov8n_ncnn_model` which can be passed as `model_path`.
    """
    def __init__(self, model_path="yolov8n_ncnn_model", use_vulkan=False):
        import os
        try:
            import ncnn
        except ImportError:
            raise ImportError("ncnn not installed. Cannot run NCNNDetector.")

        self.net = ncnn.Net()
        self.net.opt.use_vulkan_compute = use_vulkan
        print(f"model path dir: {model_path}, use_vulkan={use_vulkan}")

        # Resolve paths
        if model_path and os.path.isdir(model_path):
            # Look for .param file
            files = os.listdir(model_path)
            param_file = next((f for f in files if f.endswith('.param')), None)
            bin_file = next((f for f in files if f.endswith('.bin')), None)
            if not param_file or not bin_file:
                # Check if the folder name itself is the prefix (e.g. model.ncnn.param)
                # Ultralytics export usually: model.ncnn.param, model.ncnn.bin
                pass

            if param_file and bin_file:
                param_path = os.path.join(model_path, param_file)
                bin_path = os.path.join(model_path, bin_file)
            else:
                # Try default names
                param_path = os.path.join(model_path, "model.ncnn.param")
                bin_path = os.path.join(model_path, "model.ncnn.bin")
        else:
            # Assume path to .param, derive .bin or prefix
            if not model_path:
                model_path = "yolov8n_ncnn_model"  # Default fallback

            if model_path.endswith('.param'):
                param_path = model_path
                bin_path = model_path.replace('.param', '.bin')
            elif os.path.isdir(model_path):
                # Handle case where default fallback was used and it is a dir
                param_path = os.path.join(model_path, "model.ncnn.param")
                bin_path = os.path.join(model_path, "model.ncnn.bin")
            else:
                # Assume prefix or folder path that wasn't caught
                param_path = model_path + "/model.ncnn.param" if not model_path.endswith('.param') else model_path
                bin_path = model_path + "/model.ncnn.bin" if not model_path.endswith('.bin') else model_path.replace('.param', '.bin')

                if not os.path.exists(param_path) and not model_path.endswith('.param'):
                    # Maybe provided just prefix?
                    param_path = model_path + ".param"
                    bin_path = model_path + ".bin"

        print(f"Loading NCNN model: {param_path}")
        if not os.path.exists(param_path):
            raise FileNotFoundError(f"NCNN param file not found: {param_path}")
        if not os.path.exists(bin_path):
            raise FileNotFoundError(f"NCNN bin file not found: {bin_path}")

        self.net.load_param(param_path)
        self.net.load_model(bin_path)

        # Detect IO names
        self.input_names, self.output_names = self._detect_io_names(param_path)

    def _detect_io_names(self, param_path):
        """
        Attempt to detect input and output blob names from the .param file.
        """
        input_names = []
        output_names = []

        try:
            with open(param_path, 'r') as f:
                lines = f.readlines()

            # Find Input layer
            # Format: Input [layer_name] [in_count] [out_count] [blob_name]
            # e.g. Input in0 0 1 in0
            for line in lines:
                parts = line.strip().split()
                if not parts: continue
                if parts[0] == "Input":
                    # Format: Type Name InCount OutCount [InputBlobs] [OutputBlobs] [Params]
                    # For Input layer: Input Name 0 1 OutputBlobName
                    # We want OutputBlobName which is the input to the net
                    if len(parts) >= 5:
                        detected_input = parts[4]
                        input_names = [detected_input]
                        break

            # Find Output
            # We look for commonly known output names in the file content
            content = " ".join(lines)
            candidates = ["output0", "out0", "output"]
            for cand in candidates:
                # Naive check: if the candidate string appears as a blob name
                # It should be surrounded by spaces usually
                if f" {cand} " in content or f" {cand}\n" in content:
                    output_names = [cand]
                    break

        except Exception as e:
            print(f"Warning: Failed to parse param file for IO names: {e}")

        # Fallbacks
        if not input_names:
            input_names = ["images", "in0", "data"]
        if not output_names:
            output_names = ["output0", "out0", "output"]

        print(f"Using NCNN IO names: inputs={input_names}, outputs={output_names}")
        return input_names, output_names

    def predict(self, image, conf_threshold=0.3):
        import numpy as np
        import ncnn

        # Target size (standard YOLO)
        target_size = 640

        h, w = image.shape[:2]
        mat_in = ncnn.Mat.from_pixels_resize(image, ncnn.Mat.PixelType.PIXEL_BGR2RGB, w, h, target_size, target_size)

        # Normalize: 0-255 -> 0-1
        mean_vals = [0.0, 0.0, 0.0]
        norm_vals = [1/255.0, 1/255.0, 1/255.0]
        mat_in.substract_mean_normalize(mean_vals, norm_vals)

        ex = self.net.create_extractor()

        # Try to set input
        # We blindly try common names. ncnn ignores invalid blob names usually.
        for name in self.input_names:
            ex.input(name, mat_in)

        # Extract output
        mat_out = ncnn.Mat()
        ret = -1
        for name in self.output_names:
            ret = ex.extract(name, mat_out)
            if ret == 0:
                break

        if ret != 0:
            # print("Failed to extract output from NCNN model")
            return sv.Detections.empty()

        # Convert to numpy
        out_data = np.array(mat_out)

        # Handle Output Shapes
        # YOLOv8 export usually (1, 84, 8400) or similar
        # ncnn might flatten to (8400, 84) or (84, 8400) depending on export

        if len(out_data.shape) == 1:
            # Flattened?
            # 84 * 8400 = 705600
            if out_data.size % 84 == 0:
                out_data = out_data.reshape(-1, 84)
            else:
                return sv.Detections.empty()

        if len(out_data.shape) == 2:
            if out_data.shape[0] == 84:
                out_data = out_data.T  # (8400, 84)
        elif len(out_data.shape) == 3:
            out_data = out_data.reshape(out_data.shape[1], out_data.shape[2])
            if out_data.shape[0] == 84:
                out_data = out_data.T

        # out_data should be (N, 84)

        boxes = out_data[:, 0:4]
        scores = out_data[:, 4:]

        # Get max score and class_id
        class_ids = np.argmax(scores, axis=1)
        confidences = np.max(scores, axis=1)

        # Filter by threshold
        mask = confidences > conf_threshold
        boxes = boxes[mask]
        class_ids = class_ids[mask]
        confidences = confidences[mask]

        if len(boxes) == 0:
            return sv.Detections.empty()

        # Convert cx, cy, w, h to xyxy
        # And scale to original image size

        scale_x = w / target_size
        scale_y = h / target_size

        xyxy = np.zeros_like(boxes)
        xyxy[:, 0] = (boxes[:, 0] - boxes[:, 2]/2) * scale_x  # xmin
        xyxy[:, 1] = (boxes[:, 1] - boxes[:, 3]/2) * scale_y  # ymin
        xyxy[:, 2] = (boxes[:, 0] + boxes[:, 2]/2) * scale_x  # xmax
        xyxy[:, 3] = (boxes[:, 1] + boxes[:, 3]/2) * scale_y  # ymax

        detections = sv.Detections(
            xyxy=xyxy,
            confidence=confidences,
            class_id=class_ids.astype(int)
        )

        detections = detections.with_nms(threshold=0.5)
        # Translate NCNN 0-based class IDs to COCO 1-based format
        return translate_class_ids_to_coco(detections)
