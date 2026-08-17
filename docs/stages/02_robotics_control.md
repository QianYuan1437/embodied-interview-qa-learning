# 阶段 2 · 机器人学与控制闭环

> 从坐标表示到关节命令，建立动作真正落地的链路
> 本页由原八卷题库自动抽取完整问答，并严格按知识依赖排序。原卷仍是内容源。

**先修**：阶段 0 的坐标系直觉，以及基本向量 / 矩阵运算。

**本阶段共 13 题 · 通过标准**：能解释末端移动目标如何经过坐标变换、IK 和反馈控制变成电机命令。

[← 上一步](01_ml_foundations.html) · [返回总路线](../roadmap.html) · [下一步 →](03_rl_backbone.html)

---

## 第 1 步 · 从姿态与坐标变换开始

> 任何运动学问题都先明确相对坐标系。

<details class="qa">
<summary><span class="seq">01</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×12</span> <b>Q35</b> · 旋转矩阵、欧拉角、四元数三种姿态表示的区别和联系？</summary>

**答**：

| 表示 | 参数数 | 优点 | 缺点 |
|---|---|---|---|
| 旋转矩阵 $R \in SO(3)$ | 9（实际 3 自由度） | 无奇异、组合简单（矩阵乘法） | 冗余参数，存储/传输大 |
| 欧拉角（roll/pitch/yaw） | 3 | 直观（人类可理解） | **万向节死锁**（Gimbal Lock），依赖轴顺序 |
| 四元数 $q = [w,x,y,z]$，$\|q\|=1$ | 4（实际 3 自由度） | 无奇异、插值平滑（SLERP）、计算高效 | 不直观，有双倍映射（$q$ 和 $-q$ 表示同一转） |

**联系**：三者等价，可互相转换（旋转矩阵 ↔ 四元数 ↔ 轴角 ↔ 欧拉角）。

**机器人实践**：运动规划/插值用四元数；人机界面 / 调试显示用欧拉角；姿态矩阵运算用旋转矩阵；神经网络输出姿态通常用 6D 旋转表示（$R$ 的前两列）或四元数。

**易错**：欧拉角的旋转顺序（ZYX vs XYZ vs ZYZ）不同结果完全不同——拿到欧拉角必须确认约定；Gimbal Lock 发生在 pitch = ±90° 时 roll 和 yaw 轴重合。

</details>

<details class="qa">
<summary><span class="seq">02</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×10</span> <b>Q36</b> · 齐次变换矩阵（Homogeneous Transformation Matrix）是什么？如何用它表示坐标系变换？</summary>

**答**：**齐次变换矩阵** $T \in SE(3)$，将旋转 $R$ 和平移 $p$ 合并为 4×4 矩阵：

$$T = \begin{bmatrix} R_{3\times3} & p_{3\times1} \\ 0_{1\times3} & 1 \end{bmatrix}$$

**坐标变换**：若点在 frame B 中坐标为 $\tilde{q}_B = [x, y, z, 1]^\top$，在 frame A 中：$\tilde{q}_A = {}^A T_B \cdot \tilde{q}_B$。

**链式组合**：多个变换可直接矩阵连乘：${}^0 T_n = {}^0 T_1 \cdot {}^1 T_2 \cdots {}^{n-1} T_n$（正向运动学本质）。

**逆变换**：$T^{-1} = \begin{bmatrix} R^\top & -R^\top p \\ 0 & 1 \end{bmatrix}$，旋转部分取转置（正交矩阵性质）。

**易错**：旋转矩阵的逆是其转置（$R^{-1} = R^\top$），但整个齐次矩阵的逆**不是**直接转置 $T^\top$（平移部分要另外处理）。

</details>

<details class="qa">
<summary><span class="seq">03</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×9</span> <b>Q37</b> · D-H 参数法（Denavit-Hartenberg）是什么？四个参数各代表什么？</summary>

**答**：D-H 参数法是用**最少 4 个参数**描述相邻关节坐标系变换的标准化方法：

