# MusicianAgent: 多代理音乐编排系统

本项目基于 **Google Agent Development Kit (ADK)** 和 **Gemini 3 Flash Preview** 实现了一个专业的音乐编排系统。它采用分层多代理架构，将复杂的音乐创作需求分解为高质量的特定音轨。

## Overview
![Overview](readme_imgs/image.png)

## 🎵 功能特性
- **分层编排**：由中央“指挥官” (Orchestrator) 协调专业子代理。
- **乐理对齐**：乐理专家 (Musicologist) 代理确保调性和节奏的一致性。
- **专业合成**：专门用于打击乐和弦乐生成的代理，调用 **Google Cloud Lyria 2** 模型。
- **混音工程**：音频工程师代理负责最后的音轨合并与母带处理。
- **原生 ADK 支持**：支持通过 `adk web` 或 `adk run` 启动。
- **混合架构**：
    - **逻辑推理**：Gemini 3 Flash Preview (区域: `global`)
    - **音乐合成**：Lyria 2 REST API (区域: `us-central1`)

## 🏗 架构与工作流

系统采用 **“指挥官-蜂群” (Maestro-Swarm)** 模式。以下是代理间的协作流程：

```mermaid
sequenceDiagram
    actor User as 用户
    participant Orchestrator as 🎻 编排代理 (指挥官)
    participant Musicologist as 🎹 乐理专家 (理论)
    participant Synthesis as 🎸 合成代理 (乐乐手)
    participant Engineer as 🎚 音频工程师

    User->>Orchestrator: "创作一首史诗级电影配乐"
    activate Orchestrator
    Orchestrator->>Musicologist: 调性/速度检查
    Musicologist-->>Orchestrator: 审核通过 (110 BPM, A 小调)
    
    Orchestrator->>Synthesis: 任务委派 (节奏与旋律)
    activate Synthesis
    Synthesis-->>Orchestrator: 生成音频分轨 (.wav)
    deactivate Synthesis
    
    Orchestrator->>Engineer: 混音与母带处理
    activate Engineer
    Engineer-->>Orchestrator: 完成母带 (master.wav)
    deactivate Engineer
    
    Orchestrator-->>User: 返回最终作品
    deactivate Orchestrator
```

### 代理角色与输入示例

| 代理名称 | 图标 | 职责详解 | 典型输入示例 |
| :--- | :---: | :--- | :--- |
| **编排代理 (Orchestrator)** | 🎻 | **总指挥**：解析用户指令，管理全局 `MusicSessionState` 会话状态，并协调各子代理间的委派流程。 | "创作一段 140 BPM 的暗黑赛博朋克曲风" |
| **乐理专家 (Musicologist)** | 🎹 | **理论专家**：确保流派与速度 (BPM) 匹配，并建议调性和音阶，使所有合成音轨完美调和。 | "为忧郁的钢琴曲建议一个合适的音阶" |
| **打击乐专家 (Percussion Expert)** | 🥁 | **节奏专家**：根据流派和氛围，为 Lyria 2 编写富有细节和纹理的提示词，并生成打击分轨。 | "带有失真底鼓的重工业风鼓组" |
| **弦乐专家 (String Expert)** | 🎻 | **旋律专家**：专注于弦乐和音垫的情感表达，确保旋律层符合乐理专家的调性设定。 | "富有情感且带有深长呼吸感的大提琴独奏" |
| **音频工程师 (Audio Engineer)** | 🎚 | **后期制作**：将各分轨混音为 `master_mix.wav`，并将所有输出注册为 ADK Artifacts 供用户手动播放。 | "将打击乐和弦乐轨道连接并合成为最终母带" |

<details>
<summary><b>🔍 深度解析：代理实现原理 (技术细节)</b></summary>

