# Research Log

## [2026-02-16] 自动驾驶 Diffusion Planner 调研

### [2025-12-02] LAP: Fast LAtent Diffusion Planner with Fine-Grained Feature Distillation for Autonomous Driving
- **Authors**: Jinhao Zhang, Wenlong Xia, Zhexuan Zhou, Youmin Gong, Jie Mei
- **Link**: https://arxiv.org/abs/2512.00470v2
- **Summary**: 提出在VAE学习的latent space中进行规划的框架，解耦高层意图与低层运动学，实现10倍推理加速，在nuPlan benchmark上达到SOTA closed-loop性能。代码将开源于 https://github.com/jhz1192/Latent-Planner

### [2025-09-21] CoPlanner: An Interactive Motion Planner with Contingency-Aware Diffusion for Autonomous Driving
- **Authors**: Ruiguo Zhong, Ruoyu Yao, Pei Liu, Xiaolong Chen, Rui Yang, Jun Ma
- **Link**: https://arxiv.org/abs/2509.17080v1
- **Summary**: 统一框架联合建模多智能体交互轨迹生成与应急规划，采用pivot-conditioned diffusion机制锚定短期共享片段并生成长期分支，在nuPlan Val14和Test14上超越SOTA。

### [2026-01-19] PlannerRFT: Reinforcing Diffusion Planners through Closed-Loop and Sample-Efficient Fine-Tuning
- **Authors**: Hongchen Li, Tianyu Li, Jiazhi Yang, Haochen Tian, Caojun Wang, Lei Shi, Mingyang Shang, Zengrong Lin, Gaoqiang Wu, Zhihui Hao, Xianpeng Lang, Jia Hu, Hongyang Li
- **Link**: https://arxiv.org/abs/2601.12901v1
- **Summary**: 通过双分支优化框架对扩散规划器进行强化学习微调，同时开发nuMax模拟器实现比nuPlan快10倍的rollout，达到SOTA性能。

### [2026-01-21] HumanDiffusion: A Vision-Based Diffusion Trajectory Planner with Human-Conditioned Goals for Search and Rescue UAV
- **Authors**: Faryal Batool, Iana Zhura, Valerii Serpiva, Roohan Ahmed Khan, Ivan Valuev, Issatay Tokmurziyev, Dzmitry Tsetserukou
- **Link**: https://arxiv.org/abs/2601.14973v2
- **Summary**: 面向搜救无人机的轻量级图像条件扩散规划器，结合YOLO-11人体检测与扩散轨迹生成，在真实世界场景中达到80%任务成功率。已被HRI 2026 Late Breaking Report接受。
