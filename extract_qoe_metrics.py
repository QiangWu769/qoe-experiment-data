#!/usr/bin/env python3
"""
Extract QoE metrics (E2E delay, freeze rate) from WebRTC receiver logs.

Usage:
    python extract_qoe_metrics.py <log_file>               # Analyze single file
    python extract_qoe_metrics.py <log1> <log2> --cdf     # Compare E2E delay CDF
    python extract_qoe_metrics.py <log1> <log2> --freeze  # Freeze duration CDF + freeze rate bar
    python extract_qoe_metrics.py <log_dir>               # Analyze all logs in dir
    python extract_qoe_metrics.py <log_file> --json       # Output JSON
"""

import re
import sys
import os
import json
import numpy as np
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

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

def plot_e2e_cdf(log_files, output_path='e2e_delay_cdf.png'):
    """Plot E2E delay CDF for multiple log files."""
    colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']

    plt.figure(figsize=(10, 6))

    for i, log_file in enumerate(log_files):
        timings = parse_timing_breakdown(log_file)
        e2e = timings['e2e']

        if not e2e:
            print(f"Warning: No E2E data in {log_file}")
            continue

        sorted_data = np.sort(e2e)
        cdf = np.arange(1, len(sorted_data) + 1) / len(sorted_data)

        name = Path(log_file).stem.replace('_receiver_cloud', '')
        color = colors[i % len(colors)]

        plt.plot(sorted_data, cdf, color=color, linewidth=2,
                 label=f'{name} (mean={np.mean(e2e):.1f}ms)')

    plt.xlabel('E2E Delay (ms)', fontsize=12)
    plt.ylabel('CDF', fontsize=12)
    plt.title('E2E Delay CDF Comparison', fontsize=14)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"CDF plot saved: {output_path}")

    return output_path

def extract_freeze_durations(log_file):
    """Extract individual freeze durations from cumulative freeze data."""
    pattern = r'Freeze Count: (\d+).*Total Freeze Duration \(ms\): (\d+)'

    prev_count, prev_dur = 0, 0
    freeze_durations = []

    with open(log_file, 'r', errors='ignore') as f:
        for line in f:
            if 'VideoQuality-CoreFreeze' in line:
                match = re.search(pattern, line)
                if match:
                    count, dur = int(match.group(1)), int(match.group(2))
                    if count > prev_count:
                        freeze_durations.append(dur - prev_dur)
                        prev_count, prev_dur = count, dur

    return freeze_durations

def detect_algorithm(name):
    """Detect algorithm type from log name."""
    name_lower = name.lower()
    if 'ratio' in name_lower or 'gbr' in name_lower:
        return 'GBR'
    elif 'gcc' in name_lower:
        return 'GCC'
    else:
        return 'Unknown'

def plot_freeze_analysis(log_files, output_path='freeze_analysis.png'):
    """Plot freeze duration CDF (by algorithm) and freeze rate bar chart."""
    algo_colors = {'GCC': 'red', 'GBR': 'blue', 'Unknown': 'gray'}

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Collect data by algorithm
    algo_freeze_durations = {}
    freeze_rates = []
    names = []
    name_colors = []

    for log_file in log_files:
        name = Path(log_file).stem.replace('_receiver_cloud', '')
        names.append(name)
        algo = detect_algorithm(name)
        name_colors.append(algo_colors[algo])

        # Get freeze durations
        durations = extract_freeze_durations(log_file)
        if algo not in algo_freeze_durations:
            algo_freeze_durations[algo] = []
        algo_freeze_durations[algo].extend(durations)

        # Get freeze rate
        freeze_info = parse_freeze_rate(log_file)
        if freeze_info:
            freeze_rates.append(freeze_info['rebuffering_ratio'] * 100)
        else:
            freeze_rates.append(0)

        print(f"{name} ({algo}): {len(durations)} freezes, rate={freeze_rates[-1]:.2f}%")

    # Left plot: Freeze duration CDF by algorithm
    ax1 = axes[0]
    has_data = False
    for algo in ['GCC', 'GBR', 'Unknown']:
        if algo in algo_freeze_durations and algo_freeze_durations[algo]:
            durations = algo_freeze_durations[algo]
            sorted_data = np.sort(durations)
            cdf = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
            ax1.plot(sorted_data, cdf, color=algo_colors[algo], linewidth=2,
                     label=f'{algo} (n={len(durations)}, mean={np.mean(durations):.0f}ms)')
            has_data = True

    if has_data:
        ax1.set_xlabel('Freeze Duration (ms)', fontsize=12)
        ax1.set_ylabel('CDF', fontsize=12)
        ax1.set_title('Freeze Duration CDF by Algorithm', fontsize=14)
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
    else:
        ax1.text(0.5, 0.5, 'No freeze events', ha='center', va='center', fontsize=14)
        ax1.set_title('Freeze Duration CDF', fontsize=14)

    # Right plot: Freeze rate bar chart
    ax2 = axes[1]
    x = np.arange(len(names))
    bars = ax2.bar(x, freeze_rates, color=name_colors, alpha=0.8)
    ax2.set_xlabel('Log', fontsize=12)
    ax2.set_ylabel('Freeze Rate (%)', fontsize=12)
    ax2.set_title('Freeze Rate by Log', fontsize=14)
    ax2.set_xticks(x)
    ax2.set_xticklabels(names, rotation=45, ha='right', fontsize=9)
    ax2.grid(True, alpha=0.3, axis='y')

    # Add value labels on bars
    for bar, rate in zip(bars, freeze_rates):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                 f'{rate:.2f}%', ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"\nFreeze analysis saved: {output_path}")

    return output_path

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    # Check for --cdf flag
    if '--cdf' in sys.argv:
        log_files = [f for f in sys.argv[1:] if f not in ['--cdf', '--freeze', '--json'] and f.endswith('.log')]

        if len(log_files) < 2:
            print("Error: Need at least 2 log files for CDF comparison")
            sys.exit(1)

        plot_e2e_cdf(log_files)
        return

    # Check for --freeze flag
    if '--freeze' in sys.argv:
        log_files = [f for f in sys.argv[1:] if f not in ['--cdf', '--freeze', '--json'] and f.endswith('.log')]

        if len(log_files) < 1:
            print("Error: Need at least 1 log file for freeze analysis")
            sys.exit(1)

        plot_freeze_analysis(log_files)
        return

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