| 参数 | 含义 | 变化/固定 |
|---|---|---|
| $\theta_i$（关节角） | 绕 $Z_{i-1}$ 轴的旋转角 | **旋转关节变量**（固定关节为常数）|
| $d_i$（连杆偏距） | 沿 $Z_{i-1}$ 轴的平移距离 | **移动关节变量**（旋转关节为常数）|
| $a_i$（连杆长度） | 沿 $X_i$ 轴的距离（$Z_{i-1}$ 到 $Z_i$ 的公垂线长） | 固定（几何参数）|
| $\alpha_i$（连杆扭转角） | 绕 $X_i$ 轴从 $Z_{i-1}$ 转到 $Z_i$ 的角度 | 固定（几何参数）|

**正运动学**：给定所有关节变量 $\theta_i$（或 $d_i$），连乘 $T_i$ 得末端位姿：${}^0 T_n = \prod_{i=1}^n {}^{i-1}T_i$。

**两种约定**：标准 D-H（Craig） vs 改进 D-H（MDH / Spong）参数定义顺序略有不同，拿到参数表必须确认约定。

**易错**：标准 D-H 每帧 $X_i$ 沿公垂线方向，并不是"随便放"；如果机器人有平行或相交关节轴，D-H 坐标系有歧义，需额外约定。

</details>

---

## 第 2 步 · 从正运动学走到逆运动学

> 雅可比连接关节速度与末端速度，也是数值 IK 的核心。

<details class="qa">
<summary><span class="seq">04</span> <span class="origin">卷一</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×11</span> <b>Q39</b> · 雅可比矩阵（Jacobian）是什么？奇异性是怎么产生的？</summary>

**答**：$J(\theta) \in \mathbb{R}^{6 \times n}$ 把关节速度映射到末端速度：$\dot{x} = J\dot{\theta}$。上 3 行线速度 $J_v$，下 3 行角速度 $J_\omega$。旋转关节 $i$：$J_v^{(i)} = z_{i-1} \times (p_n - p_{i-1})$，$J_\omega^{(i)} = z_{i-1}$。

**奇异性**：$J$ 行秩降低（不满秩）时某些末端运动方向不可达（或需无穷大关节速度）。典型：手腕三轴共线、连杆完全伸直。此时 Moore-Penrose 伪逆病态（满行秩情况下 $J^\dagger = J^\top(JJ^\top)^{-1}$）→ 关节速度爆炸。

**缓解**：① 阻尼最小二乘（DLS）：$J^\dagger_{dls} = J^\top(JJ^\top + \lambda I)^{-1}$，$\lambda$ 引入阻尼，用精度换稳定；② 路径规划提前绕开奇异形位；③ 控制层限速。

**易错**：6-DOF 方阵 $J$ 直接取逆仅在满秩时有效；7-DOF 冗余臂 $J \in \mathbb{R}^{6 \times 7}$ 必须用伪逆，存在无穷多解，需加零空间约束来选优。

</details>

<details class="qa">
<summary><span class="seq">05</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×9</span> <b>Q38</b> · 逆运动学（IK）的解析解和数值解各有什么优劣？哪种更常用于 VLA 策略执行？</summary>

**答**：

**解析解（Analytical IK）**：
- 对特殊构型（如满足 Pieper 准则：3 轴交于一点的 6-DOF 机器人）可求闭式解；
- 优点：速度极快（毫秒级）、确定性强；
- 缺点：仅适用于特定构型，通用性差，解可能有多解需选优。

**数值解（Numerical IK）**：
- 基于雅可比矩阵的迭代法（梯度下降 / Newton-Raphson / Damped Least Squares）；
- 优点：通用（任意构型）、可加约束（关节限位、奇异回避）；
- 缺点：迭代耗时（ms 到 tens of ms），可能陷入局部最优，初值敏感。

**VLA 策略**：不同 VLA 的动作空间不同——OpenVLA 官方动作空间是**末端执行器 7 维增量**（$\Delta x, \Delta y, \Delta z, \Delta$roll, $\Delta$pitch, $\Delta$yaw + gripper），底层执行层需要 IK/OSC（操作空间控制）将其转换为关节指令。部分 VLA 直接输出关节角度，不需要 IK。**结论**：VLA 动作空间因模型而异，不能一概而论；但相比传统离线规划，VLA 的 IK 调用是实时嵌在控制循环中的。

**易错**：7-DOF 冗余机械臂有无穷多 IK 解（冗余自由度），需加零空间运动（null space motion）约束来选择"最优"解（如避开奇异形位）。

