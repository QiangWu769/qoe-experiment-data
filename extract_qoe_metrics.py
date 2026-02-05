#!/usr/bin/env python3
"""
Extract QoE metrics (E2E delay, freeze rate) from WebRTC receiver logs.

Usage:
    python extract_qoe_metrics.py <log_file>
    python extract_qoe_metrics.py <log_dir> --all
"""

import re
import sys
import os
import json
import numpy as np
from pathlib import Path

def parse_timing_breakdown(log_file):
    """Parse TIMING-BREAKDOWN lines from log file."""
    pattern = r'\[TIMING-BREAKDOWN\].*?e2e=(\d+)ms\s+encode=(\d+)ms\s+pacer=(\d+)ms\s+network=(\d+)ms\s+jitter_buf=(\d+)ms\s+\(packet_buf=(\d+)ms\s+frame_buf=(\d+)ms\)\s+decode=(\d+)ms'

    timings = {
        'e2e': [], 'encode': [], 'pacer': [], 'network': [],
        'jitter_buf': [], 'packet_buf': [], 'frame_buf': [], 'decode': []
    }

    with open(log_file, 'r', errors='ignore') as f:
        for line in f:
            if 'TIMING-BREAKDOWN' in line:
                match = re.search(pattern, line)
                if match:
                    timings['e2e'].append(int(match.group(1)))
                    timings['encode'].append(int(match.group(2)))
                    timings['pacer'].append(int(match.group(3)))
                    timings['network'].append(int(match.group(4)))
                    timings['jitter_buf'].append(int(match.group(5)))
                    timings['packet_buf'].append(int(match.group(6)))
                    timings['frame_buf'].append(int(match.group(7)))
                    timings['decode'].append(int(match.group(8)))

    return timings

def parse_freeze_rate(log_file):
    """Parse VideoQuality-CoreFreeze from log file."""
    pattern = r'\[VideoQuality-CoreFreeze\].*?Freeze Count:\s*(\d+).*?Total Freeze Duration \(ms\):\s*(\d+).*?Rebuffering Ratio:\s*([\d.]+).*?Playback Duration \(ms\):\s*(\d+)'

    freeze_info = None
    with open(log_file, 'r', errors='ignore') as f:
        for line in f:
            if 'VideoQuality-CoreFreeze' in line:
                match = re.search(pattern, line)
                if match:
                    freeze_info = {
                        'freeze_count': int(match.group(1)),
                        'freeze_duration_ms': int(match.group(2)),
                        'rebuffering_ratio': float(match.group(3)),
                        'playback_duration_ms': int(match.group(4))
                    }

    return freeze_info

def parse_bitrate(log_file):
    """Parse VideoQuality-Bitrate from log file."""
    pattern = r'\[VideoQuality-Bitrate\].*?Payload Bytes Received:\s*(\d+)'

    bytes_received = None
    with open(log_file, 'r', errors='ignore') as f:
        for line in f:
            if 'VideoQuality-Bitrate' in line:
                match = re.search(pattern, line)
                if match:
                    bytes_received = int(match.group(1))

    return bytes_received

def calc_stats(data):
    """Calculate statistics for a list of values."""
    if not data:
        return None
    arr = np.array(data)
    return {
        'mean': float(np.mean(arr)),
        'std': float(np.std(arr)),
        'min': float(np.min(arr)),
        'p10': float(np.percentile(arr, 10)),
        'p25': float(np.percentile(arr, 25)),
        'p50': float(np.percentile(arr, 50)),
        'p75': float(np.percentile(arr, 75)),
        'p90': float(np.percentile(arr, 90)),
        'max': float(np.max(arr)),
        'count': len(arr)
    }

def analyze_log(log_file):
    """Analyze a single log file and return QoE metrics."""
    timings = parse_timing_breakdown(log_file)
    freeze_info = parse_freeze_rate(log_file)
    bytes_received = parse_bitrate(log_file)

    results = {
        'file': str(log_file),
        'timing': {},
        'freeze': freeze_info,
        'bitrate_mbps': None
    }

    # Calculate timing statistics
    for key, values in timings.items():
        if values:
            results['timing'][key] = calc_stats(values)

    # Calculate bitrate
    if bytes_received and freeze_info and freeze_info['playback_duration_ms'] > 0:
        results['bitrate_mbps'] = bytes_received * 8 / freeze_info['playback_duration_ms'] / 1000

    return results

def print_results(results):
    """Print results in a readable format."""
    print(f"\n{'='*70}")
    print(f"Log: {results['file']}")
    print('='*70)

    # E2E delay
    if 'e2e' in results['timing']:
        e2e = results['timing']['e2e']
        print(f"\nE2E Delay ({e2e['count']} samples):")
        print(f"  Mean={e2e['mean']:.1f}ms, Std={e2e['std']:.1f}ms")
        print(f"  Min={e2e['min']:.1f}, P10={e2e['p10']:.1f}, P25={e2e['p25']:.1f}, P50={e2e['p50']:.1f}, P75={e2e['p75']:.1f}, P90={e2e['p90']:.1f}, Max={e2e['max']:.1f}")

    # Delay breakdown
    print(f"\nDelay Breakdown (mean):")
    for key in ['encode', 'pacer', 'network', 'jitter_buf', 'packet_buf', 'frame_buf', 'decode']:
        if key in results['timing']:
            print(f"  {key}: {results['timing'][key]['mean']:.1f}ms")

    # Freeze rate
    if results['freeze']:
        f = results['freeze']
        print(f"\nFreeze Rate:")
        print(f"  Rebuffering Ratio: {f['rebuffering_ratio']*100:.2f}%")
        print(f"  Freeze Count: {f['freeze_count']}")
        print(f"  Total Freeze Duration: {f['freeze_duration_ms']}ms")
        print(f"  Playback Duration: {f['playback_duration_ms']}ms")

    # Bitrate
    if results['bitrate_mbps']:
        print(f"\nBitrate: {results['bitrate_mbps']:.2f} Mbps")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    path = sys.argv[1]

    if os.path.isfile(path):
        # Single file
        results = analyze_log(path)
        print_results(results)

        # Optionally save to JSON
        if '--json' in sys.argv:
            json_path = path.replace('.log', '_qoe.json')
            with open(json_path, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to: {json_path}")

    elif os.path.isdir(path):
        # Directory - process all log files
        all_results = []
        log_files = list(Path(path).glob('**/*.log'))

        print(f"Found {len(log_files)} log files")

        for log_file in sorted(log_files):
            results = analyze_log(log_file)
            all_results.append(results)

            # Print summary line
            e2e = results['timing'].get('e2e', {}).get('mean', 'N/A')
            freeze = results['freeze']['rebuffering_ratio']*100 if results['freeze'] else 'N/A'
            bitrate = results['bitrate_mbps'] if results['bitrate_mbps'] else 'N/A'

            name = log_file.stem
            if isinstance(e2e, float):
                print(f"{name}: E2E={e2e:.1f}ms, Freeze={freeze:.2f}%, Bitrate={bitrate:.2f}Mbps")
            else:
                print(f"{name}: E2E={e2e}, Freeze={freeze}, Bitrate={bitrate}")

        # Save all results to JSON
        if '--json' in sys.argv:
            json_path = os.path.join(path, 'qoe_summary.json')
            with open(json_path, 'w') as f:
                json.dump(all_results, f, indent=2)
            print(f"\nAll results saved to: {json_path}")

if __name__ == '__main__':
    main()
