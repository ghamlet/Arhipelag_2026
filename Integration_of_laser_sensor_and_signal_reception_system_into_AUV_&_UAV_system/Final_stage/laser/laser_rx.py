#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Laser Receiver - Time-based Hamming(7,4) decoder
Читает камеру, детектит лазер, декодирует по временным интервалам
"""

import cv2
import numpy as np
import time
import sys
from collections import deque


# ==================== CONFIG ====================
CAMERA_INDEX = 0                    # /dev/video0
LASER_HSV_LOWER = np.array([0, 0, 200])   # HSV threshold for laser spot
LASER_HSV_UPPER = np.array([180, 50, 255])
MIN_CONTOUR_AREA = 5                # Minimum laser spot area (px)
MAX_CONTOUR_AREA = 500              # Maximum laser spot area (px)

# Timing constants (seconds)
START_MIN, START_MAX = 0.50, 0.70    # Start bit: 600ms ±70ms
BIT_MIN, BIT_MAX = 0.13, 0.27        # Data bit: 200ms ±70ms
RECEIVE_TIMEOUT = 2.0                # Reset if no edge for 2s

# ==================== HAMMING DECODER ====================
def decode_hamming_7(bits):
    """Classic Hamming(7,4) decoder - corrects 1-bit errors"""
    if len(bits) != 7:
        return None
    
    p1, p2, d1, p3, d2, d3, d4 = bits
    
    s1 = p1 ^ d1 ^ d2 ^ d4
    s2 = p2 ^ d1 ^ d3 ^ d4
    s3 = p3 ^ d2 ^ d3 ^ d4
    
    error_bit = (s3 << 2) | (s2 << 1) | s1
    
    if error_bit != 0:
        bit_to_flip = error_bit - 1
        if bit_to_flip < 7:
            bits[bit_to_flip] ^= 1
            print(f"[HAMMING] Corrected 1-bit error at position {error_bit}")
    
    _, _, d1, _, d2, d3, d4 = bits
    return (d1 << 3) | (d2 << 2) | (d3 << 1) | d4


# ==================== TIME-BASED DECODER ====================
class LaserTimeDecoder:
    def __init__(self):
        self.receiving = False
        self.waiting_for_start = True
        self.last_edge_time = None
        self.last_state = False
        self.bit_buffer = []
        self.start_time = None
    
    def process_frame(self, laser_on: bool, timestamp: float):
        """
        Call on EVERY frame with current laser state and timestamp.
        Returns decoded digit (0-15) or None.
        """
        # Detect edge
        if laser_on != self.last_state:
            now = timestamp
            duration = now - self.last_edge_time if self.last_edge_time else 0
            self.last_edge_time = now
            self.last_state = laser_on
            
            if self.waiting_for_start:
                # Looking for START bit (600ms ON)
                if laser_on == False:  # Falling edge after ON pulse
                    if START_MIN <= duration <= START_MAX:
                        print(f"[DECODER] START bit detected: {duration*1000:.0f}ms")
                        self.receiving = True
                        self.waiting_for_start = False
                        self.bit_buffer = []
                        self.start_time = now
                    else:
                        print(f"[DECODER] Invalid start pulse: {duration*1000:.0f}ms (expected 500-700ms)")
                return None
            
            elif self.receiving:
                # Receiving 7 data bits
                if BIT_MIN <= duration <= BIT_MAX:
                    # Falling edge = laser was ON = bit 1
                    # Rising edge = laser was OFF = bit 0
                    bit = 1 if not laser_on else 0  # laser_on is NEW state
                    self.bit_buffer.append(bit)
                    print(f"[DECODER] Bit {len(self.bit_buffer)}/7: {bit} (duration: {duration*1000:.0f}ms)")
                    
                    if len(self.bit_buffer) == 7:
                        digit = decode_hamming_7(self.bit_buffer)
                        print(f"[DECODER] *** DECODED DIGIT: {digit} ***")
                        self._reset()
                        return digit
                else:
                    print(f"[DECODER] Timing error: {duration*1000:.0f}ms (expected 130-270ms). Resetting.")
                    self._reset()
            return None
        
        # No edge - check timeout
        if self.receiving and self.last_edge_time:
            if (timestamp - self.last_edge_time) > RECEIVE_TIMEOUT:
                print(f"[DECODER] Timeout ({RECEIVE_TIMEOUT}s). Resetting.")
                self._reset()
        
        return None
    
    def _reset(self):
        self.receiving = False
        self.waiting_for_start = True
        self.bit_buffer = []
        self.last_edge_time = None
        self.last_state = False


# ==================== LASER DETECTOR ====================
class LaserDetector:
    def __init__(self):
        self.cap = cv2.VideoCapture(CAMERA_INDEX)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {CAMERA_INDEX}")
        
        # Try to set resolution/FPS
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        self.decoder = LaserTimeDecoder()
        self.frame_count = 0
        self.fps_start = time.time()
        self.fps = 0
    
    def detect_laser(self, frame):
        """Return (laser_on: bool, annotated_frame)"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, LASER_HSV_LOWER, LASER_HSV_UPPER)
        
        # Morphological cleanup
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        laser_on = False
        best_contour = None
        max_area = 0
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if MIN_CONTOUR_AREA <= area <= MAX_CONTOUR_AREA:
                if area > max_area:
                    max_area = area
                    best_contour = cnt
        
        annotated = frame.copy()
        
        if best_contour is not None:
            laser_on = True
            (x, y), radius = cv2.minEnclosingCircle(best_contour)
            center = (int(x), int(y))
            radius = int(radius)
            cv2.circle(annotated, center, radius, (0, 255, 0), 2)
            cv2.putText(annotated, "LASER", (center[0]-30, center[1]-radius-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        return laser_on, annotated
    
    def run(self):
        print("[RECEIVER] Starting laser detection loop...")
        print("[RECEIVER] Press 'q' to quit")
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("[RECEIVER] Failed to read frame")
                break
            
            timestamp = time.time()
            self.frame_count += 1
            
            # FPS calculation
            if self.frame_count % 30 == 0:
                elapsed = timestamp - self.fps_start
                self.fps = 30 / elapsed if elapsed > 0 else 0
                self.fps_start = timestamp
            
            # Detect laser
            laser_on, annotated = self.detect_laser(frame)
            
            # Decode
            digit = self.decoder.process_frame(laser_on, timestamp)
            
            if digit is not None:
                cv2.putText(annotated, f"DECODED: {digit}", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
                print(f"\n>>> RECEIVED DIGIT: {digit} <<<\n")
            
            # Status overlay
            status = "RECEIVING" if self.decoder.receiving else ("WAITING START" if self.decoder.waiting_for_start else "IDLE")
            cv2.putText(annotated, f"Status: {status}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(annotated, f"FPS: {self.fps:.1f}", (10, annotated.shape[0]-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(annotated, f"Laser: {'ON' if laser_on else 'OFF'}", (10, annotated.shape[0]-40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if laser_on else (0, 0, 255), 2)
            
            cv2.imshow('Laser Receiver', annotated)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.decoder._reset()
                print("[RECEIVER] Manual reset")
        
        self.cap.release()
        cv2.destroyAllWindows()


def main():
    try:
        detector = LaserDetector()
        detector.run()
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()