</details>

<details class="qa">
<summary><span class="seq">06</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×6</span> <b>Q43</b> · 什么是工作空间（Workspace）？奇异形位和工作空间边界有什么关系？</summary>

**答**：**工作空间**：机器人末端执行器能到达的所有**位置**集合（注：完整意义的可达性还需考虑姿态约束）。分：
- **可达工作空间**（Reachable）：至少以某一姿态能到达的位置集合；
- **灵巧工作空间**（Dexterous）：以任意姿态都能到达的位置集合（往往小得多）。

**与奇异形位的关系**：位置工作空间**边界**通常恰好是奇异形位（完全伸展或极度折叠）——此时 Jacobian 降秩，末端某方向运动需无穷大关节速度。内奇异点（如腕部奇异）在工作空间内部也可能存在。

**机器人设计取舍**：7-DOF 冗余臂扩大灵巧工作空间 + 提供零空间运动绕奇异，但增加控制复杂度。

**易错**：灵巧工作空间既受位置限制又受姿态约束，两者分开分析；可达工作空间描述的是位置可达性，不自动保证任意姿态下的可达性。

</details>

---

## 第 3 步 · 把目标接入反馈控制

> 区分控制空间，再理解 PID、阻抗与频率边界。

<details class="qa">
<summary><span class="seq">07</span> <span class="origin">卷一</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×7</span> <b>Q41</b> · 关节空间控制和任务空间（笛卡尔）控制的区别？各适合什么场景？</summary>

**答**：

- **关节空间控制**：控制目标是关节角度/速度 $\theta$，PD 控制在关节空间运行，无需 IK。**优点**：简单稳定、无奇异问题；**缺点**：末端路径不直（关节线性插值 ≠ 笛卡尔直线）。
- **任务空间（Cartesian）控制**：控制目标是末端位姿 $x$，需通过 Jacobian 或 IK 转换到关节空间。**优点**：末端路径可控（直线/圆弧）、易与视觉感知对接；**缺点**：奇异点附近不稳定，需 IK 计算开销。

**适合场景**：
- Pick-and-place、点到点运动 → 关节空间够用
- 精密装配（要求末端走直线）、力控 → 任务空间
- VLA 策略输出 → 因模型而异（OpenVLA 为末端增量、需底层 IK；部分模型直接输出关节角）

**易错**："笛卡尔控制"不等于"不需要 IK"——只是 IK 在每个控制循环内完成（数值迭代），且控制频率要够高（>100 Hz）才能近实时。

</details>

<details class="qa">
<summary><span class="seq">08</span> <span class="origin">卷一</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×8</span> <b>Q40</b> · PID 控制的三个参数各起什么作用？机器人关节 PID 调参时的典型问题？</summary>

**答**：**PID**：$u(t) = K_P e(t) + K_I \int e \,dt + K_D \dot{e}(t)$，$e = q_{desired} - q_{actual}$（关节角误差）。

- **$K_P$（比例）**：误差大则控制量大；太大 → 震荡；太小 → 稳态误差大。
- **$K_I$（积分）**：消除稳态误差（gravity compensation 不完美时的偏置）；太大 → 积分饱和（windup），超调 + 慢恢复。
- **$K_D$（微分）**：阻尼，预测趋势提前减速；太大 → 对噪声极敏感（放大高频噪声）；关节位置传感器有噪声时慎用大 $K_D$。

**机器人典型问题**：
- 负载变化（搬不同重物）→ 有效惯量变化 → 固定 PID 参数可能失稳，需自适应控制或惯量辨识。
- 重力补偿不完整 → 靠 $K_I$ 修正，易积分饱和。
- 柔性关节（弹性）→ 纯 PID 可能激发弹性振动，需加低通滤波或更高级控制（如弹性关节模型控制）。

**易错**：PID 是线性控制器，机器人动力学非线性（惯量、离心力、科里奥利力、重力随形位变化）；PID 在工作点附近可用，大范围运动需非线性补偿或现代控制。

</details>

<details class="qa">
<summary><span class="seq">09</span> <span class="origin">卷一</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×6</span> <b>Q42</b> · 阻抗控制（Impedance Control）和力控制的区别？具身机器人什么时候用力控？</summary>

