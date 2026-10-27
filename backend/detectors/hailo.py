"""
Hailo detector implementation for hardware-accelerated inference.
"""

import numpy as np
import supervision as sv
from .base import BaseDetector


def hailo_to_supervision(nms_output, threshold=0.5, img_width=1, img_height=1):
    """
    Converts Hailo class-grouped output to supervision.Detections.

    Args:
        results: The dict from infer_pipeline.infer()
        output_name: The key for the post-process layer (e.g., 'yolov8n/yolov8_postprocess')
        threshold: Confidence threshold to filter detections
        img_width/height: Pass these to get pixel coordinates; leave as 1 for normalized.
    """
    raw_detections = nms_output

    all_bboxes = []
    all_confidences = []
    all_class_ids = []

    # Iterate through the 80 class arrays
    for class_idx, class_detections in enumerate(raw_detections):
        if len(class_detections) == 0:
            continue

        for det in class_detections:
            # Hailo NMS default: [y_min, x_min, y_max, x_max, confidence]
            y_min, x_min, y_max, x_max, confidence = det

            if confidence < threshold:
                continue

            # Supervision expects: [x_min, y_min, x_max, y_max]
            # Multiply by dimensions to move from normalized to pixel space
            all_bboxes.append([
                x_min * img_width,
                y_min * img_height,
                x_max * img_width,
                y_max * img_height
            ])
            all_confidences.append(confidence)
            #instead of translate_class_ids_to_coco
            all_class_ids.append(class_idx+1)

    # If no detections were found, return an empty Detections object
    if not all_bboxes:
        return sv.Detections.empty()

    return sv.Detections(
        xyxy=np.array(all_bboxes, dtype=np.float32),
        confidence=np.array(all_confidences, dtype=np.float32),
        class_id=np.array(all_class_ids, dtype=np.int32)
    )


class HailoDetector(BaseDetector):
    def __init__(self, hef_path="yolov8n.hef"):
        import numpy as np
        try:
            from hailo_platform import (HEF, VDevice, HailoStreamInterface, InferVStreams,
                                        ConfigureParams, InputVStreamParams, OutputVStreamParams,
                                        FormatType)
        except ImportError:
            raise ImportError("hailo_platform not installed. Cannot run HailoDetector.")

        print(f"Loading Hailo HEF: {hef_path}")
        self.target = VDevice()
        self.hef = HEF(hef_path)

        # Configure
        self.configure_params = ConfigureParams.create_from_hef(self.hef, interface=HailoStreamInterface.PCIe)
        self.network_groups = self.target.configure(self.hef, self.configure_params)
        self.network_group = self.network_groups[0]

        self.network_group_params = self.network_group.create_params()

        # Create params
        self.input_vstreams_params = InputVStreamParams.make(self.network_group, format_type=FormatType.UINT8)
        self.output_vstreams_params = OutputVStreamParams.make(self.network_group, format_type=FormatType.FLOAT32)

        # Activate network group
        self.activation_context = self.network_group.activate(self.network_group_params)
        self.activation_context.__enter__()

        # Start inference pipeline
        self.pipeline = InferVStreams(self.network_group, self.input_vstreams_params, self.output_vstreams_params)
        self.pipeline.__enter__() # Keep it open

        print("Hailo inference pipeline started.")

    def __del__(self):
        if hasattr(self, 'pipeline'):
            self.pipeline.__exit__(None, None, None)
        if hasattr(self, 'activation_context'):
            self.activation_context.__exit__(None, None, None)


    def predict(self, image, conf_threshold=0.3):
        import numpy as np
        import cv2

        h, w = image.shape[:2]

        target_h, target_w = 640, 640
        resized_image = cv2.resize(image, (target_w, target_h))
        # Hailo usually expects RGB
        #input_data = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
        input_data = np.expand_dims(resized_image, axis=0)

        # Infer
        outputs = self.pipeline.infer(input_data)

        detections = sv.Detections.empty()

        # Check for NMS output, assume there is only one batch
        if len(outputs) >1:
            raise Exception("we do no batch processing I hope")

        for name, data in outputs.items():
            if "nms" in name.lower():
                detections = hailo_to_supervision(data[0],conf_threshold,w,h)

        return detections