#### 1. 编排代理 (Orchestrator - 指挥官)
- **核心原理**：状态驱动的分层协调机制。
- **工作流**：
    - **会话管理**：初始化并更新 `MusicSessionState`（包含 BPM、调性、轨道列表）。
    - **A2A 委派**：通过 ADK 的 `InvocationContext` 管理多代理间的通信流。
    - **元数据同步**：确保子代理生成的提示词 (Prompt) 能够回传到全局状态，实现前端 UI 的透明显示。
    - **触发机制**：仅在所有请求的轨道均已注册到状态后，才触发最终的混音任务。

#### 2. 乐理专家 (Musicologist - 理论家)
- **核心原理**：乐理约束与结构化校验。
- **工作流**：
    - **技术制图**：将抽象的情绪（如“雄伟”）映射为具体的技术参数（如“100 BPM, D 小调”）。
    - **合规检查**：使用 `alignment_check_tool` 验证指挥官的编排方案在音乐性上是否连贯。

#### 3. 合成专家 (打击乐与弦乐)
- **核心原理**：基于 Lyria 2 的“自愈式”合成环路。
- **实现方案**：
    - **引擎核心**：直接通过 REST API 调用位于 Vertex AI (`us-central1` 区域) 的 **Google Lyria 2 (lyria-002)**。
    - **自愈算法**：
        - 若提示词触碰安全过滤器（如涉及敏感词或版权名），代理会捕获特定错误信号。
        - **逻辑反思**：利用 Gemini 3 分析被拦截的提示词，识别冲突点。
        - **提示词重构**：自动将冲突词汇替换为音乐描述性更强的中性词汇（如 “War Drums” → “Intense Cinematic Industrial Percussion”），并自动发起重试（最多 2 次）。
    - **Artifact 处理**：将生成的音频流保存为 `ADK Part` 对象，并同步生成 `.json` 元数据支持 Premium UI 显示。

#### 4. 音频工程师 (Audio Engineer - 制作人)
- **核心原理**：基于 DSP 的多轨叠加求和。
- **实现方案**：
    - **Numpy 引擎**：将所有 WAV 分轨转换为 `float32` 数值矩阵。
    - **长度对齐**：自动为较短的轨道填充静音采样，确保所有音轨在时间轴上完全对齐。
    - **累加混音 (Additive Mixing)**：对所有采样的数值进行数学求和，实现真正的多乐器合奏（而非简单的顺序拼接）。
    - **削波保护 (Clipping Protection)**：应用安全削波层，防止多轨叠加产生的采样值溢出导致的 16-bit PCM 失真。
</details>

<details>
<summary><b>🛠 指挥官的任务工具箱 (功能列表)</b></summary>

| 代理名称 | 工具名称 (Tool) | 功能描述 | 技术原理 |
| :--- | :--- | :--- | :--- |
| **编排代理** | `music_theory_alignment_tool` | 乐理对齐校验 | 向乐理专家发起委派，确保在正式合成前序列的逻辑一致性。 |
| **乐理专家** | `alignment_check_tool` | 结构化审计 | 对当前的 BPM、调性和轨道列表进行最后的乐理审查。 |
| **打击乐专家** | `generate_audio_tool` | 节奏合成引擎 | 调用 Lyria 2 API；实现本地 WAV 持久化及 ADK Artifact 自动注册。 |
| **弦乐专家** | `generate_audio_tool` | 旋律合成引擎 | 类似打击乐工具，但针对管弦乐和旋律性音色进行了提示词优化。 |
| **音频工程师** | `mix_tracks_tool` | 高级混音处理 | 使用 `numpy` 进行采样对齐的矩阵求和，并包含 16-bit 整数削波保护。 |
| **音频工程师** | `play_audio_tool` | UI 系统集成 | 将生成的母带文件注册到 ADK 仪表盘，供用户手动点击播放。 |

</details>

## 🚀 快速入门

### 前置条件
- Python 3.10+
- 拥有 Gemini API 访问权限的 Google Cloud 项目
- 在虚拟环境中已安装 `google-adk`