**答**：

- **纯位置控制**：仅跟踪位置目标，接触时力无法限制（硬接触易损伤）。
- **力控制（Force Control）**：直接控制接触力，需要力/力矩传感器或力矩估计；精度高但刚性差（力变化时位置漂移）。
- **阻抗控制**：在期望位置轨迹上叠加弹簧-阻尼模型 $F = K(x_d - x) + B(\dot{x}_d - \dot{x})$，**将力偏差转化为位置偏差允许**；不需要显式力控制器，只要能控制关节力矩或末端位置。

**具身机器人使用场景**：
- 装配（轴孔配合/插拔连接器）：位置不确定时力控防止过载 → **阻抗/力控**
- 拧螺丝/研磨打磨：需要恒定接触力 → **力控**
- 普通 pick-and-place（抓轻物）：位置控制即可
- 人机协作（安全要求）：阻抗控制让机器人"柔软"，碰到人自动退让

**易错**：阻抗控制中 $K$（刚度）高 ≈ 位置控制；$K$ 低 ≈ 力控；调 $K/B$ 是在"硬度"和"力控精度"间权衡，不是随意设。

</details>

<details class="qa">
<summary><span class="seq">10</span> <span class="origin">卷一</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×5</span> <b>Q44</b> · 机器人控制频率（Control Frequency）的要求是什么？VLA 策略频率低有什么影响？</summary>

**答**：**基本要求**：控制频率需远高于系统最高频动态（奈奎斯特采样定理），一般：
- 关节 PD 控制：**1 kHz**（高刚度电机）或 **500 Hz**（标准）
- 力控 / 阻抗控制：**100-500 Hz**（力传感器带宽）
- 视觉反馈（闭环）：**30-100 Hz**（摄像头帧率限制）

**VLA 策略频率低的影响**：OpenVLA 在 Franka-Tabletop 约 **5 Hz**（串行 AR 解码 7 token），部分部署平台可达 15 Hz，大部分 VLA 在 5-25 Hz。
- **安全风险**：高动态任务（抓运动物体、避碰）控制环太慢，实际执行与规划脱节；
- **Action Chunking**（关键解法）：一次预测 K 步动作（如 K=10/20/50）并缓存，底层控制器以高频插值执行，策略只需低频推理；
- **π0**：用独立 Action Expert（Flow Matching，H=50 chunk）以约 50 Hz 频率输出动作，VLM 低频提供上下文理解；**GR00T-N1** 类似思路（Flow Matching action chunk），具体控制频率因机器人平台而异。

**易错**：控制频率和推理频率是两层：VLA 推理 10 Hz，但底层 PD 控制仍跑 1 kHz；两层解耦是工程关键。

</details>

---

## 第 4 步 · 最小手撕练习

> 用代码把变换、数值 IK 与 PID 连成可执行链路。

<details class="qa qa-handcoding">
<summary><span class="seq">11</span> <span class="origin">卷六</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×5</span> <b>✍ CH09</b> · 手撕齐次变换 / DH 正向运动学</summary>

**考察点**：齐次矩阵 T = [R, p; 0, 1]；DH 4 参数 (a, α, d, θ)；本实现用改进 DH（Craig），与标准 DH（Spong）矩阵形式不同；FK 由 T 连乘。

**实现**：

```python
import numpy as np

def dh_link(a, alpha, d, theta):
    # 改进 DH（Craig）：T_i^{i-1} = Rot_x(α_{i-1})·Trans_x(a_{i-1})·Rot_z(θ_i)·Trans_z(d_i)
    ct, st = np.cos(theta), np.sin(theta)
    ca, sa = np.cos(alpha), np.sin(alpha)
    return np.array([
        [ct,       -st,       0.0,   a],
        [st * ca,  ct * ca,  -sa,   -sa * d],
        [st * sa,  ct * sa,   ca,    ca * d],
        [0.0,      0.0,       0.0,   1.0],
    ])

def fk(dh_params, q):
    # dh_params: [(a, alpha, d, theta_offset), ...]；q: 关节角向量
    T = np.eye(4)
    for (a, alpha, d, theta_off), qi in zip(dh_params, q):
        T = T @ dh_link(a, alpha, d, theta_off + qi)
    # 末端位姿：左上 3×3 为 R，右上 3×1 为 p
    return T   # T[:3,:3] = R_end, T[:3,3] = p_end
```

