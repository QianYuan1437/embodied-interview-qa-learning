# 阶段 6 · 工程落地与项目排障

> 按数据流和频率边界，把模型接进真实机器人系统
> 本页由原八卷题库自动抽取完整问答，并严格按知识依赖排序。原卷仍是内容源。

**先修**：至少完成阶段 0–4，最好跑过一次训练或机器人实验。

**本阶段共 49 题 · 通过标准**：面对 loss 正常但真机失败，能按固定链路定位而不是随机调参。

[← 上一步](05_sim2real_world_models.html) · [返回总路线](../roadmap.html) · [下一步 →](../roadmap.html#阶段-7a--操作--vla-岗支线)

---

## 第 1 步 · 先建立系统分层

> 先明确感知、规划、控制、通信和任务编排的接口。

<details class="qa">
<summary><span class="seq">01</span> <span class="origin">卷五</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×7</span> <b>Q01</b> · 感知-规划-控制三层架构各层的实时性要求是什么？为什么不能统一成一个频率？</summary>

**答**：三层频率由物理约束决定，不可合并：
- **控制层（1 kHz）**：直接驱动关节电机，PID/阻抗控制环要以 1 ms 周期计算力矩，否则关节振荡（实测>2 ms 伺服驱动器异常）
- **规划层（10-100 Hz）**：运动学/动力学规划、轨迹生成；受限于求解器耗时（IK 约 1-5 ms/次）
- **感知层（30 Hz）**：相机帧率 + 深度处理约 33 ms，网络推理延迟 20-100 ms（VLA）

**不能合并**：感知 30 Hz 远不够控制（电机需 1 kHz），若等感知完成再发控制命令，关节力矩 gap 33 ms → 振荡甚至摔倒。实际做法：**层间异步 + 状态预测**——控制层用上一次规划输出做插值，感知层独立更新感知状态。

**易错**：VLA 推理 6 Hz 接的是规划层（发任务指令/动作 chunk），不是直接替换 1 kHz 控制层；底层力矩控制仍需专用实时控制器。

</details>

<details class="qa">
<summary><span class="seq">02</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×5</span> <b>Q02</b> · ROS2 vs 自研中间件：大公司为什么不直接用 ROS2 做生产系统？DDS 的优缺点是什么？</summary>

**答**：
**DDS（Data Distribution Service）**：ROS2 底层通信标准，pub/sub + QoS 策略（RELIABILITY/DEADLINE/LIVELINESS）；自动发现节点、支持多机。

**ROS2 优点**：生态丰富（rviz/rosbag/Nav2）、开发快、社区活跃；**缺点**：
- DDS 序列化开销约 50-200 µs，高频（1 kHz）控制环难以接受
- GC + Python 节点延迟不确定性
- 不支持确定性硬实时（需 PREEMPT-RT 内核补丁才能接近）

**大公司自研原因**：① 降低关键控制路径延迟（自研共享内存 IPC < 1 µs）；② 系统级安全性（watchdog / 故障隔离）；③ 专有数据格式与 CI/CD 集成。

**实际选择**：研究/仿真阶段用 ROS2，量产前把控制关键路径替换为共享内存 + 自研调度；ROS2 保留为上层工具链（录包/可视化）。

**易错**：ROS2 不是实时系统，即使加 PREEMPT-RT 也只能做软实时（~1 ms 抖动）；硬实时（< 100 µs 抖动）需专用 RTOS 或 EtherCAT。

</details>

<details class="qa">
<summary><span class="seq">03</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×4</span> <b>Q03</b> · 状态机（FSM）和行为树（BT）在机器人任务编排中的区别？各有什么适用场景？</summary>

**答**：
| | FSM | 行为树（BT） |
|---|---|---|
| 结构 | 状态 + 转移函数，扁平图 | 树形层次，Selector/Sequence/Decorator |
| 复杂度 | 状态多时"状态爆炸" | 组合子模块，扩展性好 |
| 可读性 | 简单任务直观 | 复杂任务更清晰 |
| 中断 | 全局事件触发状态跳转 | Subtree 级打断，细粒度 |
| 调试 | 单状态易定位 | 树遍历可视化好 |

**适用**：FSM → 状态少、转移清晰的控制逻辑（如抓取的 "等待/运行/完成"）；BT → 多任务序列 + 条件检查 + 回退（如"先找目标 → 接近 → 抓取 → 失败则重规划"）。

**现代趋势**：BT 已成具身机器人任务编排主流（ROS2 BehaviorTree.CPP / Nav2），VLA 的语言指令通常解析为 BT 节点序列。

**易错**：BT 不是"更好的 FSM"，状态少时 FSM 更简洁；BT 的 tick 机制（每帧重新遍历）有轻微计算开销。

</details>

<details class="qa">
<summary><span class="seq">04</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×4</span> <b>Q04</b> · 共享内存 vs 消息队列 vs ROS2 Topic，在低延迟控制回路中应该选哪种？</summary>

**答**：
| 方式 | 单次通信延迟 | 吞吐 | 适用层 |
|---|---|---|---|
| 共享内存（mmap/posix） | < 1 µs | 极高 | 1 kHz 控制回路 |
| 消息队列（LCM/ZMQ） | ~10-50 µs | 高 | 规划层（10-100 Hz） |
| ROS2 Topic（DDS） | 50-500 µs | 中 | 感知/工具层（≤ 30 Hz） |

**实际分层**：控制关键路径（关节状态 ↔ 力矩指令）→ 共享内存，加 spinlock；规划 ↔ 控制 → LCM/ZMQ（10 Hz）；感知结果 → ROS2 Topic（30 Hz）。

**关键设计**：控制线程固定 CPU core（CPU affinity）+ 禁用抢占，共享内存 double buffer 防读写冲突。

**易错**：共享内存需手动处理并发安全，不加锁或用错锁（如 mutex 导致 priority inversion）反而更慢甚至死锁。

</details>

<details class="qa">
<summary><span class="seq">05</span> <span class="origin">卷五</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×5</span> <b>Q05</b> · 什么是阻抗控制（Impedance Control）？与位置控制和力控制的区别？机器人操作任务里怎么选？</summary>

**答**：**阻抗控制**：让机器人末端呈现可调"弹簧-阻尼-质量"特性：$F = K \Delta x + D \dot{x} + M \ddot{x}$，通过调节虚拟刚度 K、阻尼 D，控制机器人与环境交互时的柔顺性。

- **位置控制**：精确跟踪轨迹，刚性高；接触未知环境时力过大 → 损坏零件或机器人
- **力控制**：维持期望接触力；需要力矩传感器 + 稳定的力估计，对刚性接触不稳定
- **阻抗控制**：两者折中；环境已知时刚、接触时柔，适合大多数操作

**选型**：无接触精密移动 → 位置控制；稳定接触力（如打磨/拧螺丝） → 力控制；插销/组装/接触不确定 → 阻抗控制。

**易错**：阻抗控制不是"只要有力矩传感器就能用"——需要精确的动力学模型（质量矩阵 M）；低成本机器人通常用导纳控制（Admittance Control，在位置控制外环）替代。

</details>

---

## 第 2 步 · 沿真实项目数据链路前进

> 从奖励、观测和动作设计走到采集、同步、清洗与真机故障。

<details class="qa">
<summary><span class="seq">06</span> <span class="origin">卷三</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×7</span> <b>Q53</b> · 强化学习和模仿学习如何结合？在你的项目里是怎么用的？</summary>

**答**：**5 种主流组合**：
1. **IL 预训练 → RL fine-tune**：BC/DAgger 学初始 → PPO/SAC 精调；工业首选最稳。
2. **联合 loss**：$L = \alpha L_{\text{BC}} + \beta L_{\text{RL}}$；适合 demos 少 + 有 reward。
3. **Offline RL**：CQL / IQL / AWAC 从静态 demos 学，无需在线交互。
4. **GAIL**：discriminator 对抗，无需 reward。
5. **RLHF / RLAIF**：偏好 → reward model → PPO。VLA 后训练也走 RL-from-experience；其中 RECAP 是 **advantage-conditioned 变体**，不是典型 PPO。

**项目答题模板**：BC 预训练 → 定义 reward = task + smoothness → PPO + GAE fine-tune → 关键是 **early stopping + KL 约束** 防偏离 BC 太远。

**易错**：纯 RL 真机 sample 贵；纯 IL 长程崩；hybrid 是工业现实。

</details>

<details class="qa">
<summary><span class="seq">07</span> <span class="origin">卷三</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×6</span> <b>Q54</b> · 你的项目里奖励函数怎么设计？为什么这么设？尝试过哪些其他形式？</summary>

**答**：**设计原则**：
1. **Dense vs Sparse**：dense 收敛快但易 reward hacking；sparse 难学但目标明确。
2. **Shaping**：加 distance / progress 等中间信号引导。
3. **Multi-component**：`R = task_reward + safety_penalty + smoothness_penalty`，相加形成总奖励。
4. **Curriculum**：早期 dense 加快学习，后期切 sparse 防 hacking。

**项目答题框架（套你的项目讲）**：
- 任务奖励：成功完成给大 +R，关键 sub-event（接触 / 接近）给小正奖励。
- 安全惩罚：碰撞 / 关节限位 / 力超限给负奖励。
- 平滑惩罚：$-\alpha \|\Delta a\|^2$ 防抖动；trade-off：α 大动作平滑但响应慢。
- 尝试过的其他形式：纯 sparse 收敛慢、纯 dense 易 hacking；最终选 hybrid。

**易错**：reward hacking 不靠 reward 曲线判断——要看 rollout 视频是否真完成任务（模型常找"接近但不抓"刷分）。

</details>

<details class="qa">
<summary><span class="seq">08</span> <span class="origin">卷三</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×5</span> <b>Q55</b> · 你怎么收集数据？真机示教 vs 仿真 vs 人类视频，各自的优劣和落地代价？</summary>

**答**：
| 来源 | 优点 | 缺点 |
|---|---|---|
| **真机示教**（teleop/VR） | 保真度最高、含接触反馈 | 1 demo 30-60s，人工最贵（ALOHA / DROID / Bridge） |
| **仿真** | 无限量、可标注 | Sim2Real gap，接触/软体仿不准（RLBench / ManiSkill / Isaac） |
| **人类视频** | 海量、多样 | 无 action label，需 retargeting（Ego4D / Something / Epic-Kitchens） |

**实务路线**：① 人类视频做 representation 预训练（R3M / VC-1 / VIP）→ ② 仿真大规模 DR pretrain → ③ 真机 ~300 demos fine-tune。

**易错**：不要单一数据源——三者结合才 scale；纯真机太贵，纯仿真 gap 大。

</details>

<details class="qa">
<summary><span class="seq">09</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×3</span> <b>Q56</b> · 末端力控有噪声怎么办？阻抗控制 / 导纳控制怎么选？</summary>

**答**：
- **阻抗控制**（Impedance）：输入**期望位置** $x_d$，输出 **force/torque**；行为类似弹簧 + 阻尼，$F = K(x_d - x) + D \dot{x}$。
- **导纳控制**（Admittance）：输入**外力** $F_{\text{ext}}$，输出**位置变化**；行为是"外力推 → 位置响应"。

**选择**：
| 场景 | 选哪个 |
|---|---|
| 机器人**主动**接触（打磨、装配、插针） | **阻抗** |
| 人**主动**引导机器人（co-bot 教学） | **导纳** |
| 高刚度任务（精确定位） | 阻抗（高 K） |
| 高顺应性任务（抓软物） | 阻抗（低 K）或导纳 |

**力觉噪声处理**：
1. **低通滤波**（一阶 IIR / 卡尔曼）去高频抖动；
2. **死区**：小于阈值视为 0；
3. **力 / 力矩传感器标定**：去重力 + 偏置；
4. **冗余传感融合**：关节扭矩 + 末端 F/T 双重估算。

**易错**：阻抗 / 导纳是**对偶**关系，不是同义；阻抗高刚 / 导纳高柔，相反。

</details>

<details class="qa">
<summary><span class="seq">10</span> <span class="origin">卷三</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×3</span> <b>Q57</b> · 你的观测空间为什么这么设？图像 + proprio + force 多模态怎么对齐 / 归一化？</summary>

**答**：**典型 VLA 观测**：
- **图像**：1-4 帧 RGB，224×224 或 256×256，多视角（手腕相机 + 第三人称）。
- **Proprio**：关节位置（rad）+ 关节速度（rad/s）+ 末端位姿（SE(3)）。
- **Force/Torque**：末端 F/T 传感器 6 维 + 关节扭矩 N 维（可选）。

**对齐 / 归一化**：
1. **图像**：CHW float，预训练 mean/std 归一化（如 ImageNet 的 `[0.485, 0.456, 0.406]`）；多视角 concat 在 channel 维。
2. **Proprio**：每维 $(x - \mu) / \sigma$，$\mu / \sigma$ 来自训练集统计。
3. **Force**：通常归一化到 $[-1, 1]$（±10 N / 1 Nm 量程）；力觉噪声大需先低通滤波。

**时序同步**：相机、关节、F/T 频率不同，训练样本通常以策略频率 / 样本频率为基准（如 10/20/50 Hz）。相机取最近且不晚于样本时刻的帧，或先估计链路延迟后做 offset 校正；高频 proprio、F/T 按样本时刻插值或窗口聚合。底层伺服 / PD 控制仍可保持数百 Hz 到 1 kHz。

**历史窗口**：常用 4-8 帧图像 + 同步 proprio 序列；用 Transformer / RNN 编码时序。

**易错**：图像忘记归一化（直接喂 [0, 255]，权重崩）；proprio 不归一化（不同关节量纲差 100 倍，训练不稳）。

</details>

<details class="qa">
<summary><span class="seq">11</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×3</span> <b>Q58</b> · 在双臂 / 移动操作场景里，你怎么设计动作空间？关节空间 vs 末端空间，trade-off 在哪？</summary>

**答**：**两种动作空间**：
| | 关节空间（joint） | 末端空间（end-effector） |
|---|---|---|
| 输出 | N 维关节位置 / 速度 / 扭矩 | 6-DoF SE(3) 末端位姿 + gripper |
| 优点 | 直接给电机，无 IK 奇异 | 任务直观（"抓 cup"），数据效率高 |
| 缺点 | 模型需学复杂关节耦合 | 需 IK 解算，奇异点问题 |
| 数据需求 | 高（耦合复杂） | 低（任务对齐自然） |

**VLA 实务**：大多数 VLA 用**末端空间**——
- OpenVLA / RT-2：7 维（6-DoF 末端位姿 + 1 维 gripper）。
- π0：同上 + 多形态适配。
- 双臂：两套末端 = 14 维（ALOHA）。
- Mobile + 双臂：+ 2 维 base = **16 维**（Mobile ALOHA）。

**绝对 / 相对动作**：绝对动作输出目标关节值或目标末端位姿，适合标定稳定、低频轨迹复现；相对动作输出相邻控制步的 $\Delta q$ / $\Delta x$，对标定误差和物体扰动有一定鲁棒性，但会累积漂移，需要限幅、闭环校正和安全检查。答题时必须说清坐标系、单位、姿态表示、控制频率，以及夹爪 / 底盘维度。

**Trade-off**：
- **数据效率**：末端空间任务对齐好，少 demos 也能学（ACT 50 demos）。
- **物理稳定**：关节空间避免 IK 奇异，但模型要学更复杂映射。
- **跨 embodiment**：末端空间易标准化；关节空间因 DoF 不同难统一。

**易错**：末端空间的 IK 奇异 / 关节限位问题需要**底层控制器 + 安全检查**兜底，不能让模型完全裸跑。

</details>

<details class="qa">
<summary><span class="seq">12</span> <span class="origin">卷三</span> <span class="lv lv-l1">L1</span> <span class="freq">补充</span> <b>Q59</b> · 数据采集到训练的数据链路如何设计？需要记录哪些字段？</summary>

**答**：我会把它说成一条可复现的数据工程链路：先采 raw log，再做相机标定、时间同步、episode 切分、异常清洗、动作 / 状态归一化，最后导出统一 schema，比如 RLDS、LeRobot，或 HDF5 + metadata。字段至少包括时间戳、语言指令、图像观测、机器人状态、action、执行后状态、机器人 / 相机 / 控制频率等 metadata；如果有深度、相机标定、成功标签或子任务标签，也要一并记录。训练前还要按任务、场景、操作者或物体划分 train / val / test，避免同一个 episode 的相邻帧泄露到测试集。

**易错**：不要只说"收了一些视频"，VLA 数据最关键的是 observation-action-time 三者可追溯。

</details>

<details class="qa">
<summary><span class="seq">13</span> <span class="origin">卷三</span> <span class="lv lv-l1">L1</span> <span class="freq">补充</span> <b>Q60</b> · 多频率传感器如何时间同步？为什么必须同步？</summary>

**答**：真实机器人里相机、关节、力传感器和控制器频率通常不同，我会先统一时钟或记录硬件时间戳，再以策略训练的采样频率生成样本。相机取最近且不晚于样本时刻的帧，或在估计相机链路延迟后做 offset 校正；高频关节和力信号再按样本时刻插值、均值 / 末值聚合。同步的目的不是让底层控制降频，底层伺服仍常见于数百 Hz 到 1 kHz，而是让模型看到的 observation 对应它要模仿的 action。

**易错**：错位一两帧在视频里不明显，但 BC 会学成"滞后控制"，真机表现就是抓取慢半拍、接触时过冲。

</details>

<details class="qa">
<summary><span class="seq">14</span> <span class="origin">卷三</span> <span class="lv lv-l1">L1</span> <span class="freq">补充</span> <b>Q61</b> · 机器人数据异常值如何清洗？归一化怎么做？</summary>

**答**：清洗要分三层：帧级异常，如图像黑屏、时间戳跳变、关节速度尖峰；片段级异常，如遥操作中断、夹爪未响应；episode 级异常，如任务失败或碰撞。普通 BC 通常以成功演示和有效动作片段为主，明显坏帧和无效 episode 不直接混入同一个监督目标；如果失败片段带有恢复动作、偏好标注或奖励信息，可以用于恢复策略、offline RL、偏好学习，甚至作为纠错示范的一部分。归一化上，图像按 backbone 要求做 mean / std，proprio 和 action 用训练集均值方差或固定物理范围，夹爪二值 / 连续值要单独处理。

**易错**：归一化统计只能 fit 训练集；用全量数据统计就是数据泄露。

</details>

<details class="qa">
<summary><span class="seq">15</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">补充</span> <b>Q62</b> · 多任务混合训练 vs 单任务微调怎么取舍？什么时候会互相干扰？</summary>

**答**：多任务混训适合想要泛化能力，尤其任务共享视觉、抓取、放置等底层技能时，它能让模型学到更稳的表征；单任务微调适合上线前追求某个任务的成功率和稳定性。互相干扰通常出现在任务动作分布冲突、语言指令不清、数据量极不均衡，或机器人形态不同却硬混时。工程上会用 task balancing、按任务采样、混入旧任务数据、LoRA adapter，或先通用预训练再小学习率微调。

**易错**：多任务不必然提升，防遗忘也不是靠"混在一起"自动解决，要靠采样比例、保留集和分任务评测。

</details>

<details class="qa">
<summary><span class="seq">16</span> <span class="origin">卷三</span> <span class="lv lv-l1">L1</span> <span class="freq">补充</span> <b>Q63</b> · 训练中 loss 下降但真机成功率不升，怎么排查？</summary>

**答**：我会先判断这是离线指标和闭环执行不一致。第一步看 validation loss 是否同步下降，排除过拟合；第二步按任务、物体、场景、操作者分桶统计成功率和失败类型；第三步回放模型输出，看动作是否平滑、是否饱和、夹爪时机是否错；第四步查数据切分、归一化、坐标系、action delay 和推理频率。很多时候 loss 下降只是模型更会拟合平均动作，真机需要的是闭环纠偏和关键接触时刻的正确动作。

**易错**：不要只盯总 loss；机器人策略要看 rollout 视频、动作分布和真机分桶成功率。

</details>

<details class="qa">
<summary><span class="seq">17</span> <span class="origin">卷三</span> <span class="lv lv-l1">L1</span> <span class="freq">补充</span> <b>Q64</b> · 真机上机械臂停滞、动作不连续或漂移，怎么排查？</summary>

**答**：我会按"模型输出、通信链路、控制器、机器人状态"四层排。先记录模型 action、反归一化 action、发送到控制器的 command、机器人实际 joint / EEF 轨迹，确认是不是单位、坐标系、限幅或 action chunk 拼接出了问题；再查推理耗时和通信延迟，看是否控制频率掉帧；最后看 IK 是否到奇异点、关节限位、安全保护或速度 / 加速度约束触发。漂移常见于相对动作累积误差，停滞常见于动作被安全层裁掉或夹爪 / 末端坐标系错。

**易错**：不要一句话归因"模型不行"，必须用日志对齐 commanded、desired 和 actual trajectory。

</details>

<details class="qa">
<summary><span class="seq">18</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">补充</span> <b>Q65</b> · 长序列任务成功率低，或物体随机摆放就失败，原因和优化？</summary>

**答**：长序列失败通常是复合误差，前面每一步的小偏差都会把后续状态带出训练分布；随机摆放失败则多半是视觉定位、相机外参、深度尺度、语言 grounding 或训练数据覆盖不足。优化上，短期可以加 action chunking、重规划频率、失败恢复数据和关键子任务检测；数据上要做位置、背景、光照、物体实例的覆盖；架构上可用分层规划，把长任务拆成 pick、place、open 等技能。

**易错**：随机化不是只换背景图，末端与物体的几何关系、遮挡和接触状态也要覆盖。

</details>

<details class="qa">
<summary><span class="seq">19</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">补充</span> <b>Q66</b> · 如果加触觉、力反馈或 3D 信息，数据采集和模型要怎么改？</summary>

**答**：加这些模态首先是数据问题：触觉、力、点云都要有时间戳、标定和单位；力传感器要视安装方式做 bias / gravity compensation；点云要处理外参、深度尺度和缺失点。模型上可以把 3D 用 point encoder 或 voxel / BEV encoder，触觉和力用 MLP / Transformer 编成 token，再和视觉语言 token 融合。输出端是否预测力或阻抗目标取决于底层控制栈；很多项目只是把力觉作为 observation 和安全约束，不直接让 VLA 输出力。

**易错**：模态越多不一定越好；同步、标定和噪声处理不到位会让模型更不稳定。

</details>

<details class="qa">
<summary><span class="seq">20</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">补充</span> <b>Q67</b> · 本地评测、官方榜单和真机结果不一致，怎么解释和验证？</summary>

**答**：我会把三者看成不同分布。本地评测可能和训练集接近，官方榜单强调标准 benchmark，真机还多了延迟、标定、控制器和环境扰动。解释时先确认 action space、图像预处理、相机视角、任务成功定义和容差是否一致，再看是否用了同一 checkpoint、同一归一化统计和同一推理频率。验证上要固定随机种子和评测脚本，同时保留 rollout 视频和失败分类，最后用真机 A / B test 决策。

**易错**：榜单高不代表真机稳，真机低也不一定是模型差，可能是部署接口或标定错。

</details>

<details class="qa">
<summary><span class="seq">21</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">补充</span> <b>Q68</b> · LoRA / PEFT 微调 VLA 时冻结哪里？怎么验证没有灾难性遗忘？</summary>

**答**：常见做法是冻结大部分视觉 backbone 和语言 backbone，只在 LLM attention / MLP 的低秩矩阵、action head 或 projector 上训练；数据很少时冻结更多，数据充足且 embodiment 差异大时可以开放 action head、adapter 或后几层。验证不能只看新任务成功率，还要保留一组旧任务、基础语言理解和原始机器人任务作为 replay eval，看是否出现旧任务成功率下降、语言指令理解退化或动作分布漂移。

**易错**：LoRA 省显存但不自动防遗忘；学习率、rank、训练步数和 replay 数据同样关键。

</details>

---

## 第 3 步 · 形成数据飞轮与排障顺序

> 采集闭环之后，按可观测链路逐层排查失败。

<details class="qa">
<summary><span class="seq">22</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×6</span> <b>Q21</b> · teleop 遥操设备如何选型？VR / leader-follower / exoskeleton / Aloha-style 各适合什么场景？</summary>

**答**：
| 设备 | 示例 | 优势 | 劣势 | 适用场景 |
|---|---|---|---|---|
| **Leader-follower arm** | ALOHA, Lerobot SO-ARM100 | 力反馈自然，学习曲线低 | 需配套夹爪，双臂协调难 | 桌面操作、精细抓取 |
| **VR 手柄** | Quest 3 + ROS bridge | 低成本，6-DoF 追踪 | 无力觉，远端操作抖动大 | 大范围移动任务，数据量级 |
| **动作捕捉套装** | Rokoko / Vicon | 全身 DoF，丰富表达 | 昂贵，标注后处理复杂 | 人形全身操控 |
| **外骨骼** | Inspire Dexterous Hand + arm | 手指级灵巧度 | 穿戴复杂，延迟高 | 5 指灵巧操作（如拧瓶盖） |
| **数据手套** | SenseGlove / HaptX | 触觉反馈 | 贵，续航 | 精密触感任务 |

**2024-2026 主流**：ALOHA-style leader-follower（双臂 14-16 DoF）是最多公开数据集的选择；宇树 G1 用 VR + 全身运动捕捉。选型核心：**操作的 DoF 要求**（精细 → exo，范围 → VR，双臂 → leader-follower）。

**易错**：VR 手柄抖动会污染数据（需平滑滤波 / 仅用关键帧），不能直接当 GT 动作。

</details>

<details class="qa">
<summary><span class="seq">23</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×5</span> <b>Q22</b> · Open-X-Embodiment / DROID / Ego4D 三大数据集的区别与各自定位？</summary>

**答**：
| 数据集 | 规模 | 载体 | 特点 | 适用 |
|---|---|---|---|---|
| **Open-X-Embodiment** | 1M+ 轨迹，22 种机器人 | 多 embodiment | 最大多体系开放数据集；任务短/简单，多样性强 | VLA 预训练，跨机器人泛化 |
| **DROID** | 76K 轨迹，~350h，Franka Panda | 单 embodiment | 564 场景、86 个任务、50 名采集者；自然语言指令 | 真实场景操作，policy 微调 |
| **Ego4D** | 3500+ 小时视频，74 个地点 | 纯视频，非机器人 | 以人为主视角，活动多样；无动作标签 | 视觉表征预训练（视觉理解），不直接训策略 |

**关键区别**：OXE 多体系宽泛，DROID 单体系高质量，Ego4D 无动作标签（只能做视觉预训练）。VLA 预训练通常：Ego4D + OXE 做视觉/语言预训练 → 任务数据微调 → DROID 验证泛化。

**易错**：Ego4D 不能直接训练机器人策略（缺动作标签），只用于视觉表征学习；不要说"用 Ego4D 训策略"。

</details>

<details class="qa">
<summary><span class="seq">24</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×5</span> <b>Q23</b> · 如何设计高质量机器人数据采集流程？数据清洗与标注的关键点是什么？</summary>

**答**：**采集流程设计**：
1. **环境标准化**：固定照明/背景/相机位姿（减少无关变量），但 DROID-style 也需多场景覆盖泛化
2. **Operator 培训**：操作员统一培训（避免动作风格差异），多 operator 增加多样性（Mobile ALOHA 策略）
3. **同步录制**：多相机（wrist + overhead）+ 关节状态 + 时间戳对齐；< 1 ms 同步需**硬件触发**（外部触发信号）或 PTP（IEEE 1588，µs 级）；NTP 只能做毫秒级粗同步
4. **在线质量筛**：任务完成检测（如物体位置传感器）自动过滤失败轨迹

**数据清洗关键**：
- **抖动过滤**：VR 手柄输入需低通滤波（截止频率 5-10 Hz）
- **动作平滑**：去除突变（速度超阈值的帧）
- **失败轨迹剔除**：夹爪未闭合 / 末端超出工作空间 → 自动剔除
- **标注**：自然语言任务描述（多人标注取一致）；成功/失败标签

**易错**：不要只收集"成功轨迹"——失败轨迹（负样本）对 RLHF / offline RL 有价值；完全清洗掉失败数据使策略无法学习恢复。

</details>

<details class="qa">
<summary><span class="seq">25</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×4</span> <b>Q24</b> · 互联网视频预训练（Ego4D/Something-Something/YouTube）对机器人策略有什么用？有哪些根本局限？</summary>

**答**：**用处**：① 学习视觉表征（物体形状、纹理、手部运动先验）→ 下游机器人任务 fine-tune 数据需求减少 5-10×；② 学习物理常识（物体如何掉落、液体如何流动）→ 减少仿真的 domain gap；③ 语言-视觉对齐（理解任务指令）。

**典型使用**：Ego4D 预训练 → EgoVLP/MAE 视觉 encoder → 迁移到 VLA（如 Octo 用 ImageNet 预训练 ViT）；**R3M**（Nair et al., 2022）用 **Ego4D** 人类活动视频预训练，对桌面抓取任务有明显收益。

**根本局限**：
- **无动作标签**：视频只有像素，不知道机器人该输出什么关节角 / 力矩
- **视角不匹配**：人手视角 vs 机器人腕部相机视角有巨大 domain gap
- **物理差异**：人手柔顺，机器人刚性，力的分布完全不同
- **长尾分布**：互联网视频大量是日常活动，机器人精密操作数据极少

**易错**：视频预训练的收益主要在**视觉感知**层，不会"自动学会如何操控"——策略学习仍需机器人专属数据。

</details>

<details class="qa">
<summary><span class="seq">26</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×5</span> <b>Q25</b> · 数据飞轮（Data Flywheel）的核心闭环是什么？为什么 scale 起来很难？</summary>

**答**：**数据飞轮闭环**：部署机器人 → 采集交互数据（成功+失败）→ 过滤/标注 → 训练改进策略 → 更好的策略 → 更多/更难任务 → 继续采集。理论上闭环越快越强。

**为什么难 scale**：
1. **数据采集速度瓶颈**：teleop 需要人工操作，单台机器人采集约 1-5 demos/小时，1000 demos = 200-1000 人时
2. **数据多样性 vs 质量矛盾**：多场景保证泛化，但每场景样本少 → long-tail 问题
3. **标注成本**：自然语言任务描述 + 成功/失败标签 + 关键帧标注，人工成本非线性增长
4. **分布 shift**：旧数据与新策略的状态分布不一致 → 需 DAgger-style 在线数据收集
5. **Reset 成本**：真机每次 demo 后需 reset 场景，人工耗时大

**行业现状（2025）**：自主数据采集（机器人在夜晚自己采集）+ VR 远程采集集群是主要突破方向；Physical Intelligence（π）、Figure 都有大规模 teleop 采集基础设施。

**易错**：数据飞轮不是"有了数据就飞轮"，闭环的关键是**数据质量筛选 + 增量训练策略**，垃圾数据会反向拖累策略。

</details>

<details class="qa">
<summary><span class="seq">27</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×3</span> <b>Q26</b> · 自主数据采集（Autonomous Data Collection）有哪些思路？与 teleop 相比的优势和局限？</summary>

**答**：**主要思路**：
1. **Reset-free Learning**：策略自主探索，无需人工 reset（如 Forward-Backward RL，在"做任务"和"恢复初始态"间循环）
2. **Curiosity-Driven Exploration**：自动选择"信心低"状态收集数据（DAGGER 风格在线查询）
3. **Scripted / Heuristic Collection**：写简单程序控制机器人随机/系统地扫描工作空间，采集带 annotation 的场景数据
4. **Human-in-the-Loop**：策略自主运行，失败时触发远程 teleoperation 补全

**vs teleop 优势**：24/7 无人工，单机器人日采集量可达 teleop 的 10-50×；边际成本极低。

**局限**：
- 初始策略不够强时，自主探索只采到低价值数据（随机碰撞）
- 缺乏任务目标驱动（需要 reward 定义或任务成功检测）
- 安全性：无人监督下需硬件安全限位

**易错**：自主数据采集不是"让机器人自己学"——仍需要明确的成功/失败检测和数据标注机制。

</details>

<details class="qa">
<summary><span class="seq">28</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×6</span> <b>Q27</b> · 训练好的策略真机表现差，第一步怎么排查 sim2real gap？系统化排查流程是什么？</summary>

**答**：**系统化排查流程（由浅入深）**：

**Step 1 — 输入分布检查**：记录真机传感器数据（图像/关节状态）与仿真数据的分布差异（直方图对比）；常见：光照/背景/物体颜色偏差，关节摩擦力估计不准。

**Step 2 — 策略输出检查**：在真机上 rollout 时 log 动作分布；若策略输出与仿真动作差异大，说明观测 domain gap 大；若动作分布类似但执行失败，是执行器/物理 gap。

**Step 3 — 逐模块 ablation**：
- 关掉感知，直接输入仿真参考状态 → 排查控制 gap
- 用仿真相机 → 排查视觉 gap
- 用真实图像 + ground truth 状态 → 排查策略泛化

**Step 4 — 常见 gap 原因**：
- 物体质量/摩擦系数不准 → 加 domain randomization 重训
- 相机内参/外参偏差 → 重新标定
- 控制频率 / 延迟不匹配 → 统一仿真和真机延迟设置

**易错**：不要第一步就调超参数，先定位 gap 来源再针对性修；盲目加 DR 有时反而降低真机策略质量（过度泛化导致精度下降）。

</details>

<details class="qa">
<summary><span class="seq">29</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×5</span> <b>Q28</b> · 什么是 reward hacking？机器人训练中的常见表现和解决思路？</summary>

**答**：**Reward hacking**：策略找到了"高 reward 但违背任务意图"的捷径行为，即 reward 函数没有完整表达人的意图。

**机器人常见表现**：
- 抓取任务：夹爪直接压住物体（不抬起）触发"接触 = 抓到"reward
- 导航任务：机器人原地抖动触发"速度大 = 探索积极"reward
- 灵巧操作：过度用力挤压物体达成"接触力 > 阈值"的假成功

**解决思路**：
1. **Reward Shaping 精细化**：加约束（如同时检测抬起高度 + 接触力 + 位移）
2. **RLHF / Preference Learning**：人类偏好标注替代 reward 函数
3. **Demo-conditioned reward**：只有动作接近 demo 时才给 reward（如 GAIL/AIRL）
4. **多目标约束**：主 reward + 行为约束 penalty（如异常力矩惩罚）
5. **真机验证频率提高**：仿真训练 + 每 N 步真机评估，早发现 hacking 行为

**易错**：Reward hacking 不是"策略 bug"，是 reward 设计问题；加更多训练数据解决不了，必须修 reward 定义。

</details>

<details class="qa">
<summary><span class="seq">30</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×5</span> <b>Q29</b> · 灾难性遗忘（Catastrophic Forgetting）在 VLA 微调中怎么出现？如何缓解？</summary>

**答**：**出现场景**：将预训练 VLA（在大规模数据上训练的通用能力）在特定任务数据上**全参数微调**时，模型快速过拟合新任务 → 遗忘预训练时的语言理解/视觉泛化能力，在新任务上成功，其他任务失败。

**常见表现**：微调后在原任务上成功率骤降（如 OpenVLA 微调新桌面抓取 → 忘记开门）；语言指令理解变差（只能响应微调数据的指令风格）。

**缓解策略**：
1. **LoRA / PEFT**：只更新 < 1% 参数，冻结主干 → 最常用
2. **EWC**：Fisher 信息矩阵指导，惩罚重要参数大幅改变
3. **Replay / Co-training**：混入预训练数据（Mobile ALOHA co-train 策略）
4. **KI（Knowledge Insulation）**：π0.5 思路，stop-gradient 隔离 VLM 和 Action Expert
5. **差异 lr**：VLM backbone 用极小 lr（1e-5），action head 用较大 lr（1e-4）

**易错**：LoRA 不能完全防遗忘；彻底防遗忘仍需 co-training 混入原始数据。

</details>

<details class="qa">
<summary><span class="seq">31</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×4</span> <b>Q30</b> · 关节控制振荡的常见原因与调参思路？PID 和阻抗控制各怎么调？</summary>

**答**：**振荡原因**：
- PID P 增益过大 → 超调 + 振荡（欠阻尼）
- 控制频率低（> 10 ms 周期）→ 相位滞后 → 条件不稳定
- 关节静摩擦（stiction）→ 低速黏滑（stick-slip）现象
- VLA 动作 chunk 末端不连续 → 关节速度跳变

**PID 调参**：① Ziegler-Nichols 法（逐渐增 P 至临界振荡，读取 $K_u$ 和 $T_u$，代入公式计算 P/I/D）；② 人工逐步调：先清零 I/D，调 P 至刚好振荡，再加 D（微分减振荡），最后加 I（消除稳态误差）；③ 加前馈（Feedforward）：预计算重力补偿，减轻 P 的负担。

**阻抗控制调参**：虚拟刚度 K 太大 → 刚性振荡（减 K 或加 D）；阻尼 D 太小 → 欠阻尼（增 D 至临界阻尼 $D = 2\sqrt{KM}$）；质量 M 影响响应速度（通常设为实际惯量的 1-5×）。

**VLA chunk 振荡**：Chunk 边界加速度不连续 → 用三次样条插值平滑相邻 chunk 的连接；或减小 chunk 长度 H。

**易错**：不要把"振荡"和"稳态误差"混淆，两者病根不同（前者是 P/D 问题，后者是 I 问题）。

</details>

<details class="qa">
<summary><span class="seq">32</span> <span class="origin">卷五</span> <span class="lv lv-l3">L3</span> <span class="freq">🔥×3</span> <b>Q31</b> · Diffusion Policy 训练时的 Mode Collapse（模式坍塌）如何排查？</summary>

**答**：**Diffusion Policy 的 Mode Collapse**：多模态动作分布下，策略只学会一种模式（如总是选同一抓取方向），丢失其他合法方案。

**排查方法**：① 同一观测下多次采样（N=100）动作，绘 2D 投影；若全部聚成一团 → collapse；② log 各 diffusion step 的 loss，若小 t（精细步）loss 极低而大 t 偏高 → 过拟合单一模式；③ 检查 score 网络输出方差是否异常小。

**根本原因**：① 训练数据单模态（operator 风格单一）→ 增加操作员多样性；② Beta schedule 过早收紧 → 调整为 cosine schedule；③ CFG Guidance scale 过高 → 降低；④ lr 过大 → 降至 1e-4 以下。

**易错**：Diffusion Policy 本设计防 mode collapse，若仍 collapse 先查数据；与 GAN collapse 机制不同，无需改判别器。

</details>

<details class="qa">
<summary><span class="seq">33</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×3</span> <b>Q32</b> · 传感器漂移（Sensor Drift）怎么检测和补偿？以 IMU 和力矩传感器为例？</summary>

**答**：**IMU 漂移**：陀螺仪积分误差随时间累积（Gyro bias），表现为姿态估计随时间漂移（静止时角速度输出非零）。
- 检测：静置机器人采集 N 秒数据，计算静态时 bias 均值和方差
- 补偿：① 开机标定（校准 bias offset）；② **互补滤波 / EKF**：融合加速度计（无漂移但噪声大）和陀螺仪（短期精准但长期漂），EKF 状态量含 bias 项自动估计

**力矩传感器漂移**：温度变化导致零点漂移（Thermal Drift），表现为无负载时力/力矩读数随温度升高缓慢变化。
- 检测：预热机器人 5-10 分钟，监测空载读数变化（> 0.5 N 为需补偿）
- 补偿：① 运行前**重新清零（tare）**；② 建立温度-零点补偿模型（查表或线性拟合）；③ 选用内置温度补偿的传感器（ATI Axia / Rokbi）

**通用原则**：定期标定（每月或每 N 小时作业）；记录环境温度、湿度与漂移量，建补偿表。

**易错**：不要把"漂移"和"噪声"混淆——漂移是系统性偏差（低频），噪声是随机（高频）；滤波器设计不同。

</details>

<details class="qa">
<summary><span class="seq">34</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×3</span> <b>Q33</b> · VLA 推理时序抖动（Inference Jitter）如何影响控制？有哪些工程解决方案？</summary>

**答**：**问题**：VLA 推理延迟不固定（如均值 100 ms，标准差 20 ms），控制器收到动作指令的时刻不确定 → 关节速度跳变 → 轻则轨迹抖动，重则触发安全限位急停。

**影响分析**：若控制器按 1 kHz 插值 VLA 的 chunk 动作，当下一个 chunk 延迟到达，插值无法外推过长时间 → 动作"卡住"或突变；若插值时间超过 chunk 覆盖时域，末端处于未定义状态。

**工程解决方案**：
1. **Double Buffering + 预取**：控制器维护两个 chunk buffer，当前 chunk 执行时，后台异步请求下一个；推理时间 < chunk 执行时间（H × Δt）时抖动透明
2. **时间戳对齐**：VLA 输出动作时附带时间戳，控制器按绝对时间执行而非相对偏移
3. **速度平滑器**：最终动作前过一个速度限幅滤波器（max velocity / max acceleration），截断因时序抖动引起的瞬时加速度峰值
4. **Padding 策略**：chunk 设计时末尾几帧动作与上一段对齐（零加速度），给推理预留 buffer

**易错**：时序抖动不是"硬件故障"，是软件调度问题；加大 chunk H 可增加推理容忍时间，但增加 open-loop 误差。

</details>

---

## 第 4 步 · 最后处理速度和训练规模

> 模型先正确，再学习推理加速、边缘部署和分布式训练。

<details class="qa">
<summary><span class="seq">35</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×6</span> <b>Q06</b> · VLA 推理为什么慢（只有 6 Hz）？有哪些主流提速路线？</summary>

**答**：**根本原因**：VLA 基于自回归 LLM，动作 7 维离散化 → **7 token 串行解码**，7B VLA 单步约 150-200 ms，控制频率 ≤ 6 Hz。

**主流提速路线**：
1. **并行动作头**：OpenVLA-OFT、GR00T N1 同时解码所有维度，7 次串行 → 1 次 forward（显著加速）
2. **量化**：INT8 PTQ → 7B 权重 ~14 GB（FP16）→ ~7 GB（INT8），推理显存 8-10 GB，吞吐提升 30-50%
3. **Token 压缩**：π0-FAST 用 DCT + BPE 把 chunk 压成约 10-20 token，减少 AR 步数
4. **视觉特征复用**：跳帧更新视觉 token，减少 ViT forward 次数
5. **投机解码**：小 draft 模型先猜 k 个 token，大模型并行验证

**易错**：提速不等于升硬件——AR 串行是架构瓶颈；需并行化或 token 压缩才能根本提速。

</details>

<details class="qa">
<summary><span class="seq">36</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×6</span> <b>Q07</b> · INT8 / FP16 / AWQ / GPTQ 量化的区别？机器人推理部署推荐哪种？</summary>

**答**：
| 量化方案 | 粒度 | 精度损失 | 工具链 | 典型场景 |
|---|---|---|---|---|
| **FP16** | 全精度半精度 | 极小 | PyTorch AMP | 训练/A100 推理基线 |
| **INT8 PTQ** | 逐层 / 逐 channel | 小（VLA 可接受） | TensorRT / ONNX | Jetson Orin 边缘部署 |
| **AWQ** | 逐 channel，权重感知 | 极小（比 GPTQ 稳） | AutoAWQ | LLM/VLA INT4 |
| **GPTQ** | Block-wise 二阶优化 | 小 | AutoGPTQ | LLM INT4，离线量化 |

**机器人推荐**：
- 云端/工作站（A100/H100）→ BF16 训练 + FP16 推理
- Jetson Orin AGX（64GB）→ **INT8 PTQ（TensorRT）**：7B VLA 约 8-10 GB 显存，推理 8-12 Hz
- 更极限边缘（< 16 GB）→ AWQ INT4：7B → ~4 GB，但精度需验证

**易错**：AWQ 和 GPTQ 都是 INT4 量化，AWQ 保护"显著权重"通道不量化，精度更稳；不要把 PTQ 和 QAT 混淆（QAT 需重新训练，精度最高但成本高）。

</details>

<details class="qa">
<summary><span class="seq">37</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×5</span> <b>Q08</b> · TensorRT vs ONNX Runtime vs TorchScript：机器人部署场景如何选型？各有什么局限？</summary>

**答**：
| 框架 | 优势 | 局限 | 适用场景 |
|---|---|---|---|
| **TensorRT** | NVIDIA GPU 最优（层融合/kernel 选择），FP16/INT8 加速最佳 | 仅 NVIDIA GPU，编译耗时，算子覆盖有限 | Jetson/DGX 部署 VLA 推理 |
| **ONNX Runtime** | 跨平台（CPU/GPU/ARM），生态广，导出简单 | 不如 TensorRT 极致，部分 custom op 不支持 | x86 边缘盒 / 非 NVIDIA 平台 |
| **TorchScript** | 无需外部框架，直接 Python → C++ | 优化有限，JIT 图不稳定，性能弱于 TRT | 原型/调试/快速部署 |

**典型工作流**：PyTorch 训练 → ONNX 导出（中间格式）→ TensorRT 编译（Jetson 部署）。

**VLA 特殊挑战**：LLM 的 KV cache / 动态 shape 不易导出 ONNX；通常用 TensorRT-LLM（专为 LLM 优化的 TRT 版本）或 vLLM（服务器端）。

**易错**：TorchScript 不是推理框架，只是序列化格式；不要把 TorchScript 当成 TRT 的替代品用于生产。

</details>

<details class="qa">
<summary><span class="seq">38</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×4</span> <b>Q09</b> · Jetson Orin AGX 跑 7B VLA 的典型配置和瓶颈在哪？如何估算推理吞吐？</summary>

**答**：**Jetson Orin AGX 64GB**（2023，275 TOPS INT8，64 GB LPDDR5 统一内存）：

**典型配置**：
- 7B VLA INT8 量化 → ~8-10 GB 显存
- 推理吞吐：**8-12 Hz**（取决于视觉 encoder 大小和 chunk 长度）
- 功耗：~40-60W（vs A100 ~400W）

**估算方法**：FP16 模型 = 参数量 × 2 bytes；INT8 = 参数量 × 1 byte；7B × 1 byte = 7 GB，加 KV cache + 激活 ≈ 9-11 GB。推理延迟 ≈ forward FLOPs / 峰值算力（考虑 memory-bound 效率 40-60%）。

**瓶颈**：① 统一内存带宽（204 GB/s）是主瓶颈——LLM 推理 memory-bound；② 视觉 encoder（ViT-L 约 300M）单帧约 20 ms；③ 散热限制功耗 throttling。

**易错**：TOPS 是 INT8 峰值，实际 LLM 推理用不满（带宽受限）；不要用 TOPS 直接估算真实 token/s。

</details>

<details class="qa">
<summary><span class="seq">39</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×5</span> <b>Q10</b> · 知识蒸馏（Knowledge Distillation）的流程是什么？机器人场景有哪些适配挑战？</summary>

**答**：**KD 流程**：Teacher（大模型）软化输出（temperature T > 1 的 softmax 分布）→ Student 模仿 teacher 的"暗知识"（soft label + 中间层特征对齐），在小模型上实现接近大模型的性能。

**常规 KD 步骤**：① 确定 teacher（如 7B VLA）→ ② 设计 student（如 1B）→ ③ 在数据集上运行 teacher 生成 soft label → ④ student 用 KL 散度 + 任务 loss 联合训练。

**机器人场景挑战**：
- 动作输出是**多模态分布**（Diffusion/Flow Matching），KL 散度对多模态效果差；改用 **feature-level 蒸馏** 或 **score distillation**
- 训练数据量小（1K-50K demos），student 易过拟合 teacher
- 真机评估成本高，无法像 NLP 那样快速迭代 student 质量

**实际路线**：π0 系列用 PaliGemma 3B（SigLIP + Gemma 组合）作预训练 VLM backbone；LoRA 量化微调比全量 KD 更常用，成本更低。

**易错**：KD 不是"直接 copy teacher 权重 + 减小网络"，是软标签驱动的训练过程。

</details>

<details class="qa">
<summary><span class="seq">40</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×4</span> <b>Q11</b> · Flash Attention 在 VLA 推理中的收益是什么？KV cache 在 VLA 长 context 场景的必要性与局限？</summary>

**答**：**Flash Attention**（Dao et al., 2022）：分块计算注意力，不在 HBM 存储完整 $QK^T$ 矩阵，将内存从 $O(L^2)$ 降至 $O(L)$，同时减少 HBM 读写次数 → **VLA 长序列（图像 token ~256 + 文本 + 历史 chunk）推理速度提升 2-4×**，显存节省显著。

**KV Cache 必要性**：自回归解码时，每次生成新 token 都要重算历史 key/value → KV cache 把历史 K, V 缓存，只算新 token 的 Q，从 $O(n^2)$ 降到 $O(n)$，推理速度提升约 5-10×。

**VLA 中的局限**：
- 视觉 token（图像 ~256）× H=50 chunk × 推理步数 → KV cache 线性增长，Jetson 64 GB 统一内存可能撑不住长任务
- 每步动作需要**更新** KV（新观测 token），非纯生成场景，cache 命中率低于 NLP
- 解决方案：Sliding Window Attention（只缓存最近 K 步）或 Chunk-wise 更新

**易错**：Flash Attention 是训练/推理都有收益的算子优化，不是专门给推理用的；KV cache 是推理专属（训练用 gradient checkpointing 替代）。

</details>

<details class="qa">
<summary><span class="seq">41</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×3</span> <b>Q12</b> · batched inference 与机器人实时控制的矛盾如何解决？</summary>

**答**：**矛盾**：batched inference 通过聚合多个请求摊销固定 overhead，吞吐提升 N×；但单个请求必须等 batch 凑满才发，**延迟增加** = 等待时间 + 计算时间，与机器人实时控制的低延迟需求（< 100 ms）冲突。

**解决思路**：
1. **单路独占**：单机器人 → batch_size=1，不凑批，延迟最低但 GPU 利用率低
2. **时间窗口 mini-batch**：固定最大等待时间（如 10 ms），无论 batch 凑没凑满都发；在多机器人集群（Fleet）中平衡延迟和吞吐
3. **持续批处理（Continuous Batching）**：vLLM 实现，请求随到随入 batch，不固定等待窗口；适合云端推理服务
4. **Action Chunking 预计算**：一次 VLA forward 生成 H=50 步动作，低层控制器跑完再请求下次推理；实际推理频率 1-2 Hz，对 batch 要求低

**易错**：Action Chunking 不是"减少 VLA 调用频率"的妥协，而是 ACT 的核心设计思想（降低复合误差）；推理频率低是副产品。

</details>

<details class="qa">
<summary><span class="seq">42</span> <span class="origin">卷五</span> <span class="lv lv-l3">L3</span> <span class="freq">🔥×3</span> <b>Q13</b> · 投机解码（Speculative Decoding）的原理是什么？机器人 VLA 能用吗？有哪些挑战？</summary>

**答**：**原理**：用小 draft 模型（如 1B）串行快速生成 k 个候选 token，再用大 target 模型（如 7B）**并行验证**所有 k 个 token（一次 forward）；若验证通过则接受，否则截断重生成。理论加速比 = k / (1 + k × rejection_rate)，实测 NLP 场景 2-3×。

**机器人 VLA 的可行性**：
- **可行**：动作 token 分布相对简单（7 维连续动作离散化），draft 模型命中率可能较高
- **挑战 1**：VLA 动作 token 只有 7-350 个（chunk），speculation benefit 小（NLP 句子上千 token）
- **挑战 2**：需要维护两个模型（draft + target）的显存，Jetson 上极为紧张
- **挑战 3**：VLA 带视觉 token，draft 模型也需要处理图像 → 不是纯 LLM 投机

**实际应用**：主要见于云端 VLA 服务（多请求并发），边缘部署更常用量化 + 并行动作头（如 GR00T N1 的扩散式并行动作生成）；两者原理不同，但都减少了解码步数。

**易错**：投机解码不改变模型精度（验证步保证与 target 分布一致），是纯推理加速技巧。

</details>

<details class="qa">
<summary><span class="seq">43</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×7</span> <b>Q14</b> · DDP / FSDP / DeepSpeed ZeRO 三者区别？VLA（7B）训练用哪个？</summary>

**答**：
| 方案 | 切分内容 | 每卡所需显存 | 通信量 | 适用 |
|---|---|---|---|---|
| **DDP** | 不切分（每卡完整模型） | 完整参数 + 梯度 + 优化器 | all-reduce 梯度 | < 3B，单机多卡 |
| **FSDP（ZeRO-3）** | 参数/梯度/优化器全切分 | 1/N（+临时通信开销） | all-gather + reduce-scatter | ≥ 7B，多机 |
| **DeepSpeed ZeRO-1/2/3** | 逐级切分优化器/梯度/参数 | 递减 | 递增 | ≥ 7B，灵活配置 |

**7B VLA 推荐**：
- **4×A100（40GB）**：FSDP or ZeRO-2（切梯度+优化器，不切参数）→ 稳定快
- **8×A100（80GB）**：ZeRO-1（只切优化器）足够，通信少
- **多机（≥4 节点）**：ZeRO-3 / FSDP + NVLink 节点内、InfiniBand 跨节点

**实测规律**：ZeRO-3 显存最省但通信最多，跨机 InfiniBand 慢时吞吐下降明显；VLA 首选 **ZeRO-2 + activation offload** 平衡显存和速度。

**易错**：FSDP 是 PyTorch 原生的 ZeRO-3 等价实现，不是比 ZeRO 更先进，是平台选择（PyTorch vs DeepSpeed）。

</details>

<details class="qa">
<summary><span class="seq">44</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×5</span> <b>Q15</b> · VLA 训练需要多少显存？如何估算 7B 模型的训练显存？</summary>

**答**：**估算公式（混合精度训练，Adam optimizer）**：

显存 ≈ 参数 × (2 B FP16 参数 + 2 B FP16 梯度 + 4 B FP32 主参数 + 4 B Adam m + 4 B Adam v) + 激活值

= 参数量 × **16 bytes** + 激活值

**7B VLA 示例**：7 × 10⁹ × 16 = **112 GB**（仅模型状态），+ 激活值（batch 依赖，约 20-60 GB）→ 总计 **130-170 GB**。

**优化手段**：① gradient checkpointing：激活值只存 checkpoint 节点，重算其余，激活显存 → ~10 GB（代价：增加约 30% 计算量）；② ZeRO-3 切分到 8 卡：每卡 ~20 GB；③ INT8 量化 + LoRA：7B LoRA 约 20-30 GB（仅训练 adapter 参数，不更新全量权重）。

**典型配置**：7B VLA 全参数微调 → **8 × A100 80GB**（ZeRO-2）；LoRA 微调 → **4 × A100 40GB**。

**易错**："7B 模型 = 7 GB" 是 INT8 推理权重估算（1 byte/param）；FP16 推理权重约 14 GB；训练还需 Adam 优化器状态（额外 8 bytes/param），总量完全不同数量级。

</details>

<details class="qa">
<summary><span class="seq">45</span> <span class="origin">卷五</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×5</span> <b>Q16</b> · 混合精度训练（AMP）原理？FP16 vs BF16，VLA 训练建议用哪个？</summary>

**答**：**AMP 原理**：前向/反向用低精度（FP16/BF16）计算，维护 FP32 主参数副本用于更新；梯度放大（GradScaler）防 FP16 下溢（underflow）。节省显存约 50%，训练加速 2-3×（Tensor Core 专为低精度优化）。

**FP16 vs BF16**：
| | FP16（E5M10） | BF16（E8M7） |
|---|---|---|
| 指数位 | 5 位（范围小） | 8 位（与 FP32 同范围） |
| 精度位 | 10 位（精度高） | 7 位（精度略低） |
| 溢出风险 | 高（需 GradScaler） | 极低（范围与 FP32 一致） |
| 硬件支持 | A100/V100 均支持 | A100/H100 强支持；V100 不支持 |

**VLA 建议**：A100/H100 → **BF16**（无需 GradScaler，更稳定，VLM 大梯度场景不溢出）；V100 → FP16 + GradScaler。

**易错**：AMP 不是"全程 FP16"——优化器更新和权重维护仍是 FP32，只是前反向低精度。BF16 不需要 GradScaler。

</details>

<details class="qa">
<summary><span class="seq">46</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×5</span> <b>Q17</b> · Flash Attention 的原理是什么？VLA 训练中为何几乎是标配？</summary>

**答**：**标准 Attention 瓶颈**：$QK^T$（$L \times L$）需 $O(L^2)$ HBM 读写；VLA context 达 512-2048 token 时带宽成瓶颈。

**核心思路**：① 分块（Tiling）：Q, K, V 小块在 SRAM 上完成 softmax + 加权，不写中间矩阵回 HBM；② Online Softmax 修正：维护 running max/sum 保证数值等价；③ 反向时重算 attention（不缓存 $L^2$ 矩阵）。

**收益**：HBM 读写 $O(L^2) → O(L)$，速度 2-4×，显存大幅降低。

**VLA 几乎标配原因**：多帧图像 token（每帧 256）+ 文本 + 历史动作，context 长度大，标准 attention 显存紧张甚至 OOM。

**易错**：Flash Attention 只改变内存访问模式，不改变计算结果（数学等价）；与 KV cache 优化目标不同——Flash Attention 训练/推理通用，KV cache 仅推理。

</details>

<details class="qa">
<summary><span class="seq">47</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×4</span> <b>Q18</b> · gradient checkpointing 原理？VLA 训练中怎么用？与 ZeRO 如何配合？</summary>

**答**：**原理**：标准反向传播缓存所有前向激活（显存 $O(L \times depth)$）。Gradient Checkpointing 只保留每 N 层一个 checkpoint 节点，反向时从最近节点重算中间激活，以约 **30% 额外计算** 换取 **60-80% 激活显存节省**，且梯度数值不变（数学等价）。

**VLA 配置**：对 LLM backbone 每层开 `gradient_checkpointing=True`；视觉 ViT 层数少，可不开。

**与 ZeRO 配合**：ZeRO-2/3 切分参数/梯度显存；gradient checkpointing 切分激活显存，两者正交互补。典型：7B + ZeRO-2 + checkpointing → 4 × A100 40GB 可跑。

**易错**：不是"保存 ckpt 文件"，是激活重计算；开启后训练速度降低约 30%，不影响梯度准确性。

</details>

<details class="qa">
<summary><span class="seq">48</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×4</span> <b>Q19</b> · 单机多卡 vs 多机训练：VLA 常见配置与跨机通信的瓶颈在哪？</summary>

**答**：
| | 单机多卡（8 × A100） | 多机（如 4 × 8 卡） |
|---|---|---|
| 卡间带宽 | NVLink 600 GB/s（A100 SXM） | InfiniBand 200-400 Gb/s（~25-50 GB/s）|
| 通信延迟 | 极低（µs） | ms 级 |
| 扩展性 | 受机器限制 | 水平扩展 |
| 常见瓶颈 | 单机内存（8 × 80GB = 640GB） | 跨机 all-reduce 等待 |

**VLA 常见配置**：
- 7B 全参数：8 × A100 80GB（ZeRO-2），单机足够
- 13B-70B 或大批量：多机，用 InfiniBand + NCCL，ZeRO-3
- 通信优化：gradient compression（梯度稀疏化/1-bit）or Async SGD（有精度损失）

**跨机瓶颈**：7B 模型 FP16 梯度约 14 GB，InfiniBand 200 Gb/s（实际有效带宽 ~60%）传输需 ~1 s；gradient accumulation 增大 batch 可分摊通信开销。

**易错**：多机不是"卡越多越快"——强扩展效率（Strong Scaling Efficiency）在 8+ 节点后常见 < 80%；通信开销随节点数增加。

</details>

<details class="qa">
<summary><span class="seq">49</span> <span class="origin">卷五</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×3</span> <b>Q20</b> · torch.compile 在 VLA 训练中的加速收益与常见坑？</summary>

**答**：**torch.compile**（PyTorch 2.0+）：基于 TorchDynamo（Python 字节码捕获计算图）+ TorchInductor（生成 Triton GPU kernel），将 eager 模式编译为融合 kernel，减少 kernel launch 次数和 HBM 读写。

**典型收益**：纯 Transformer forward/backward 约 **10-30% 吞吐提升**（无数据 IO 瓶颈时）；VLA 因含视觉 encoder + 动作头，实测 5-20%（因图像预处理、动态 shape 等限制编译效率）。

**常见坑**：① **动态 shape**：VLA 输入长度变化 → 每种 shape 重编译（首次 1-3 min），加 `dynamic=True` 缓解；② **自定义 CUDA op**（如 Flash Attention）fallback eager，需显式标注；③ **silent fallback**：编译失败不报错，需加日志确认是否生效。

**VLA 建议**：主要对 LLM backbone 开，视觉 encoder 保持 eager 避免动态 shape 坑。

**易错**：torch.compile 不能替代 Flash Attention（解决不同层面），两者可叠加。

</details>

---

## 阶段结束时怎么复习

1. 点击“全部折叠”，只看题目口述答案。
2. 能说出答案后标记“已掌握”；不要因为“看懂了”就标记。
3. 第二天使用“只看未掌握”，第 7 天再完整复述一次。
4. 回到[总学习路线](../roadmap.html)，检查通过标准后再进入下一阶段。
