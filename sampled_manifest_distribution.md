# Sampled Manifest Summary (30,000 clips)

- Source: `SpatialVID/spatialvid_data/sampled_manifest.csv`
- Total duration: **95.67 hours** (mean clip length: 11.48 s)
- Sampling method: weighted sampler with camera-trajectory diversity (see “Sampling recipe” below).

## Numeric fields

| Field | count / unique | min / max | mean | median | std | quantiles q01 / q05 / q10 / q25 / q50 / q75 / q90 / q95 / q99 |
| --- | --- | --- | --- | --- | --- | --- |
| num frames | 30,000 / 754 | 73 / 901 | 530.03 | 450 | 280.01 | 91 / 124 / 175 / 300 / 450 / 899 / 900 / 900 / 900 |
| fps | 30,000 / 626 | 22.32 / 60.01 | 45.62 | 59.94 | 15.39 | 23.98 / 24.00 / 29.97 / 29.97 / 59.94 / 60.00 / 60.00 / 60.00 / 60.01 |
| aesthetic score | 30,000 / 29,622 | 4.41 / 6.21 | 4.84 | 4.81 | 0.247 | 4.440 / 4.483 / 4.533 / 4.651 / 4.809 / 4.986 / 5.165 / 5.285 / 5.529 |
| luminance score | 30,000 / 29,785 | 65.03 / 130.00 | 108.48 | 112.11 | 15.97 | 67.27 / 75.83 / 83.95 / 98.77 / 112.11 / 121.33 / 126.45 / 128.22 / 129.64 |
| motion score | 30,000 / 29,912 | 3.00 / 9.00 | 4.94 | 4.62 | 1.47 | 3.031 / 3.153 / 3.294 / 3.716 / 4.622 / 5.875 / 7.176 / 7.908 / 8.700 |
| ocr score | 30,000 / 14,404 | 0.0 / 0.7342 | 0.0124 | 0.0051 | 0.0236 | 0 / 0 / 0 / 0.0008 / 0.0051 / 0.0138 / 0.0316 / 0.0497 / 0.1062 |
| moveDist | 30,000 / 29,992 | 0.00146 / 38.27 | 2.25 | 1.480 | 2.71 | 0.0210 / 0.0669 / 0.1388 / 0.4844 / 1.480 / 2.941 / 4.993 / 7.335 / 13.628 |
| distLevel | 30,000 / 5 | 0 / 4 | 2.71 | 3 | 1.21 | 0 / 0 / 1 / 2 / 3 / 4 / 4 / 4 / 4 |
| rotAngle | 30,000 / 29,992 | 0.1500 / 6.0422 | 0.761 | 0.534 | 0.661 | 0.1549 / 0.1756 / 0.2024 / 0.2988 / 0.5337 / 0.9815 / 1.6512 / 2.1399 / 3.1880 |
| trajTurns | 30,000 / 5 | 0 / 4 | 0.961 | 1 | 0.743 | 0 / 0 / 0 / 0 / 1 / 1 / 2 / 2 / 3 |
| dynamicRatio | 30,000 / 29,416 | 0 / 0.5827 | 0.1046 | 0.0906 | 0.0760 | 0 / 0.0061 / 0.0171 / 0.0463 / 0.0906 / 0.1489 / 0.2094 / 0.2486 / 0.3291 |
| duration (s) | 30,000 / 3,237 | 3.00 / 15.04 | 11.48 | 14.98 | 4.30 | 3.10 / 3.70 / 4.45 / 7.41 / 14.98 / 15.00 / 15.00 / 15.02 / 15.02 |
| weight | 30,000 / 20,076 | 0.270 / 16.17 | 1.29 | 1.14 | 0.87 | 0.482 / 0.482 / 0.532 / 0.785 / 1.138 / 1.447 / 1.951 / 3.366 / 4.825 |

## Categorical Top-10 (proportion)
- motionTags: right,forward 21.50%; left,forward 19.82%; forward 19.26%; stationary 5.07%; up,left,forward 4.06%; right,left,forward 3.65%; right 3.15%; up,forward 2.70%; right,up,forward 2.22%; left 2.00%
- sceneType: Urban;Street Scene 23.17%; Natural Landscape; Mountain Road 3.73%; Interior; Living Room 2.75%; Natural Landscape; Forest Trail 1.76%; Interior; Bedroom 1.35%; Interior; Kitchen 1.11%; Natural Landscape; Mountain Valley 1.10%; Natural Landscape; Mountain Trail 1.04%; Urban; City Street 1.01%; Rural; Village Street 0.90%
- brightness: Bright 76.22%; Dim/Dark 22.46%; Dim 1.18%; others ≪1%
- timeOfDay: Daytime 44.13%; Daytime (Midday/Noon/Afternoon) 27.01%; Night 10.47%; Unknown 10.35%; Dawn 1.87%; Dusk 1.54%; Dusk/Evening 1.51%; others <1%
- weather: Sunny 42.20%; Cloudy 26.38%; Unknown 15.47%; Rainy 9.43%; Snowy 5.52%; others ≪1%
- crowdDensity: Deserted 50.94%; Sparse 28.13%; Moderate 10.91%; Crowded 7.87%; Unknown 2.15%

## Sampling recipe 采样策略
- 过滤条件：
  - 时长 ≥ 3 秒
  - 美学分按亮度分桶过滤：Bright桶内 去美学分数底部 5%，非Bright桶内 去美学分数底部 2%
- camera trajectory：
  - moveDist 分桶：S<0.5, M<3, L<8, XL≥8；rotAngle：S<0.5, M<1.5, L<3, XL≥3；trajTurns：0 / 1 / 2 / 3+；逆频率 (α=0.8) 做均衡来diverse
- 质量权重：
  - motion score > 8.8 镜头太晃降权重；distLevel=0 镜头静止降权重
  - 美学分按 z-score 线性缩放，截断 [0.5, 1.5]
- 语义多样性权重：
  - brightness α=0.6，timeOfDay α=0.6，weather α=0.6，sceneType α=0.7，motionTags α=0.5；各自权重设上下限
- 合成权重：
  - 先分别求 W_dyn=W_move×W_rot×W_turn、W_sem=亮度×时间×天气×scene×motionTags、W_qual=motion score×distLevel×美学；各自归一到均值=1，再相乘，最后截断 [0.05, 20]，无放回抽样（size=N）

## Duration
- Total: ~96.17 hours
- Mean clip: 11.54 s