**易错**：Craig 与 Spong 不可整链混用（前者坐标系固定在近端、Rot_x 先做；后者固定在远端、Rot_z 先做）；连乘顺序应 base → end。

</details>

<details class="qa qa-handcoding">
<summary><span class="seq">12</span> <span class="origin">卷六</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×6</span> <b>✍ CH07</b> · 手撕数值 IK（Jacobian 伪逆 / DLS）</summary>

**考察点**：循环 残差→Jacobian→Δq→更新；伪逆奇异处发散；DLS 加阻尼防爆炸；步长 clamp。

**实现**：

```python
import numpy as np

def ik_dls(fk, jac, q0, x_target, lam=0.05, alpha=0.5,
           tol=1e-4, max_iter=200, dq_max=0.2):
    # fk(q) → 末端位姿向量；jac(q) → 雅可比 (m×n)
    q = q0.copy()
    for _ in range(max_iter):
        e = x_target - fk(q)
        if np.linalg.norm(e) < tol:
            return q, True
        J = jac(q)
        # Damped Least Squares：J⁺_DLS = J'·(J·J' + λ²·I)^{-1}，奇异处仍数值稳
        JJt = J @ J.T
        damp = (lam ** 2) * np.eye(JJt.shape[0])
        dq = J.T @ np.linalg.solve(JJt + damp, e)
        # 步长 clamp 防单步过大震荡 / 跨越奇异
        n = np.linalg.norm(dq)
        if n > dq_max:
            dq *= dq_max / n
        q = q + alpha * dq
    return q, False
```

**易错**：奇异附近用纯伪逆 → 关节速度爆炸；α 过大震荡发散、过小收敛慢；忽略关节限位（重活岗会追问 weighted clamping / null-space）。

</details>

<details class="qa qa-handcoding">
<summary><span class="seq">13</span> <span class="origin">卷六</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×9</span> <b>✍ CH01</b> · 手撕位置型 / 增量型 PID</summary>

**考察点**：PID 三项物理意义；位置型 vs 增量型公式差异；离散化 dt 处理；D 项放反馈避免设定值阶跃尖峰。

**实现**：

```python
class PID:
    def __init__(self, Kp, Ki, Kd, dt):
        self.Kp, self.Ki, self.Kd, self.dt = Kp, Ki, Kd, dt
        self.integral = 0.0
        self.prev_err = 0.0      # e(k-1)
        self.prev_prev_err = 0.0 # e(k-2)，增量型 D 项要
        self.prev_meas = 0.0     # 位置型 D 项放反馈量

    def position(self, sp, y):
        # 位置型：u(k) = Kp·e + Ki·Σe·dt + Kd·(-Δy/dt)
        e = sp - y
        self.integral += e * self.dt
        d = -(y - self.prev_meas) / self.dt   # 反馈微分，避免设定值阶跃尖峰
        self.prev_meas = y
        return self.Kp * e + self.Ki * self.integral + self.Kd * d

    def incremental(self, sp, y):
        # 增量型：Δu = Kp·(e-e₁) + Ki·e·dt + Kd·(e-2e₁+e₂)/dt
        e = sp - y
        du = (self.Kp * (e - self.prev_err)
              + self.Ki * e * self.dt
              + self.Kd * (e - 2 * self.prev_err + self.prev_prev_err) / self.dt)
        self.prev_prev_err, self.prev_err = self.prev_err, e
        return du   # 累加到上一步 u 上由调用方负责
```

**易错**：位置型必须配 anti-windup（→ CH02）；增量型需保存 e(k-2) 才能算 D；D 项放误差时 setpoint 阶跃 → 微分尖峰，工程上一律放反馈量。

</details>

---

## 阶段结束时怎么复习

1. 点击“全部折叠”，只看题目口述答案。
2. 能说出答案后标记“已掌握”；不要因为“看懂了”就标记。
3. 第二天使用“只看未掌握”，第 7 天再完整复述一次。
4. 回到[总学习路线](../roadmap.html)，检查通过标准后再进入下一阶段。
