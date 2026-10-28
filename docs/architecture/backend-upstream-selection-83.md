# WallpaperBackend 上游复用选型评审（Issue #83）

- **日期**：2026-10-28
- **状态**：选型建议（PROPOSAL），不代表已实现、已批准增加依赖或通过真实桌面验证
- **依据**：[ADR 0010](../adr/0010-wallpaper-backend-adapter-contract.md)、[当前架构](../architecture.md)、[Issue #83](https://github.com/pkking/ezwallpaper/issues/83)
- **本次边界**：仅研究文档；**不修改代码、依赖、CLI 默认、registry、持久化状态或桌面配置**。保持 Noctalia 是唯一已接入的自动轮换后端。
- **证据级别**：`D` = 官方上游文档/命令手册明确记载；`I` = 从文档推导出的可行集成方向（尚未测试）；`U` = 没有独立证据/待验证。请不要将 `D` 误当作对 ezwallpaper 的运行时测试。

## 1. 先确认需要复用的层级

| 层级 | ezwallpaper 现状 | 应自研还是复用 |
|---|---|---|
| 获取/解码/本地内容与 ID | Core 已实现；与桌面无关 | 保留现有 Core |
| 按输出轮换计划、epoch、shuffle bag、锁、状态与失败恢复 | 已实现，`src/rotation_cli.rs` 通过端口使用 Noctalia | **保留唯一控制器/状态所有者**，不要引入第三方轮换调度器 |
| 桌面环境发现、单次壁纸设置 | 已隔离 Noctalia、GNOME、Plasma、LXQt、feh、swaybg、wallpaper-rs 到命名后端 | 原有全局单次能力继续使用，不因选型重写 |
| 按显示器寻址、设置、精确路径读回 | 目前只有 Noctalia 的已接入轮换端口 | **优先复用既有 compositor IPC / 运行中的 wallpaper daemon**；薄适配实现校验、超时和读回 |
| 额外 renderer 进程/退出/恢复 | swaybg 仅一次启动/早退观察，无已建立的持久生命周期管理 | 不新增通用 renderer，优先复用当前 session 拥有者；对并发 renderer 采用 fail-closed |

**不可降低的合并条件**：`BackendCapabilities(scope=PerOutput, acknowledgement=ExactPathReadback)` 只有在**已经完成输出身份校验、向指定输出设置、再独立查询该输出上的精确目标路径**后才能获准用于自动轮换。进程成功返回、用户配置、上次选择、进程存活、可见像素都不能单独替代相应确认。像素证明属于另一个独立的 E2E 层。全局/只支持命令接受的后端继续允许 one-shot，但不进入 acknowledged rotation。详见 [ADR 0010](../adr/0010-wallpaper-backend-adapter-contract.md)。

## 2. 上游候选功能矩阵

以下“逐屏/路径读回”仅表示**有文档支持的接口**；不是本仓已通过的实现。页面检查日期为 2026-10-28。

| 上游/方式 | 适用场景 | 逐屏寻址 | 独立读回候选 | renderer/状态所有权 | 已知限制与维护/许可证据 | 初步判断 |
|---|---|---|---|---|---|---|
| [Hyprland hyprpaper](https://wiki.hypr.land/Hypr-Ecosystem/hyprpaper/) | Hyprland 中**已运行** hyprpaper | **D**：`hyprctl hyprpaper wallpaper '[mon], [path], [fit_mode]'` | **D**：`hyprctl hyprpaper listactive` 按 monitor 返回 path | hyprpaper 管理自己的 renderer；ezwallpaper 只调用其 IPC | 文档明确不同版本的命令不同；旧 `preload/reload/listloaded` 示例不能作为新版本假设 | **P0 候选**：最接近 `PerOutput+ExactPathReadback`，需验证语法/路径格式、超时、monitor 映射和单 renderer |
| [awww（原 swww）](https://codeberg.org/LGFae/awww) | 支持 layer-shell 的 Wayland compositor（Sway、部分 niri 等）；不能假设 GNOME 支持 | **D**：[awww-img(1)](https://manpages.opensuse.org/Tumbleweed/awww/awww-img.1.en.html) 的 `awww img --outputs`；[awww-query 手册](https://manpages.opensuse.org/Tumbleweed/awww/awww-query.1.en.html) 可发现 output | **D**：`awww query -j` 返回 namespace/output/displaying.image | 长期运行 `awww-daemon`；必须明确由谁启动/复用以及 namespace；不得与已运行的 Noctalia/Hyprpaper 双重渲染 | [原 swww 仓库](https://github.com/LGFae/swww) 已于 2025-10-31 归档，现已迁至 Codeberg；[新发布记录](https://newreleases.io/project/codeberg/LGFae/awww/release/v0.12.0) 提到 JSON 查询；[发行包](https://mynixos.com/nixpkgs/package/awww) 标注 GPL-3.0 | **P1 候选**：适合可明确拥有 daemon 的 compositor；需要证明 JSON 路径与真正显示目标的对应关系 |
| [Sway 原生 output bg IPC](https://github.com/swaywm/sway/blob/master/sway/sway-output.5.scd) | Sway compositor 已在运行 | **D**：`swaymsg output <name> bg <file> <mode>`，`swaymsg -t get_outputs` 列举输出 | **U**：官方命令手册未证明存在可以按输出独立回读精确背景文件的稳定契约 | Sway 管理其壁纸/所需 swaybg；无需 ezwallpaper 自行管理第二个进程 | 输出名字在插拔时可能变化；Sway 文档建议使用 make/model/serial 组合 | **one-shot 优先候选**；达不到严格独立读回之前不能加入轮换 registry；与 awww 二选一 |
| [swaybg](https://github.com/swaywm/swaybg/blob/master/swaybg.1.scd) | 单次背景设置、wlroots/Wayland | **D**：独立 `--output` 指定输出 | **U**：无独立 path readback API 证据 | 长期前台 renderer，替换/杀死进程需要治理 | 当前 ezwallpaper 已有全局 one-shot；启动成功≠显示/读回 | 保持当前已实现能力；不把它升级为受确认轮换 |
| [wpaperd](https://github.com/danyspin97/wpaperd/blob/main/README.md) | 有 wlr-layer-shell 的 compositor + 运行中的 wpaperd | **D**：`wpaperctl set /path DP-1` | **D**：[官方说明](https://github.com/danyspin97/wpaperd) 在 `XDG_STATE_HOME/wpaperd/wallpapers/<display>` 创建指向当前图片的符号链接；是否足以在并发状态下提供独立证据仍需验证 | wpaperd 自带定时轮换、配置及持久 daemon；**必须禁用/协调其调度器**，避免双 owner | README 明确不支持 GNOME，**Hyprland 也不支持**；GPL-3.0+；依赖 layer-shell/GL 运行环境 | **P1 条件备选**：Sway 类平台有用，若可控 daemon 与 symlink 读回，但不应作为 Hyprland 默认后端 |
| [more-wallpapers crate 0.4.0](https://docs.rs/crate/more-wallpapers/latest) | 希望以 Rust crate 复用 X11、KDE、XFCE、Sway 的逐屏设置 | **D**：官方支持矩阵对 X11/KDE/Sway/XFCE 标为逐屏；Windows/macOS 与 GNOME Wayland 仅全局回退 | **U**：文档公开的逐屏 `set_wallpapers_from_vec`/`WallpaperBuilder` 并不证明有独立读回 | 借用各 DE API/外部工具；`fallback` feature 可能改变选择/语义 | MIT OR Apache-2.0；最新 crate 版本 **0.4.0 (2024-03-29)**，维护活跃度与当前 DE API 兼容性需复核；X11 依赖 xwallpaper/libxrandr | **P2 技术候选**：优先小范围代码/兼容性评审，**不能仅凭逐屏 set 能力升级为轮换** |
| [Waypaper](https://github.com/anufrievroman/waypaper) | 使用者侧 GUI 和多后端聚合 | **D**：`--monitor` 和 `--backend` 由 [CLI 文档](https://github.com/anufrievroman/waypaper-docs/blob/main/usage.md) 给出 | **U**：Waypaper 的 `--list`/内部配置状态不等于其底层 renderer 的独立确认 | 另带自己的 restore/slideshow/后台操作及对 backend 的选择 | Python/GTK 前端 + 外部后端；引入会重复 ezwallpaper 管理器/调度职责 | **参考实现，非嵌入依赖**；只学习后台选择、调用参数/输出映射，不另起一套 GUI 和状态所有权 |
| [UniDesktop API (UDA)](https://unidesktop.github.io/en/guides/wallpaper/) | Rust 跨平台 global apply/主题等桌面功能 | **U/尚不可用**：壁纸专题明确“Per-monitor selection is part of the Display Topology work”；总览即使写 multi-monitor 也不能认定逐屏可用 | **U**：`GET_WALLPAPER` 读“配置值”不保证实际该 monitor 的壁纸 | 后端会执行 hyprpaper→swww、feh→nitrogen 等回退，可能意外启动竞争 renderer | [官方壁纸指南](https://unidesktop.github.io/en/guides/wallpaper/) 明确这些限制与 fallback 次序 | **暂不采用**为严格轮换端口；未来可比较 global-only，但没必要替换当前稳定 one-shot |
| [XDG Desktop Portal Wallpaper v1](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.Wallpaper.html) | 可交互或沙箱环境的全局设置 | **否**：接口仅 `SetWallpaperFile/URI`、`set-on`（背景/锁屏/两者），无 monitor 选择 | **否**：异步请求/用户许可并非指定显示器的路径读回 | 桌面 portal 后端自行处理；可能出现交互授权 | API 和是否支持受安装的 portal backend 决定；本地文件须用 `SetWallpaperFile`，不能给 URI 方法直接塞 `file:` | **仅考虑 global-only、用户同意的一次性路径**；不适合作为无人值守逐屏轮换 |
| 已有 [wallpaper-rs](https://crates.io/crates/wallpaper) / 本仓 native | Windows/macOS、部分 Linux 全局壁纸 | 现有本仓仅 `GlobalOnly` | 现有本仓仅 `CommandAccepted` | 原生桌面 API | 已纳入仓库依赖/相关 headless CI；真实桌面像素未由 CI 证明 | **保持不动**；避免仅为“统一 crate”造成回归 |
| 已有 Noctalia v5 IPC | niri/Noctalia 或实际 Noctalia shell | **已实现**本仓 `PerOutput`、connector 验证 | **已实现**本仓 `wallpaper-get` 确认精确路径 | Noctalia owns renderer；ezwallpaper 已统一轮换状态 | 仅相关固定版本虚拟 Sway/niri 证据，物理显示器仍未测 | **维持首选/不替换**；不得在此 session 再启动 awww/swaybg/hyprpaper |

### 2.1 证据解读与矛盾

1. **明确记录“已存在可调用 API”不等于已满足生产轮换**。对 hyprpaper 的 `listactive`、awww 的 `query -j`、wpaperd 的符号链接，尚需用实际已打包版本的双屏测试证明读回是**执行之后独立查询**，与输出 ID、目标绝对路径一一对应；重启/并发失败时不能伪造 `PathObserved`。官方命令退出 0 只代表请求处理。
2. **awww/swww 名称与版本**：swww 的旧 GitHub 仓库已归档，优先验证新 awww；不能把旧 swww CLI/缓存布局视为新版本稳定 API。awww JSON 格式以 [awww-query manpage](https://manpages.opensuse.org/Tumbleweed/awww/awww-query.1.en.html) 为准；要锁定运行时版本/命名空间，避免不同 namespace 混用。
3. **Sway 逐屏 ≠ 精确读回**：`output ... bg` 官方支持，输出枚举也支持，但未找到同一级别的独立背景路径 readback 保证。它可能由 Sway 管理 swaybg 而非 ezwallpaper，故更适合替换未来“自启第二个 swaybg”的方向；仍只能归为 `CommandAccepted` 直到有新证据。
4. **UDA 总览与壁纸接口文档不一致**：选择粒度以[详细 wallpaper guide](https://unidesktop.github.io/en/guides/wallpaper/)为准。它强调“读取的是配置值，可能不等于渲染状态”，且隐藏回退可能违背本仓 fail-closed 条款。
5. **wpaperd 兼容范围不是“所有 Wayland”**：上游明确 GNOME 不支持、Hyprland 不支持；项目自身的周期更换必须关闭/隔离，否则会破坏本仓按 epoch 去重、失败恢复和唯一状态所有权。
6. **许可证不是运行时读回能力**：本仓 MIT，more-wallpapers MIT/Apache-2.0；awww 与 wpaperd 为 GPL-3.0 系列。调用用户**另行安装**的可执行程序与将其代码/二进制嵌入、捆绑发布应分别评估。**不能简单推断调用一个 GPL 外部可执行程序就使本仓自动变为 GPL**；打包/分发之前需要独立许可证与制品策略评审。

## 3. 建议的选型（有条件，通过证据门槛后方能执行）

| 目标环境 | 主路径 | 备选/回退 | 当前准入状态 |
|---|---|---|---|
| niri + Noctalia / 已运行 Noctalia | 继续现有 Noctalia v5 IPC、`wallpaper-get` | **无自动回退** | **现有本仓实现**；物理仍 U |
| Hyprland + 已安装并运行 hyprpaper | 优先对接官方 hyprpaper IPC + `listactive` | 仅**用户明确选定** awww 时尝试；绝不后台静默启动两个 renderer | **P0 研究建议，尚未实现** |
| Sway（使用 Sway 自管背景） | 优先 Sway 原生 output/bg IPC 作为单次逐屏设置 | 要实现严格轮换：评估用户显式选择的 awww 或已运行 wpaperd 的读回 | **仅单次 P1**；严格轮换需要另选有证据的后端 |
| 通用 layer-shell Wayland（含可适配 niri） | 仅当前会话没有已占用背景 renderer 且用户明确授权时，评估 awww + JSON 路径查询 | wpaperd：只在明确安装且关闭内部轮换、平台兼容时 | **P1 候选**；不自动推断所有 Wayland 支持 |
| KDE Plasma / XFCE / X11 | 保留当前已实现 global one-shot；评估 more-wallpapers 的逐屏寻址封装与输出映射 | 需要另外找到稳定**独立路径读回**；否则不自动轮换 | **P2**；不改变全局 one-shot |
| GNOME | 保留 GSettings global-only | Portal 可做有 consent 的 global-only 单次动作 | **无已证实的通用逐屏轮换** |
| Windows/macOS | 保留既有 wallpaper-rs native `GlobalOnly/Submitted` | 不为统一 API 引入额外 frontend | **现有实现保持不动** |

**排序理由**：先攻克**无需引入 Rust crate、上游直接提供“逐输出设置＋独立路径查询”**的 hyprpaper；其次评估已经存在进程且可显式选择的 awww，代价是长期 daemon 生命周期与 GPL 分发。Sway 原生 IPC、more-wallpapers 虽解决了设置或输出寻址，但缺少本仓严格的**路径读回证据**，不可与上述两者并列为已具备可靠轮换能力。

## 4. 实施前必须完成的验收合同（分阶段、独立 PR）

**G0 – 纯文档选型完成（本 PR）**：记录上游准确命令/版本与负面证据，审查许可证和默认行为；没有任何新 backend 代码。

**G1 – 只读 discovery 和兼容性约束（未来独立 PR）**

- 查询当前 compositor、目标 backend 实际存在的 IPC/socket、renderer 所有者以及 `--version`/`--help` 能力；未知版本或多 renderer 冲突 fail-closed，不能“发现无程序就自动安装/启动”。
- 记录每个候选目标使用的**上游输出 ID**，对接 `OutputScope::PerOutput`；启动前对所有目标执行可达性和相互区分校验。热插拔/重命名不得误命中其他屏幕。
- 禁止偷改桌面自动启动文件、hyprpaper/wpaperd/Waypaper 配置、已有后台进程、screen 锁或 systemd timer。

**G2 – 独立 apply/readback 契约（每个后端单独 PR）**

- 采用只传 argv 的调用（无 shell 注入），限制超时，校验正常绝对本地路径、包含空格及 Unicode 的路径；有分隔符/换行/URI 限制的上游按真实协议严格拒绝，不能默默转义出错误显示器。
- `set(<output>, <path>)` 后另执行 `query/readback(<output>)`：比较精确目标路径与归属，不可仅根据本地 intent、缓存配置或进程状态提交。输出未知、命令失败、daemon 崩溃、读回不一致、一部分输出成功时均保证原子状态协议（仅每个已确认的输出可提交）。
- 用注入 fake runner/fixtures 验证这些条件，不做用户桌面操作；保持 `Rotation Controller` 与 Core、状态 schema 不变。

**G3 – 虚拟 compositor 原生 E2E（针对实际集成的上游程序版本）**

- 双虚拟输出各设不同路径并分别查询，提供**原生**日志、输出映射、截图和 daemon/version 证据；单次成功不推导出真实物理设备行为。
- 处理 daemon 突然死亡、重连、无 IPC、重名/重排序输出、连接/断开、一屏失败一屏成功；验证不会引入 Noctalia 和 awww/Hyprpaper 并行渲染。
- 用户环境真实显示器/4K/GPU/锁屏/注销/热插拔的可视验证，单独列为 **U**，不混入 CI 通过含义。

**G4 – 发行及维护评审（引入任何新依赖前）**

- 固定支持的上游版本和命令结构，确认使用中 distro 的可安装性与维护状况；跨 Debian、Fedora/openEuler 的可执行程序存在性应分别确认，不能仅凭 README 判断。
- 比较直接调用已安装 binary/IPC（首选）与引入 crate；仅在 crate 带来明确、稳定、可审计的独立读回优势时才考虑新依赖。
- 对 GPL 程序仅支持**用户自行安装并运行**的外部进程时，清晰界定交互与发包边界；若要 bundling/linking、自动下载或再分发，先专项许可与供应链评审。

### 应新开而不是混在一个 PR 中的工作单元

1. **Hyprpaper provider**：`hyprctl` 版本能力探测、`listactive` 解析、逐屏 path equivalence 和后台冲突检查；先注入 fake，再验证真实上游 virtual compositor，独立源代码 PR/归档。
2. **awww provider**：按指定 namespace 的 `query -j` 输出枚举/路径匹配、daemon 持续可达与冲突策略；单独 PR、单独实测。
3. **Sway direct IPC / wpaperd comparison**：先专门验证 Sway 背景路径读回是否存在及 wpaperd symlink 稳定性；未证明则只实现 one-shot，不获自动轮换准入。
4. **more-wallpapers 兼容性/维护审查**：仅在 KDE/XFCE/X11 需要逐屏但不改变轮换状态时评估；本选型不授权 crate 变更。

## 5. 未决问题与授权边界

- **用户需要决定的后续行为变更**：某个 session 没有活动 wallpaper daemon 时，是否允许显式启动自有 daemon？默认选哪个？如何识别已由 Noctalia/Waypaper/wpaperd 管理的 renderer？只要没有专门决策，全部维持**不自动启动/不隐式回退**。
- **尚无生产证明**：Hyprpaper、awww、wpaperd 的路径查询在真实不同 compositor/版本中的原子性与输出身份，二次查询在图像 transition 过程中的行为，Linux 实际 4K/GPU/hotplug，GNOME/Plasma/XFCE 单个物理输出映射，macOS/Windows 原生壁纸设置的实际屏幕效果。
- **与本次 PR 解耦**：不引入新 ADR；已接受的 ADR 0010 端口/状态提交原则完全不变。本文仅重新定义后续**优先复用上游协议**的候选顺序，没有修改组件或完成标记；因此 `docs/architecture.svg` **保持不变**（不存在新的 implemented 节点/依赖箭头）。

## 6. 主要原始资料

1. Hyprland 官方 [hyprpaper IPC](https://wiki.hypr.land/Hypr-Ecosystem/hyprpaper/)（`wallpaper`、`listactive`，注意旧命令差异）。
2. Sway 官方 [sway-output(5)](https://github.com/swaywm/sway/blob/master/sway/sway-output.5.scd)（按屏 `output bg`、`get_outputs`，输出身份可能重映射）。
3. swaybg 官方 [swaybg(1)](https://github.com/swaywm/swaybg/blob/master/swaybg.1.scd)（`--output`，无读回保证）。
4. awww [新上游](https://codeberg.org/LGFae/awww)、[awww-img(1)](https://manpages.opensuse.org/Tumbleweed/awww/awww-img.1.en.html)、[awww-query(1)](https://manpages.opensuse.org/Tumbleweed/awww/awww-query.1.en.html)（JSON 查询和 namespace）、[swww archived](https://github.com/LGFae/swww)、[v0.12.0 发布记录](https://newreleases.io/project/codeberg/LGFae/awww/release/v0.12.0)。
5. wpaperd 上游 [README/使用与生命周期说明](https://github.com/danyspin97/wpaperd/blob/main/README.md)（`wpaperctl set`、显示器 symlink、GPL-3.0+、GNOME/Hyprland 不支持）。
6. more-wallpapers [docs.rs crate 0.4.0](https://docs.rs/crate/more-wallpapers/latest)（逐屏矩阵、发布日期、依赖与许可证）。
7. Waypaper [repo](https://github.com/anufrievroman/waypaper)、[CLI 选项](https://github.com/anufrievroman/waypaper-docs/blob/main/usage.md)（`--backend`、`--monitor`）。
8. UniDesktop API [wallpaper guide](https://unidesktop.github.io/en/guides/wallpaper/)（逐屏 TODO、配置值与渲染状态的区别、隐式 fallback）。
9. XDG Portal [Wallpaper v1](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.Wallpaper.html)（global 设置、交互与异步响应、无按显示器选择）。
