# SpatialVID-HQ Sampling & Download Kit

包含内容（自足可上传）：
- `sample_spatialvid_sampler.py`：加权采样器（时长 ≥3s，动力学/语义/质量分组归一后合成权重）。
- `sampled_manifest.csv`：当前 30k 抽样结果。
- `sampled_manifest_distribution.md`：分布报告与算法说明。
- `download_from_manifest.py`：根据 manifest 下载并只解压所需视频/标注。
- `get_instructions_enhanced.py`：指令生成脚本（interval 可设 4）。

快速使用
1) 安装依赖：`pip install pandas huggingface_hub`
2) 下载 30,000 条（默认取本目录的 `sampled_manifest.csv` 前 30k，可加 `--shuffle` 打乱后截取；如需更少，用 `-n` 覆盖）：
   ```bash
   huggingface-cli login  # 如未登录
   python download_from_manifest.py -n 30000 --repo-id SpatialVID/SpatialVID-HQ --local-dir SpatialVID/spatialvid_data
   ```
   - 会下载对应组的 `videos/group_xxxx.tar.gz` 和 `annotations/group_xxxx.tar.gz`，仅解压 manifest 中需要的 mp4 和注释目录。
   - tar 包保留不删，可手动清理。
3) 生成指令（interval=4）：
   - CSV：直接用本目录的 `sampled_manifest.csv`（如需改名，先 `cp sampled_manifest.csv filtered.csv` 再指定）。
   - 确保每个 `id` 有 `${dir_path}/{id}/reconstructions/poses.npy`，已有非空 `instructions.json` 会被跳过；需重算先删。
   - 运行示例（已将脚本放在本目录）：
     ```bash
     python get_instructions_enhanced.py \
       --csv_path sampled_manifest.csv \
       --dir_path /path/to/data/root \
       --intervals 4 \
       --alphas 0.05
     ```
     如代码里 `process_single_row` 调用顺序有问题，确保使用 `(args, row, param_combinations)` 顺序。

采样器要点
- 硬过滤：时长 ≥3 秒；美学分按亮度分桶切底（Bright 去底 5%，非 Bright 去底 2%）。
- 权重：动力学（moveDist/rotAngle/trajTurns，逆频率 α=0.8 部分均衡）、语义（亮度/时间/天气/scene/motionTags）与质量（motion score 轻降权高值、distLevel=0 轻降权、美学 z 缩放），各组均值归一后相乘，截断 [0.05,20]，无放回采样。
