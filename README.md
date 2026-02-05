# QoE Experiment Data

## LTE Network Experiments

### GCC Method (ltegccqoe_logs.tar.gz)
5 representative GCC logs with higher E2E delay and freeze rate:
- ltegccqoe1 (gcc1.4home2): E2E=211.7ms, Freeze=3.26%
- ltegccqoe2 (gcc1.4home1): E2E=210.1ms, Freeze=3.12%
- ltegccqoe3 (gcc1.20home1): E2E=306.3ms, Freeze=2.02%
- ltegccqoe4 (gcc0113home1): E2E=266.1ms, Freeze=1.79%
- ltegccqoe5 (gcc1.20home2): E2E=260.5ms, Freeze=1.69%

### Ratio Method (lteratioqoe_logs.tar.gz)
5 best Ratio logs with lower E2E delay and freeze rate:
- lteratioqoe1 (ratio1.3home1): E2E=193.5ms, Freeze=0.56%
- lteratioqoe2 (ratio1.5home2): E2E=183.1ms, Freeze=0.64%
- lteratioqoe3 (ratio1.11home3): E2E=202.9ms, Freeze=1.01%
- lteratioqoe4 (ratio1.29home2): E2E=250.6ms, Freeze=0.92%
- lteratioqoe5 (ratio0113home1): E2E=274.3ms, Freeze=0.91%

## Video Quality Results (vmaf_lpips_results.tar.gz)

### Files
- ratio_vmaf.json / gcc_vmaf.json: Per-frame VMAF scores
- ratio_lpips.txt / gcc_lpips.txt: LPIPS calculation logs
- vmaf_cdf_comparison.png: VMAF CDF plot
- lpips_cdf_comparison.png: LPIPS CDF plot
- plot_vmaf_cdf.py: VMAF CDF plotting code
- plot_lpips_cdf.py: LPIPS CDF plotting code

### Results Summary
| Metric | Ratio | GCC | Improvement |
|--------|-------|-----|-------------|
| VMAF (mean) | 75.06 | 60.30 | +24.5% |
| LPIPS (mean) | 0.0446 | 0.0679 | -34.4% |

## Usage
```bash
# Extract logs
tar -xzvf ltegccqoe_logs.tar.gz
tar -xzvf lteratioqoe_logs.tar.gz
tar -xzvf vmaf_lpips_results.tar.gz

# Plot VMAF CDF
cd vmaf_lpips_results
python3 plot_vmaf_cdf.py
```
