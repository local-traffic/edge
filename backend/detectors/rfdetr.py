"""
RF-DETR detector implementation.
"""

from .base import BaseDetector


class RFDETRDetector(BaseDetector):
    def __init__(self):
        from rfdetr import RFDETRBase, RFDETRNano
        print("Loading RF-DETR model...")
        #self.model = RFDETRBase()
        self.model = RFDETRNano()
        ## doesnt work but doent expect miracles anyway ...
        #self.model.optimize_for_inference()
        print("RF-DETR model loaded.")

    def predict(self, image, conf_threshold=0.3):
        # RF-DETR expects RGB and already outputs COCO 1-based class IDs (no translation needed)
        return self.model.predict(image, threshold=conf_threshold)
