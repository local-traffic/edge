
import unittest
import time
from backend.speed_calculator import SpeedCalculator, SpeedMeasurement

def mock_transform(x, y, w, h):
    # Map 0-1 to 0-100 meters
    return (x * 100, y * 100)

class TestSpeedCalculatorV2(unittest.TestCase):
    def setUp(self):
        self.calc = SpeedCalculator(mock_transform)
        self.frame_width = 1000
        self.frame_height = 1000

    def test_missing_timestamps(self):
        # Points without timestamps should result in no speed calculation
        points = []
        for i in range(5):
            points.append({
                'x': i * 100, 
                'y': 0
                # No 'time' key
            })
            
        measurement = self.calc.calculate(points, self.frame_width, self.frame_height)
        
        # Should be valid object but with 0 speed/invalid status because no segments could be calculated
        # The code returns "no valid speed segments" if segment_data is empty
        self.assertFalse(measurement.is_valid)
        self.assertEqual(measurement.comment, "no valid speed segments")


    def test_jittery_timestamps(self):
        # Average speed 10 m/s but with jittery timestamps
        points = []
        start_time = 1000.0
        
        # Expected: Distance 10m per step
        timestamps = [0, 0.9, 2.1, 2.9, 4.0, 5.1]
        
        for i, t in enumerate(timestamps):
             points.append({
                'x': 0 + (i * 100), 
                'y': 0,
                'time': start_time + t
            })

        measurement = self.calc.calculate(points, self.frame_width, self.frame_height)
        
        self.assertTrue(measurement.is_valid)
        # The average should be close to 10 m/s (50 meters in 5.1 seconds ~= 9.8 m/s)
        self.assertAlmostEqual(measurement.avg_speed_ms, 9.8, delta=0.5)

    def test_outlier_rejection(self):
        points = []
        start_time = 1000.0
        
        # Normal points
        for i in range(5):
            points.append({
                'x': i * 100, 
                'y': 0,
                'time': start_time + i
            })
            
        # Outlier point (impossible speed): jumped 1000 pixels (100m) in 0.1s => 1000 m/s
        points.append({
            'x': 2000, 
            'y': 0,
            'time': start_time + 5.1
        })
        
        # Back to normal
        points.append({
            'x': 500, 
            'y': 0,
            'time': start_time + 6.0
        })

        measurement = self.calc.calculate(points, self.frame_width, self.frame_height)
        
        # avg_speed_ms uses straight-line distance (first→last point) / total time,
        # so outlier segments are smoothed out rather than excluded: 50m / 6s ≈ 8.33 m/s
        self.assertLess(measurement.max_speed_ms, 100.0)
        self.assertAlmostEqual(measurement.avg_speed_ms, 8.33, delta=1.0)

if __name__ == '__main__':
    unittest.main()
