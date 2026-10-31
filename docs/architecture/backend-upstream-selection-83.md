# WallpaperBackend 开源复用选型——源码复核版（Issue #83）

**版本**：2026-10-28；**状态**：PROPOSAL / code-audited；**不代表运行时验证**。本文件替代本 PR 首版基于 Wiki/README/CLI 帮助的候选排序，**只用上游实现代码和本仓现有代码作能力判断**。未读到实现源码的项目标为 `BLOCKED_SOURCE`，不能从文档介绍推断可用于自动轮换。

## 0. 源码证据规则与决策边界

- **CODE**：列出上游 repo、固定 commit、源文件、具体函数/行范围和这段代码真正证明的事实。固定 commit 引用不跟随默认分支漂移。
- **CONTRACT**：协议的 XML/IDL 定义可证明接口字段与语义，但不能证明调用成功或真实像素。必须结合服务端处理代码。
- **UNVERIFIED**：尚无源码或执行证据。不得把示例、README、安装包、命令帮助、成功退出码或预计适配能力写作已证明的实现。
- **TESTED**：仅针对本仓已有、真实跑过的 Noctalia/Sway 虚拟 CI；不能推导到未接入后端或物理桌面。
- **选择硬条件**：按显示器寻址 + **设置之后独立读取该显示器当前精确路径** + 单一 wallpaper renderer/scheduler 所有权 + 故障/时序可控。前两项代码存在不表示后两项已验证。
- **现有实现**：[本仓 port](../../src/backend/mod.rs) `OutputScope`/`Acknowledgement`/`ApplyStatus`、`require_acknowledged_outputs`；[registry](../../src/backend/registry.rs) **只**实例化 Noctalia；[Noctalia IPC](../../src/backend/noctalia.rs) 原始 `wallpaper-set` 后再次 `wallpaper-get` 比对，不把像素当 `PathObserved`；[Cargo.toml](../../Cargo.toml) 已有 `wallpaper=3.2.0`。严格轮换从来不是“setter 返回成功即可持久化”。上述代码以 [ezwallpaper master `dc1355b`](https://github.com/pkking/ezwallpaper/commit/dc1355b0685c2ab35fe1d80974c7534b706a4661) 为基线。
- 本轮**不更新 ADR 0010、renderer、Core/CLI/状态协议、默认值、Cargo 依赖、SVG**；建议仅作为后续独立验证任务的输入。

## 1. 源码追踪对照（上游提交固定）

| 候选 | 能力与调用链——固定源码 | 被代码证明的结果 | 未证明/阻塞项 | 选型 |
|---|---|---|---|---|
| **hyprpaper v0.8.4 + Hyprland v0.57.0 `hyprctl`** | **Released Hyprwire v2 client:** [Hyprland `0aa6745` `hyprctl/src/hyprpaper/Hyprpaper.cpp` L55–136](https://github.com/hyprwm/Hyprland/blob/0aa6745f705f2c4b0a5004eb019ef76e5bbdb426/hyprctl/src/hyprpaper/Hyprpaper.cpp#L55-L136) 的 `doWallpaper` 从 `hyprctl hyprpaper wallpaper 'monitor,path,fit'` 通过 `IClientSocket` 握手绑定 v2 manager，发送 `path/monitor_name/fit_mode/apply` 并等待 success/failed；[L139–184](https://github.com/hyprwm/Hyprland/blob/0aa6745f705f2c4b0a5004eb019ef76e5bbdb426/hyprctl/src/hyprpaper/Hyprpaper.cpp#L139-L184) 的 `doListActive` **重新打开独立连接**、校验 spec 版本 ≥2、创建 status object，输出 `monitor: path` 并 `roundtrip`；[main.cpp L532–539](https://github.com/hyprwm/Hyprland/blob/0aa6745f705f2c4b0a5004eb019ef76e5bbdb426/hyprctl/src/main.cpp#L532-L539) 错误返回非零。**Released server:** [hyprpaper `20fc0fa` IPC.cpp L60–165](https://github.com/hyprwm/hyprpaper/blob/20fc0fa6c2056c388a4cd69cb394a9f989dd27c0/src/ipc/IPC.cpp#L60-L165) 校验 monitor/path，`addState` 后回 success，`get_status_object` 输出各 target 的 `m_lastPath`；[XML v2](https://github.com/hyprwm/hyprpaper/blob/20fc0fa6c2056c388a4cd69cb394a9f989dd27c0/hw-protocols/hyprpaper_core.xml) 定义 wildcard/状态事件 | **CODE/CONTRACT**：**确有可直接复用的已发布 `hyprctl` v2 客户端**，不必因为 daemon 换二进制 IPC 就自行重写 Hyprwire；`wallpaper` success 是配置入队，另起一次 `listactive` 查询才得到独立的逐屏 **路径状态**，并非显示像素。两版对应生成协议 XML blob 一致 | `CVarList2` 以逗号分字段，对含逗号路径/输出须先拒绝或独立证明安全；无内置操作超时证据，未来调用者必须限制子进程运行时间；`listactive` 可能无目标或重复行，必须严格解析；空 monitor 会 wildcard，禁止；hyprpaper 多图目录可自转，禁止双 scheduler；旧安装版本、真实 compositor、并发/热插拔与 pixels 均 **UNASSESSED** | **P0a：优先复用已安装且版本/能力匹配的 `hyprctl`，只作显式 opt-in 候选；本 PR 未实现新后端** |
| **wpaperd** | [`ipc/src/lib.rs` L5–75](https://github.com/danyspin97/wpaperd/blob/483225a9c6ad4f9bbf9104f958eafee9c47d4612/ipc/src/lib.rs#L5-L75) 定义 `SetWallpaper{path,monitors}`, `CurrentWallpaper{monitor}`, `AllWallpapers` 及 `PathBuf` 响应；[`daemon/src/ipc_server.rs` L92–216](https://github.com/danyspin97/wpaperd/blob/483225a9c6ad4f9bbf9104f958eafee9c47d4612/daemon/src/ipc_server.rs#L92-L216) 根据 monitor 匹配 surface，`SetWallpaper` 校验图片并调用 `set_image` + `pause_for_set` + `load_new_wallpaper`；`CurrentWallpaper` 读 `image_picker.current_image()` | **CODE**：完整的**命名输出设置 + 独立进程内查询当前图像路径**，比之前依赖 symlink 的论证更强。[image_picker.rs L385–405, L438–445, L522–524](https://github.com/danyspin97/wpaperd/blob/483225a9c6ad4f9bbf9104f958eafee9c47d4612/daemon/src/image_picker.rs#L385-L405) 显示 set 先存 forced path，当前图像由 `update_current_image` 更新；[`surface.rs` L350–366](https://github.com/danyspin97/wpaperd/blob/483225a9c6ad4f9bbf9104f958eafee9c47d4612/daemon/src/surface.rs#L350-L366) 在装载完成路径中更新 symlink/current image 并开始 transition。[`surface.rs` L856–916](https://github.com/danyspin97/wpaperd/blob/483225a9c6ad4f9bbf9104f958eafee9c47d4612/daemon/src/surface.rs#L856-L916) 的 symlink 写入**可失败且仅告警** | **`SetWallpaper` 的 `IpcResponse::Ok` 先于异步图片加载，不是路径确认；应该轮询独立 `CurrentWallpaper` 直到目标精确匹配/超时，并区分此前恰好已是目标路径。查询反映图片状态而非 compositor 像素**。自身周期调度、Wayland 支持范围、daemon 生命周期、GL/热插拔与许可证均待验证 | **P0b：最有把握的可复用 IPC 候选**，在兼容 compositor 且已经运行时比 symlink 更好 |
| **Sway 原生 IPC** | [Sway `1652c54` `background.c` L29–144](https://github.com/swaywm/sway/blob/1652c54b73f67df17b7b4ab0b0f7048204aa8104/sway/commands/output/background.c#L29-L144) `output_cmd_background` 将背景 path/fit 写入 `output_config`；[`ipc-json.c` L331–430](https://github.com/swaywm/sway/blob/1652c54b73f67df17b7b4ab0b0f7048204aa8104/sway/ipc-json.c#L331-L430) 输出 JSON 描述输出/活动状态，没有在这些路径导出 `background` 路径字段；[`more-wallpapers sway.rs`](https://github.com/LuckyTurtleDev/more-wallpapers/blob/a282d1912dffd3a59803d79413a09e739d2adb1d/more-wallpapers/src/linux/sway.rs#L47-L78) 同样调用 `swaymsg output <name> bg <path> <mode>` | **CODE**：Sway 支持按输出**设置配置**，没有从检查到的 IPC 输出函数证明独立 path readback | 未穷举所有 Sway 内外部读回方式，不能宣称全系统绝对不存在；但按当前证据**不足以让本仓提交轮换状态** | **单次逐屏设置候选**，严格轮换暂不准入 |
| **more-wallpapers 0.4.0** | [`a282d19` Sway setter](https://github.com/LuckyTurtleDev/more-wallpapers/blob/a282d1912dffd3a59803d79413a09e739d2adb1d/more-wallpapers/src/linux/sway.rs#L47-L78) 枚举 `get_outputs`，然后按屏执行 `swaymsg output ... bg`，对每屏 `wallpaper:None`；[KDE setter](https://github.com/LuckyTurtleDev/more-wallpapers/blob/a282d1912dffd3a59803d79413a09e739d2adb1d/more-wallpapers/src/linux/kde.rs#L31-L76) 用 `desktops()` 枚举 desktop ID 并生成 `writeConfig(Image,FillMode)` 脚本；[XFCE setter](https://github.com/LuckyTurtleDev/more-wallpapers/blob/a282d1912dffd3a59803d79413a09e739d2adb1d/more-wallpapers/src/linux/xfce.rs#L5-L103) 使用 `xfconf-query` | **CODE**：主要封装现有 DE 设置命令；KDE 的 `desktop.id` 不是通用物理 monitor ID，Sway 的 `Screen.wallpaper` 并没有由 Sway 查询当前背景路径获得 | 没有发现满足 **“请求后另从 renderer 查询精确路径”** 的公共接口；旧 crate [0.4.0 (2024-03-29)](https://docs.rs/crate/more-wallpapers/0.4.0) 不能当作当前 DE API 正确性的证明。没有明显收益去替换本仓已写的 thin setter | **降级：不作为逐屏自动轮换依赖；先不加 crate** |
| **UniDesktop API / UDA** | [`a74bd2c` Linux `wallpaper.rs` L126–168](https://github.com/UniDesktop/SDK/blob/a74bd2cf372efad2407d6be4b57739e682cf1d9a/crates/uda-platform-linux/src/wallpaper.rs#L126-L168) 构造 `format!("HDMI-{}", monitor)`，而非从 compositor 实际输出清单映射；[L201–300](https://github.com/UniDesktop/SDK/blob/a74bd2cf372efad2407d6be4b57739e682cf1d9a/crates/uda-platform-linux/src/wallpaper.rs#L201-L300) 先尝试 `hyprpaper` / `swww init`，再回退 feh/nitrogen，`get_wallpaper` 直接 `NotSupported`；[Windows `wallpaper.rs` L287–315](https://github.com/UniDesktop/SDK/blob/a74bd2cf372efad2407d6be4b57739e682cf1d9a/crates/uda-platform-windows/src/wallpaper.rs#L287-L315) 忽略监视器 index 执行全局 Win32 API | **CODE**：不是可用的 named-output acknowledgement backend；尤其会触发静默 fallback 或隐式全屏设置，违反 ADR 0010 | 旧 `hyprpaper` CLI 参数与当前 Hyprwire 协议并不匹配；不能因公共 `WallpaperManager` trait 有 `get_wallpaper` 就认为 Linux 实现有 readback | **明确不采用** |
| **Waypaper** | [`0ef0d1e` `waypaper/changer.py` L240–330](https://github.com/anufrievroman/waypaper/blob/0ef0d1edc4c81dff656b5dc9951522c2b836d673/waypaper/changer.py#L240-L330) `seek_and_destroy` `killall` 或 `kill -9` 旧 renderer；[L490–540](https://github.com/anufrievroman/waypaper/blob/0ef0d1edc4c81dff656b5dc9951522c2b836d673/waypaper/changer.py#L490-L540) 的 `change_with_awww` 先销毁 swaybg/hyprpaper/swww-daemon，按需自行启动 awww-daemon | **CODE**：它是一个接管 renderer 生命周期与切换的前端管理器，而非严格“只读 detect + 向既有进程委托”的薄库 | 与本仓“不自动终止/替换第三方 renderer”强约束冲突；不可直接复用这一层 | **仅作生态参考，不复用为 backend** |
| **XDG Wallpaper Portal** | [xdg-desktop-portal `Wallpaper.xml` 源码](https://github.com/flatpak/xdg-desktop-portal/blob/main/data/org.freedesktop.portal.Wallpaper.xml) （以及 [Debian 1.22.1 原样 XML](https://sources.debian.org/src/xdg-desktop-portal/1.22.1%2Bds-1/data/org.freedesktop.portal.Wallpaper.xml)）：接口只有 `SetWallpaperURI/SetWallpaperFile`、`set-on` 和 async request handle；没有 `output` 字段或每显示器 `GetWallpaper` 方法 | **CONTRACT**：仅全局/背景与锁屏选择，**不能满足本仓命名输出严格轮换** | 具体 portal 后端能否成功、弹窗与否属于部署时行为，非这份 XML 能证明 | **global-only（未来可选），非轮换候选** |
| **awww（迁至 Codeberg）** | [新上游 Codeberg](https://codeberg.org/LGFae/awww)；[旧 swww 仓库](https://github.com/LGFae/swww) 已归档。可读到打包 `awww-img(1)`、`awww-query(1)` 手册，但**本轮无法访问当前 Codeberg 代码文件/固定 SHA** | **BLOCKED_SOURCE**：原报告所说 `img --outputs` / `query -j` 目前仅为命令手册层面的证据；不满足用户要求的**实现代码依据** | 需获取归档/镜像并检验客户端 JSON 协议、daemon IPC handler、output-path 状态的更新时间与 timeout、namespace；在做到前不能断言 `PathObserved` 可实现 | **暂缓选型，不排 P1；先补源码再决定** |
| **Noctalia / native + GNOME/Plasma/LXQt/feh/swaybg** | 本仓 [Noctalia 模块](../../src/backend/noctalia.rs) 明确 `wallpaper-get` 再比较；[native](../../src/backend/native.rs)、[GNOME](../../src/backend/gnome.rs)、[Plasma](../../src/backend/plasma.rs)、[LXQt](../../src/backend/lxqt.rs)、[feh](../../src/backend/feh.rs)、[swaybg](../../src/backend/swaybg.rs) 已由 port 封装单次能力 | **本仓代码事实**：Noctalia 是 registry 唯一 accepted rotation；其他已实现 global one-shot 不等于其真实桌面像素/逐屏 readback | 无需因“统一上游 SDK”重复迁移；物理 Windows/macOS/Wayland、GPU、4K、hotplug 仍 UNASSESSED | **维持现状** |

## 2. 之前报告需要显式撤回或纠正的结论

1. **2026-10-31 二次纠正：此前将“旧文本 IPC 已删除”推断为“`hyprctl listactive` 不能复用”是错误的**。初版仅检查 hyprpaper **服务端**，漏掉了 Hyprland **客户端**源码。固定已发布 [Hyprland v0.57.0 `doWallpaper`/`doListActive`](https://github.com/hyprwm/Hyprland/blob/0aa6745f705f2c4b0a5004eb019ef76e5bbdb426/hyprctl/src/hyprpaper/Hyprpaper.cpp#L55-L184) 证实 `hyprctl` 本身实现 Hyprwire v2 握手、设置和**独立连接**的 status 快照；匹配 [hyprpaper v0.8.4 服务端](https://github.com/hyprwm/hyprpaper/blob/20fc0fa6c2056c388a4cd69cb394a9f989dd27c0/src/ipc/IPC.cpp#L60-L165)。应区分 *旧的 raw text socket 协议*（不再用于该服务端）与 *保留的 `hyprctl` 用户命令*（其客户端内部已迁移协议）。但是 `success` 仍不足以认定渲染，必须重新调用 `listactive` 并精确校验目标输出/路径，且实际发布版本组合、超时和像素尚未运行时验证。
2. **升级 wpaperd 的理由完全不同**：原版只提 symlink，其实有更直接、可明确映射 monitor 的 IPC `CurrentWallpaper` 和 `AllWallpapers`。但是 `SetWallpaper` 的 `Ok` 在异步加载前后存在时序差，不能立即提交状态；应循环读 `CurrentWallpaper` 并在超时后故障退出。符号链接创建失败仅写 warn，**不能单靠链接存在判断服务成功**。
3. **撤回“awww 已经具备源代码验证的 readback”的隐含判断**：本轮仍然无法读取迁移后的 Codeberg daemon/CLI 代码，故 awww 暂无资格直接作为最高优先级实现。历史 swww 的实现不能替代 awww 新版本。
4. **不引入 more-wallpapers 或 UDA 以图直接获得跨桌面轮换**：前者 Sway 调用的是与直接 IPC 同层的 `swaymsg`，后者 Linux `get_wallpaper` 是 `NotSupported` 且伪造 `HDMI-N`。引入后反而可能掩盖输出标识/回退边界。
5. **Waypaper 不应被作为生命周期治理参考照搬**：源码明确有结束现有 daemon 的策略，而本仓要求 renderer 只能由用户显式控制、自动选型不得触发竞态切换。

## 3. 修订后选型顺序（只有具备源码证据才能提升状态）

| 顺序 | 具体工作包 | 准入的已知源码证据 | 下阶段必须补齐的独立证据 |
|---|---|---|---|
| **1** | **wpaperd IPC 技术验证**（限定已安装/已运行/兼容 compositor） | `ipc::IpcMessage::{SetWallpaper,CurrentWallpaper,AllWallpapers}`，daemon 的按 monitor 读路径及同步/异步分界 | **先不写产品代码**：CLI 版本与协议帧、双输出、路径变更延迟、decode 失败、旧目标重用、防止自身自动 rotation 冲突、重连/热插拔 |
| **2** | **Hyprpaper v0.8.4 + Hyprland v0.57.0 的已发布 `hyprctl` v2 客户端复用验证**（仅未来显式选择） | [客户端源码](https://github.com/hyprwm/Hyprland/blob/0aa6745f705f2c4b0a5004eb019ef76e5bbdb426/hyprctl/src/hyprpaper/Hyprpaper.cpp#L55-L184) 已具 `wallpaper` v2 apply 与另一连接的 `listactive` 快照；[服务端源码](https://github.com/hyprwm/hyprpaper/blob/20fc0fa6c2056c388a4cd69cb394a9f989dd27c0/src/ipc/IPC.cpp#L60-L165) 回状态路径 | 不必引入新 Hyprwire Rust/C++ 依赖；首先验证已安装命令真实版本与 handshake、受限逗号路径、子进程超时、命令退出码、`listactive` 精确/唯一输出解析、配置目录自转与跨 compositor 兼容，再经独立用户决策开启新后端；真实虚拟双屏像素与物理硬件仍缺 |
| **3** | **Sway 原生 IPC 的逐屏 one-shot 补充证据** | `background.c` 可设置配置，`ipc-json.c` 不暴露所需 path | 需要另找到实际稳定的独立 wallpaper path query，未解决前不能提升到自动轮换 |
| **4** | **awww 固定 commit 源码提取和重审** | **BLOCKED_SOURCE**，不得借 README/manpage 声称代码功能 | 获得当前 Codeberg source、真实 client/daemon IPC 和状态更新链，然后重新排序（可能超过 1–2） |
| **保持** | Noctalia rotation、其他 global one-shot | 本仓 `src/backend/*` 和 registry | 物理显示器/桌面现状的运行实测独立进行 |

`wpaperd` 的项目源码确实支持接收 monitor/path 和查询 path，但**不能因为文档选型就自动创建新后台服务或切换用户的壁纸 renderer**。如果用户环境已经运行 Noctalia/hyprpaper/其他 manager，继续 fail-closed；不能在没有用户明确授权时后台启动竞争 renderer。代码中的 `IpcResponse::Ok` / `success` 均不足以认定真实 framebuffer pixels。

## 4. 每个未来后端的代码级验收与反例

1. **固定真实上游版本**：把 commit/tag、实际安装 `--version`/协议版本、CLI/IPC parser 和 daemon handler 的对应代码放到 PR；缺乏源代码的上游直接标记 `BLOCKED_SOURCE`。
2. **只读 capability preflight**：监控输出身份（端口名/稳定 ID 与输出数目）、当前 compositor/session、服务 socket/namespace、已运行 renderer 所有权；所有输出预检查通过后才能动本仓用户状态，禁止匿名/global 目标暗中代替显示器。
3. **路径设置与独立读回**：在两个输出发送不同路径 `p1`/`p2`；先拿到 ack，再对每个输出独立查询确认，轮询有界超时；旧值恰与新值相同的路径不能错误当成新命令成功。异常输入包括空格/Unicode/换行/分隔符/不存在文件与图片解码失败。
4. **异步阶段和 renderer**：测试 daemon `Ok` 早于图像加载、路径已改变而像素仍在 transition、进程崩溃/重启、另一个管理器抢占背景、热插拔/同名输出等分歧，未获确证绝不提交。wpaperd 的当前路径不是物理像素结果；hyprpaper `active_wallpaper` 也是路径状态而非 framebuffer 报告。
5. **版本、发行许可与最低供应链**：明确上游项目自己的依赖、生命周期与发行方式；外部用户安装二进制的 CLI/IPC 与将源码/程序打包链接到 MIT 产品的许可证后果不同，不做法律结论；GPL 项目需独立分发审查。
6. **每个功能单独 PR + E2E**：不修改 Core planner 和本仓轮换 state schema；独立 fake 负面矩阵证明失败不会写状态；针对实际 native compositor/daemon 版本收集双输出日志和 framebuffer；实体桌面 4K/GPU/会话生命周期仍标 UNVERIFIED。

## 5. 资料分类与已知不足

- **已完整读取的上游关键代码**：hyprpaper v0.8.4 IPC.cpp/Hyprwire XML/UI.cpp，**Hyprland v0.57.0 `hyprctl` Hyprwire v2 `doWallpaper/doListActive` 与 main.cpp 退出码**；wpaperd IPC 定义/daemon handler/image picker/surface；Sway output/background.c 与 ipc-json.c；more-wallpapers Sway/KDE/XFCE；UDA Linux/Windows；Waypaper changer.py；XDG Wallpaper XML。固定 commit 的源码锚点见表。
- **无法读取/未展开实现**：迁移到 Codeberg 的 awww 最新源码；GUI/桌面实际像素；macOS 原生具体物理路径；KDE/XFCE 当前真实版本的运行时兼容性。对这些候选 **不作支持结论**。
- **不以未验证缺失为事实**：未在已检查文件中看到某接口，最多得出“当前检查范围没有证据”，不能断言整个代码库永远不存在。
- **图示非影响说明**：本文件只更正上游源码研究与排序；accepted ADR 0010、现有实现与将来适配边界不变，因此 `docs/architecture.svg` **无需变更**。当前没有新增支持的后端。

## 6. 恢复与后续开发边界

本 PR 完成后应先为 **wpaperd IPC 验证**和 **Hyprwire v2 客户端验证**分别建独立 issue/plan；在源码与版本研究足够前**不得直接修改 registry、增添外部依赖或实际启动 daemon**。另一个独立任务先抓取 Codeberg awww 源码，修正 `BLOCKED_SOURCE` 并重新比较。

本仓 Issue #83 在本研究通过后仍 OPEN。没有任何本仓的新 per-output backend 已因本报告变成 `IMPLEMENTED`，也没有真实物理像素或 GPU/4K/hotplug 的保证。


### 2026-10-31 补充证据边界（Issue #128）

- **已发布版本，而非仅 GitHub `main`**：Hyprland `v0.57.0` commit `0aa6745f705f2c4b0a5004eb019ef76e5bbdb426` 的 `hyprctl/src/hyprpaper/Hyprpaper.cpp` blob `1d2589ba4a40f751ccb9538acbdc71c869cf9c86`，与本轮检索到的 `4b9ac40...` 一致；hyprpaper `v0.8.4` commit `20fc0fa6c2056c388a4cd69cb394a9f989dd27c0` 的 `IPC.cpp` blob `052b1b5f1bc5684d687ddd05a5673cb0aafda53c`，协议 XML blob `3d26a10211775662709f0af27ecac617150c13fd`。这是**固定源码相互对应**，不是实际二进制/系统组合成功的证据。
- **调用链**：`hyprctl hyprpaper wallpaper 'DP-1,/abs/file.png,cover'` → 客户端解析逗号参数、规范化 path、连接 `.hyprpaper.sock` 并进行 Hyprwire 握手 → `hyprpaper_wallpaper.apply` → daemon `WallpaperMatcher::addState` → success；此时不承诺像素。**独立** `hyprctl hyprpaper listactive` → 另建连接和 `hyprpaper_status` object → server 返回每个 `CWallpaperTarget::m_lastPath` → `monitor: path`；调用方只认可确切目标且路径一致。没有对应 target 时 `listactive` 不一定含该输出，必须失败，而不是将 0 exit 认作成功。
- **负面安全边界**：命令使用 `CVarList2(..., ',')`，不应把任意含逗号的绝对路径直接拼为参数；以 **argv** 调用而非 shell；禁止空 monitor，防止 wildcard；校验所有输出、禁止重复和空输出；对客户端握手/轮询施加真正的**子进程超时**（可终止自己派生的 `hyprctl`，绝不杀 renderer）；固定输出/文件时避免 hyprpaper 自身的多图目录定时器；**已安装旧版 hyprctl** 未证明具有此 v2 client，不能按 wiki 或包名推断。
- **仍未准入运行时**：没有真实 Hyprland + hyprpaper 两输出像素、路径先后时序、热插拔、不同版本包、GPU/4K、真实用户会话证据；`src/backend/registry.rs` 仍只支持 Noctalia 默认 + wpaperd 显式备选。**新增 hyprpaper 运行时选项需单独确认策略**，本报告只纠正源码事实与下阶段验证路线。