### 环境配置
1. 克隆仓库到本地。
2. 激活虚拟环境。
3. 配置 Google Cloud 凭据（例如：`gcloud auth application-default login`）。

### 运行系统

您可以通过交互式 CLI 或 Web UI 运行编排系统。

#### 步骤 2：启动高级工作站 (v0.2 Premium Studio)
这是体验玻璃拟态 UI、实时日志和多轨混合的最佳方式。

1.  **启动 ADK 后端引擎**:
    ```bash
    PYTHONPATH=. ./.venv/bin/adk api_server agents/
    ```
    *请保持此终端开启。*

2.  **启动 Premium Bridge (前端)**:
    ```bash
    # 在新终端中运行
    python3 api_server.py
    ```

3.  **访问 Studio**: 在浏览器中打开 [http://localhost:8080](http://localhost:8080)。

#### 步骤 3：启动标准 ADK Web UI
如果您更喜欢原始的 ADK 界面：
```bash
PYTHONPATH=. ./.venv/bin/adk web agents/
```
访问 [http://localhost:8000](http://localhost:8000)。

#### 步骤 4：交互式 CLI 模式
```bash
PYTHONPATH=. ./.venv/bin/adk run agents/orchestrator
```

#### 步骤 3：验证输出
- 代理将模拟音频生成过程（目前使用模拟文件名）。
- 您可以在最终响应中看到音轨列表和“母带”路径。

### 🌟 实战演练示例

#### 例子 A：史诗级电影配乐
- **输入词**：*"帮我创作一首史诗级的电影配乐。我想要激昂的小提琴旋律，背景要有沉重的战鼓声，营造一种英雄出征前的壮丽感。"*
- **流程**：指挥官咨询乐理专家（设定 D 小调，100 BPM），然后委派给弦乐和打击乐专家生成提示词。

#### 例子 B：赛博朋克电子乐
- **输入词**：*"来一首 140 BPM 的赛博朋克电子乐。要那种霓虹感十足的合成器音效，加上强力且冰冷的工业电子鼓点。"*
- **流程**：指挥官锁定 BPM，并要求合成代理生成高能量的工业风电音提示词。

#### 例子 C：旅行 VLOG（原声与清新）
- **输入词**：*"为一段旅行 VLOG 创作轻松愉快的原声配乐。使用明亮的木吉他、轻微的沙锤音以及欢快的口哨旋律，营造阳光明媚的氛围。"*
- **流程**：指挥官设定愉悦的基调（大调，105 BPM），并要求合成代理使用自然、温暖的音色。

#### 例子 D：悬疑片段（紧张且氛围感）
- **输入词**：*"为一段电影悬疑片段生成紧张的氛围音乐。侧重于低频的底噪、偶尔出现的时钟滴答声，以及高音的小提琴断奏。"*
- **流程**：指挥官营造出缓慢推进的紧张感（70 BPM，小调），侧重于悬念渲染。

#### 例子 E：自然纪录片（宏大且壮丽）
- **输入词**：*"为自然纪录片的航拍空镜创作一段宏大、高亢的管弦乐。我需要起伏的弦乐组和深沉共鸣的定音鼓，以突显山脉的雄伟。"*
- **流程**：合成代理生成具有电影质感的“音墙”提示词，以匹配史诗级的视觉规模。

### 💡 进阶技巧
- **持续调整**：你可以进行追加指令！例如：*"鼓声太大了，请把它调小一点，并且把速度放慢到 80 BPM。"*
- **指定乐器**：你可以精确要求乐器，如 *"在桥段部分加入一段中国竹笛独奏。"*

## 📂 项目结构
```text
agents/
├── common/              # 共享数据模型 (MusicSessionState, Track)
├── orchestrator/       # 根代理 (指挥官)
├── musicologist/       # 乐理专家
├── percussion_expert/  # 节奏专家
├── string_expert/      # 弦乐专家
└── audio_engineer/     # 混音与母带专家
```
