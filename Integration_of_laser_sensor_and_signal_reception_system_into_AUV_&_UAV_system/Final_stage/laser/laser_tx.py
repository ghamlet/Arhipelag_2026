#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Laser Transmitter - Hamming(7,4) protocol
Передаёт цифру 0-15 через лазер дрона по протоколу:
- Start bit: 600ms ON
- 7 bits: 200ms each (1=ON, 0=OFF)
- Tolerance: ±70ms
"""

import rospy
import time
import sys
from user.library import DroneLibrary


# Hamming(7,4) encoding: 4 data bits -> 7 bits (p1, p2, d1, p3, d2, d3, d4)
def encode_hamming_7(value):
    """Encode 4-bit value (0-15) to 7-bit Hamming code"""
    if not 0 <= value <= 15:
        raise ValueError("Value must be 0-15")
    
    d1 = (value >> 3) & 1
    d2 = (value >> 2) & 1
    d3 = (value >> 1) & 1
    d4 = value & 1
    
    # Parity bits
    p1 = d1 ^ d2 ^ d4
    p2 = d1 ^ d3 ^ d4
    p3 = d2 ^ d3 ^ d4
    
    return [p1, p2, d1, p3, d2, d3, d4]


# Timing constants (seconds)
START_DURATION = 0.60      # Start bit: 600ms
BIT_DURATION = 0.20        # Data bit: 200ms
GAP_DURATION = 0.05        # Inter-bit gap: 50ms
LASER_OFF_DELAY = 0.10     # Extra off time after start bit


def send_digit(drone, digit, verbose=True):
    """Send a single digit (0-15) via laser"""
    bits = encode_hamming_7(digit)
    
    if verbose:
        rospy.loginfo(f"Sending digit {digit} -> bits: {bits}")
    
    # Ensure laser is off first
    drone.set_laser(0)
    time.sleep(0.1)
    
    # START BIT: 600ms ON
    if verbose:
        rospy.loginfo("Start bit: 600ms ON")
    drone.set_laser(1)
    time.sleep(START_DURATION)
    drone.set_laser(0)
    time.sleep(LASER_OFF_DELAY)
    
    # 7 DATA BITS: 200ms each
    for i, bit in enumerate(bits):
        if verbose:
            rospy.loginfo(f"Bit {i+1}/7: {'ON' if bit else 'OFF'} ({BIT_DURATION*1000:.0f}ms)")
        
        if bit == 1:
            drone.set_laser(1)
            time.sleep(BIT_DURATION)
            drone.set_laser(0)
        else:
            drone.set_laser(0)
            time.sleep(BIT_DURATION)
        
        time.sleep(GAP_DURATION)
    
    # Ensure laser off at end
    drone.set_laser(0)
    
    if verbose:
        rospy.loginfo("Transmission complete")


def main():
    rospy.init_node('laser_tx_node', anonymous=True)
    
    # Parse argument
    if len(sys.argv) > 1:
        try:
            digit = int(sys.argv[1])
            if not 0 <= digit <= 15:
                rospy.logerr("Digit must be 0-15")
                return
        except ValueError:
            rospy.logerr("Usage: laser_tx.py <digit 0-15>")
            return
    else:
        digit = 5  # Default test value
        rospy.logwarn(f"No digit provided, sending default: {digit}")
    
    drone = DroneLibrary()
    drone.start()
    
    try:
        rospy.loginfo(f"Starting laser transmission: digit={digit}")
        send_digit(drone, digit)
        rospy.loginfo("Done")
        
    except Exception as e:
        rospy.logerr(f"Error: {e}")
    finally:
        drone.set_laser(0)
        drone.set_offline_mode()
        drone.stop()


if __name__ == '__main__':
    main()